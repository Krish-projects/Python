#This file opens a page to enter the flight details
import datetime
import glob 
import json
import csv
import logging
import os
import pathlib
import random
import requests
import string
import shutil
import subprocess
import sys 
import threading
import time


import numpy as np

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from pytz import timezone

# print ("Flightdetails.py first call startin at : startupTime",datetime.datetime.now())

#Python files download
#-----------
import Sampler

from Calibration import Window
from Sample_development import Sample
from Status_Window import Status_Window
from VirtualKeyboard import VirtualKeyboard

import deviceStatus as DS
#-----------------


class GetPlaneId(QWidget):
    
    sig_flightDetails_Close = pyqtSignal()	
    sig_noFromSupplies = pyqtSignal()
    sig_Cancel_Finish = pyqtSignal()
    sig_flightSpectroError = pyqtSignal()
    
    
    def __init__(self,  flightNumber, workOrder, deviceId, telemetry_q, log_q, charger_connected):
        super (GetPlaneId, self).__init__()
        GetPlaneId.setGeometry(self, 0, 22, 480, 250)
        
        self.log_q = log_q
        self.telemetry_q = telemetry_q
        self.deviceId = deviceId
        self.flightNumber=flightNumber
        self.workOrder = workOrder
        self.charger_connected = charger_connected
        
        self.data = ''      
        
        self.keyboard1 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard2 = VirtualKeyboard(self.data, False, self.log_q)
        self.keyboard1.sigInputString.connect(self.Aircraft_number)
        self.keyboard2.sigInputString.connect(self.Plane_ID)    

        self.randomValue_seat=[]
        self.randomValue_description = []
        DS.locationsList = []   
        
        self.Airline = ''
        self.AircraftMake = ''
        self.AircraftType = ''

        self.filesInFolder = ''
        self.seatNo = ''
        self.seatRow = ''
        self.seatClass = ''
        self.seatType = ''
        self.description = ''
        self.surface = ''
        
        self.home()
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","FD","charger_connected event cleared... "])
            self.log_q.put(["debug","FD","!!!!!!!! CLOSING FLIGHT DETAILS WINDOW due to "+ DS.cause_Of_logout[DS.logout_cause_value]+" !!!!!!!"])
            self.close_NoSupplies()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","FD","Timer started"])        
        
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","FD","!!!!!!!!!!! EXITING FLIGHT DETAILS PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","FD","Timer stopped"])          
        
    def home(self):
        """
        Displaying push buttons in the page
        """
        Aircraft_number = QtWidgets.QLabel("Enter Plane Rego for Flight " + self.flightNumber, self)
        Aircraft_number.setGeometry(50, 20, 430, 40)

        self.calibrationRequiredLabel = QLabel('Calibration Required',self)
        self.calibrationRequiredLabel.move(140,180)
        self.calibrationRequiredLabel.hide()
        
        Aircraft_ID = QtWidgets.QLabel("Plane Rego", self)
        Aircraft_ID.setGeometry(60, 70, 170, 40)
        self.Aircraft_ID = QtWidgets.QLineEdit("", self)
        self.Aircraft_ID.setGeometry(190, 70, 200, 40)
        for i in range(len(DS.planenumberAndrego)):
            self.log_q.put(["debug","FD","In flight details, DS.planenumberAndrego[i]: "+str(DS.planenumberAndrego[i])])
            if self.flightNumber == DS.planenumberAndrego[i]:
                self.Aircraft_ID.setText(DS.planenumberAndrego[i+1])
        
        
        self.next = QtWidgets.QPushButton("Next", self)
        self.next.resize(self.next.sizeHint())
        self.next.move(210, 140)
        self.next.clicked.connect(self.timer_and_page_close)
        self.next.clicked.connect(self.got_tail_number)

        cancel = QtWidgets.QPushButton("Cancel", self)
        cancel.resize(cancel.sizeHint())
        cancel.move(340, 140)
        cancel.clicked.connect(self.close_app)
        # cancel.clicked.connect(self.close)

        
        calibrate = QtWidgets.QPushButton("Calibrate", self)
        calibrate.resize(calibrate.sizeHint())
        calibrate.move(60, 140)
        calibrate.clicked.connect(self.availableSupplies)    
        
        self.Aircraft_ID.mousePressEvent = self.VKB2
        
        self.time_diff = int(time.time()-DS.calibratedTime)
        self.log_q.put(["info","FD","time_diff = %d, time.time()=%f, DS.calibratedTime = %f"%(self.time_diff,time.time(),DS.calibratedTime)])
        # ### remove the line below###
        # self.next.setEnabled(True)
        # #############
        if self.time_diff>DS.calibrationTimeLimit:
            self.log_q.put(["info","FD","Calibration performed over 4 hours ago. Operator instructed to recalibrate."])
            # QMessageBox.warning(self,"Recalibrate", "Calibration timeout. \n Redo calibration")
            self.next.setEnabled(False)
            self.calibrationRequiredLabel.show()            

    def got_tail_number(self):
        """
        Check whether the operator entered the plane rego.
        If yes, move to get regime function,
        else, prompt to enter the plane rego.
        """    
        if self.Aircraft_ID.text():
            self.time_diff = int(time.time()-DS.calibratedTime)
            self.log_q.put(["info","FD","time_diff = %d, time.time()=%f, DS.calibratedTime = %f"%(self.time_diff,time.time(),DS.calibratedTime)])            
            time_diff_sec = self.time_diff%(24*3600)
            time_hours = time_diff_sec//3600  ###extracting hours from time difference
            time_diff_sec%= 3600 ##Getting remaining time in sec
            time_min = time_diff_sec//60 ###Extracting mins
            time_diff_sec %= 60 ##Getting remaining time in sec
            self.log_q.put(["info","FD","Calibration performed %d:%02d:%02d H:M:S ago. So continuing next step."%(time_hours,time_min,time_diff_sec)])
            self.regimeTime = self.GetRegime(self.flightNumber, self.workOrder, self.Aircraft_ID.text(), self.deviceId, self.telemetry_q, self.log_q)
        else:
            QtWidgets.QMessageBox.warning(self, "Entry is empty", "Please enter Plane Rego")
            self.show()

