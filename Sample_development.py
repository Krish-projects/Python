import datetime
import json
import math
import os
import pathlib
import random
import shutil
import sys 
import time



import numpy as np


from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from datetime import date, datetime, time 

# print ("sampledevelopment.py first call startin at : startupTime",datetime.datetime.now())

#Python files downloaded
#------------
from Add_Locations import addLocation
from Measurement import Measure
from Status_Window import Status_Window

import abs_analysis as ab
import AnalyserSamplerComms as samplerComms
import CSV_Files_Compare as Compare
import deviceStatus as DS 

import LED_Driver
import Sampler
#------------


class HeaderView(QtWidgets.QHeaderView):
    def mouseReleaseEvent(self, event):
        index = self.visualIndexAt(event.pos().x())
        logical_index = self.logicalIndex(index)
        if logical_index == 0:
            super().mouseReleaseEvent(event)

class Sample(QtWidgets.QMainWindow):

    sig_Sample_close = pyqtSignal()
    sig_sampleSpectroError = pyqtSignal() 
    sig_noSupplies = pyqtSignal()

    def __init__(self,  flightNumber, tailNumber, workOrder, deviceId, telemetry_q, log_q, charger_connected):
        super (Sample, self).__init__()
        self.log_q = log_q
        self.telemetry_q = telemetry_q
        self.deviceId = deviceId

        Sample.setGeometry(self, 0, 22, 480, 250)
        self.AN=flightNumber
        self.operatingAirlineCode = list(flightNumber)
        self.log_q.put(["info","SD","OperatingAirlineCode = "+str(self.operatingAirlineCode)])
        self.Aircraft_ID = tailNumber 
        self.workOrder = workOrder
        self.charger_connected = charger_connected
        
        self.log_q.put(["info","SD","----------Opening Sample Module----------"])
        self.data = ''
        self.FinishWorkOrder = False
        DS.samplingCount = 0
        self.home()
        self.display_jobs() #Calls display jobs function

        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","SD","charger_connected event cleared... "])
            self.log_q.put(["debug","SD","!!!!!!!! CLOSING SAMPLE WINDOW !!!!!!!"])
            self.close_application()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","SD","Timer started"])   

    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","SD","!!!!!!!!!!! EXITING SAMPLE PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","SD","Timer stopped"])         
        
    def home(self):
        
        btn = QtWidgets.QPushButton("Add", self)
        btn.clicked.connect(self.varAssign_Add)         
        btn.resize(btn.sizeHint())
        btn.move(10, 210)   
        
        btn = QtWidgets.QPushButton("Finish", self)       
        btn.clicked.connect(self.timer_and_page_close)
        btn.clicked.connect(self.Finish)
        btn.resize(btn.sizeHint())
        btn.move(190, 210)    
        
        btn = QtWidgets.QPushButton("Cancel", self)
        btn.clicked.connect(self.Cancel)
        btn.resize(btn.sizeHint())
        btn.move(360, 210)
        
        self.table = QtWidgets.QTableWidget(self)
        self.table.setGeometry(QtCore.QRect(10, 5, 460, 200))
        self.table.setColumnCount(7)
        
        self.header = HeaderView(QtCore.Qt.Horizontal)
        self.header.setSectionsClickable(True)
        
        self.table.setHorizontalHeader(self.header)
        self.table.setSortingEnabled(True)  


       
    def varAssign_Add(self):
        self.varAssign_Tab_state = False
        self.availableSupplies()   

    def Cancel(self):
        self.FinishWorkOrder = False
        self.close_Application(self.FinishWorkOrder)
        
    def Finish(self):
        self.FinishWorkOrder = True

        self.close_Application(self.FinishWorkOrder)         
  
      
    def addlocation(self):
        A_No = str(self.AN)
        A_ID = str(self.Aircraft_ID)
        self.timer_and_page_close()         
        self.AddLocation = addLocation(str(A_No), str(A_ID), self.log_q, self.workOrder, self.deviceId, self.telemetry_q, self.charger_connected)
