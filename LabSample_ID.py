
import sys 
import time
import datetime


# print ("LabSample_ID.py first call startin at : startupTime",datetime.datetime.now())



from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from VirtualKeyboard import VirtualKeyboard

import deviceStatus as DS 




class labID(QWidget):
    sig_labID = pyqtSignal()
    sig_labIDCancelled = pyqtSignal()
    def __init__(self, log_q):
        """
        Prompts the operator to enter the Labsample ID
        """
        super(labID, self).__init__()
        labID.setGeometry(self,0, 22, 480, 250)

        self.log_q = log_q
        data = ''
        
        self.keyboard1 = VirtualKeyboard(data, False, log_q)
        self.keyboard1.sigInputString.connect(self.idnumber)


        
        self.titleText = QtWidgets.QLabel("Enter the ID number of the Vial", self)
        self.titleText.setGeometry(QtCore.QRect(50, 40, 400, 20))
        self.titleText.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))

        ID_number = QtWidgets.QLabel("Vial ID", self)
        ID_number.move(50, 100)
        self.ID_number = QtWidgets.QPushButton("", self)
        self.ID_number.resize(self.ID_number.sizeHint())
        self.ID_number.setStyleSheet("background-color: white;")
        self.ID_number.setGeometry(140, 100, 150, 30)

        self.ID_number.clicked.connect(self.VKB1)
        
     
        
        self.ok = QtWidgets.QPushButton("OK", self)
        self.ok.move(150,150)
        self.ok.resize(self.ok.minimumSizeHint())
        self.ok.clicked.connect(self.OK_pressed)
        
        self.ok = QtWidgets.QPushButton("Cancel", self)
        self.ok.move(250,150)
        self.ok.resize(self.ok.minimumSizeHint())
        self.ok.clicked.connect(self.close_application)


        
    def VKB1(self):
        
        if self.keyboard1.isHidden():
            self.log_q.put(["debug", "LS", 'Virtual Keyboard enabled'])
            self.keyboard1.show()
        else:
            self.keyboard1.hide()
    def idnumber(self, data):
        self.log_q.put(["info","LS", 'Vial ID: '+data])            
        self.ID_number.setText(data) 

    def OK_pressed(self):
        DS.analyserLabSampleID = str(self.ID_number.text())
        DS.analyserLabSampleCount += 1     
        self.log_q.put(["info", "LS", 'Vial ID entered and OK pressed'])        
        self.close()
        self.sig_labID.emit()            
        
    def close_application(self):
        QtWidgets.qApp.processEvents()
        self.log_q.put(["warning", "LS", 'Vial ID not entered and CANCEL pressed'])  
        self.close()
        self.sig_labIDCancelled.emit()

        



    
