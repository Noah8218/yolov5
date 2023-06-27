from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.QtCore import Qt, QPoint, QRect
import selectClass

__author__ = "Atinderpal Singh"
__license__ = "MIT"
__version__ = "1.0"
__email__ = "atinderpalap@gmail.com"

class ImageViewer:
    ''' Basic image viewer class to show an image with zoom and pan functionaities.
        Requirement: Qt's Qlabel widget name where the image will be drawn/displayed.
    '''
    def __init__(self, qlabel, lbRect, lbPos, image_W, image_H, imageName, main_class_instance, classLists):
        self.qlabel_image = qlabel                            # widget/window name where image is displayed (I'm usiing qlabel)
        self.qimage_scaled = QImage()                         # scaled image to fit to the size of qlabel_image
        self.qpixmap = QPixmap()                              # qpixmap to fill the qlabel_image
        self.lbrect= lbRect
        self.lbpos = lbPos
        self.image_W = image_W
        self.image_H = image_H
        self.imageName = imageName
        self.main_class_instance = main_class_instance
        self.classLists = classLists

        for item in self.classLists:
            self.main_class_instance.addItem(item)

        self.zoomX = 1              # zoom factor w.r.t size of qlabel_image
        self.position = [0, 0]      # position of top left corner of qimage_label w.r.t. qimage_scaled
        self.panFlag = False        # to enable or disable pan

        self.qlabel_image.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.__connectEvents()

        self.rect_start = None
        self.rect_end = None
        self.rect = None

    def __connectEvents(self):
        # Mouse events
        self.qlabel_image.mousePressEvent = self.mousePressAction
        self.qlabel_image.mouseMoveEvent = self.mouseMoveAction
        self.qlabel_image.mouseReleaseEvent = self.mouseReleaseAction        

    def onResize(self):
        ''' things to do when qlabel_image is resized '''
        self.qpixmap = QPixmap(self.qlabel_image.size())
        self.qpixmap.fill(QtCore.Qt.gray)
        self.qimage_scaled = self.qimage.scaled(self.qlabel_image.width() * self.zoomX, self.qlabel_image.height() * self.zoomX, QtCore.Qt.KeepAspectRatio)
        self.update()

    def loadImage(self, imagePath):
        ''' To load and display new image.'''
        self.qimage = QImage(imagePath)
        self.qpixmap = QPixmap(self.qlabel_image.size())
        if not self.qimage.isNull():
            # reset Zoom factor and Pan position
            self.zoomX = 1
            self.position = [0, 0]
            self.qimage_scaled = self.qimage.scaled(self.qlabel_image.width(), self.qlabel_image.height(), QtCore.Qt.KeepAspectRatio)
            self.update()     
            self.image_W = self.qimage_scaled.width()       
            self.image_H = self.qimage_scaled.height()       
        else:
            self.statusbar.showMessage('Cannot open this image! Try another one.', 5000)

    def update(self):
        ''' This function actually draws the scaled image to the qlabel_image.
            It will be repeatedly called when zooming or panning.
            So, I tried to include only the necessary operations required just for these tasks. 
        '''
        if not self.qimage_scaled.isNull():
            # check if position is within limits to prevent unbounded panning.
            px, py = self.position
            px = px if (px <= self.qimage_scaled.width() - self.qlabel_image.width()) else (self.qimage_scaled.width() - self.qlabel_image.width())
            py = py if (py <= self.qimage_scaled.height() - self.qlabel_image.height()) else (self.qimage_scaled.height() - self.qlabel_image.height())
            px = px if (px >= 0) else 0
            py = py if (py >= 0) else 0
            self.position = (px, py)            
            if self.zoomX == 1:
                self.qpixmap.fill(QtCore.Qt.white)

            # the act of painting the qpixamp
            painter = QPainter()
            painter.begin(self.qpixmap)
            painter.drawImage(QtCore.QPoint(0, 0), self.qimage_scaled,
                    QtCore.QRect(self.position[0], self.position[1], self.qlabel_image.width(), self.qlabel_image.height()))
            if self.rect_start is not None and self.rect_end is not None:
                painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                painter.drawRect(QtCore.QRect(self.rect_start, self.rect_end))
            painter.end()

            self.qlabel_image.setPixmap(self.qpixmap)
        else:
            pass

    def mousePressAction(self, QMouseEvent):
        x, y = QMouseEvent.pos().x(), QMouseEvent.pos().y()
        if self.panFlag:
            self.pressed = QMouseEvent.pos()
            self.anchor = self.position
        self.rect_start = QMouseEvent.pos()
        self.rect_end = QMouseEvent.pos()

    def mouseMoveAction(self, QMouseEvent):
        x, y = QMouseEvent.pos().x(), QMouseEvent.pos().y()
        # Update the label with the current mouse position
        self.lbpos.setText(f"X: {x}, Y: {y}")

        if self.pressed:
            dx, dy = x - self.pressed.x(), y - self.pressed.y()
            self.position = self.anchor[0] - dx, self.anchor[1] - dy
            self.update()
        self.rect_end = QMouseEvent.pos()
        self.update()

        self.rect = QtCore.QRect(self.rect_start, self.rect_end)
        rect_x = self.rect.x()
        rect_y = self.rect.y()
        rect_w = self.rect.width()
        rect_h = self.rect.height()
        self.lbrect.setText(f"Rect (X:{rect_x}, Y:{rect_y}, W:{rect_w}, H:{rect_h})")

    def mouseReleaseAction(self, QMouseEvent):
        self.pressed = None
        self.rect_start = None
        self.rect_end = None

        self.edit_class_window = selectClass.selectClass(self.main_class_instance, self.classLists, self.lbrect, self.image_W, self.image_H, self.imageName, self.qimage_scaled)  # 새로운 editClass 인스턴스를 생성합니다.
        self.edit_class_window.show()  # editClass를 보여줍니다. 

    def zoomPlus(self):
        self.zoomX += 1
        px, py = self.position
        px += self.qlabel_image.width()/2
        py += self.qlabel_image.height()/2
        self.position = (px, py)
        self.qimage_scaled = self.qimage.scaled(self.qlabel_image.width() * self.zoomX, self.qlabel_image.height() * self.zoomX, QtCore.Qt.KeepAspectRatio)
        self.update()

    def zoomMinus(self):
        if self.zoomX > 1:
            self.zoomX -= 1
            px, py = self.position
            px -= self.qlabel_image.width()/2
            py -= self.qlabel_image.height()/2
            self.position = (px, py)
            self.qimage_scaled = self.qimage.scaled(self.qlabel_image.width() * self.zoomX, self.qlabel_image.height() * self.zoomX, QtCore.Qt.KeepAspectRatio)
            self.update()

    def resetZoom(self):
        self.zoomX = 1
        self.position = [0, 0]
        self.qimage_scaled = self.qimage.scaled(self.qlabel_image.width() * self.zoomX, self.qlabel_image.height() * self.zoomX, QtCore.Qt.KeepAspectRatio)
        self.update()

    def enablePan(self, value):
        self.panFlag = value