#Calls the class "addRegime" to add the location details
        self.AddLocation.show()
        self.AddLocation.sig_locationDetails.connect(self.addrow)
        self.AddLocation.sig_addLocation_Close.connect(self.enableTimer) 
        self.AddLocation.sig_AddL_SpectrometerError.connect(self.enableTimer) 
        self.AddLocation.sig_samplerWillNotReturn.connect(self.enableTimer)
        
    def Sample_spectrometerError(self):
        self.timer_and_page_close()
        self.sig_sampleSpectroError.emit()

          
#This function displays the list of locations downloaded from the server        
    def display_jobs(self):

        row_number = 0
        col_number = 0
        
        
        horHeaders = ["Seat", "Description", "Surface", "Class", "Result", "Confidence %", "Absorbance"]
        
        self.table.setHorizontalHeaderLabels(horHeaders)
        
        self.table.verticalHeader().setVisible(False)

        for locations in DS.locationsList:
            self.table.insertRow(row_number)
            item = QTableWidgetItem(locations[0])
            item.setTextAlignment(QtCore.Qt.AlignHCenter)#### Aligning the seat number center
            self.table.setItem(row_number, 3, QTableWidgetItem(locations[2]))            
            self.table.setItem(row_number, 1, QTableWidgetItem(locations[3]))
            self.table.setItem(row_number, 2, QTableWidgetItem(locations[4]))
            self.table.setItem(row_number, 0, item)
            row_number += 1       
        self.workOrder["Flight"]["OperatingAirlineCode"] = self.operatingAirlineCode[0]+self.operatingAirlineCode[1]
        self.workOrder["Flight"]["FlightNumber"] = self.AN
        self.workOrder["Flight"]["TailNumber"] = self.Aircraft_ID
        self.log_q.put(["info","SD","self.workOrder[Flight][OperatingAirlineCode]"+str(self.workOrder["Flight"]["OperatingAirlineCode"])])
        self.log_q.put(["info","SD","self.workOrder[Flight][FlightNumber]"+str(self.workOrder["Flight"]["FlightNumber"])])
        self.log_q.put(["info","SD","self.workOrder[Flight][TailNumber]"+str(self.workOrder["Flight"]["TailNumber"])])
        self.log_q.put(["info","SD","self.workOrder[Flight][PlaneSeries]"+str(self.workOrder["Flight"]["PlaneSeries"])])

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        self.table.sortByColumn(0, QtCore.Qt.AscendingOrder)

        self.table.setSelectionBehavior(QTableView.SelectRows) 
        self.table.cellClicked.connect(self.varAssign_Tab) 
        
        self.show()

    def varAssign_Tab(self):
        self.varAssign_Tab_state = True
        row = self.table.currentRow()
        result = self.table.item(row, 4)
        self.log_q.put(["info","SD", 'result is ',str(result)])
        if result !=None:
            resample = QtWidgets.QMessageBox.question(self, "LOW SUPPLY" ,"This location is already sampled. Do you want to sample this location again? ") 
            if resample == QtWidgets.QMessageBox.Yes: 
                self.availableSupplies()
            else:
                self.show()
            
        else:
            self.availableSupplies()        
        
    def availableSupplies (self):
        x=True
        self.NO = False
        while x:
            self.timer_and_page_close()             
            self.supplyAvailability = Status_Window(self.log_q, self.charger_connected)
            self.supplyAvailability.show() 
            
            self.log_q.put(["info","SD","Checking Supply availability"])
            self.log_q.put(["info","SD","Checking Battery Precent for analysis"])
            # self.log_q.put(["info","MW","DS.analyserBattery = %d, DS.samplerBattery = %d, DS.analyserCharging = %d"%(DS.analyserBattery, DS.samplerBattery, DS.analyserCharging)])    
            if (DS.analyserBattery <= DS.analyserBatteryThreshold or DS.samplerBattery <= DS.samplerBatteryThreshold) and DS.analyserCharging != 1:                
                status = Sampler.S_cmd_Get_status()
                if (status['status'] == 'Disconnected'):
                    pass
                else:                   
                    QtWidgets.QMessageBox.warning(self, "Battery Level Critical" ,"Battery level low. Connect to the Charger")            
                    self.log_q.put(["info","MW","DS.analyserBattery = %d, DS.samplerBattery = %d, DS.analyserCharging = %d"%(DS.analyserBattery, DS.samplerBattery, DS.analyserCharging)])    
                    self.log_q.put(["info","SD","Battery level low. Operator instructed to connect to the Charger"])
                x=False
            elif DS.analyserSolventRemaining <= DS.analyserSolventThreshold or DS.analyserWasteRemaining<=DS.analyserWasteThreshold:
                self.log_q.put(["info","MW","Checking solvent availability for analysis"])   
                QtWidgets.QMessageBox.warning(self, 'Change Solvent Bag!', "Not enough supplies to perform sampling. Please change Consummables. ")
                QtWidgets.qApp.processEvents()
                

                x=False
                # self.NO = True
                break
                    
            elif DS.analyserPadAge>= DS.padAgeThreshold:
                self.log_q.put(["info","SD","Checking Sample pad age"])   
                choice = QtWidgets.QMessageBox.warning(self, 'Change Sample Pad!', "Sample pad needs changing.\nClick Yes when changed.")
                # self.supplyAvailability.resetSamplerpadValue() 

                x=False
                # self.NO = True
                break
                    
            else:    
                self.log_q.put(["info","SD","Got enough supplies. Displaying the available supplies"]) 
                x=False
        if self.NO:
            DS.logout_cause_value =  4
            self.checkStatus()
        else:
            # self.supplyAvailability.sig_SpectrometerError.connect(self.enableTimer)
            self.supplyAvailability.sig_SpectrometerError.connect(self.checkStatus)
            self.supplyAvailability.sig_Sampler_will_not_return.connect(self.close_application)
            
            # self.supplyAvailability.sig_availableSupplies.connect(self.enableTimer)     
            self.supplyAvailability.sig_availableSupplies.connect(self.checkStatus)
        
    def checkStatus(self):
        self.enableTimer()
        if self.NO:
            self.timer_and_page_close()
            self.log_q.put(["info","MW","Insufficient supplies. Exiting due to insufficient supplies!!!"]) 
            
            QtWidgets.QMessageBox.warning(self, "LOW SUPPLY" ,"Exiting due to insufficient supplies!!!") 
            self.close_application()

            
        else:

            self.availableSupplies1()
        
    def close_application(self):
        self.timer_and_page_close()
        self.log_q.put(["debug","SD",'*********Closing Sample development window due to '+ DS.cause_Of_logout[DS.logout_cause_value]+' *********'])          
        self.sig_noSupplies.emit()
        
    def availableSupplies1(self):
    
        if self.varAssign_Tab_state:
            
            self.row = self.table.currentRow()
            self.column = self.table.currentColumn()
            self.cell_is_clicked(self.row,self.column) 
            
        else:
            self.addlocation()        
   

    def addrow(self, cabin, name, description, surface, result, confidence, absorbance):
        self.table.setSortingEnabled(False) #disable table sort while we add a row
        self.rowposition = self.table.rowCount()
        self.table.insertRow(self.rowposition)
        # self.log_q.put(["info","SD", 'seat number is %s' % (name)])
        
        self.table.setItem(self.rowposition, 3, QTableWidgetItem(str(cabin)))
        self.table.setItem(self.rowposition, 1, QTableWidgetItem(str(description)))
        self.table.setItem(self.rowposition, 2, QTableWidgetItem(str(surface)))
        self.table.setItem(self.rowposition, 4, QTableWidgetItem(str(result)))
        self.table.setItem(self.rowposition, 5, QTableWidgetItem(str(confidence)))
        self.table.setItem(self.rowposition, 6, QTableWidgetItem(str(absorbance)))
        
        name_strip = []
        name_strip = list(name)
        if len(name_strip)<3:
            name_ = "{:02d}".format(int(name_strip[0]))
            # self.log_q.put(["info","SD", 'name_ %s' % (name_)])
            name = name_+name_strip[1]
            # self.log_q.put(["info","SD", 'name %s' % (name)])
            
        item = QTableWidgetItem(str(name))
        item.setTextAlignment(QtCore.Qt.AlignHCenter)#### Aligning the seat number        
        self.table.setItem(self.rowposition, 0, item) 
        # now colour the row green or red depending on confidence/absorbance
        for j in range(self.table.columnCount()):
            if float(confidence) <=50 or float(absorbance)>=2:
                self.table.item(self.rowposition, j).setBackground(QtGui.QColor(200, 0, 0)) #green
            else:
                self.table.item(self.rowposition, j).setBackground(QtGui.QColor(0, 200, 0)) #red
    
        self.table.setSortingEnabled(True) #reenable table sort
        self.show()
        self.log_q.put(["info","SD","----------End of Measurement in a new location added by the Operator-------"])         
