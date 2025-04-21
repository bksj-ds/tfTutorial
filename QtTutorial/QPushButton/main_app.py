# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 23:02:45 2025

@author: Fata
"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout
from PyQt5.QtCore import pyqtSignal, QObject

# 1. 시그널 정의용 클래스
class Communicator(QObject):
    custom_clicked = pyqtSignal()

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.comm = Communicator()  # 커뮤니케이터 객체 생성
        self.initUI()

    def initUI(self):
        self.label = QLabel('버튼을 클릭해보세요', self)
        self.btn = QPushButton('시그널 발생', self)

        # 2. QPushButton → 커스텀 시그널 연결
        self.btn.clicked.connect(self.emit_custom_signal)

        # 3. 커스텀 시그널 → 슬롯 함수 연결
        self.comm.custom_clicked.connect(self.custom_action)

        vbox = QVBoxLayout()
        vbox.addWidget(self.label)
        vbox.addWidget(self.btn)
        self.setLayout(vbox)

        self.setWindowTitle('Custom Signal Example')
        self.setGeometry(300, 300, 300, 150)
        self.show()

    def emit_custom_signal(self):
        # 버튼을 누르면 커스텀 시그널을 발생시킴
        self.comm.custom_clicked.emit()

    def custom_action(self):
        # 커스텀 시그널을 수신하면 실행됨
        self.label.setText('커스텀 시그널이 발생했습니다!')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