#This function is invoked when the "Cancel" button is clicked
    def close_app(self):
        """
        Exiting the page
        """     
        self.timer_and_page_close()         
        self.log_q.put(["warning","FD","CANCEL button clicked!!!!"])
        self.cancelPressed = 1
        self.sig_flightDetails_Close.emit()
        
#This function is invoked when the Supplies are not refilled
    def close_NoSupplies(self):
         
        self.log_q.put(["error","FD","%%%%%%%%%% Exiting the application due to due to "+ DS.cause_Of_logout[DS.logout_cause_value]+" %%%%%%%%%%"])
        self.timer_and_page_close()
        self.sig_noFromSupplies.emit()
        
#This function is invoked when the the SPECTROMETER is unresponsive
    def flight_spectrometerError(self):
        self.log_q.put(["error","FD","%%%%%%%%%% Exiting the application due to "+ DS.cause_Of_logout[DS.logout_cause_value]+" %%%%%%%%%%"])
        self.timer_and_page_close()
        # self.sig_flightSpectroError.emit()        

    def CancelFinish_Signal(self):
        self.log_q.put(["warning","FD"," Workorder finished or cancelled"])
        self.sig_Cancel_Finish.emit()   
        
        


    def availableSupplies (self):
        """
        Check for enough supplies. 
        If no enough supplies to refill, then logout the user.
        """      
        x=True
        self.NO = False
        while x:
            self.timer_and_page_close()               
            self.supplyAvailability = Status_Window(self.log_q, self.charger_connected)
            self.supplyAvailability.show()        
            self.log_q.put(["info","FD","Checking Supply availability"])
            self.log_q.put(["info","FD","Checking Battery Percent for analysis"])
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


                x=False
                # self.NO = True
                break
                    

                
            if DS.analyserPadAge>= DS.padAgeThreshold:
                
                QtWidgets.QMessageBox.warning(self, 'Change Sample Pad!', "Sample pad needs changing.\nClick Yes when changed.")
                self.log_q.put(["info","FD","Change pad, age is: " + str(DS.analyserPadAge)])

                x=False
                # self.NO = True
                break
                    
            else:    
                self.log_q.put(["info","FD","Got enough supplies"]) 
                x=False
                pass

        if self.NO:
            DS.logout_cause_value =  4
            self.checkStatus()
        else:

            self.supplyAvailability.sig_availableSupplies.connect(self.enableTimer)                  
            self.supplyAvailability.sig_availableSupplies.connect(self.Calibrate)
            # self.supplyAvailability.sig_SpectrometerError.connect(self.enableTimer)
            self.supplyAvailability.sig_SpectrometerError.connect(self.enableTimer)
            self.supplyAvailability.sig_Sampler_will_not_return.connect(self.close_NoSupplies)
            
           

    def checkStatus(self):        
        if self.NO:
            self.log_q.put(["info","FD","Exiting due to insufficient supplies!!!"])
            self.timer_and_page_close()           
            DS.messageType = 'Sampling aborted due to insufficient supply'
            QtWidgets.QMessageBox.warning(self, "LOW SUPPLY" ,"Exiting due to insufficient supplies!!!") 
            DS.logout_cause_value =  4
            self.close_NoSupplies()
            
        

    def Calibrate(self):
        """
        Call calibration sequence 
        """  
        if DS.process_started:          
            self.log_q.put(["info","FD","CALIBRATION clicked"])
            self.timer_and_page_close()            
            self.calibrate = Window(self.log_q, self.telemetry_q, self.charger_connected)
            self.Calibration = self.calibrate.steps()
            self.log_q.put(["debug","FD","self.Calibration = "+ str(self.Calibration)+" ..."])
            # self.show()
            if self.Calibration== 0: ### Successful completion
                self.enableTimer()
                self.next.setEnabled(True)
                self.calibrationRequiredLabel.hide()
            elif self.Calibration == 2: ### Received confirmation tath user will not remove the charger
                self.log_q.put(["debug","FD","Received response as "+ DS.cause_Of_logout[DS.logout_cause_value]+" ..."])
                self.close_NoSupplies()
            elif self.Calibration == 3:### Received calibration error
                self.enableTimer()
            else:        
                # self.flight_spectrometerError()
                self.enableTimer()
        else:
            self.log_q.put(["debug","FD","Charger connected..."])
            return         
        
        
 #Checks the entered flight details

    
    def VKB1(self, event):
        
        if self.keyboard1.isHidden():
            self.log_q.put(["debug", "FD", 'Virtual Keyboard enabled'])
            self.keyboard1.show()
        else:
            self.keyboard1.hide()
            
    def VKB2(self, event):
        
        if self.keyboard2.isHidden():
            self.log_q.put(["debug", "FD", 'Virtual Keyboard enabled'])
            self.keyboard2.show()
        else:
            self.keyboard2.hide()
        
        
    def Aircraft_number(self, data):
        self.Aircraft_number.setText(data)
        
    def Plane_ID(self, data):
        self.log_q.put(["debug", "FD", 'Entered Plane Rego: %s' % data.upper().replace('-','')])
        self.Aircraft_ID.setText(data.upper().replace('-',''))
        


    def GetRegime(self, flightNumber, workOrder, planeid, deviceId, telemetry_q, log_q):
        """
        Start the Timer and thread until one of the following process is complete:
        1. Download the workorder from the webservice
        2. Create our own locations by entering the airline and rego against the database
        3. When Cancel button is pressed.
        """ 
        
        self.log_q = log_q
        self.telemetry_q = telemetry_q
        self.deviceId = deviceId
        self.flightNumber = flightNumber
        self.workOrderid = workOrder
        self.planeID = planeid.upper().replace('-','')


        #---------------comment for no internet-------------------------------------
        self.timer = QBasicTimer()
        self.step = 0

        self.progressBar = QProgressDialog("Downloading Test Details", "Cancel", 0, 100)

        self.progressBar.setGeometry(30,140,400,100)
        self.progressBar.show()
        self.regimeprogress = 0
        self.timer.start(1000,self)
        self.cancelPressed = 0 #used when user hits cancel during HTTP request
        #kick off HTTP request (POST) for RegimeInstance
        self.thread = threading.Thread(target=self.getRegimeInstance)
        self.thread.start()
        self.show()
        #--------------uncomment for no internet-----------------------------------------------
        # with open('WOwRegimeInstance.json','rt') as regifile:
            # self.r = regifile.read()
        # self.workOrder = json.loads(self.r)
        # self.Analyser(self.flightNumber, self.planeID, self.workOrder)
        #-------------------------------------------------------------
        

    def timerEvent(self, e):
        """
        Timer event started. The timer is stopped upon following isntances:
        1. If the timer value reaches 100.
        2. If Cancel button is pressed.
        3. If a value is returned for regimeprocess. The values and details for regimeprocess are as follows:
            1 - When the locations are downloaded from webservice or created from the database
            2 - If there is no data to be downloaded from the webservice
            3 - If the airline and/or plane rego did not match the entered values and the user wants to create a generalised locations
        """     
        if self.step >= 100:
            
            self.timer.stop()
            return
        if self.regimeprogress == 0:
            self.step = self.step + 1
            self.progressBar.setValue(self.step)
            if self.progressBar.wasCanceled():
                self.cancelPressed = 1
                self.timer.stop()
                self.progressBar.hide()
        else:
            if self.cancelPressed == 1:
                # user has pressed cancel during HTTP request. Ignore response and continue
                return
            else:
                if self.regimeprogress == 1:
                    
                    self.progressBar.setValue(100)
                    self.timer.stop()
                    self.timer_and_page_close()
                    self.progressBar.hide()
                        
                    self.Analyser(self.flightNumber, self.planeID, self.workOrder_New)                   
                   
                else:
                    self.timer_and_page_close()
                    self.progressBar.setValue(100)
                    self.timer.stop()
                    self.progressBar.hide()
                    newRego = QMessageBox.question(self, 'Message',
                                "Tail number not found for this Airline. Do you want to create one?")
                    if newRego == QtWidgets.QMessageBox.Yes:
                        self.log_q.put(["info","FD","New tail number for the airline entered.... "])
                        self.Airline = 'General'
                        self.Rego = self.Aircraft_ID
                        self.AircraftType = 'B738'
                        self.FileName =  self.Airline+'_'+self.AircraftType      
                        
                        self.path = DS.regoDirectory
                        self.files = os.listdir(self.path)


                        for name in self.files:
                            if name == self.FileName+'.csv':
                                self.seatdetails = np.genfromtxt( self.path+'/'+self.FileName+'.csv', delimiter=',', dtype="|U20")
                                self.seatNo = self.seatdetails[:,0]
                                self.seatRow = self.seatdetails[:,1]
                                self.seatType = self.seatdetails[:,2]
                                self.seatClass = self.seatdetails[:,3]
                                
                                self.noOfSeats = len(self.seatNo)
                                self.lengthTotal = int(self.noOfSeats/int(DS.totalSamplingLocations)) 
                                self.log_q.put(["info","FD","Total seat segments = "+ str(self.lengthTotal)])
     
                                self.locationDescription = np.genfromtxt( self.path+'/Description_Details.csv', delimiter=',', dtype="|U50")
                                self.description = self.locationDescription[:,0]
                                self.surface = self.locationDescription[:,1]        
                                self.length_Description = len(self.locationDescription)             
                            
                                for i in range(0,int(DS.totalSamplingLocations)):

                                    rV = random.randint(self.lengthTotal*i,self.lengthTotal*(i+1))
                                    self.randomValue_seat.append(rV) 
                                    self.randomValue_description = random.sample(range(int(DS.totalSamplingLocations)),  self.length_Description)
                                    
                                # self.log_q.put(["info","FD","randomValue_seat = "+ str(self.randomValue_seat)])
                                # self.log_q.put(["info","FD","randomValue_Description = "+ str(self.randomValue_description)])
                            

                                
                                    
                        self.generateRandomLocations() 
                        self.Analyser(self.flightNumber, self.planeID, self.workOrder_New)
                       
                    else:
                        self.log_q.put(["info","FD","Falling back to change the tail number.......... "])

                        self.show()
                    return                      
                
            return


        
    def getRegimeInstance(self):
        """
        Performs one of the following actions and returns a value mentioned in timerEvent function:
        1. Check the entered rego and airline name against the database
        2. Downloads the location details from webservice and returns a value mentioned in timerEvent function
        """     
        todaystr = str(datetime.date.today())    
        self.targetDate = datetime.datetime.now(tz=timezone(DS.ourTimezone)).isoformat()
        

        with open('dummyJSON.json','rt') as regimeInstancefile:
            self.rInstance = regimeInstancefile.read()
        self.workOrder_New = json.loads(self.rInstance)
        self.workOrder_New['WorkOrderId']=self.workOrderid
        self.workOrder_New['ModifiedDate']=todaystr
        self.workOrder_New['OperatorName']=DS.userID
        self.workOrder_New['Flight']['FlightNumber']=self.flightNumber
        self.workOrder_New['Flight']['FlightDate']= str(self.targetDate)
        self.workOrder_New['Flight']['TailNumber']=self.planeID
        self.workOrder_New['Flight']['OperatingAirlineCode']= "QANTAS"
        
   
        self.log_q.put(["debug","FD","RegimeInstance = "+str(self.workOrder_New)])

        self.strip_airlineCode = list(self.flightNumber.upper())
        self.combine_airlineCode = self.strip_airlineCode[0]+self.strip_airlineCode[1]
        self.log_q.put(["info","FD","First 2 letters of Airline Code is "+ str(self.combine_airlineCode)])
        
        self.airlineCodeToAirline = np.genfromtxt( DS.regoDirectory+'Airlines_with_Code.csv', delimiter=',', dtype="|U50")
        self.log_q.put(["info","FD","Loaded Airlines Codes data"])
        for i, row in enumerate(self.airlineCodeToAirline):
            for j, column in enumerate(row):
                if self.combine_airlineCode == column:
                    self.airline = row[0]
                    # self.log_q.put(["info","FD","self.airline is  "+ str(self.airline)])
        Z=True
        self.log_q.put(["info","FD","Built Airlines Codes data"])
        while Z:
            try:            
                self.log_q.put(["info","FD","Airline Code is  "+ str(self.combine_airlineCode)+" Airline company is "+ str(self.airline)])

                with open(DS.regoDirectory+'planerego.csv','r') as f:
                  reader=csv.reader(f)
                  allplanes=list(reader)
                # self.log_q.put(["info","FD","Built Planes rego data"])
                self.log_q.put(["info","FD","Looking for: "+self.planeID])
                # self.log_q.put(["info","FD","Length of entered planeid: "+str(len(list(self.planeID)))])
                if (len(list(self.planeID))<5):
                    # self.log_q.put(["info","FD","Length of all planes: "+str(len(allplanes))])
                    for i in range(len(allplanes)):
                        stripRego = list(allplanes[i][1])
                        regoCombine = stripRego[len(stripRego)-3]+stripRego[len(stripRego)-2]+stripRego[len(stripRego)-1]

                        if regoCombine == self.planeID and allplanes[i][0]==self.airline  :
                            # self.log_q.put(["info","FD","Got it"])
                            self.Airline = allplanes[i][0]
                            self.planeID = allplanes[i][1]
                            self.AircraftMake = allplanes[i][2]
                            self.AircraftType = allplanes[i][3]          

                            
                else:
                
                    for plane in allplanes:
                          if plane[1] == self.planeID and plane[0]==self.airline  :
                            # self.log_q.put(["info","FD","Got it"])
                            self.Airline = plane[0]
                            self.planeID = plane[1]
                            self.AircraftMake = plane[2]
                            self.AircraftType = plane[3]        
                        
                self.FileName =  self.Airline+'_'+self.AircraftType           
                self.FolderName = self.Airline   
                self.log_q.put(["info","FD","FileName name is "+ str(self.FileName)])
                self.log_q.put(["info","FD","Airline name is "+ str(self.Airline)])        
                self.log_q.put(["info","FD","Rego is "+ str(self.planeID)])
                self.log_q.put(["info","FD","AircraftMake is "+ str(self.AircraftMake)])
                self.log_q.put(["info","FD","AircraftType is "+ str(self.AircraftType)])
                self.log_q.put(["info","FD","Folder name is "+ str(self.FolderName)])
                        
                self.path = DS.regoDirectory
                self.folder = os.listdir(self.path)
                
                for foldername in self.folder:
                    if foldername == self.FolderName:
                        self.filesInFolder = os.listdir(self.path+foldername)
                        

                for name in self.filesInFolder:
                    if name == self.FileName+'.csv':
                        self.log_q.put(["info","FD","File name is "+ str(name)])
                        self.seatdetails = np.genfromtxt( self.path+self.FolderName+'/'+self.FileName+'.csv', delimiter=',', dtype="|U20")
                        self.seatNo = self.seatdetails[:,0]
                        self.seatRow = self.seatdetails[:,1]
                        self.seatType = self.seatdetails[:,2]
                        self.seatClass = self.seatdetails[:,3]
                        
                        self.noOfSeats = len(self.seatNo)-1
                        self.log_q.put(["info","FD","noOfSeats = "+ str(self.noOfSeats)])
                        self.lengthTotal = int(self.noOfSeats/int(DS.totalSamplingLocations))
                                                
                        self.locationDescription = np.genfromtxt( self.path+'/Description_Details.csv', delimiter=',', dtype="|U50")
                        self.description = self.locationDescription[:,0]
                        self.surface = self.locationDescription[:,1]        
                        self.length_Description = len(self.locationDescription)                       
                        
                        for i in range(0,int(DS.totalSamplingLocations)):

                            rV = random.randint(self.lengthTotal*i,self.lengthTotal*(i+1))
                            self.randomValue_seat.append(rV) 
                            self.randomValue_description = random.sample(range(int(DS.totalSamplingLocations)),  self.length_Description)

                        self.log_q.put(["info","FD","randomValue_seat = "+ str(self.randomValue_seat)])
                        self.log_q.put(["info","FD","randomValue_Description = "+ str(self.randomValue_description)])
                        

                
                self.generateRandomLocations()        
                self.regimeprogress = 1
                Z=False 
            except Exception as e:

                self.log_q.put(["info","FD","Tail number not found in the database!!!!!!!!!!! Prompting operator to create one." + str(e)])
                self.regimeprogress = 3
                
                Z=False
                    

                   
        
     
    def Analyser(self, flightNumber, tailNumber, workOrder):
        """
        Migrate to Sample development page
        """      
        self.timer_and_page_close()
        self.sampling_page = Sample( flightNumber, tailNumber, workOrder, self.deviceId, self.telemetry_q, self.log_q, self.charger_connected)

        self.sampling_page.sig_Sample_close.connect(self.CancelFinish_Signal)
        self.sampling_page.sig_noSupplies.connect(self.close_NoSupplies) 
        self.sampling_page.sig_sampleSpectroError.connect(self.enableTimer)
 



    def generateRandomLocations(self):
        """
        Create Random locations from the list of seats and locations
        """     

        ############Generating Random locations################
        for i in range(0,int(DS.totalSamplingLocations)):
        
            self.seat = self.seatNo[self.randomValue_seat[i]]+self.seatRow[self.randomValue_seat[i]]
            self.SeatClass = len(self.seatClass[self.randomValue_seat[i]])
 
            
            self.Description = self.description[self.randomValue_description[i]]
            self.Surface = self.surface[self.randomValue_description[i]]
            
            
            if int(self.seatNo[self.randomValue_seat[i]])<10: ### Appending 0 for single digit value (from 0 to 9)###
                self.seat = '{:02d}'.format(int(self.seatNo[self.randomValue_seat[i]]))+self.seatRow[self.randomValue_seat[i]]
  
            
                
            if self.seatType[self.randomValue_seat[i]] == 'BULKHEAD':
                self.Description = 'BULKHEAD'
                self.Surface = 'Non-Floor'
                
            self.log_q.put(["info","FD","Selected values : seatNo:"+ self.seat+ ", seatRow:"+ self.seatRow[self.randomValue_seat[i]]+ ", seatClass:"+ self.seatClass[self.randomValue_seat[i]]+ ", Description:"+ self.Description+ ", Surface:"+ self.Surface])
            self.locationsLists = self.seat,self.seatRow[self.randomValue_seat[i]],self.seatClass[self.randomValue_seat[i]], self.Description, self.Surface
            DS.locationsList.append(self.locationsLists)
        self.log_q.put(["info","FD","Locations ="+ str(DS.locationsList)])
        ##################################################################            