#------------         
 #When the workorder is clicked   
    def cell_is_clicked(self, row, column):
        self.item1 = self.table.item(self.row, self.column)
        self.Description = self.table.item(row, 1)
        self.description = self.Description.text() 
        self.Surface = self.table.item(row, 2)
        self.surface = self.Surface.text()
        self.class1 = self.table.item(row, 3)
        self.Class = self.class1.text()
        self.seat = self.table.item(row, 0)
        try:
            nextSeatRow = row+1
            self.nextSeat = self.table.item(nextSeatRow, 0)
            self.nextSeatNumber = self.nextSeat.text()
            # self.log_q.put(["info","SD", 'in Try,nextSeatRow is %s' % str(nextSeatRow)])
            # self.log_q.put(["info","SD", 'in Try,Next seat is %s' % (self.nextSeatNumber)])
        except:
            self.nextSeatNumber = ''
            # self.log_q.put(["info","SD", 'In except, Next seat is %s' % (self.nextSeatNumber)])
        self.seatNumber = self.seat.text()
        
        self.log_q.put(["info","SD", 'Location ID %s in %s %s on %s is clicked' % (self.seatNumber, self.description, self.surface, self.Class)])        
        self.log_q.put(["info","SD", 'Next seat is %s' % (self.nextSeatNumber)])
        self.timer_and_page_close() 
        
        self.startMeasurement = Measure('predeterminedLocation', self.seatNumber, self.surface, self.Class, self.description, self.AN, self.Aircraft_ID, self.workOrder, self.deviceId, self.telemetry_q,self.log_q, self.data, self.nextSeatNumber, self.charger_connected)
        self.startMeasurement.sig_measurementComplete.connect(self.colour)
        self.startMeasurement.sig_windowCancel.connect(self.enableTimer)  
        self.startMeasurement.sig_samplerWillNotReturn.connect(self.enableTimer) 
        self.startMeasurement.sig_SpectrometerError.connect(self.enableTimer)                
        self.startMeasurement.sig_drain_problem.connect(self.enableTimer)
        
 
