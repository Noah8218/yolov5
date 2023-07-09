import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore, QtWidgets
import os
import shutil

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

_loadPath = resource_path('save.txt')
#UI파일 연결
#단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType(resource_path('selectClass.ui'))[0]

_current_path = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_path)

def save_list(classLists, file_path):
    with open(file_path, 'w') as file:
        for item in classLists:
            file.write(f"{item}\n")

#화면을 띄우는데 사용되는 Class 선언
class selectClass(QMainWindow, form_class):
    def __init__(self, main_class_instance=None,  classLists=None, lbRect=None, 
                 image_W=None, image_H=None, imageName=None, qimage_scaled=None) :
        super().__init__()
        self.setupUi(self)
        self.btrnCheck.clicked.connect(self.addListValue)
        self.qlist_Classe.itemClicked.connect(self.list_item_clicked)
        self.btnCancel.clicked.connect(self.close_window)
        self.main_class_instance = main_class_instance if main_class_instance is not None else None
        self.classLists = classLists if classLists is not None else None
        self.lbrect= lbRect if lbRect is not None else None
        self.image_W = image_W if image_W is not None else None
        self.image_H = image_H if image_H is not None else None
        self.imageName = imageName if imageName is not None else None
        self.qimage_scaled = qimage_scaled if qimage_scaled is not None else None

        if self.classLists is not None:
            for item in self.classLists:
                self.qlist_Classe.addItem(item)

    def showmain(self) :
        self.w = QMainWindow()
        self.w.show()

    def list_item_clicked(self, item):
        # When QListWidget item is clicked, set QLineEdit text to item's text
        self.tbName.setText(item.text())

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            selectindex = self.qlist_Classe.selectedItems()
            for index in selectindex:
                self.main_class_instance.takeItem(self.qlist_Classe.row(index))
                self.qlist_Classe.takeItem(self.qlist_Classe.row(index))
                self.classLists.pop(self.qlist_Classe.row(index))
        
            save_list(self.classLists, _loadPath)
        else:
            super().keyPressEvent(event)

    def find_matching_index(self):
        text = self.tbName.text() # line_edit text 값 가져오기

        # Iterate over each item in QListWidget
        for i in range(self.qlist_Classe.count()):
            if self.qlist_Classe.item(i).text() == text:  # If the item text matches QLineEdit text
                return i  # Return the row number
        return -1  # Return -1 if no match found

    def write_to_file(self, index, normalCenterX, normalCenterY, normalW, normalH, filename):
        # Open the file in append mode ('a')
        if os.path.exists(filename):
            with open(filename, 'a') as f:
                # Write the data to the file, separated by spaces
                f.write(f"{index} {normalCenterX} {normalCenterY} {normalW} {normalH}\n")
        else:
            with open(filename, 'w') as f:
                # Write the data to the file, separated by spaces
                f.write(f"{index} {normalCenterX} {normalCenterY} {normalW} {normalH}\n")
     # 버튼 클릭 시 윈도우를 닫는 함수
    def close_window(self):
        self.close()

    def addListValue(self) :
        try:
            index = self.find_matching_index()

            s = self.lbrect.text()
            values = s.replace('Rect (', '').replace(')', '').split(', ')
            rect_x = int(values[0].split(':')[1])
            rect_y = int(values[1].split(':')[1])
            rect_w = int(values[2].split(':')[1])
            rect_h = int(values[3].split(':')[1])
            rect_centerX = rect_x + (rect_w/2)
            rect_centerY = rect_y + (rect_h/2)

            normalCenterX = rect_centerX / self.image_W
            normalCenterY = rect_centerY / self.image_H
            normalW = rect_w / self.image_W
            normalH = rect_h / self.image_H
            # You can then use this function like this:
            saveImagePath = _current_dir + '\\data\\train\\images\\' + self.imageName
            filename_without_ext = os.path.splitext(self.imageName)[0]
            output = _current_dir + '\\data\\train\\labels\\' + filename_without_ext +'.txt'
            self.qimage_scaled.save(saveImagePath)
            self.write_to_file(index, normalCenterX, normalCenterY, normalW, normalH, output)

            self.close()
        except Exception as e:                             # 예외가 발생했을 때 실행됨
            print('예외가 발생했습니다.', e)    


if __name__ == "__main__" :
    #QApplication : 프로그램을 실행시켜주는 클래스
    app = QApplication(sys.argv) 

    #WindowClass의 인스턴스 생성
    myWindow = selectClass() 

    #프로그램 화면을 보여주는 코드
    myWindow.show()

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()