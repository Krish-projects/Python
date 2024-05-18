import datetime
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys 
import time

import Adafruit_BBIO.GPIO as GPIO
import matplotlib.pyplot as plt
import numpy as np

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# print ("Add_Locations.py first call startin at : startupTime",datetime.datetime.now())

#Python files downloaded
#------------
# from Analysed_output import dataAnalyse
from Measurement import Measure
from VirtualKeyboard import VirtualKeyboard

import deviceStatus as DS 
#------------


global addSampleResult
addSampleResult = []

#Class to add new location details
class addLocation(QWidget):
    

    sig_locationDetails = QtCore.pyqtSignal(str, str, str, str, str, str, str)
    sig_addLocation_Close = pyqtSignal()
    sig_AddL_SpectrometerError = pyqtSignal()
    sig_samplerWillNotReturn = pyqtSignal() ### This signal will be used for charger connected

    
    def __init__(self, item1, tailNumber, log_q, workOrder, deviceID, telemetry_q, charger_connected):
        super (addLocation, self).__init__()
        self.log_q = log_q
        self.f_name=item1
        self.A_ID = tailNumber
        self.workOrder = workOrder
        self.regime = workOrder["RegimeInstance"]
        self.deviceID = deviceID
        self.telemetry_q = telemetry_q
        self.data = ''
        self.nextSeatNumber = ""
        self.charger_connected = charger_connected
        
        self.setGeometry(0, 22, 480, 250)
        self.log_q.put(["debug","AL",'************Entering Add Location Module************'])
        self.Area()

        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","AL","charger_connected event cleared... "])
            self.log_q.put(["debug","AL","!!!!!!!! CLOSING ADD LOCATION WINDOW !!!!!!!"])
            self.close_application()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","AL","Timer started"])    

    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","AL","!!!!!!!!!!! EXITING ADD LOCATION PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","AL","Timer stopped"])          

    def close_application(self):
        self.log_q.put(["debug","AL",'Exiting Add locations page due to'+ DS.cause_Of_logout[DS.logout_cause_value]+' '])
        self.sig_samplerWillNotReturn.emit()
        self.timer_and_page_close()
        
    def Area(self):
        """
        Allows the operator to add new location.
        """

        class_lbl = QtWidgets.QLabel("Class", self)
        class_lbl.move(10, 20)
        self.class_btn = QtWidgets.QPushButton("", self)
        self.class_btn.resize(self.class_btn.sizeHint())
        self.class_btn.setStyleSheet("background-color: white;")
        self.class_btn.setGeometry(150, 20, 200, 30)
 
        
        seat_lbl = QtWidgets.QLabel("Seat", self)
        seat_lbl.move(10, 60)
        self.seat_btn = QtWidgets.QPushButton("", self)
        self.seat_btn.resize(self.seat_btn.sizeHint())
        self.seat_btn.setStyleSheet("background-color: white;")
        self.seat_btn.setGeometry(150, 60, 200, 30)

        
        description_lbl = QtWidgets.QLabel("Description", self)
        description_lbl.move(10, 100)
        self.description_btn = QtWidgets.QPushButton("", self)
        self.description_btn.resize(self.description_btn.sizeHint())
        self.description_btn.setStyleSheet("background-color: white;")
        self.description_btn.setGeometry(150, 100, 200, 30)

        
        surface_lbl = QtWidgets.QLabel("Surface", self)
        surface_lbl.move(10, 140)
        self.surface_btn = QtWidgets.QPushButton("", self)
        self.surface_btn.setStyleSheet("background-color: white;")
        self.surface_btn.resize(self.surface_btn.sizeHint())
        self.surface_btn.setGeometry(150, 140, 200, 30)

        notes_lbl = QtWidgets.QLabel("Notes", self)
        notes_lbl.move(10, 180)
        self.notes_box = QtWidgets.QTextEdit(self)
        self.notes_box.move(100, 150)
        self.notes_box.setGeometry(150, 180, 200, 50)
        self.notes_box.setObjectName("textEdit")
        self.notes_box.mousePressEvent = self.VKB5
        
        add_btn = QtWidgets.QPushButton("Add", self)
        add_btn.resize(add_btn.sizeHint())
        add_btn.move(370, 50)       
        add_btn.clicked.connect(self.Add)  
        # add_btn.clicked.connect(self.timer_and_page_close)        

        
        cancel_btn = QtWidgets.QPushButton("Cancel", self)
        cancel_btn.resize(cancel_btn.sizeHint())
        cancel_btn.move(370, 150)
        cancel_btn.clicked.connect(self.close_app1)   
        
        
        self.class_btn.clicked.connect(self.VKB1)
        self.seat_btn.clicked.connect(self.VKB2)
        self.description_btn.clicked.connect(self.VKB3)
        self.surface_btn.clicked.connect(self.VKB4)

        self.keyboard1 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard2 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard3 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard4 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard5 = VirtualKeyboard(self.data, False, self.log_q)
        
        self.keyboard1.sigInputString.connect(self.class_entry)
        self.keyboard2.sigInputString.connect(self.seat_entry)
        self.keyboard3.sigInputString.connect(self.description_entry)
        self.keyboard4.sigInputString.connect(self.surface_entry)        
        self.keyboard5.sigInputString.connect(self.notes_entry)
        
        self.show()
        




    def close_app1(self):
        self.timer_and_page_close()
        self.sig_addLocation_Close.emit()
        

        