#Colour the sample location details with green        
    def colour(self, seat, description, surface, Class):
        self.log_q.put(["info","SD","Location sampled and results added to the table"])
        self.Class = Class
        self.description = description
        self.surface = surface
        self.seat = seat
   
        self.table.clearSelection()
        self.table.setSortingEnabled(False) #disable table sort while we add a row
        self.table.setItem(self.row, 1, QTableWidgetItem(str(self.description)))
        self.table.setItem(self.row, 2, QTableWidgetItem(str(self.surface)))
        self.table.setItem(self.row, 3, QTableWidgetItem(str(self.Class)))
        self.table.setItem(self.row, 4, QTableWidgetItem(str(int(DS.result))))
        self.table.setItem(self.row, 5, QTableWidgetItem(str(int(DS.confidence))))
        self.table.setItem(self.row, 6, QTableWidgetItem(str(DS.absorbance)))  
        self.log_q.put(["info","SD", 'self.seat is %s' % self.seat])        
        item = QTableWidgetItem(str(self.seat))
        item.setTextAlignment(QtCore.Qt.AlignHCenter)#### Aligning the seat number        
        self.table.setItem(self.row, 0, item) 
        
        for j in range(self.table.columnCount()):
            self.log_q.put(["info","SD", 'j is %d' % j])
            if float(DS.confidence)<=50 or float(DS.absorbance)>=2:
                self.table.item(self.row, j).setBackground(QtGui.QColor(200, 0, 0))
            else:
                self.table.item(self.row, j).setBackground(QtGui.QColor(0, 200, 0))
        
        # for i in range(self.table.rowCount()):
            # self.log_q.put(["info","SD", 'self.table.item(i,0).text is %s' % str(self.table.item(i,0).text())])        
            # if self.table.item(i,0).text() == self.seat:
                # for j in range(self.table.columnCount()):
                    # self.log_q.put(["info","SD", 'j is %d' % j])
                    # if float(DS.confidence)<=50 or float(DS.absorbance)>=2:
                        # self.table.item(i, j).setBackground(QtGui.QColor(200, 0, 0))
                    # else:
                        # self.table.item(i, j).setBackground(QtGui.QColor(0, 200, 0))            
                         
        self.table.setSortingEnabled(True) #disable table sort while we add a row        
        self.enableTimer()
        self.log_q.put(["info","SD","----------End of Measurement in Predetermined Location-------"])        



