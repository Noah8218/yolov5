from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore, QtWidgets
import sys
import os
import shutil

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

#UI파일 연결
#단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType(resource_path('editClass.ui'))[0]

_current_path = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_path)
_loadPath = _current_dir + '\\save.txt'
_loadPath = resource_path('save.txt')


def save_list(classLists, file_path):
    with open(file_path, 'w') as file:
        for item in classLists:
            file.write(f"{item}\n")

#화면을 띄우는데 사용되는 Class 선언
class editClass(QMainWindow, form_class):
    def __init__(self, main_class_instance=None, classLists=None):
        super().__init__()
        self.setupUi(self)  # UI 파일에서 정의한 위젯들을 초기화합니다.
        self.btrnCheck.clicked.connect(self.addListValue)
        self.btnCancel.clicked.connect(self.close_window)
        self.main_class_instance = main_class_instance if main_class_instance is not None else None
        self.classLists = classLists if classLists is not None else []

        if self.classLists:
            for item in self.classLists:
                self.qlist_Classe.addItem(item)

    def showmain(self) :
        self.w = QMainWindow()
        self.w.show()
     # 버튼 클릭 시 윈도우를 닫는 함수
    def close_window(self):
        self.close()

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

    def addListValue(self) :
        text = self.tbName.text() # line_edit text 값 가져오기
        self.qlist_Classe.clear()
        self.classLists.append(text)
        for item in self.classLists:
            self.qlist_Classe.addItem(item)

        self.main_class_instance.clear()
        for item in self.classLists:
            self.main_class_instance.addItem(item)

        save_list(self.classLists, _loadPath)

if __name__ == "__main__" :
    #QApplication : 프로그램을 실행시켜주는 클래스
    app = QApplication(sys.argv) 

    #WindowClass의 인스턴스 생성
    myWindow = editClass() 

    #프로그램 화면을 보여주는 코드
    myWindow.show()

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()