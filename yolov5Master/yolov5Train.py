import os
import yaml
from glob import glob
import subprocess
import sys

# 실행 파일의 경로
exe_dir = os.path.dirname(os.path.abspath(sys.executable))

# data 폴더 경로
data_dir = os.path.join(exe_dir, 'data')

# train, val 폴더 경로
train_dir = os.path.join(data_dir, 'train')
val_dir = os.path.join(data_dir, 'valid')

# images, labels 폴더 경로
train_images_dir = os.path.join(train_dir, 'images')
train_labels_dir = os.path.join(train_dir, 'labels')
val_images_dir = os.path.join(val_dir, 'images')
val_labels_dir = os.path.join(val_dir, 'labels')

# data 폴더 및 하위 폴더들이 없는 경우 생성
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
if not os.path.exists(train_dir):
    os.makedirs(train_dir)
if not os.path.exists(val_dir):
    os.makedirs(val_dir)
if not os.path.exists(train_images_dir):
    os.makedirs(train_images_dir)
if not os.path.exists(train_labels_dir):
    os.makedirs(train_labels_dir)
if not os.path.exists(val_images_dir):
    os.makedirs(val_images_dir)
if not os.path.exists(val_labels_dir):
    os.makedirs(val_labels_dir)

current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

app_env = os.getenv('APP_ENV', 'development')

# 상대 경로를 절대 경로로 변환합니다.


# 현재 스크립트 파일의 경로를 얻습니다.
current_path = os.path.dirname(os.path.abspath(sys.argv[0]))

# train.py 파일의 경로
train_script = os.path.join(current_path, 'train.py')

# data.yaml 파일의 경로

current_path2 = os.path.dirname(os.path.abspath(__file__))

if app_env == 'development': 
    data_yaml = os.path.join(current_path2, '..', 'data.yaml')
else:  # production
    data_yaml = os.path.join(current_path2, 'data.yaml')

def RunYolov5Train():
    subprocess.run(['python', train_script, '--img', '160', '--batch', '32', '--epochs', '50', '--data', data_yaml, '--cfg', 'yolov5m.yaml', '--weights', 'yolov5m.pt', '--device', '0'])

RunYolov5Train()

# YOLOv5 학습 스크립트를 호출합니다.
        # 이 코드는 'python train.py --img 640 --batch 16 --epochs 3 --data coco128.yaml --weights yolov5s.pt' 명령을 실행합니다.
#subprocess.run(['python', 'train.py', '--img', '320', '--batch', '16', '--epochs', '500', '--data', 'data.yaml', '--cfg', 'yolov5m.yaml', '--weights', 'yolov5m.pt', '--device', '0'])
#python train.py --img 320 --batch 16 --epochs 500 --data data.yaml --cfg yolov5m.yaml --weights yolov5m.pt --device 0

# YOLOv5 추론 스크립트를 호출합니다.
# 이 코드는 'python detect.py --weights yolov5s.pt --img 640 --conf 0.25 --source data/images/' 명령을 실행합니다.
#subprocess.run(['python', 'detect.py', '--weights', 'yolov5s.pt', '--img', '640', '--conf', '0.25', '--source', 'data/images/'])
