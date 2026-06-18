# YOLOv5 Labeling AI Worker

이 프로젝트는 C# 라벨링 앱에서 실행하는 헤드리스 YOLOv5 AI Worker입니다. Python 쪽은 UI를 만들지 않고, TCP 메시지를 받아 모델 상태 확인, 이미지 검출, 학습 실행만 담당합니다. 라벨 저장과 클래스 관리는 C# 앱이 담당하며 Python은 후보 검출 결과만 반환합니다.

## 구성

- `labeling_tcp_client.py`: C# 앱과 통신하는 메인 AI Worker
- `labelling_tcp_client.py`: 기존 파일명을 위한 호환 래퍼
- `best.pt`: 기본 검출 가중치
- `yolov5Master/`: YOLOv5 학습/검출 코드
- `launchers/start-yolo-worker.bat`: C# 또는 사용자가 실행할 수 있는 BAT 런처
- `launchers/start-yolo-tcp-client.ps1`: PowerShell 런처
- `tools/YoloTcpClientLauncher/`: C# 앱에서 실행 가능한 exe 런처 소스

## 실행

Python 가상환경은 기본적으로 `C:\Git\yolov5\.venv`를 사용합니다.

```powershell
& "C:\Git\yolov5\.venv\Scripts\python.exe" "C:\Git\yolov5\labeling_tcp_client.py" `
  --host 127.0.0.1 `
  --port 5000 `
  --weights "C:\Git\yolov5\best.pt" `
  --model-root "C:\Git\yolov5\yolov5Master" `
  --image-root "C:\Git\py\KtemData" `
  --conf 0.25 `
  --retry
```

BAT 런처:

```bat
C:\Git\yolov5\launchers\start-yolo-worker.bat
```

exe 런처 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Git\yolov5\launchers\build-yolo-tcp-client-launcher.ps1"
```

빌드 후 실행 파일:

```text
C:\Git\yolov5\dist\YoloTcpClientLauncher\YoloTcpClientLauncher.exe
```

exe 런처는 다음 옵션을 받을 수 있습니다.

```text
--project-root C:\Git\yolov5
--host 127.0.0.1
--port 5000
--weights C:\Git\yolov5\best.pt
--model-root C:\Git\yolov5\yolov5Master
--image-root C:\Git\py\KtemData
--conf 0.25
--device 0
--preload
```

## Smoke Test

파서/응답 구조만 확인:

```powershell
& "C:\Git\yolov5\.venv\Scripts\python.exe" "C:\Git\yolov5\labeling_tcp_client.py" --self-test
```

`best.pt`와 이미지 경로로 실제 모델 로딩 및 검출 확인:

```powershell
C:\Git\yolov5\launchers\smoke-test-yolo-worker.bat "C:\Git\py\KtemData\Teaching_0.bmp"
```

직접 실행:

```powershell
& "C:\Git\yolov5\.venv\Scripts\python.exe" "C:\Git\yolov5\labeling_tcp_client.py" `
  --smoke-test `
  --weights "C:\Git\yolov5\best.pt" `
  --model-root "C:\Git\yolov5\yolov5Master" `
  --image "C:\Git\py\KtemData\Teaching_0.bmp"
```

## TCP Protocol

AI Worker는 C# TCP 서버에 클라이언트로 접속합니다. 기본 주소는 `127.0.0.1:5000`입니다.

기본 프로토콜은 UTF-8 JSON Lines입니다. C# 앱은 JSON 객체 1개를 한 줄로 보내고 마지막에 `\n`을 붙입니다. Python 응답도 JSON 객체 1개와 `\n`입니다.

모든 요청은 가능한 한 `requestId`를 포함해야 합니다. `DetectImage`는 `imageId`도 포함해야 합니다. Python은 응답에 같은 `requestId`와 `imageId`를 그대로 돌려주므로 C# 앱에서 비동기 응답 매칭에 사용할 수 있습니다.

공통 응답 필드:

```json
{
  "type": "DetectImageResult",
  "version": 1,
  "requestId": "req-001",
  "imageId": "img-001",
  "ok": true
}
```

오류 형식:

```json
{
  "ok": false,
  "error": {
    "code": "DetectImageFailed",
    "message": "Image file not found: C:\\missing.bmp",
    "exceptionType": "FileNotFoundError",
    "details": {}
  }
}
```

### HealthCheck

요청:

```json
{"type":"HealthCheck","requestId":"req-health-001"}
```

