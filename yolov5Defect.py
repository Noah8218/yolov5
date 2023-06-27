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
model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt')

def detect_and_draw(input_image):    
    # Convert QImage to numpy array
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

    # If image is a PIL Image
    elif isinstance(input_image, ImageFile.ImageFile):
        arr = np.array(input_image)

    else:
        print("Unsupported image type")
        return

    # Convert the numpy array image to a PIL Image object
    image = Image.fromarray(arr)

    # Perform detection
    results = model(image)

    # Print results
    results.print()

    # Draw results on image
    results_img = results.render()

    # Display image
    cv2.imshow('Detection Results', results_img[0])
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Use the function
path = _current_dir + '\\runs\\train\\exp\\weights\\best.pt'
    # Load image
#image = Image.open('10.jpeg')

# Load an image using OpenCV
#cv_image = cv2.imread('10.jpeg')

#detect_and_draw(cv_image)