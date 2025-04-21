# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 14:06:12 2025

@author: TF
"""
# main_app.py
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from ui_main import Ui_MainWindow

# Signal 정의 클래스
class DataEmitter(QObject):
    updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_label_text)
        self.timer.start(1000)

    def update_label_text(self):
        self.counter += 1
        self.updated.emit(f"Signal 업데이트: {self.counter}")

# 메인 윈도우 클래스
class MyApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.emitter = DataEmitter()
        self.emitter.updated.connect(self.label.setText)

        self.pushButton.clicked.connect(self.handle_click)

    def handle_click(self):
        self.label.setText("버튼이 눌렸습니다!")

app = QApplication(sys.argv)
window = MyApp()
window.show()
sys.exit(app.exec_())