응답: `HealthCheckResult`

```json
{
  "type": "HealthCheckResult",
  "version": 1,
  "requestId": "req-health-001",
  "ok": true,
  "state": "ready",
  "worker": {"name": "yolov5-labeling-ai-worker", "pid": 1234},
  "model": {"state": "notLoaded", "loaded": false},
  "tasks": []
}
```

### ModelStatus

현재 모델 상태만 조회:

```json
{"type":"ModelStatus","requestId":"req-model-001"}
```

모델 로딩까지 수행:

```json
{"type":"ModelStatus","requestId":"req-model-002","load":true}
```

응답: `ModelStatusResult`

`model.state`는 `notLoaded`, `loading`, `ready`, `error` 중 하나입니다. 로딩 실패 시 `model.lastError`와 최상위 `error`에 structured JSON 오류가 들어갑니다.

### DetectImage

이미지 경로 기반 검출 요청:

```json
{
  "type": "DetectImage",
  "requestId": "req-detect-001",
  "imageId": "img-001",
  "imagePath": "C:\\Git\\py\\KtemData\\Teaching_0.bmp"
}
```

상대 경로를 보내면 Worker의 `--image-root` 기준으로 해석합니다.

응답: `DetectImageResult`

```json
{
  "type": "DetectImageResult",
  "version": 1,
  "requestId": "req-detect-001",
  "imageId": "img-001",
  "ok": true,
  "elapsedMs": 120,
  "image": {"path": "C:\\Git\\py\\KtemData\\Teaching_0.bmp", "width": 1920, "height": 1080},
  "candidates": [
    {
      "candidateId": "det-0",
      "classId": 0,
      "className": "NG",
      "confidence": 0.92,
      "x": 10.0,
      "y": 20.0,
      "width": 100.0,
      "height": 80.0,
      "bbox": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 80.0},
      "normalizedBbox": {"x": 0.0052, "y": 0.0185, "width": 0.052, "height": 0.074}
    }
  ]
}
```

Python은 이 후보 목록만 반환합니다. 라벨 파일 저장, 확정 라벨 관리, 클래스 편집은 C# 앱에서 처리합니다.

### TrainYolo

학습은 백그라운드 프로세스로 실행됩니다. 요청을 받으면 즉시 `TrainYoloResult`를 반환하고, 진행/완료 상태는 `TaskStatus` 메시지로 추가 전송합니다.

요청:

```json
{
  "type": "TrainYolo",
  "requestId": "req-train-001",
  "taskId": "train-001",
  "dataYaml": "C:\\Git\\yolov5\\data.yaml",
  "weights": "C:\\Git\\yolov5\\best.pt",
  "imgSize": 640,
  "batchSize": 8,
  "epochs": 100,
  "device": "0",
  "project": "C:\\Git\\yolov5\\runs\\train",
  "name": "labeling"
}
```

즉시 응답:

```json
{
  "type": "TrainYoloResult",
  "version": 1,
  "requestId": "req-train-001",
  "ok": true,
  "taskId": "train-001",
  "state": "started"
}
```

상태 이벤트:

```json
{
  "type": "TaskStatus",
  "version": 1,
  "requestId": "req-train-001",
  "taskId": "train-001",
  "taskType": "TrainYolo",
  "state": "completed",
  "exitCode": 0,
  "logTail": []
}
```

동시에 하나의 학습 작업만 실행합니다. 이미 학습 중이면 `TaskAlreadyRunning` 오류를 반환합니다.

### StopTask

학습 중지 요청:

```json
{"type":"StopTask","requestId":"req-stop-001","taskId":"train-001"}
```

응답:

```json
{
  "type": "StopTaskResult",
  "version": 1,
  "requestId": "req-stop-001",
  "ok": true,
  "taskId": "train-001",
  "state": "stopping"
}
```

## Legacy Compatibility

기존 `StartDefect`, `StartTraining`, `StopDefect`, `StopTraining` 패킷도 읽을 수 있도록 유지했습니다. 신규 C# 앱은 JSON Lines 프로토콜과 `HealthCheck`, `ModelStatus`, `DetectImage`, `TrainYolo`, `StopTask` 메시지를 사용하는 것을 권장합니다.

## Dependency Note

이 레거시 YOLOv5 코드는 `pkg_resources`를 사용하므로 `setuptools<81`을 유지해야 합니다. `requirements.txt`에 해당 조건이 포함되어 있습니다.