#Calls the "Sample acquire class"        
    def run_add(self, item1, item2, item3, item4, item5, item6):
        """
        Performs measurement after adding new location
        """
        self.Class = str(self.class_btn.text())
        self.seatNumber = str(self.seat_btn.text())        
        self.description = str(self.description_btn.text())
        self.surface = str(self.surface_btn.text())
        self.flightno = str(self.f_name)
        self.rego = str(self.A_ID)
        self.timer_and_page_close()                        
        self.startMeasurement = Measure('addLocation', self.seatNumber, self.surface, self.Class, self.description, self.flightno, self.rego, self.workOrder, self.deviceID, self.telemetry_q,self.log_q, self.data, self.nextSeatNumber, self.charger_connected)
        self.startMeasurement.sig_measurementComplete.connect(self.Next)
        self.startMeasurement.sig_windowCancel.connect(self.close_app1)        
        self.startMeasurement.sig_SpectrometerError.connect(self.error)  
        self.startMeasurement.sig_samplerWillNotReturn.connect(self.close_application)
        
    def error(self):
    
        self.sig_AddL_SpectrometerError.emit()
        self.timer_and_page_close()
        
		

#From Add_regime_test file
    def Next(self):
#Result calculation performed in here
        # self.output = dataAnalyse()
        # (self.result, self.confidence, self.error, self.absorbance) = self.output.results()  
        # self.result = int(self.result)
        # self.confidence = int(self.confidence)

        self.emitvalues(str(self.class_btn.text()), str(self.seat_btn.text()), str(self.description_btn.text()), str(self.surface_btn.text()), str(DS.result), str(DS.confidence), str(DS.absorbance))
		


