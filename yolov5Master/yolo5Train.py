import os
import yaml
from glob import glob
import subprocess

current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

def create_yaml(train_images, val_images, class_names, output_yaml_path):
    # Create a dictionary with the necessary information for the yaml file
    data = {
        'val': val_images,
        'nc': len(class_names),
        'names': class_names
    }

    # Write the dictionary to a yaml file
    with open(output_yaml_path, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

# YOLOv5 학습 스크립트를 호출합니다.
        # 이 코드는 'python train.py --img 640 --batch 16 --epochs 3 --data coco128.yaml --weights yolov5s.pt' 명령을 실행합니다.
#subprocess.run(['python', 'train.py', '--img', '320', '--batch', '16', '--epochs', '50', '--data', 'data.yaml', '--cfg', 'yolov5m.yaml', '--weights', 'yolov5m.pt', '--device', '0'])


# YOLOv5 추론 스크립트를 호출합니다.
# 이 코드는 'python detect.py --weights yolov5s.pt --img 640 --conf 0.25 --source data/images/' 명령을 실행합니다.
#subprocess.run(['python', 'detect.py', '--weights', 'yolov5s.pt', '--img', '640', '--conf', '0.25', '--source', 'data/images/'])


# 이미지 경로 list로 넣기
#train_img_list = glob('./train/images/*.jpg') + glob('./train/images/*.jpeg') + glob('./train/images/*.png')
#valid_img_list = glob('./valid/images/*.jpg') + glob('./valid/images/*.jpeg') + glob('./train/images/*.png')


# txt 파일에 write
#with open('./train.txt', 'w') as f:
	#f.write('\n'.join(train_img_list) + '\n')
    
#with open('./valid.txt', 'w') as f:
	#f.write('\n'.join(valid_img_list) + '\n')

output = '\\output.yaml'
output_Path = current_dir + output

trainPath = current_dir + '\\train.txt'
vaildPath = current_dir + '\\valid.txt'

# Example usage:
#create_yaml(trainPath, vaildPath, ['camera', 'class2'], output_Path)