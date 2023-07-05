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

_current_path = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_path)
# Load YoloV5 model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt').to(device)

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

        # Convert center x, center y, width, height to top left x, top left y, width, height
        #x, y, w, h = detections
        #tlx, tly = x - w / 2, y - h / 2

        
        # Print results
        results.print()

        # Draw results on image
        #results_img = results.render()

        # Resize the image
        #desired_size = (800, 600)  # You can adjust this as needed

        # Get the aspect ratio of the image
        #aspect_ratio = results_img[0].shape[1] / results_img[0].shape[0]

       # if(aspect_ratio >= 1):
            # Image is wide
       #     res = int(desired_size[0] / aspect_ratio)  # Width adjusted to maintain aspect ratio
       #     dim = (desired_size[0], res)
      #  else:
            # Image is tall
       #     res = int(desired_size[1] * aspect_ratio)  # Height adjusted to maintain aspect ratio
       #     dim = (res, desired_size[1])

        # Resize the image
      #  resized_image = cv2.resize(results_img[0], dim, interpolation=cv2.INTER_AREA)

        # Display image
       # cv2.imshow('Detection Results', resized_image)
       # cv2.waitKey(0)
       # cv2.destroyAllWindows()
    except Exception as e:
           print(e)
           
    return detected_objects  # Return the list of detected objects
    

# Use the function
path = _current_dir + '\\runs\\train\\exp\\weights\\best.pt'
    # Load image
#image = Image.open('10.jpeg')

# Load an image using OpenCV
#cv_image = cv2.imread('10.jpeg')

#detect_and_draw(cv_image)