#Adds the location details in the json file        
    def Add(self):
        empty_location = {"Type":"type", "Name":"name", "Description":"description", "surface":"surface"}
                         
        if self.seat_btn.text() == "":

            
            QtWidgets.QMessageBox.warning(self, "No data" ,"Add a Seat number!!!") 
            QtWidgets.qApp.processEvents()
            self.log_q.put(["warning","AL", 'Enter a valid seat number']) 
            self.show()
        else:
            name_strip = []
            name_strip = list(self.seat_btn.text())
            self.log_q.put(["info","SD", 'name_strip %s' % (name_strip)])
            if len(name_strip)<2:
                QtWidgets.QMessageBox.warning(self, "No data" ,"Add a Seat or row number!!!") 
                QtWidgets.qApp.processEvents()
                self.log_q.put(["warning","AL", 'Enter a valid seat number or row number']) 
                self.show()
            else:
            
                self.Class = self.class_btn.text()
                self.seat = self.seat_btn.text()        
                self.description = self.description_btn.text()
                self.surface = self.surface_btn.text()
                self.flightno = str(self.f_name)
                self.rego = str(self.A_ID)
                
                testWorkOrder = self.regime["RegimeLocations"]    
                
                myResults_Add =[]
                myNewLocation = []
                myLocation = empty_location
                myLocation["Class"] = self.Class
                myLocation["Name"] = self.seat
                myLocation["Description"] = self.description
                myLocation["surface"] = self.surface      
                if len(self.workOrder)<=15:
                    pass
                else:
                    myNewLocation.append(myLocation)
                    testWorkOrder.append(myNewLocation)
                
                self.run_add(str(self.class_btn.text()), str(self.seat_btn.text()), str(self.description_btn.text()), str(self.surface_btn.text()), str(self.f_name), str(self.A_ID))
          
         
    def emitvalues(self, i_1, i_2, i_3, i_4, i_5, i_6, i_7):
        """
        Sends signal to the previous page
        """
        self.Class = str(self.class_btn.text())
        self.seatNumber = str(self.seat_btn.text())        
        self.description = str(self.description_btn.text())
        self.surface = str(self.surface_btn.text())
        # self.result = str(DS.result)
        # self.confidence = str(DS.confidence)
        # self.absorbance = str(DS.absorbance)
   
        self.sig_locationDetails.emit(self.Class, self.seatNumber, self.description, self.surface, str(DS.result), str(DS.confidence), str(DS.absorbance))
        self.log_q.put(["info","AL","************Exiting Add location module************"])        
        self.timer_and_page_close()

        
                
        
    def VKB1(self):
        
        if self.keyboard1.isHidden():
            self.log_q.put(["debug","AL", 'Virtual Keyboard enabled to enter Class'])
            self.keyboard1.show()
        else:
            self.keyboard1.hide()
            
    def VKB2(self):
        
        if self.keyboard2.isHidden():
            self.log_q.put(["debug","AL", 'Virtual Keyboard enabled to enter Seat']) 
            self.keyboard2.show()
        else:
            self.keyboard2.hide()
 
    def VKB3(self):
        
        if self.keyboard3.isHidden():
            self.log_q.put(["debug","AL", 'Virtual Keyboard enabled to enter Description'])  
            self.keyboard3.show()
        else:
            self.keyboard3.hide()
            
    def VKB4(self):
        
        if self.keyboard4.isHidden():
            self.log_q.put(["debug","AL", 'Virtual Keyboard enabled to enter Surface'])  
            self.keyboard4.show()
        else:
            self.keyboard4.hide() 
            
    def VKB5(self, event):
        
        if self.keyboard5.isHidden():
            self.log_q.put(["debug","AL", 'Virtual Keyboard enabled to enter Notes']) 
            self.keyboard5.show()
        else:
            self.keyboard5.hide()
        
    def class_entry(self, data):
        self.log_q.put(["info","AL", 'Class: '+data])      
        self.class_btn.setText(data)
        
    def seat_entry(self, data):
        self.log_q.put(["info","AL", 'Seat: '+data])   
        seatNo = list(data)

        if seatNo[0].isdigit():
            self.seat_btn.setText(data)
            
        else:
            QtWidgets.QMessageBox.warning(self, "Enter valid first number" ,"Seat must start with a number. e.g: 11A") 
            QtWidgets.qApp.processEvents()
            
            
        
    def description_entry(self, data):
        self.log_q.put(["info","AL", 'Description: '+data]) 
        self.description_btn.setText(data)
        
    def surface_entry(self, data):
        self.log_q.put(["info","AL", 'Surface: '+data])            
        self.surface_btn.setText(data)  
        
    def notes_entry(self, data):
        self.data = data
        self.log_q.put(["info","AL", 'Notes: '+self.data]) 
        self.notes_box.setText(self.data)          



        