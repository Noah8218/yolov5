import sys, os
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QImage, QPixmap
import UI
from UI.actions import ImageViewer

from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtCore import QThread
from editClass import editClass  # 변환된 UI 파일을 import 합니다.
import yolov5Master.yolov5Defect as yolov5Defect
import tkinter as tk
import asyncio
from Device.asyncClient import Client, on_connect, on_disconnect, on_message, run_classification
from PIL import Image
from PyQt5.QtCore import pyqtSignal
import io

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

_loadPath = resource_path('save.txt')
PATH = resource_path('main.ui')

#UI파일 연결
#단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType(PATH)[0]
VALID_FORMAT = ('.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.PBM', '.PGM', '.PPM', '.TIFF', '.XBM')  # Image formats supported by Qt

class LoopThread(QThread):
    on_message = pyqtSignal(str)  # Signal that will be emitted when a message is received

    def __init__(self, window_class):
        super().__init__()
        self.window_class = window_class

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = Client('localhost', 5000, on_connect, on_disconnect, self.message_received)
        loop.run_until_complete(client.start())
        loop.run_forever()

    def message_received(self, message):
        self.on_message.emit(message)  # Emit signal when a message is received




def getImages(folder):
    ''' Get the names and paths of all the images in a directory. '''
    image_list = []
    if os.path.isdir(folder):
        for file in os.listdir(folder):
            if file.upper().endswith(VALID_FORMAT):
                im_path = os.path.join(folder, file)
                image_obj = {'name': file, 'path': im_path }
                image_list.append(image_obj)
    return image_list

def load_list(file_path):
    with open(file_path, 'r') as file:
        classLists = file.read().splitlines()
    return classLists

def file_exists(file_path):
    return os.path.exists(file_path)

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

#화면을 띄우는데 사용되는 Class 선언
class WindowClass(QMainWindow, form_class) :
    def __init__(self) :
        super().__init__()
        self.setupUi(self)
        
        self.pilImage = Image.new('RGB', (800, 600), 'white')
        self.mainQimage = QImage()
        self.classe_list = list()
        self.image_W = 0
        self.image_H = 0
        self.imageName = ""
        if file_exists(_loadPath):
            self.classe_list = load_list(_loadPath)
            #self.qlist_Classe.clear()
            #for item in self.classe_list:
             #   self.qlist_Classe.addItem(item)
            #print(self.classe_list)  # ['class1', 'class2', 'class3']

        self.image_viewer = ImageViewer(self.qlabel_image, self.lbrect, self.lbMousePos, self.image_W, self.image_H, self.imageName, self.qlist_Classe, self.classe_list)
        self.qlist_images.itemClicked.connect(self.item_click)
        self.open_folder.clicked.connect(self.selectDir)
        self.btnEditLabel.clicked.connect(self.open_edit_class)
        self.btnInfer.clicked.connect(self.RunClassification)
        self.label = QLabel(self)   
        self.initUI() 

        self.loop_thread = LoopThread(self)
        self.loop_thread.on_message.connect(self.RunClassification)  # Connect RunClassification to the on_message signal
        self.loop_thread.start()


    async def RunClassification(self, message):
        if message == 'StartDefect':
            # Convert byte data to a PIL Image object
            image = Image.open(io.BytesIO(message))
            # Run the classification
            h =  image.height
            w =  image.width
            print(image.format)
            yolov5Defect.detect_and_draw(image)

        #property
    def classLists(self):
        return self.classe_list

    #classLists.setter
    def classLists(self, value):
        self.classe_list = value
        self.qlist_Classe.clear()
        for item in self.classe_list:
            self.qlist_Classe.addItem(item)

    def open_edit_class(self):
        self.edit_class_window = editClass(self.qlist_Classe, self.classe_list)  # 새로운 editClass 인스턴스를 생성합니다.
        self.edit_class_window.show()  # editClass를 보여줍니다.         

    def initUI(self):
        self.layout = QVBoxLayout()        
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    def item_click(self, item):
        self.cntr = self.items.index(item)
        self.imageName = item.text()
        self.image_viewer.imageName = self.imageName
        self.image_viewer.loadImage(self.logs[self.cntr]['path'])
        self.mainQimage = QImage(self.logs[self.cntr]['path'])
        self.pilImage = Image.open(self.logs[self.cntr]['path'])
        imag1_size = self.pilImage.size

        print(imag1_size)
    #btn_1이 눌리면 작동할 함수
    def button1Function(self) :
        print("btn_1 Clicked")
    def selectDir(self):
        ''' Select a directory, make list of images in it and display the first image in the list. '''
        # open 'select folder' dialog box
        #self.folder = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', '', 'All File(*);; Image File(*.png *.jpg)')
        
        self.folder = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if not self.folder:
            QMessageBox.warning(self, 'No Folder Selected', 'Please select a valid Folder')
            return
        
        self.logs = getImages(self.folder)
        self.numImages = len(self.logs)

        # make qitems of the image names
        self.items = [QListWidgetItem(log['name']) for log in self.logs]
        for item in self.items:
            self.qlist_images.addItem(item)

        # display first image and enable Pan 
        self.cntr = 0
        self.image_viewer.enablePan(True)
        self.imageName = os.path.basename(self.logs[self.cntr]['path'])
        
        self.image_viewer.imageName = self.imageName
        self.image_viewer.loadImage(self.logs[self.cntr]['path'])
        self.items[self.cntr].setSelected(True)
        #self.qlist_images.setItemSelected(self.items[self.cntr], True)

        # enable the next image button on the gui if multiple images are loaded
        if self.numImages > 1:
            self.next_im.setEnabled(True)

    def OpenFileImage(self):
        fname = QFileDialog.getOpenFileName(self, 'Open File', '', 'All File(*);; Image File(*.png *.jpg)')
        if fname[0]:

            image = QPixmap(fname[0])

            self.label.setPixmap(image)
            self.label.setContentsMargins(10,50,10,10)
            self.label.resize(image.width(), image.height())

        else:
            QMessageBox.about(self, 'warning', '파일을 선택하지 않았습니다.')
        

if __name__ == "__main__" :
    #QApplication : 프로그램을 실행시켜주는 클래스
    app = QApplication(sys.argv) 

    #loop_thread = LoopThread()
    #loop_thread.start()

    #WindowClass의 인스턴스 생성
    myWindow = WindowClass() 
    #프로그램 화면을 보여주는 코드
    myWindow.show()
    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()