import datetime
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys 
import time


from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# print ("Editlocationdetails.py first call startin at : startupTime",datetime.datetime.now())

from VirtualKeyboard import VirtualKeyboard

import deviceStatus as DS




class edit_locationDetails(QWidget):
    sig_editComplete = pyqtSignal(str, str, str, str, str)
    sig_workorder_Complete = pyqtSignal(str, str)
    sig_editClose = pyqtSignal()
    sig_charger_connected = pyqtSignal()
    
    def __init__(self, log_q, window, seat, description, surface, Class, data, charger_connected):
        super(edit_locationDetails, self).__init__()
        edit_locationDetails.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q
        self.seat = seat
        self.description = description
        self.surface = surface
        self.Class = Class
        self.window = window
        self.data = data
        self.edit = False
        self.site = ''
        self.airline = ''
        self.flight = ''
        self.rego = ''
        self.workorderid = '' 
        self.charger_connected = charger_connected
        self.start_process = True   
        if self.window == "Edit":
            
            self.edit = True
            
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
            self.notes_box.setText(self.data)
            
            add_btn = QtWidgets.QPushButton("Update", self)
            add_btn.resize(add_btn.sizeHint())
            add_btn.move(370, 50)       
            add_btn.clicked.connect(self.addComplete_Close)  
            # add_btn.clicked.connect(self.close)        

            
            cancel_btn = QtWidgets.QPushButton("Cancel", self)
            cancel_btn.resize(cancel_btn.sizeHint())
            cancel_btn.move(370, 150)
            cancel_btn.clicked.connect(self.close_app1)   
            
            self.class_btn.setText(self.Class)
            self.seat_btn.setText(self.seat)
            self.description_btn.setText(self.description)
            self.surface_btn.setText(self.surface)
            
            
            self.class_btn.clicked.connect(self.VKB1)
            self.seat_btn.clicked.connect(self.VKB2)
            self.description_btn.clicked.connect(self.VKB3)
            self.surface_btn.clicked.connect(self.VKB4)        
            
            self.keyboard_1 = VirtualKeyboard(self.Class, False, log_q)
            self.keyboard_2 = VirtualKeyboard(self.seat, False, log_q)
            self.keyboard_3 = VirtualKeyboard(self.description, False, log_q)
            self.keyboard_4 = VirtualKeyboard(self.surface, False, log_q)
            self.keyboard_5 = VirtualKeyboard(self.data, False, self.log_q)
            
            self.keyboard_1.sigInputString.connect(self.class_entry)  
            self.keyboard_2.sigInputString.connect(self.seat_entry)
            self.keyboard_3.sigInputString.connect(self.description_entry)         
            self.keyboard_4.sigInputString.connect(self.surface_entry)
            self.keyboard_5.sigInputString.connect(self.notes_entry)

            self.log_q.put(["debug","LD",'************Entering Location Details Edit Module************'])
            
            self.show()
            
        elif self.window == "WorkOrder":
        
            self.edit = False
            
            flight_lbl = QtWidgets.QLabel("Flight #", self)
            flight_lbl.move(10, 57)
            self.flight_btn = QtWidgets.QPushButton("", self)
            self.flight_btn.resize(self.flight_btn.sizeHint())
            self.flight_btn.setStyleSheet("background-color: white;")
            self.flight_btn.setGeometry(150, 50, 200, 40)

            
            rego_lbl = QtWidgets.QLabel("Plane Rego", self)
            rego_lbl.move(10, 127)
            self.rego_btn = QtWidgets.QPushButton("", self)
            self.rego_btn.resize(self.rego_btn.sizeHint())
            self.rego_btn.setStyleSheet("background-color: white;")
            self.rego_btn.setGeometry(150, 120, 200, 40) 
            rego_lbl_optional = QtWidgets.QLabel("(Optional)", self)
            rego_lbl_optional.move(360, 127)  

            
            add_btn = QtWidgets.QPushButton("Update", self)
            add_btn.resize(add_btn.sizeHint())
            add_btn.move(50, 210)       
            add_btn.clicked.connect(self.addComplete_Close)  
            # add_btn.clicked.connect(self.close)        
            
            cancel_btn = QtWidgets.QPushButton("Cancel", self)
            cancel_btn.resize(cancel_btn.sizeHint())
            cancel_btn.move(370, 210)
            
            cancel_btn.clicked.connect(self.close_app1) 
            
            self.flight_btn.clicked.connect(self.VKB3)
            self.rego_btn.clicked.connect(self.VKB4)            
            

            self.keyboard_3 = VirtualKeyboard(self.surface, False, log_q)
            self.keyboard_4 = VirtualKeyboard(self.Class, False, log_q)

            
            self.keyboard_3.sigInputString.connect(self.description_entry)       
            self.keyboard_4.sigInputString.connect(self.surface_entry)  

            self.log_q.put(["debug","LD",'************Entering WorkOrder create Module************'])
            
            self.show()            
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():
            # self.no_Supplies = True
            DS.engineer = True
            
            self.log_q.put(["debug","LD",'************ Exiting WorkOrder create Module due to '+ DS.cause_Of_logout[DS.logout_cause_value]+' ************'])
            self.sig_charger_connected.emit()
            self.timer_and_page_close()
            
            self.charger_connected.clear()
            
        self.Timer.start(1000)

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","LD","Timer started"])
        
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","LD","!!!!!!!!!!! EXITING LOCATION DETAILS PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","LD","Timer stopped"])         

    def addComplete_Close(self):
        if DS.process_started:    
            if not self.edit:
            
                if self.flight_btn.text():
                    choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                    self.log_q.put(["warning","LD", 'Update button clicked!!!'])    

                    if choice == QtWidgets.QMessageBox.Yes:
                        self.log_q.put(["debug","LD",'Update button clicked. Exiting the application'])   
                        DS.planenumberAndrego+=[self.flight]
                        if self.rego_btn.text():
                            DS.planenumberAndrego+=[self.rego.replace('-','')]
                            self.log_q.put(["info","LD", 'DS.planenumberAndrego: '+str(DS.planenumberAndrego)])             
                        else:
                            DS.planenumberAndrego+=[""]
                        self.log_q.put(["info","LD", 'DS.planenumberAndrego: '+str(DS.planenumberAndrego)])                      
                        self.sig_workorder_Complete.emit( self.flight, self.rego)
                        self.timer_and_page_close()
                    else:
                        self.show()        
                else:
                    QtWidgets.QMessageBox.warning(self, "Entry is empty", "Please enter Flight number")
                    self.log_q.put(["warning","LD", 'Enter a valid flight number']) 
                    self.show()  
            else:
                choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                self.log_q.put(["warning","LD", 'Update button clicked!!!'])    

                if choice == QtWidgets.QMessageBox.Yes:
                    self.log_q.put(["debug","LD",'Update button clicked. Exiting the application'])   

                    self.sig_editComplete.emit(self.seat, self.description, self.surface, self.Class, self.data)
                    self.timer_and_page_close()
                else:
                    self.show()  
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            return                    
                    

                
    def close_app1(self):
        if DS.process_started:     
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            self.log_q.put(["warning","LD", 'CANCEL button clicked!!!'])                 
            if choice == QtWidgets.QMessageBox.Yes:
                self.log_q.put(["debug","LD",'Exiting the application.....'])  
                self.timer_and_page_close()
                self.sig_editClose.emit()
            
            else:
                self.show()
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return                  
            
    def VKB1(self):
        
        if self.keyboard_1.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Class'])
            self.keyboard_1.show()
        else:
            self.keyboard_1.hide()
            
    def VKB2(self):
        
        if self.keyboard_2.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Seat']) 
            self.keyboard_2.show()
        else:
            self.keyboard_2.hide()
 
    def VKB3(self):
        
        if self.keyboard_3.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Description'])  
            self.keyboard_3.show()
        else:
            self.keyboard_3.hide()
            
    def VKB4(self):
        
        if self.keyboard_4.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Surface'])  
            self.keyboard_4.show()
        else:
            self.keyboard_4.hide() 
            
    def VKB5(self, event):
        
        if self.keyboard_5.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Notes']) 
            self.keyboard_5.show()
        else:
            self.keyboard_5.hide()
            
    def VKB6(self):
        
        if self.keyboard_6.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter Surface'])  
            self.keyboard_6.show()
        else:
            self.keyboard_6.hide()             

        
    def class_entry(self, data):
        if DS.process_started:     
            if self.edit:
                self.log_q.put(["info","LD", 'Class: '+data])   
                self.Class = data
                self.class_btn.setText(data)
            else:
                self.log_q.put(["info","LD", 'Site: '+data])  
                self.site = data
                self.site_btn.setText(data)            
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return                  
        
    def seat_entry(self, data):
        if DS.process_started:     
            if self.edit:
                self.log_q.put(["info","LD", 'Seat: '+data]) 
                self.seat = data
                self.seat_btn.setText(data)
                
            else:
                self.log_q.put(["info","LD", 'Airline: '+data]) 
                self.airline = data
                self.airline_btn.setText(data) 
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return                 
        
    def description_entry(self, data):
        if DS.process_started:     
            if self.edit:
                self.log_q.put(["info","LD", 'Description: '+data]) 
                self.description = data
                self.description_btn.setText(data)
            else:
                self.log_q.put(["info","LD", 'Flight: '+data])  
                self.flight = data
                if len(data)<2:
                    QMessageBox.warning(self,"Incorrect length", "Enter valid flight number")
                    self.log_q.put(["info","LD", 'Flight number is empty or single character: '+data]) 
                else:
                    self.flight_btn.setText(data)
             
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return   

            
    def surface_entry(self, data):
        if DS.process_started:     
            if self.edit:
                self.log_q.put(["info","LD", 'Surface: '+data])
                self.surface = data
                self.surface_btn.setText(data)  
            else:
                self.log_q.put(["info","LD", 'Rego: '+data])   
                self.rego = data.upper()
                self.rego_btn.setText(data.upper().replace('-',''))  
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return                 
        
    def notes_entry(self, data):
        if DS.process_started:         
            if self.edit:
                self.data = data
                self.log_q.put(["info","LD", 'Notes: '+self.data]) 
                self.notes_box.setText(self.data) 
            else:
                self.log_q.put(["info","LD", 'WorkorderID: '+data])   
                self.workorderid = data            
                self.workorderid_btn.setText(data) 
        else:
            self.log_q.put(["debug","LD","Charger connected..."])
            self.timer_and_page_close()
            return                