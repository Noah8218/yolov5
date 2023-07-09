import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel
from PIL import Image
import cv2
import numpy as np
import torch
from torchvision import transforms
import os
from PIL import Image, ImageFile
import io

# 현재 파일의 절대 경로를 구합니다.
current_path = os.path.dirname(os.path.abspath(__file__))

app_env = os.getenv('APP_ENV', 'development')

# 상대 경로를 절대 경로로 변환합니다.

if app_env == 'development': 
    model_path = os.path.join(current_path, '..', 'yolov5Master')
    weights_path = os.path.join(current_path, '..', 'best.pt')
else:  # production
    model_path = os.path.join(current_path, 'yolov5Master')
    weights_path = os.path.join(current_path, 'best.pt')

import sys
try:
    model = torch.hub.load(model_path, 'custom', source='local', path=weights_path, force_reload=True)
except Exception as e:
    print("Error:", str(e))
    sys.exit(1)

#model = torch.hub.load('D:\Git\yolov5\dist\Program\yolov5Master', 'custom', source ='local', path='best.pt',force_reload=True)

# 모델을 로드합니다.
#model = torch.hub.load(model_path, 'custom', weights_path, source='local')

def detect_and_draw(input_image):    
    # Convert QImage to numpy array
    try:
        detected_objects = [] 
        
        if isinstance(input_image, QImage):
            h = input_image.height()
            w = input_image.width()
            bytes_per_line = input_image.bytesPerLine()
            channels = bytes_per_line // w
            ptr = input_image.bits()
            ptr.setsize(h * bytes_per_line)
            arr = np.frombuffer(ptr, np.uint8).reshape(h, w, channels)

        # Convert QLabel to QImage, then to numpy array
        elif isinstance(input_image, QLabel):
            pixmap = input_image.pixmap()
            if pixmap is not None:
                qimage = pixmap.toImage()
                h = qimage.height()
                w = qimage.width()
                bytes_per_line = qimage.bytesPerLine()
                channels = bytes_per_line // w
                ptr = qimage.bits()
                ptr.setsize(h * bytes_per_line)
                arr = np.frombuffer(ptr, np.uint8).reshape(h, w, channels)
            else:
                print("No image found in QLabel")
                return

        # If image is already a numpy array (OpenCV format)
        elif isinstance(input_image, np.ndarray):
            arr = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
            # Perform detection
            results = model(arr)

        # If image is a PIL Image
        elif isinstance(input_image, ImageFile.ImageFile):
            #arr = np.array(input_image)
            image = input_image
            # Perform detection
            results = model(image)
        else:
            print("Unsupported image type")
            return

        # Get bounding boxes and class information
        detections = results.pandas().xywhn[0]  # xywhn are normalized to 0-1 range

        # Convert xywh from normalized values to pixel values
        h, w = image.size

        # Print xywh and class for each detection
        for _, detection in detections.iterrows():
            x, y, width, height, confidence, class_idx, class_name = detection
            x, y, width, height = x * w, y * h, width * w, height * h  # x, y, width, height in pixel values
            tlx, tly = x - width / 2, y - height / 2  # top-left x, y
            print(f'Class: {class_name}, Confidence: {confidence}, BBox (tlx, tly, w, h): {tlx, tly, width, height}')

            detected_objects.append({
                'className': class_name,
                'confidence': confidence,
                'x': tlx,
                'y': tly,
                'width': width,
                'height': height,
            })
        results.print()
    except Exception as e:
           print(e)
           
    return detected_objects  # Return the list of detected objects
    