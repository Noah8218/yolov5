# YOLOv5 Labeling Worker

라벨링 프로그램에서 호출하는 Python YOLO worker입니다.

기본 기준:

- 프로젝트 위치: `C:\Git\yolov5`
- 가중치: `best.pt`
- 샘플 이미지: `data\train\images`
- 실행 Python: `.venv\Scripts\python.exe`

## 처음 실행

```bat
launchers\setup-yolo-worker.bat
```

이 명령은 `.venv`를 만들고 `requirements.txt` 기준으로 필요한 패키지를 설치합니다.

설치만 다시 확인하려면:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launchers\ensure-yolo-environment.ps1
```

패키지가 빠져 있으면 설치까지 같이 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launchers\ensure-yolo-environment.ps1 -InstallIfMissing
```

## 바로 추론 테스트

```bat
launchers\smoke-test-yolo-worker.bat
```

정상이라면 `Teaching_0.jpeg`로 `best.pt`를 로드하고 JSON 결과를 출력합니다.
`ok: true`, `candidates`가 보이면 라벨링 앱에서도 테스트 추론이 가능한 상태입니다.

## 라벨링 앱에서 쓰는 파일

```text
best.pt
data\train\images\Teaching_0.jpeg
labelling_tcp_client.py
yolov5Master\
launchers\start-yolo-tcp-client.ps1
launchers\smoke-test-yolo-worker.bat
```

`best.pt`와 `data\train\images`가 없으면 라벨링 앱의 `첫점검` 또는 `테스트`에서 실패합니다.

## Worker 직접 실행

라벨링 앱 없이 worker를 TCP client로 띄울 때:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launchers\start-yolo-tcp-client.ps1
```

라벨링 앱에서 `AI 검출`을 누르면 보통 이 worker를 자동으로 실행합니다.

## C# 런처

라벨링 앱에서 exe 런처를 사용할 때 필요한 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launchers\build-yolo-tcp-client-launcher.ps1
```

결과:

```text
dist\YoloTcpClientLauncher\YoloTcpClientLauncher.exe
```

## 문제가 날 때

- `.venv` 없음: `launchers\setup-yolo-worker.bat`
- 패키지 누락: `ensure-yolo-environment.ps1 -InstallIfMissing`
- `best.pt` 없음: 이 저장소 루트에 `best.pt` 확인
- 샘플 이미지 없음: `data\train\images` 확인
- 라벨링 앱 연결 실패: 앱에서 `학습 준비 > 첫점검 > 테스트` 순서로 확인

YOLO 학습/검출 코드는 Python이 담당하고, 라벨 저장과 후보 확정은 C# 라벨링 앱이 담당합니다.
