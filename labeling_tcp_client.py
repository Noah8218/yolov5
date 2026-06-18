#!/usr/bin/env python3
"""Headless YOLOv5 AI worker for the C# labeling application.

The worker connects to the C# TCP listener, receives JSON messages, loads the
configured YOLOv5 model on demand, returns detection candidates, and can launch
YOLOv5 training as a background task. It intentionally contains no UI logic.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Callable, Iterable

from PIL import Image


PACKET_SEPARATOR = b"\n\n"
PNG_IEND_MARKER = b"IEND"
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_ROOT = SCRIPT_ROOT / "yolov5Master"
DEFAULT_WEIGHTS = SCRIPT_ROOT / "best.pt"
DEFAULT_IMAGE_ROOT = SCRIPT_ROOT.parent / "py" / "KtemData"
DEFAULT_DATA_YAML = SCRIPT_ROOT / "data.yaml"

LEGACY_TYPE_MAP = {
    "StartDefect": "DetectImage",
    "StartTraining": "TrainYolo",
    "StopDefect": "StopTask",
    "StopTraining": "StopTask",
}


@dataclass
class IncomingMessage:
    message_type: str
    request_id: str = ""
    image_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    binary_payload: bytes = b""
    raw_type: str = ""
    legacy: bool = False


@dataclass
class TrainTask:
    task_id: str
    request_id: str
    command: list[str]
    cwd: Path
    process: subprocess.Popen[str]
    started_at_utc: str
    state: str = "running"
    stop_requested: bool = False
    finished_at_utc: str | None = None
    exit_code: int | None = None
    log_tail: deque[str] = field(default_factory=lambda: deque(maxlen=80))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def compact_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def make_error(code: str, message: str | Exception, details: dict[str, Any] | None = None, include_trace: bool = False) -> dict[str, Any]:
    if isinstance(message, Exception):
        exc = message
        error: dict[str, Any] = {
            "code": code,
            "message": str(exc),
            "exceptionType": type(exc).__name__,
        }
        if include_trace:
            error["trace"] = traceback.format_exc()
    else:
        error = {"code": code, "message": str(message)}

    if details:
        error["details"] = details
    return error


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def get_first(payload: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        value = payload.get(name)
        if value is not None and value != "":
            return value
    return default


def resolve_path(value: Any, base_dir: Path | None = None) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()
    if base_dir is not None:
        return (base_dir / path).resolve()
    return path.resolve()


def collect_environment_diagnostics(model_root: Path, weights: Path, image_root: Path, data_yaml: Path) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "cwd": os.getcwd(),
        "scriptRoot": str(SCRIPT_ROOT),
        "modelRoot": str(model_root),
        "modelRootExists": model_root.exists(),
        "weightsPath": str(weights),
        "weightsExists": weights.exists(),
        "imageRoot": str(image_root),
        "imageRootExists": image_root.exists(),
        "dataYaml": str(data_yaml),
        "dataYamlExists": data_yaml.exists(),
        "torchInstalled": False,
        "torchVersion": "",
        "cudaAvailable": False,
        "cudaDeviceCount": 0,
    }

    try:
        import torch

        diagnostics["torchInstalled"] = True
        diagnostics["torchVersion"] = str(getattr(torch, "__version__", ""))
        diagnostics["cudaAvailable"] = bool(torch.cuda.is_available())
        diagnostics["cudaDeviceCount"] = int(torch.cuda.device_count()) if hasattr(torch.cuda, "device_count") else 0
    except Exception as exc:
        diagnostics["torchError"] = str(exc)

    return diagnostics


class JsonResponseWriter:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.lock = threading.Lock()

    def send(self, envelope: dict[str, Any]) -> None:
        envelope.setdefault("version", 1)
        data = compact_json(envelope) + b"\n"
        with self.lock:
            self.sock.sendall(data)


class YoloDetector:
    def __init__(self, model_root: Path, weights: Path, device: str, img_size: int, conf: float, iou: float, debug: bool = False):
        self.model_root = model_root
        self.weights = weights
        self.device = device
        self.img_size = img_size
        self.conf = conf
        self.iou = iou
        self.debug = debug
        self.model: Any = None
        self.state = "notLoaded"
        self.last_error: dict[str, Any] | None = None
        self.loaded_at_utc: str | None = None
        self.load_started_at_utc: str | None = None
        self.load_ms: int | None = None
        self.class_names: list[str] = []
        self.lock = threading.Lock()

    def load(self) -> Any:
        with self.lock:
            if self.model is not None:
                return self.model

            self.state = "loading"
            self.last_error = None
            self.load_started_at_utc = utc_now()
            started = time.perf_counter()

            try:
                if not self.model_root.exists():
                    raise FileNotFoundError(f"YOLOv5 model root not found: {self.model_root}")
                if not self.weights.exists():
                    raise FileNotFoundError(f"YOLOv5 weights not found: {self.weights}")

                if str(self.model_root) not in sys.path:
                    sys.path.insert(0, str(self.model_root))

                import torch

                patch_torch_load_for_yolov5(torch)
                model = torch.hub.load(
                    str(self.model_root),
                    "custom",
                    path=str(self.weights),
                    source="local",
                    force_reload=False,
                )
                if self.device:
                    model.to(self.device)
                model.conf = self.conf
                model.iou = self.iou

                self.model = model
                self.state = "ready"
                self.loaded_at_utc = utc_now()
                self.load_ms = int((time.perf_counter() - started) * 1000)
                self.class_names = self._read_class_names(model)
                return model
            except Exception as exc:
                self.model = None
                self.state = "error"
                self.load_ms = int((time.perf_counter() - started) * 1000)
                self.last_error = make_error("ModelLoadFailed", exc, include_trace=self.debug)
                raise

    def reset_weights(self, weights: Path) -> None:
        with self.lock:
            self.weights = weights
            self.model = None
            self.state = "notLoaded"
            self.last_error = None
            self.loaded_at_utc = None
            self.load_started_at_utc = None
            self.load_ms = None
            self.class_names = []

    def status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "loaded": self.model is not None,
            "modelRoot": str(self.model_root),
            "weightsPath": str(self.weights),
            "weightsExists": self.weights.exists(),
            "device": self.device,
            "imgSize": self.img_size,
            "conf": self.conf,
            "iou": self.iou,
            "loadedAtUtc": self.loaded_at_utc,
            "loadStartedAtUtc": self.load_started_at_utc,
            "loadMs": self.load_ms,
            "classNames": self.class_names,
            "lastError": self.last_error,
        }

    def detect_path(self, image_path: Path, confidence: float | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        image = Image.open(image_path).convert("RGB")
        image.load()
        detections = self.detect_image(image, confidence=confidence)
        return detections, {
            "path": str(image_path),
            "width": image.width,
            "height": image.height,
        }

    def detect_bytes(self, image_bytes: bytes, confidence: float | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image.load()
        detections = self.detect_image(image, confidence=confidence)
        return detections, {
            "path": "",
            "width": image.width,
            "height": image.height,
        }

    def detect_image(self, image: Image.Image, confidence: float | None = None) -> list[dict[str, Any]]:
        model = self.load()
        old_conf = getattr(model, "conf", None)
        if confidence is not None:
            model.conf = max(0.0, min(1.0, float(confidence)))

        try:
            results = model(image, size=self.img_size)
        finally:
            if confidence is not None and old_conf is not None:
                model.conf = old_conf

        table = results.pandas().xyxy[0]
        image_width, image_height = image.size
        detections: list[dict[str, Any]] = []

        for index, row in table.iterrows():
            x1 = max(0.0, float(row["xmin"]))
            y1 = max(0.0, float(row["ymin"]))
            x2 = max(0.0, float(row["xmax"]))
            y2 = max(0.0, float(row["ymax"]))
            width = max(0.0, x2 - x1)
            height = max(0.0, y2 - y1)
            class_value = row.get("class", None)
            class_id = self._to_int_or_none(class_value)
            class_name = str(row.get("name", ""))
            confidence = float(row.get("confidence", 0) or 0)

            detections.append(
                {
                    "candidateId": f"det-{index}",
                    "classId": class_id,
                    "className": class_name,
                    "confidence": confidence,
                    "x": x1,
                    "y": y1,
                    "width": width,
                    "height": height,
                    "bbox": {
                        "x": x1,
                        "y": y1,
                        "width": width,
                        "height": height,
                    },
                    "normalizedBbox": {
                        "x": x1 / image_width if image_width else 0,
                        "y": y1 / image_height if image_height else 0,
                        "width": width / image_width if image_width else 0,
                        "height": height / image_height if image_height else 0,
                    },
                }
            )

        return detections

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        try:
            if value is None or value != value:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _read_class_names(model: Any) -> list[str]:
        names = getattr(model, "names", [])
        if isinstance(names, dict):
            return [str(names[key]) for key in sorted(names.keys())]
        if isinstance(names, (list, tuple)):
            return [str(name) for name in names]
        return []


class TaskManager:
    def __init__(self, model_root: Path, default_data_yaml: Path, default_device: str, debug: bool = False):
        self.model_root = model_root
        self.default_data_yaml = default_data_yaml
        self.default_device = default_device
        self.debug = debug
        self.lock = threading.Lock()
        self.tasks: dict[str, TrainTask] = {}

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return [self._task_status(task) for task in self.tasks.values()]

    def start_train(self, message: IncomingMessage, detector: YoloDetector, writer: JsonResponseWriter | None) -> dict[str, Any]:
        payload = message.payload
        with self.lock:
            active = [task for task in self.tasks.values() if task.process.poll() is None]
            if active:
                task = active[0]
                return {
                    "type": "TrainYoloResult",
                    "requestId": message.request_id,
                    "ok": False,
                    "taskId": task.task_id,
                    "error": make_error("TaskAlreadyRunning", "A training task is already running.", {"activeTaskId": task.task_id}),
                }

        try:
            command = self._build_train_command(payload, detector)
            env = os.environ.copy()
            env["GIT_PYTHON_REFRESH"] = "quiet"
            env["PYTHONPATH"] = os.pathsep.join([str(self.model_root), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            process = subprocess.Popen(
                command,
                cwd=str(self.model_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except Exception as exc:
            return {
                "type": "TrainYoloResult",
                "requestId": message.request_id,
                "ok": False,
                "error": make_error("TrainStartFailed", exc, include_trace=self.debug),
            }

        task_id = str(get_first(payload, ["taskId"], uuid.uuid4().hex))
        task = TrainTask(
            task_id=task_id,
            request_id=message.request_id,
            command=command,
            cwd=self.model_root,
            process=process,
            started_at_utc=utc_now(),
        )

        with self.lock:
            self.tasks[task_id] = task

        thread = threading.Thread(target=self._monitor_train_task, args=(task, writer), daemon=True)
        thread.start()

        return {
            "type": "TrainYoloResult",
            "requestId": message.request_id,
            "ok": True,
            "taskId": task_id,
            "state": "started",
            "command": command,
            "startedAtUtc": task.started_at_utc,
        }

    def stop_task(self, request_id: str, task_id: str = "", task_type: str = "") -> dict[str, Any]:
        task = self._find_stoppable_task(task_id, task_type)
        if task is None:
            return {
                "type": "StopTaskResult",
                "requestId": request_id,
                "ok": False,
                "taskId": task_id,
                "error": make_error("TaskNotFound", "No running task matched the stop request."),
            }

        with self.lock:
            task.stop_requested = True
            task.state = "stopping"

        if task.process.poll() is None:
            task.process.terminate()

        return {
            "type": "StopTaskResult",
            "requestId": request_id,
            "ok": True,
            "taskId": task.task_id,
            "state": "stopping",
        }

    def stop_all(self) -> None:
        with self.lock:
            tasks = list(self.tasks.values())
        for task in tasks:
            if task.process.poll() is None:
                task.stop_requested = True
                task.process.terminate()

    def _find_stoppable_task(self, task_id: str, task_type: str) -> TrainTask | None:
        normalized_type = task_type.lower()
        with self.lock:
            if task_id:
                task = self.tasks.get(task_id)
                if task and task.process.poll() is None:
                    return task
                return None

            for task in self.tasks.values():
                if task.process.poll() is not None:
                    continue
                if not normalized_type or normalized_type in {"train", "training", "trainyolo"}:
                    return task
        return None

    def _monitor_train_task(self, task: TrainTask, writer: JsonResponseWriter | None) -> None:
        self._send_task_status(task, writer, "running", "YOLOv5 training started.")

        assert task.process.stdout is not None
        for line in task.process.stdout:
            clean = line.rstrip()
            if clean:
                task.log_tail.append(clean)
                print(f"[train:{task.task_id}] {clean}", flush=True)

        exit_code = task.process.wait()
        task.exit_code = exit_code
        task.finished_at_utc = utc_now()

        if task.stop_requested:
            task.state = "stopped"
            message = "YOLOv5 training stopped."
        elif exit_code == 0:
            task.state = "completed"
            message = "YOLOv5 training completed."
        else:
            task.state = "failed"
            message = "YOLOv5 training failed."

        self._send_task_status(task, writer, task.state, message)

    def _send_task_status(self, task: TrainTask, writer: JsonResponseWriter | None, state: str, message: str) -> None:
        if writer is None:
            return
        try:
            writer.send(
                {
                    "type": "TaskStatus",
                    "requestId": task.request_id,
                    "taskId": task.task_id,
                    "taskType": "TrainYolo",
                    "state": state,
                    "message": message,
                    "startedAtUtc": task.started_at_utc,
                    "finishedAtUtc": task.finished_at_utc,
                    "exitCode": task.exit_code,
                    "logTail": list(task.log_tail)[-20:],
                }
            )
        except OSError as exc:
            print(f"failed to send task status: {exc}", flush=True)

    def _task_status(self, task: TrainTask) -> dict[str, Any]:
        return {
            "taskId": task.task_id,
            "taskType": "TrainYolo",
            "requestId": task.request_id,
            "state": task.state,
            "startedAtUtc": task.started_at_utc,
            "finishedAtUtc": task.finished_at_utc,
            "exitCode": task.exit_code,
        }

    def _build_train_command(self, payload: dict[str, Any], detector: YoloDetector) -> list[str]:
        train_script = self.model_root / "train.py"
        if not train_script.exists():
            raise FileNotFoundError(f"YOLOv5 train.py not found: {train_script}")

        data_yaml = resolve_path(get_first(payload, ["dataYaml", "data", "datasetYaml"], self.default_data_yaml), SCRIPT_ROOT)
        if not data_yaml.exists():
            raise FileNotFoundError(f"YOLO data YAML not found: {data_yaml}")

        img_size = str(get_first(payload, ["imgSize", "imgsz", "img"], detector.img_size))
        batch_size = str(get_first(payload, ["batchSize", "batch"], 16))
        epochs = str(get_first(payload, ["epochs", "epoch"], 100))
        device = str(get_first(payload, ["device"], self.default_device))
        weights_value = get_first(payload, ["weights", "weightsPath"], detector.weights)
        cfg_value = get_first(payload, ["cfg", "cfgPath"], "")
        hyp_value = get_first(payload, ["hyp", "hypPath"], "")
        project_value = get_first(payload, ["project", "projectPath"], "")
        name_value = get_first(payload, ["name", "runName"], "")
        workers_value = get_first(payload, ["workers"], "")

        command = [
            sys.executable,
            str(train_script),
            "--imgsz",
            img_size,
            "--batch-size",
            batch_size,
            "--epochs",
            epochs,
            "--data",
            str(data_yaml),
        ]

        if as_bool(payload.get("trainFromScratch", False)):
            command.extend(["--weights", ""])
        elif weights_value is not None:
            weights = resolve_path(weights_value, SCRIPT_ROOT)
            if not weights.exists():
                raise FileNotFoundError(f"YOLO weights not found: {weights}")
            command.extend(["--weights", str(weights)])

        if cfg_value:
            cfg = self._resolve_yolo_file(cfg_value)
            if not cfg.exists():
                raise FileNotFoundError(f"YOLO cfg not found: {cfg}")
            command.extend(["--cfg", str(cfg)])

        if hyp_value:
            hyp = self._resolve_yolo_file(hyp_value)
            if not hyp.exists():
                raise FileNotFoundError(f"YOLO hyp file not found: {hyp}")
            command.extend(["--hyp", str(hyp)])

        if device:
            command.extend(["--device", device])
        if project_value:
            command.extend(["--project", str(resolve_path(project_value, SCRIPT_ROOT))])
        if name_value:
            command.extend(["--name", str(name_value)])
        if as_bool(payload.get("existOk", payload.get("exist_ok", False))):
            command.append("--exist-ok")
        if workers_value != "":
            command.extend(["--workers", str(workers_value)])

        cache_value = payload.get("cache")
        if cache_value is not None and cache_value is not False:
            command.append("--cache")
            if isinstance(cache_value, str) and cache_value.lower() not in {"true", "1", "yes"}:
                command.append(cache_value)

        return command

    def _resolve_yolo_file(self, value: Any) -> Path:
        path = Path(str(value))
        if path.is_absolute():
            return path.resolve()
        candidates = [
            self.model_root / path,
            self.model_root / "models" / path,
            self.model_root / "data" / path,
            SCRIPT_ROOT / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return (self.model_root / path).resolve()


class LabelingAiWorker:
    def __init__(self, detector: YoloDetector, task_manager: TaskManager, image_root: Path, writer: JsonResponseWriter | None = None, debug: bool = False):
        self.detector = detector
        self.task_manager = task_manager
        self.image_root = image_root
        self.writer = writer
        self.debug = debug
        self.started_at_utc = utc_now()
        self.handlers: dict[str, Callable[[IncomingMessage], dict[str, Any]]] = {
            "HealthCheck": self.handle_health_check,
            "ModelStatus": self.handle_model_status,
            "DetectImage": self.handle_detect_image,
            "TrainYolo": self.handle_train_yolo,
            "StopTask": self.handle_stop_task,
            "InvalidMessage": self.handle_invalid_message,
        }

    def handle(self, message: IncomingMessage) -> dict[str, Any]:
        handler = self.handlers.get(message.message_type)
        if handler is None:
            return {
                "type": "Error",
                "requestId": message.request_id,
                "imageId": message.image_id,
                "ok": False,
                "error": make_error("UnknownMessageType", f"Unsupported message type: {message.raw_type or message.message_type}"),
            }

        try:
            return handler(message)
        except Exception as exc:
            return {
                "type": "Error",
                "requestId": message.request_id,
                "imageId": message.image_id,
                "ok": False,
                "error": make_error("UnhandledWorkerError", exc, include_trace=self.debug),
            }

    def shutdown(self) -> None:
        self.task_manager.stop_all()

    def handle_health_check(self, message: IncomingMessage) -> dict[str, Any]:
        return {
            "type": "HealthCheckResult",
            "requestId": message.request_id,
            "ok": True,
            "state": "ready",
            "worker": {
                "name": "yolov5-labeling-ai-worker",
                "pid": os.getpid(),
                "startedAtUtc": self.started_at_utc,
                "nowUtc": utc_now(),
            },
            "environment": collect_environment_diagnostics(
                self.detector.model_root,
                self.detector.weights,
                self.image_root,
                DEFAULT_DATA_YAML,
            ),
            "model": self.detector.status(),
            "tasks": self.task_manager.snapshot(),
        }

    def handle_model_status(self, message: IncomingMessage) -> dict[str, Any]:
        if as_bool(message.payload.get("load", False)) or as_bool(message.payload.get("ensureLoaded", False)):
            try:
                self.detector.load()
            except Exception:
                pass

        status = self.detector.status()
        return {
            "type": "ModelStatusResult",
            "requestId": message.request_id,
            "ok": status["state"] == "ready",
            "model": status,
            "error": status["lastError"],
        }

    def handle_detect_image(self, message: IncomingMessage) -> dict[str, Any]:
        image_id = message.image_id or str(get_first(message.payload, ["imageId"], ""))
        confidence = self._resolve_confidence(message.payload)
        started = time.perf_counter()

        try:
            if message.binary_payload:
                detections, image_info = self.detector.detect_bytes(message.binary_payload, confidence=confidence)
            else:
                image_bytes_b64 = get_first(message.payload, ["imageBytesBase64", "imageBase64"], "")
                if image_bytes_b64:
                    detections, image_info = self.detector.detect_bytes(
                        base64.b64decode(str(image_bytes_b64), validate=True),
                        confidence=confidence,
                    )
                else:
                    image_path_value = get_first(message.payload, ["imagePath", "path", "filePath"], "")
                    if not image_path_value:
                        raise ValueError("DetectImage requires imagePath or imageBytesBase64.")
                    image_path = self._resolve_image_path(image_path_value)
                    if not image_id:
                        image_id = image_path.stem
                    detections, image_info = self.detector.detect_path(image_path, confidence=confidence)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if message.legacy:
                return {
                    "type": "ResultDefect",
                    "requestId": message.request_id,
                    "imageId": image_id,
                    "items": detections,
                    "error": "",
                }

            return {
                "type": "DetectImageResult",
                "requestId": message.request_id,
                "imageId": image_id,
                "ok": True,
                "elapsedMs": elapsed_ms,
                "image": image_info,
                "model": self.detector.status(),
                "candidates": detections,
            }
        except Exception as exc:
            error = make_error("DetectImageFailed", exc, include_trace=self.debug)
            if message.legacy:
                return {
                    "type": "ResultDefect",
                    "requestId": message.request_id,
                    "imageId": image_id,
                    "items": [],
                    "error": error["message"],
                    "structuredError": error,
                }
            return {
                "type": "DetectImageResult",
                "requestId": message.request_id,
                "imageId": image_id,
                "ok": False,
                "candidates": [],
                "model": self.detector.status(),
                "error": error,
            }

    def handle_train_yolo(self, message: IncomingMessage) -> dict[str, Any]:
        return self.task_manager.start_train(message, self.detector, self.writer)

    def handle_stop_task(self, message: IncomingMessage) -> dict[str, Any]:
        payload = message.payload
        task_id = str(get_first(payload, ["taskId"], ""))
        task_type = str(get_first(payload, ["taskType", "type"], ""))
        if message.raw_type == "StopTraining":
            task_type = "TrainYolo"
        return self.task_manager.stop_task(message.request_id, task_id=task_id, task_type=task_type)

    def handle_invalid_message(self, message: IncomingMessage) -> dict[str, Any]:
        return {
            "type": "Error",
            "requestId": message.request_id,
            "imageId": message.image_id,
            "ok": False,
            "error": message.payload.get("error") or make_error("InvalidMessage", "Invalid message."),
        }

    def _resolve_image_path(self, value: Any) -> Path:
        path = Path(str(value)).expanduser()
        if path.is_absolute():
            return path.resolve()
        if path.exists():
            return path.resolve()
        return (self.image_root / path).resolve()

    def _resolve_confidence(self, payload: dict[str, Any]) -> float | None:
        value = get_first(payload, ["confidence", "conf", "threshold", "minimumConfidence"], None)
        if value is None:
            return None

        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return None


def patch_torch_load_for_yolov5(torch_module: Any) -> None:
    """YOLOv5 checkpoints need full pickle loading on PyTorch 2.6+."""

    if getattr(torch_module.load, "_labeling_app_compat", False):
        return

    original_load = torch_module.load

    def load_with_legacy_checkpoint_default(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    load_with_legacy_checkpoint_default._labeling_app_compat = True
    torch_module.load = load_with_legacy_checkpoint_default


def parse_messages(buffer: bytearray) -> Iterable[IncomingMessage]:
    while True:
        while buffer and buffer[0] in b"\r\n\t ":
            del buffer[0]

        if not buffer:
            return

        if buffer.startswith(b"{"):
            line_break = buffer.find(b"\n")
            if line_break < 0:
                return
            line = bytes(buffer[:line_break]).strip()
            del buffer[: line_break + 1]
            if not line:
                continue
            yield parse_json_line_message(line)
            continue

        separator_index = buffer.find(PACKET_SEPARATOR)
        if separator_index < 0:
            return

        command = buffer[:separator_index].decode("ascii", errors="replace").strip()
        payload_start = separator_index + len(PACKET_SEPARATOR)
        packet_length = find_legacy_packet_end(command, buffer, payload_start)
        if packet_length < 0:
            return

        payload = bytes(buffer[payload_start:packet_length])
        del buffer[:packet_length]
        yield parse_legacy_message(command, payload)


def parse_json_line_message(line: bytes) -> IncomingMessage:
    try:
        payload = json.loads(line.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON message must be an object.")
        raw_type = str(get_first(payload, ["type", "messageType", "command", "action"], ""))
        if not raw_type:
            raise ValueError("JSON message requires type.")
        message_type = LEGACY_TYPE_MAP.get(raw_type, raw_type)
        return IncomingMessage(
            message_type=message_type,
            request_id=str(get_first(payload, ["requestId"], "")),
            image_id=str(get_first(payload, ["imageId"], "")),
            payload=payload,
            raw_type=raw_type,
            legacy=raw_type in LEGACY_TYPE_MAP,
        )
    except Exception as exc:
        return IncomingMessage(
            message_type="InvalidMessage",
            payload={"error": make_error("InvalidJson", exc)},
            raw_type="InvalidMessage",
        )


def parse_legacy_message(command: str, payload_bytes: bytes) -> IncomingMessage:
    message_type = LEGACY_TYPE_MAP.get(command, command)
    payload: dict[str, Any] = {}
    binary_payload = b""

    if payload_bytes:
        if command in {"StartDefect"}:
            binary_payload = payload_bytes
        else:
            try:
                decoded = json.loads(payload_bytes.decode("utf-8"))
                if isinstance(decoded, dict):
                    payload = decoded
            except Exception as exc:
                payload = {"_parseError": make_error("InvalidLegacyPayload", exc)}

    request_id = str(get_first(payload, ["requestId"], ""))
    image_id = str(get_first(payload, ["imageId"], ""))
    return IncomingMessage(
        message_type=message_type,
        request_id=request_id,
        image_id=image_id,
        payload=payload,
        binary_payload=binary_payload,
        raw_type=command,
        legacy=True,
    )


def find_legacy_packet_end(command: str, buffer: bytearray, payload_start: int) -> int:
    if command == "StartDefect":
        return find_png_packet_end(buffer, payload_start)
    if command in {"StartTraining", "TrainYolo", "DetectImage", "ModelStatus"}:
        if payload_start >= len(buffer):
            return payload_start
        return find_json_packet_end(buffer, payload_start)
    if command in {"StopTraining", "StopDefect", "StopTask", "HealthCheck"}:
        return payload_start
    return find_line_packet_end(buffer)


def find_json_packet_end(buffer: bytearray, start: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    saw_open = False

    for index in range(start, len(buffer)):
        char = chr(buffer[index])
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char.isspace() and not saw_open:
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            saw_open = True
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return index + 1

    return -1


def find_png_packet_end(buffer: bytearray, start: int) -> int:
    marker_index = buffer.find(PNG_IEND_MARKER, start)
    if marker_index < 0:
        return -1
    return marker_index + len(PNG_IEND_MARKER) + 4


def find_line_packet_end(buffer: bytearray) -> int:
    line_break = buffer.find(b"\n")
    return line_break + 1 if line_break >= 0 else -1


def build_detector(args: argparse.Namespace) -> YoloDetector:
    return YoloDetector(
        model_root=Path(args.model_root).resolve(),
        weights=Path(args.weights).resolve(),
        device=args.device,
        img_size=args.img_size,
        conf=args.conf,
        iou=args.iou,
        debug=args.debug,
    )


def build_task_manager(args: argparse.Namespace) -> TaskManager:
    return TaskManager(
        model_root=Path(args.model_root).resolve(),
        default_data_yaml=Path(args.data_yaml).resolve(),
        default_device=args.device,
        debug=args.debug,
    )


def run_client(args: argparse.Namespace) -> int:
    detector = build_detector(args)
    task_manager = build_task_manager(args)

    if args.preload:
        try:
            detector.load()
            print(compact_json({"type": "ModelStatusResult", "ok": True, "model": detector.status()}).decode("utf-8"), flush=True)
        except Exception as exc:
            print(compact_json({"type": "ModelStatusResult", "ok": False, "model": detector.status(), "error": make_error("ModelLoadFailed", exc)}).decode("utf-8"), flush=True)

    while True:
        try:
            with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
                print(f"connected to labeling app at {args.host}:{args.port}", flush=True)
                sock.settimeout(args.timeout)
                writer = JsonResponseWriter(sock)
                worker = LabelingAiWorker(detector, task_manager, Path(args.image_root).resolve(), writer=writer, debug=args.debug)
                try:
                    return read_loop(sock, args, worker, writer)
                finally:
                    worker.shutdown()
        except OSError as exc:
            if not args.retry:
                print(f"connect failed: {exc}", flush=True)
                return 1
            print(f"connect failed: {exc}; retrying in {args.retry_delay}s", flush=True)
            time.sleep(args.retry_delay)


def read_loop(sock: socket.socket, args: argparse.Namespace, worker: LabelingAiWorker, writer: JsonResponseWriter) -> int:
    buffer = bytearray()
    handled = 0

    while True:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            continue

        if not chunk:
            print("labeling app closed connection", flush=True)
            return 0

        buffer.extend(chunk)
        for message in parse_messages(buffer):
            handled += 1
            response = worker.handle(message)
            writer.send(response)

            if args.once and handled >= 1:
                return 0


def run_smoke_test(args: argparse.Namespace) -> int:
    detector = build_detector(args)
    image_path_value = args.detect_file or args.image
    if not image_path_value:
        print(compact_json({"type": "SmokeTestResult", "ok": False, "error": make_error("MissingImagePath", "--smoke-test requires --image or --detect-file.")}).decode("utf-8"), flush=True)
        return 2

    image_path = resolve_image_path_for_cli(image_path_value, Path(args.image_root).resolve())
    started = time.perf_counter()
    log_tail: list[str] = []
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    try:
        if args.debug:
            detections, image_info = detector.detect_path(image_path)
        else:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                detections, image_info = detector.detect_path(image_path)
            log_tail = tail_lines(stdout_buffer.getvalue(), stderr_buffer.getvalue())

        result = {
            "type": "SmokeTestResult",
            "requestId": "smoke-test",
            "imageId": image_path.stem,
            "ok": True,
            "elapsedMs": int((time.perf_counter() - started) * 1000),
            "weightsPath": str(Path(args.weights).resolve()),
            "image": image_info,
            "model": detector.status(),
            "candidates": detections,
            "logTail": log_tail,
        }
        print(compact_json(result).decode("utf-8"), flush=True)
        return 0
    except Exception as exc:
        if not args.debug:
            log_tail = tail_lines(stdout_buffer.getvalue(), stderr_buffer.getvalue())
        result = {
            "type": "SmokeTestResult",
            "requestId": "smoke-test",
            "imageId": image_path.stem,
            "ok": False,
            "weightsPath": str(Path(args.weights).resolve()),
            "image": {"path": str(image_path)},
            "model": detector.status(),
            "logTail": log_tail,
            "error": make_error("SmokeTestFailed", exc, include_trace=args.debug),
        }
        print(compact_json(result).decode("utf-8"), flush=True)
        return 1


def run_self_test() -> int:
    json_messages = (
        b'{"type":"HealthCheck","requestId":"req-health"}\n'
        b'{"type":"ModelStatus","requestId":"req-model"}\n'
        b'{"type":"DetectImage","requestId":"req-detect","imageId":"img-1","imagePath":"sample.bmp"}\n'
    )
    training = b'StartTraining\n\n{"requestId":"req-train","imgSize":640,"batchSize":8,"epochs":1,"dataYaml":"C:/data/data.yaml"}'
    image = b"StartDefect\n\n\x89PNG\r\n\x1a\nmock-data" + PNG_IEND_MARKER + b"\x00\x00\x00\x00"
    buffer = bytearray(json_messages + training + image)
    messages = list(parse_messages(buffer))

    assert len(messages) == 5, f"expected 5 messages, got {len(messages)}"
    assert messages[0].message_type == "HealthCheck"
    assert messages[1].message_type == "ModelStatus"
    assert messages[2].message_type == "DetectImage"
    assert messages[2].request_id == "req-detect"
    assert messages[2].image_id == "img-1"
    assert messages[3].message_type == "TrainYolo"
    assert messages[3].request_id == "req-train"
    assert messages[4].message_type == "DetectImage"
    assert messages[4].legacy
    assert messages[4].binary_payload.startswith(b"\x89PNG")
    assert not buffer

    status = json.loads(compact_json({"type": "HealthCheckResult", "requestId": "req-health", "ok": True}))
    assert status["requestId"] == "req-health"

    print("self-test passed", flush=True)
    return 0


def resolve_image_path_for_cli(value: Any, image_root: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()
    if path.exists():
        return path.resolve()
    return (image_root / path).resolve()


def tail_lines(*values: str, limit: int = 30) -> list[str]:
    lines: list[str] = []
    for value in values:
        lines.extend(line.strip() for line in value.splitlines() if line.strip())
    return lines[-limit:]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv5 TCP AI worker for the C# labeling app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--model-root", default=str(DEFAULT_MODEL_ROOT))
    parser.add_argument("--image-root", default=str(DEFAULT_IMAGE_ROOT))
    parser.add_argument("--data-yaml", default=str(DEFAULT_DATA_YAML))
    parser.add_argument("--device", default="")
    parser.add_argument("--img-size", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--retry-delay", type=float, default=3)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preload", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--detect-file", default="")
    parser.add_argument("--image", default="")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()
    if args.smoke_test or args.detect_file or args.image:
        return run_smoke_test(args)
    return run_client(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
