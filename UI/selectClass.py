import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore, QtWidgets
import os

current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)

PATH = current_dir +"\\selectClass.ui"

#UI파일 연결
#단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType(PATH)[0]

_current_path = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_path)
_loadPath = _current_dir + '\\save.txt'

def save_list(classLists, file_path):
    with open(file_path, 'w') as file:
        for item in classLists:
            file.write(f"{item}\n")

#화면을 띄우는데 사용되는 Class 선언
class selectClass(QMainWindow, form_class):
    def __init__(self, main_class_instance,  classLists, lbRect, image_W, image_H, imageName, qimage_scaled) :
        super().__init__()
        self.setupUi(self)  # UI 파일에서 정의한 위젯들을 초기화합니다.
        self.btrnCheck.clicked.connect(self.addListValue)
        self.qlist_Classe.itemClicked.connect(self.list_item_clicked)
        self.btnCancel.clicked.connect(self.close_window)
        self.main_class_instance = main_class_instance
        self.classLists = classLists
        self.lbrect= lbRect
        self.image_W = image_W
        self.image_H = image_H
        self.imageName = imageName
        self.qimage_scaled = qimage_scaled

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