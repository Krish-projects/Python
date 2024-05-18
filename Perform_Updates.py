from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
# from PyQt5.QtGui import QPixmap

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import deviceStatus as DS 
import time


class PerformUpdatesGUI(QWidget):

    sig_PerformUpdatesGUI_closed = pyqtSignal()
    
    def __init__(self, log_q, mp_status):
        super(PerformUpdatesGUI,self).__init__()
        self.log_q = log_q
        self.mp_status = mp_status
        PerformUpdatesGUI.setGeometry(self,0, 22, 480, 250)
        self.testmodetitle = self.setWindowTitle("Update Firmware")
        
        self.updateButton = QtWidgets.QPushButton("Start Updates", self)
        self.updateButton.resize(self.updateButton.sizeHint())
        self.updateButton.move(120,80)
        self.updateButton.clicked.connect(self.perform_updates)
        
        self.samplerUpdateStatus = QtWidgets.QLabel("", self)
        self.samplerUpdateStatus.setGeometry(20,120,450,30)
        self.analyserUpdateStatus = QtWidgets.QLabel("", self)
        self.analyserUpdateStatus.setGeometry(20,170,450,30)
        self.log_q.put(["debug","UF","Update Firmware page open"])
        
        self.exitButton = QtWidgets.QPushButton("Close", self)
        self.exitButton.resize(self.exitButton.sizeHint())
        self.exitButton.move(400,210)
        self.exitButton.clicked.connect(self.exitButton_clicked)
        
        if self.mp_status.sampler_req == "":
            self.samplerUpdateStatus.setText("Sampler Update NOT Required")
        else:
            self.samplerUpdateStatus.setText("Sampler Update Required")
        if self.mp_status.firmware_req == "":
            self.analyserUpdateStatus.setText("Analyser Update NOT Required")
        else:
            self.analyserUpdateStatus.setText("Analyser Update Required")
        self.show()
        
 
    def perform_updates(self):
        confirm = QMessageBox.question(self, 'Message',
                    "Are you sure you want to perform updates?", QMessageBox.Yes | 
                    QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            QtWidgets.qApp.processEvents()
            self.mp_status.perform_updates = True
            QtWidgets.qApp.processEvents()
            if not self.mp_status.sampler_req == "":
                self.samplerUpdateStatus.setText("Sampler update in progress")
                while not self.mp_status.sampler_req == "":
                    self.log_q.put(["debug","UP","Updates still pending, waiting"])
                    time.sleep(1)
                if self.mp_status.samplerUpdateStatusGood:
                    self.samplerUpdateStatus.setText("Sampler update complete")
                else:
                    self.samplerUpdateStatus.setText("Sampler update failed, contact Support")
                
            QtWidgets.qApp.processEvents()
            if not self.mp_status.firmware_req == "":
                self.analyserUpdateStatus.setText("Firmware update in progress")
                while not self.mp_status.firmware_req == "" and self.mp_status.perform_updates:
                    self.log_q.put(["debug","UP","Updates still pending, waiting"])
                    QtWidgets.qApp.processEvents()
                    time.sleep(1)
                if self.mp_status.updateStatusGood:
                    self.analyserUpdateStatus.setText("Analyser firmware update complete")
                else:
                    self.analyserUpdateStatus.setText("Analyser update failed, contact Support")
            QtWidgets.qApp.processEvents()


    def exitButton_clicked(self):
        self.log_q.put(["debug","UP", 'Exitting firmware update page'])
        self.close()
        self.sig_PerformUpdatesGUI_closed.emit()        