#This function is invoked whenever "Finish" or "Cancel" button is clicked

    def close_Application(self, finish):
        if finish:
        
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure you want to Finish the Work Order?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            self.log_q.put(["warning","SD","FINISH button clicked!!!!"])
            if choice == QtWidgets.QMessageBox.Yes:
                if DS.samplingCount!=0:
        # # #######Time stamp at end of sampling locations#############
                    self.log_q.put(["info","SD","Time taken to complete sampling in "+ str(self.AN)+" is "+str('{:02d}'.format(DS.totalTime.minutes))+" : "+str('{:02d}'.format(DS.totalTime.seconds))+" (mm:ss)"])
                    QtWidgets.QMessageBox.about(self, "Battery Level Critical" ,"Time taken to sample "+ str(self.AN)+" aircraft is "+str('{:02d}'.format(DS.totalTime.minutes))+" : "+str('{:02d}'.format(DS.totalTime.seconds))+" (mm:ss)")
        # # #############################################################################         
                DS.samplingCount = 0            
                self.log_q.put(["debug","SD","Finishing the workorder and exiting the application....."])
                DS.messageType = 'Finished'
                self.timer_and_page_close()
                self.log_q.put(["info","SD","--------Sample Module Complete------------"])
                self.sig_Sample_close.emit()
                self.log_q.put(["info","SD","--------Sample Module Complete after emit------------"])
            
            else:
                self.show()
        else:
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure you want to Cancel the Work Order?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            self.log_q.put(["warning","SD","CANCEL button clicked!!!!"])
            if choice == QtWidgets.QMessageBox.Yes:
                self.log_q.put(["debug","SD","Cancelling the Work Order and exiting the application....."])
                DS.messageType = 'Cancelled/Incomplete'  
                self.timer_and_page_close()
                self.log_q.put(["info","SD","--------Sample Module Cancelled or Incomplete------------"])
                self.sig_Sample_close.emit()
                self.log_q.put(["info","SD","--------Sample Module Cancelled or Incomplete after emit------------"])
            
            else:
                self.show()
                
                
