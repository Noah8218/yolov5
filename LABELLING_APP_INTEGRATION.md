# Labeling App Integration

This folder is the YOLOv5 AI Worker runtime for the C# labeling app.

Current C# integration:

- The C# app sends JSON Lines requests for `HealthCheck`, `ModelStatus`, and `DetectImage`.
- `DetectImage` includes `requestId`, `imageId`, `imagePath`, and `confidence`.
- Python returns `DetectImageResult` with the same `requestId`/`imageId`; the C# app uses those values to reject stale detection results.
- Legacy `StartDefect`, `StartTraining`, `StopDefect`, and `StopTraining` packets remain supported for compatibility. C# falls back to legacy `StartDefect` only when an image path is not available.
- The Python worker applies per-request `confidence` as the YOLO inference threshold when it is provided.
- `HealthCheckResult.environment` reports Python executable/version, torch version, CUDA availability, model root, weights, image root, and `data.yaml` existence so the C# app can show worker diagnostics.

Default paths:

- Project root: `C:\Git\yolov5`
- TCP worker: `C:\Git\yolov5\labeling_tcp_client.py`
- Legacy wrapper: `C:\Git\yolov5\labelling_tcp_client.py`
- Weights: `C:\Git\yolov5\best.pt`
- Image root for relative paths: `data\train\images`
- YOLOv5 root: `C:\Git\yolov5\yolov5Master`

Setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\launchers\ensure-yolo-environment.ps1" -InstallIfMissing
```

Worker launcher also checks `.venv` and `requirements.txt` before startup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\launchers\start-yolo-tcp-client.ps1"
```

Manual run:

```powershell
& ".\.venv\Scripts\python.exe" .\labeling_tcp_client.py --retry --weights ".\best.pt" --model-root ".\yolov5Master" --image-root ".\data\train\images"
```

Parser smoke test:

```powershell
& ".\.venv\Scripts\python.exe" .\labeling_tcp_client.py --self-test
```

Single-image model smoke test:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\launchers\smoke-test-yolo-worker.ps1"
```

C# launcher source:

```text
tools\YoloTcpClientLauncher
```

Build launcher exe:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\launchers\build-yolo-tcp-client-launcher.ps1"
```
