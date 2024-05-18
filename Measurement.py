import datetime
from pytz import timezone
import json
import math
import os
import pathlib
import shutil
import sys 
import time

# print ("measurement.py first call startin at : startupTime",datetime.datetime.now())

import Adafruit_BBIO.GPIO as GPIO

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from dateutil.relativedelta import relativedelta, MO

# print ("measurement.py second call startin at : startupTime",datetime.datetime.now())

from Analysed_output import dataAnalyse
import AnalyserSamplerComms as samplerComms
from LabSample_ID import labID
from locationDetails import edit_locationDetails
from Spectrometer_capture import Capture
from Valves_Pump_control import Valves
from VirtualKeyboard import VirtualKeyboard



import deviceStatus as DS 
from CSV_Files_Compare import Compare

import LED_Driver
import Sampler


GPIO.setup("P9_28", GPIO.OUT) ##Lab Drain valve (valve 2 in schematic)
GPIO.setup("P9_24", GPIO.OUT) ##Waste Drain valve (valve 1 in schematic)
GPIO.setup("P9_27", GPIO.OUT) ##valve connecting tube and exit valves
GPIO.setup("P9_29", GPIO.IN) ##Bubble detector
        
class Measure(QWidget):
    sig_measurementComplete = pyqtSignal(str, str, str, str) 
    sig_SpectrometerError = pyqtSignal() 
    sig_windowCancel =  pyqtSignal()
    sig_samplerWillNotReturn = pyqtSignal()
    sig_drain_problem = pyqtSignal()


    def __init__(self, cmd, seatNumber, surface, Class, description, flightNumber, tailNumber, workOrder, deviceId, telemetry_q, log_q, data, nextSeatNumber, charger_connected):
        super (Measure, self).__init__()
        Measure.setGeometry(self,0, 22, 480, 250) 
        
        self.cmd = str(cmd)
        self.seatNumber = seatNumber 
        self.surface = surface 
        self.Class = Class     
        self.description = description  
        self.AN=flightNumber
        self.Aircraft_ID = tailNumber      
        self.workOrder = workOrder 
        self.deviceId = deviceId        
        self.telemetry_q = telemetry_q
        self.log_q = log_q   
        self.data = data  
        self.nextSeatNumber = nextSeatNumber
        self.charger_connected = charger_connected
            

        self.Labanalyse_notrequired = True
        self.quitMiddle = False
        self.started = True    
        self.timeout = time.time() + 30 
        self.rarRetry = 0 
        DS.result = 0
        self.samplerWillNotReturn =False
        self.drained = False
        self.drained1 =False
        self.labSampleCollected = False
        self.rinseComplete = True
        self.error = True
        self.lowConfidence = False
        self.secondMeasurement = 0
        self.drain_problem = False
        self.secondmeasurement_complete = False
        
        self.keyboard1 = VirtualKeyboard(self.data, False, log_q)
        self.keyboard1.sigInputString.connect(self.notesMaintenance)  
        
        self.timeDisplay = QtWidgets.QLabel(self)
        self.timeDisplay.setGeometry(10, 110, 460, 25)
        self.timeDisplay.setAlignment(Qt.AlignTop) 
        
        self.statusDisplay = QtWidgets.QLabel(self)
        self.statusDisplay.move(40, 105)            
        self.statusDisplay.setGeometry(10, 140, 460, 50) 
        self.statusDisplay.setAlignment(Qt.AlignTop)        
        self.statusDisplay.setWordWrap(True)

        self.PermDisplay = QtWidgets.QLabel(self)
        self.PermDisplay.setGeometry(10, 155, 460, 50)
               
        self.Go_btn = QtWidgets.QPushButton("Go", self)
        self.Go_btn.resize(self.Go_btn.sizeHint())
        self.Go_btn.move(380, 210)
        self.Go_btn.clicked.connect(self.start)        
            
        self.Cancel_btn = QtWidgets.QPushButton("Cancel", self)
         
        self.Cancel_btn.resize(self.Cancel_btn.sizeHint())
        self.Cancel_btn.move(250, 210)
        self.Cancel_btn.clicked.connect(self.close_app)    

        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
        if DS.enableLabSample == "Yes":
            self.Lab_checkbox = QCheckBox("Lab sample", self)
            self.Lab_checkbox.setGeometry(20, 195, 200, 60)    
         
        
        if self.cmd == 'predeterminedLocation' or self.cmd == 'addLocation':
            self.log_q.put(["info","MT",'-------------Entering Sampling in '+str(self.cmd)+'---------------'])
            self.log_q.put(["info","MT",'Notes from addLocation '+str(self.data)])
            self.edit_btn = QtWidgets.QPushButton("Edit location", self)
            self.edit_btn.resize(self.edit_btn.sizeHint())
            self.edit_btn.move(10, 50)
            self.edit_btn.clicked.connect(self.edit) 

            self.presentDisplayText = QtWidgets.QLabel("Take sample at " + self.Class , self)
            self.presentDisplayText.setGeometry(10, 10, 450, 20)
            self.presentDisplayText.setWordWrap(True)        
            self.presentDisplay = QtWidgets.QLabel(self)
            self.presentDisplay.setGeometry(180, 20, 300, 100)
            QtWidgets.qApp.processEvents()
            if self.nextSeatNumber =='':
                self.presentDisplay.setText("Seat No: " + self.seatNumber+"\nArea: " + self.description + "\nSurface: " + self.surface)    
            else:
                self.presentDisplay.setText("Seat No: " + self.seatNumber+" ( Next : "+self.nextSeatNumber+" ) \nArea: " + self.description + "\nSurface: " + self.surface)    
            QtWidgets.qApp.processEvents()                
            self.show()

        elif self.cmd == 'singleSample':
            self.log_q.put(["info","MT",'-------------Entering Sampling in '+ self.cmd +'---------------'])        
            
            Notes = QtWidgets.QLabel("Notes", self)
            Notes.move(10, 20)
            self.Notes = QtWidgets.QTextEdit(self)
            self.Notes.setGeometry(90, 20, 320, 65)
            self.Notes.setObjectName("textEdit")
            self.statusDisplay.setText('Enter Notes then click Go')
          
            self.Notes.mousePressEvent = self.VKB1
            self.show()
            
        else:#Calibration sequence
            pass


        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","MT","charger_connected event cleared... "])
            self.log_q.put(["debug","MT","!!!!!!!! CLOSING MEASUREMENT WINDOW !!!!!!!"])
            self.Charger_Connected()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","MT","Timer started"])  

    def Charger_Connected(self):
     
        self.quitMiddle = True
        self.started = False
        if self.drain_problem:
            
            # QMessageBox.critical(self, 'Message',"Draining issues. \n Try replacing Residual bag.")
            # QtWidgets.qApp.processEvents()   
            if self.secondmeasurement_complete:
                self.sig_measurementComplete.emit(self.seatNumber, self.description, self.surface, self.Class)
            else:
                self.sig_drain_problem.emit()
        else:
            self.log_q.put(["debug", "MT", '^^^^^^^^^ Closing Measurement page due to due to '+str(DS.cause_Of_logout[DS.logout_cause_value])+' ^^^^^^^^^^^']) 
            self.sig_samplerWillNotReturn.emit() 
        self.timer_and_page_close()
          

    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","MT","!!!!!!!!!!! EXITING MEASUREMENT PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","MT","Timer stopped"])          

    def edit(self):
        """
        Opens a new page to edit the location details
        """
    
        self.timer_and_page_close()       
        self.log_q.put(["debug","MT",'************Entering Edit Location Module************'])
        self.editLocationDetails = edit_locationDetails(self.log_q, "Edit", self.seatNumber, self.description, self.surface, self.Class, self.data, self.charger_connected)
        self.editLocationDetails.show()
        self.editLocationDetails.sig_editComplete.connect(self.updateLocations)
        self.editLocationDetails.sig_editClose.connect(self.enableTimer) 
        self.editLocationDetails.sig_charger_connected.connect(self.Charger_Connected) 
        
         
    def updateLocations(self, seat, description, surface, Class, notes): 
        """
        Opens a new page to update the location details
        """    
        self.Class = Class
        self.seatNumber = seat        
        self.description = description
        self.surface = surface
        self.data = notes    

        self.log_q.put(["info","MT", 'Class: '+self.Class+'seat:'+self.seatNumber+'description: '+self.description+'surface:'+self.surface]) 
        self.presentDisplayText.setText("Take sample at " + self.Class)
        QtWidgets.qApp.processEvents()

        self.presentDisplay.setText("Seat No: " + self.seatNumber+" ( Next : "+self.nextSeatNumber+" ) \nArea: " + self.description + "\nSurface: " + self.surface)    
        QtWidgets.qApp.processEvents()
        self.enableTimer()

    def VKB1(self, event):
       
        if self.keyboard1.isHidden():
            self.log_q.put(["debug","MT", 'Virtual Keyboard enabled to enter Notes in '+self.cmd])
            self.keyboard1.show()
        else:
            self.keyboard1.hide()

    def VKBignore(self, event):
    # Used as a dummy click handler for when we don't want to do anything with a click
            pass

    def notesMaintenance(self, data):
        self.data = data
        self.log_q.put(["info","MT", 'Notes: '+self.data])        
        self.Notes.setText(self.data)


    def close_app(self):
        self.log_q.put(["debug","MT","CANCEL button clicked!!!!"])
        self.Cancel_btn.setEnabled(False)
        QtWidgets.qApp.processEvents()
        if self.quitMiddle:
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure you want to Quit?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            QtWidgets.qApp.processEvents()
                  
            if choice == QtWidgets.QMessageBox.Yes:
                if self.started:
                    self.started = False
                    self.error = False
                self.log_q.put(["debug", "MT", '........Exiting the application.....']) 

                self.statusDisplay.setText("Draining Residual solvent")
                QtWidgets.qApp.processEvents()
                LED_Driver.LED_OFF(self.log_q)
                self.drainvalve = Valves(self.log_q, False, 'waste', "rinse") #enable waste drain valve
                self.drainvalve.operateValves()
                self.suppliesUpdated()        

                if self.samplerWillNotReturn:
                    self.log_q.put(["debug", "MT", 'Sampler is not returning back']) 
                    self.sig_samplerWillNotReturn.emit()
                    
                else:
                    self.sig_windowCancel.emit()
                self.timer_and_page_close()                 
            else:
                self.Cancel_btn.setEnabled(True)
                QtWidgets.qApp.processEvents()
                self.log_q.put(["debug", "MT", 'Exit cancelled']) 
                pass        
        else:        
            self.sig_windowCancel.emit() 
            self.log_q.put(["debug", "MT", 'Emitting sig_windowCancel signal in else statement']) 
            self.timer_and_page_close()             

        

    def samplerConnectionCheck(self):
        """
        Checks whether the sampler is connected to the analyser
        """    
        QtWidgets.qApp.processEvents()        
        if self.started:     
            x = True
            while x:
                status = Sampler.S_cmd_Get_status()
                
                self.log_q.put(["debug","MT","---------------------START OF SAMPLER CONNECTION----------------" ])            
                
                if status['status'] == 'Disconnected':
                    if (status['last_cmd'] == 'Wipe'):   
                        x=False                        
                        pass
                    elif (status['last_cmd'] != 'Wipe'):

                        self.statusDisplay.setText('Please reconnect the Sampler!!')
                        QtWidgets.qApp.processEvents()            
                        
                        self.log_q.put(["debug","MT","--------------SAMPLER CONNECTION IN DISCONNECTED MODULE ----------------------"])

                        time.sleep(0.5)
                        if (time.time() > self.timeout):            
                            confirm = QMessageBox.question(self, 'Message',
                                        "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                        QMessageBox.No, QMessageBox.No)
                            if confirm == QMessageBox.No:
                                x=False
                                self.samplerWillNotReturn = True
                                self.close_app()
                            else:
                                self.log_q.put(["debug","MT","Keep waiting for another timeout"])
                                self.timeout = time.time() + 30      
                elif (status['status'] == 'Ready' or status['status'] == 'Busy'):  
                    self.timeout = time.time() + 30
                    
                    self.log_q.put(["debug","MT","--------------SAMPLER CONNECTION IN READY MODULE ----------------------"])
                    x=False
                    pass 
                                    
                else:
                    x=False
                    pass  
                loop =  QtCore.QEventLoop()    
                QTimer.singleShot(1000, loop.quit)  
        else:
            self.timer_and_page_close()             
 
 
    def samplerNotPresent(self):
        QMessageBox.warning(self, 'Message',"Sampler not in place. Return it back and try again")
        QtWidgets.qApp.processEvents()
        self.log_q.put(["debug","MT","Sampler is disconnected. Operator instructed to connect the sampler." ])
     
    def samplerError(self):
        QMessageBox.critical(self, 'Sampler Error',"Sampler error!!!! \n Contact Support.")
        QtWidgets.qApp.processEvents()
        self.started = False
        self.quitMiddle = False
        self.log_q.put(["debug","MT","Sampler entered into unreceoverable state. Operator instructed to return it back to manufacturer." ])        
        if DS.logout_cause_value != 3:
            drainvalve = Valves(self.log_q, False, "waste", "calibrate")
            drainvalve.operateValves()
        self.close_app()
        
    def start(self):
        self.log_q.put(["info","MT","Go button clicked"])
        LED_Driver.LED_heaterON(self.log_q)
#######Time stamp from start of display of sampling locations#############
        if DS.samplingCount==0:
            DS.samplingStartTime = datetime.datetime.now()
            self.log_q.put(["info","MT","Sampling started at "+str(DS.samplingStartTime)])
#############################################################################        
        DS.samplingCount += 1
        self.Go_btn.setDisabled(True)
        if self.cmd !='singleSample':
            self.edit_btn.setDisabled(True)
        if self.cmd == 'singleSample':
            self.Notes.mousePressEvent = self.VKBignore   #ignore clicks in Notes box (only for Single Sample here)
        self.quitMiddle = True 
        #make sure there's a Sampler there before we start
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents() 
        if self.started:        
            self.squirtSolvent(False, False, True)
        else:
            self.timer_and_page_close()  
            
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()       
        if self.started:            
            while (not samplerComms.Wipe(self.log_q)):
                pass
                
            
        else:
            self.timer_and_page_close()

        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()         
        if self.started:             
            status = self.statusModule()
            if status:
                DS.sampleTime = datetime.datetime.now(tz=timezone(DS.ourTimezone)).isoformat()
                pass
            else:
                self.commErrorAfterSampling()
        else:
            self.timer_and_page_close()


        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()   
              
        # error = True ###This is to make sure that if there is any error while samle extraction we need to rinse the sampler pad and start new measurement
        while self.error:
            QtWidgets.qApp.processEvents() 
            if self.started:  
                QtWidgets.qApp.processEvents()    
                self.log_q.put(["info","MT","Sampler rotated Fast after wipe OK"]) 
                self.statusDisplay.setText('Wetting Sampler pad')
                QtWidgets.qApp.processEvents()
                # wet pad for sample extraction
                DS.postSamplingSolventVolume = 0##Need to initialise to 0 if there is any error while rotation. This needs to be added everytime
                x=True
                while x:         
                    QtWidgets.qApp.processEvents()
                    samplerRotate_status = samplerComms.samplerRotate(self.log_q,"Fast","postSolventSquirt")
                    self.log_q.put(["debug","MT","When extracting sample, Sampler Fast Rotate_status = "+ str(samplerRotate_status)])
                    if samplerRotate_status == 1:  ##Successful sampler rotation
                        DS.sampler_faultRetry = 0
                        x = False
                        self.cS = self.captureSample() #Perform experiemnt and show the result
                        self.log_q.put(["debug","MT","State of capture sample, self.cS = "+ str(self.cS)])
                        if self.cS == 1: ###Success
                            self.error = False
                        elif self.cS == 2: ###Sampler error
                            return
                        elif self.cS == 3 or self.cS == 4:
                            self.error = False
                            self.log_q.put(["debug","MT","EXITTING!!!!!!!!! "])
                            self.Charger_Connected()
                            return
                        else:
                            self.spectrometerNotFoundError()                          
                    elif samplerRotate_status == 2:  ##Rotate state is error
                        x = False
                        self.commErrorAfterSampling()
                    elif samplerRotate_status == 3:  ##Sampler error unrecovered                        
                        x = False   
                        self.samplerError()
                    else: ## Sampler disconnected
                        self.samplerNotPresent()
                        x = False
                        self.commErrorAfterSampling()
            else:
                self.error = False
                self.timer_and_page_close()
          

    def squirtSolvent(self, refCheck, calibrate, firstSolventSquirt):
        """
        Squirts solvent for sampling/Calibration
        """    
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:           
                
            self.calibrate = calibrate
            if firstSolventSquirt:
                self.log_q.put(["info","MT",'-------------Initializing Solvent Squirt---------------'])        

            self.statusDisplay.setText('Wetting Sampler pad')
            QtWidgets.qApp.processEvents()
            if refCheck:
                DS.calibrateVolume = 0
                sampleType = "calibrate"
            elif self.calibrate:
                DS.calibrateVolume = 0
                sampleType = "calibrate"
            else:
                DS.sampleSquirtVolume = 0
                sampleType = "preSolventSquirt"
 
            x=True
            while x:
                if self.started:
                    QtWidgets.qApp.processEvents() 
                    samplerRotate_status = samplerComms.samplerRotate(self.log_q,"Slow",sampleType)
                    self.log_q.put(["debug","MT","When sampler rotating slow, Sampler Slow Rotate_status = "+ str(samplerRotate_status)])
                    if samplerRotate_status == 1: ##Successful sampler rotation
                        QtWidgets.qApp.processEvents()
                        DS.sampler_faultRetry = 0
                        x=False  
                        if self.calibrate:
                            return True ### if successful rotation                     
                    elif samplerRotate_status == 2: ##sampler rotation error
                        pass
                    elif samplerRotate_status == 3:  ##Sampler error unrecovered                        
                        x = False   
                        self.samplerError()  
                        if self.calibrate:
                            return False    ### To handle the sampler when it is not recovered from error
                    else: ##Sampler disconnected                   
                        self.samplerNotPresent()                    
                else:
                    x=False
                    self.timer_and_page_close()
                    self.log_q.put(["debug","MT","Charger connected..."])
                    return                     
        else:
            self.timer_and_page_close()                                     


    def Wipe(self): 
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:            
            if samplerComms.Wipe(self.log_q):
                return True
            else: 
                return False                
        else:
            self.timer_and_page_close()    
        

    def statusModule(self):
        """
        Checks status of the analyser
        """    
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:           
            self.log_q.put(["info","MT","Sampler ready for sampling"])    
            self.statusDisplay.setText('Remove sampler for sampling')
            QtWidgets.qApp.processEvents()
            GPIO.output("P9_27", GPIO.HIGH)
            GPIO.output("P9_24", GPIO.HIGH)
            GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
            time.sleep(3)
            GPIO.output("P9_27", GPIO.LOW)
            GPIO.output("P9_24", GPIO.LOW)
            GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve 

            loop = True
            while loop:
                # Sampler status requested 
                self.statusResponse = samplerComms.Status(self.log_q)
                
                if self.statusResponse == 1:
                    self.sCM = self.statusCheckModule()
                    if self.sCM:
                        
                        self.log_q.put(["info","MT","**********Status Module successfully completed *******"])
                        loop = False
                        return True
                    else:
                        pass
                elif self.statusResponse == 0:
                
                    self.sCM = self.statusCheckModule()
                    if self.sCM:
                        self.log_q.put(["info","MT","**********Status Module in error *********"])
                        loop = False                        
                        return False
                        
                    else:
                    
                        self.log_q.put(["info","MT","**********Status Module in error *********"])
                        loop = False                        
                        return False
                else: ###self.statusResponse =2 which means sampler will not return
                    loop = False
                    self.samplerWillNotReturn = True
                    self.close_app()
                    

        else:
            self.timer_and_page_close()             
 
    def statusCheckModule(self):
        x=True
        while x:    
            self.statusCheck = samplerComms.checkStatus(self.log_q)
            if self.statusCheck ==0:
                x=False
                return True       
            elif self.statusCheck==1:
                self.statusDisplay.setText('Remove sampler and press trigger button for sampling')
                QtWidgets.qApp.processEvents()                
            else:
            
                x=False
                return False               
            

    def commErrorAfterSampling(self):  
        """
        If there is an error after sampling, following steps will be performed.
        """    
        if self.started:     
            QMessageBox.warning(self,"Sampler Error","Sampler error detected. \n Redo the sample.")
            self.log_q.put(["info","MT",'---Start of commErrorAfterSampling Module----'])
            self.statusDisplay.setText("Draining Residual solvent")
            QtWidgets.qApp.processEvents()
            self.drain = Valves(self.log_q, False, 'waste', 'preSolventSquirt')
            if self.drain.operateValves():
                self.rinse()  #Start RINSE cycle
                if self.calibrate:
                    self.drain = Valves(self.log_q, False, 'waste', 'calibrate')
                else:       
                    self.drain = Valves(self.log_q, False, 'waste', 'rinse')
                self.drain.operateValves()
                self.statusDisplay.setText('Sampler pad rinsed and solvent drained')
                QtWidgets.qApp.processEvents()     
                self.log_q.put(["info","MT",'---End of commErrorAfterSampling Module----'])
                self.start()
            else:
                self.log_q.put(["info","MT",'---Error while draining in commErrorAfterSampling module----'])
                self.drain_problem = True
                self.Charger_Connected()
        else:
            self.timer_and_page_close()          
         
 

        
#Operations performed in captureSample module: 1. Set brightness = 75% (set brightness function), 
#2. Capture the sample spectrum(Calling Sample1 class)
    def captureSample(self):
        """
        Capture the sample, analyse and display the result
        0 - False, 1 - True, 2 - Sampler error, 3 - Charger connected
        4 - Draining issues
        """    
       
        if self.started:   
            self.timeout = time.time() + 30  
            self.Cancel_btn.setEnabled(False)
            self.statusDisplay.setText('Setting operational temperature')
            QtWidgets.qApp.processEvents()
############ if the system is idle for more than 5 mins, the LED heater turns OFF#######
    ######## This segment will turn ON the heater if the Led heater turns off ########
            temp = LED_Driver.getTemp('led',self.log_q)
            if temp < DS.targetTemp - 1:
                LED_Driver.LED_heaterON(self.log_q)
    ########################################################################################            
            
            checkLoop_1=True
            while checkLoop_1:
                LED_state = LED_Driver.LED_ON(self.log_q,False)###Checking LED is false
                self.log_q.put(["debug","MT","LED state (1-success, 2-Board error, 3-Sampler disconnected)"])
                self.log_q.put(["debug","MT","LED state = "+ str(LED_state)])
                if LED_state == 2:###LED heater error
                    checkLoop_1 = False
                    QMessageBox.warning(self,"LED Error","LED Heater Error \n Contact Support")
                    QtWidgets.qApp.processEvents()
                    self.spectrometerNotFoundError() #exit is the only choice
                elif LED_state == 3: ###Sampler disconnected error
                    self.samplerNotPresent()
                    QtWidgets.qApp.processEvents()
                    if (time.time() > self.timeout):            
                        confirm = QMessageBox.question(self, 'Message',
                                    "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                    QMessageBox.No, QMessageBox.No)
                        QtWidgets.qApp.processEvents()
                        if confirm == QMessageBox.No:
                            checkLoop_1 = False
                            x=False
                            self.samplerWillNotReturn = True
                            self.close_app()
                        else:
                            self.log_q.put(["debug","MT","Keep waiting for another timeout"])
                            self.timeout = time.time() + 30      
                else:### All requirements satisfied.
                    checkLoop_1 = False
                    self.log_q.put(["info","MT","Capturing Sample spectrum"])
                    self.statusDisplay.setText('Analysing sample')
                    QtWidgets.qApp.processEvents()
                    self.sampleCapture = Capture(self.log_q)  
                    self.spectroFound = self.sampleCapture.Sample()
                    if self.spectroFound:
                        self.log_q.put(["info","MT","Sample spectrum captured"])  
                        LED_Driver.LED_OFF(self.log_q)
                        # self.log_q.put(["info","MT","DS.postSamplingSolventVolume = "+str(DS.postSamplingSolventVolume)])
                        self.log_q.put(["info","MT","Calculating results"])

                #Result calculation performed in here
                        self.output = dataAnalyse(self.log_q)
                        (self.result1, DS.confidence, DS.error, DS.absorbance) = self.output.results()  
                        DS.result = DS.result+int(round(self.result1))
                        DS.confidence = int(round(DS.confidence))
                        self.storeData()
                       
                        self.labCheckBoxUnchecked = True
                        if DS.enableLabSample == "Yes":
                            if (self.Lab_checkbox.isChecked() or DS.confidence<=DS.confidenceThreshold):
                                if self.Lab_checkbox.isChecked():
                                    self.labCheckBoxUnchecked = False
                                else:
                                    pass
                                if self.labCheckBoxUnchecked and DS.confidence<=DS.confidenceThreshold:
                                    self.Lab_checkbox.toggle()
                                else:
                                    pass
                                   
                                self.PermDisplay.setText("Result: Permethrin : " + str(DS.result) + "  Confidence: " + str(DS.confidence))
                           
                        else:
                            
                            
                            self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")
                            if not self.drainvalve.operateValves():
                                self.log_q.put(["info","MT","AFTER FIRST MEASUREMENT, Error while draining"])
                                self.drain_problem = True
                                return 4
                            else:
                                self.log_q.put(["info","MT","***********Entering for second capture********"])
                                QtWidgets.qApp.processEvents()
                                DS.postSamplingSolventVolume = 0##Need to initialise to 0 if there is any error while rotation. This needs to be added everytime
                                x=True
                                while (x):  
                                    if self.started:
                                        self.statusDisplay.setText('Wetting Sampler pad')
                                        QtWidgets.qApp.processEvents()
                                        # wet pad for sample extraction                            
                                        QtWidgets.qApp.processEvents()
                                        self.log_q.put(["debug","MT","Second capture, SENDING FAST ROTATE COMMAND "])
                                        self.slowRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","postSolventSquirt")    
                                        self.log_q.put(["debug","MT","Second capture, Sampler Fast Rotate Response = "+ str(self.slowRotateResponse)])
                                        if self.slowRotateResponse == 1: ##Successful sampler rotation

                                            QtWidgets.qApp.processEvents()
                                            DS.sampler_faultRetry = 0
                                            x=False                                
                                            self.statusDisplay.setText('Setting operational temperature')
                                            QtWidgets.qApp.processEvents()  
                                            checkLoop_2=True
                                            while checkLoop_2:
                                                LED_state = LED_Driver.LED_ON(self.log_q,False)###Checking LED is false
                                                self.log_q.put(["debug","MT","LED state (1-success, 2-Board error, 3-Sampler disconnected)"])
                                                self.log_q.put(["debug","MT","LED state = "+ str(LED_state)])
                                                if LED_state == 2:###LED heater error
                                                    checkLoop_2 = False
                                                    QMessageBox.warning(self,"LED Error","LED Heater Error \n Contact Support")
                                                    QtWidgets.qApp.processEvents()
                                                    self.spectrometerNotFoundError() #exit is the only choice
                                                elif LED_state == 3: ###Sampler disconnected error
                                                    self.samplerNotPresent()
                                                    QtWidgets.qApp.processEvents()
                                                    if (time.time() > self.timeout):            
                                                        confirm = QMessageBox.question(self, 'Message',
                                                                    "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                                                    QMessageBox.No, QMessageBox.No)
                                                        QtWidgets.qApp.processEvents()
                                                        if confirm == QMessageBox.No:
                                                            x=False
                                                            checkLoop_2 = False
                                                            self.samplerWillNotReturn = True
                                                            self.close_app()
                                                        else:
                                                            self.log_q.put(["debug","MT","Keep waiting for another timeout"])
                                                            self.timeout = time.time() + 30      
                                                else:### All requirements satisfied.
                                                    checkLoop_2 = False 
                                                self.log_q.put(["info","MT","Capturing Sample spectrum after rinse"])
                                                self.statusDisplay.setText('Analysing sample')
                                                QtWidgets.qApp.processEvents()
                                                self.sampleCapture = Capture(self.log_q)  
                                                self.spectroFound = self.sampleCapture.Sample()
                                                if self.spectroFound:
                                                    self.log_q.put(["info","MT","Sample spectrum captured"])  
                                                    # self.LEDrst()
                                                    LED_Driver.LED_OFF(self.log_q)
                                                    # self.log_q.put(["info","MT","DS.postSamplingSolventVolume = "+str(DS.postSamplingSolventVolume)])
                                                    self.log_q.put(["info","MT","Calculating results after rinse"])

                                                #Result calculation performed in here
                                                    self.output = dataAnalyse(self.log_q)
                                                    (self.result2, self.confidence2, self.error, self.absorbance) = self.output.results()  
                                                    if int(round(self.confidence2))>=70:
                                                        DS.result = DS.result+int(round(self.result2))
                                                    # self.confidence = int(round(self.confidence))
                                                    self.secondmeasurement_complete= True
                                                    self.storeData()  #### Storing the second spectrum
                                                    self.PermDisplay.setText("Result: Permethrin : " + str(DS.result) + "  Confidence: " + str(DS.confidence))

                                                    self.log_q.put(["info","MT","Results: Permethrin : "+str(DS.result)+" mg/sq.m, Confidence : "+ str(DS.confidence)+" %, Error = "+str(DS.error)+" %, Absorption = "+str(DS.absorbance)])                    
                                                   
                                                    # self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt")        
                                                    # self.statusDisplay.setText('Solvent drained')
                                                    # QtWidgets.qApp.processEvents()
                                                else:
                                                    x = False
                                                    checkLoop_2 = False 
                                                    self.Cancel_btn.setEnabled(True)
                                                    return 0                                                
                                        elif self.slowRotateResponse == 2: ##Sampler rotation error
                                            x = False
                                            self.commErrorAfterSampling()
                                            return
                                            
                                        elif self.slowRotateResponse == 3:  ##Sampler error unrecovered                        
                                            x = False  
                                            self.samplerError()
                                            return 2
                                        else: ##Sampler disconnected
                                            self.samplerNotPresent()
                                    else:
                                        x = False 
                                        self.log_q.put(["info","MT","identifying"])                    
                                        self.timer_and_page_close()
                                        return 3
                                self.log_q.put(["info","MT","***********Exiting after second capture********"])                    
                                
                        self.log_q.put(["info","MT","Results: Permethrin : "+str(DS.result)+" mg/sq.m, Confidence : "+ str(DS.confidence)+" %, Error = "+str(DS.error)+" %, Absorption = "+str(DS.absorbance)])  
                                            
        #######Time stamp at the time of result display #############
                        self.samplingFinishTime = datetime.datetime.now()
                        self.log_q.put(["info","MT","Result displayed at "+str(self.samplingFinishTime)])
                        self.timeDifference = relativedelta(self.samplingFinishTime, DS.samplingStartTime)
                        
                        self.log_q.put(["info","MT","Time taken to complete sampling is "+str(self.timeDifference.minutes)+" : "+str(self.timeDifference.seconds)])
                        
                        if DS.samplingCount  == 1 or self.cmd == 'singleSample':
                            DS.totalTime = self.timeDifference
                            
                        else:
                            DS.totalTime =self.timeDifference
                        self.timeDisplay.setText("Total time "+str('{:02d}'.format(DS.totalTime.minutes))+" : "+str('{:02d}'.format(DS.totalTime.seconds))+" (mm:ss)")
                        self.totalTime_inSec = DS.totalTime.minutes * 60 + DS.totalTime.seconds
        #############################################################################                   
                        
                        if DS.absorbance >=2:
                            QMessageBox.warning(self, "High Absorption" ,"Overrange result")
                            QtWidgets.qApp.processEvents()  
                            
                        if DS.absorbance <(-0.1) and DS.confidence == 0:
                            QMessageBox.warning(self, "Low Absorption" ,"Redo calibration before sampling any new location!!")
                            QtWidgets.qApp.processEvents()  


                        self.addNotes = addNotes(self.log_q, self.data, DS.result, DS.confidence)
                        self.addNotes.show()
                        self.addNotes.sig_continue.connect(self.Vial)
                        
                      
                        self.Cancel_btn.setEnabled(True)   
                        return 1                
                    else:
                        self.Cancel_btn.setEnabled(True)
                        return 0

        else:
            self.timer_and_page_close()  
            return 3            


    def spectrometerNotFoundError(self):
        """
        Unresponsive spectrometer during measurement will emit signal to return the analyser to the manufacturer
        """    
        if self.started: 
            QMessageBox.warning(self, "Spectrometer Error" ,"Spectrometer Error")
            self.log_q.put(["error", "MT", '-----SPECTROMETER NOT FOUND!!!------']) 
            QtWidgets.qApp.processEvents() 
            
            self.statusDisplay.setText("Draining Residual solvent")
            QtWidgets.qApp.processEvents()
            self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")
            self.drainvalve.operateValves()
            DS.analyserSolventCount= round(DS.analyserSolventRemaining/DS.sampleVolume)   #Updating device status values                       
            self.log_q.put(["info","MT","Solvent bag available for "+str(DS.analyserSolventCount)+" samples"])
            self.log_q.put(["info","MT","ANALYSER SOLVENT REMAINING  = "+str(round(DS.analyserSolventRemaining,1))])
            
            DS.analyserWasteCount= round(DS.analyserWasteRemaining/DS.sampleVolume)   #Updating device status values 
            self.log_q.put(["info","MT","Waste bag available for "+str(DS.analyserWasteCount)+" samples"]) 
            self.log_q.put(["info","MT","ANALYSER WASTE REMAINING  = "+str(round(DS.analyserWasteRemaining,1))])
            self.started = False
            self.timer_and_page_close()
            if self.secondmeasurement_complete:
                self.sig_measurementComplete.emit(self.seatNumber, self.description, self.surface, self.Class)   
            else:
                self.sig_SpectrometerError.emit()      
        else:
            self.timer_and_page_close()            

    def Vial(self, notesAppend):
        """
        Prompts the user to enter the vial id if
        1. the confidence is less than 50% or 
        2. if the user wants to check the result experimentally
        """    
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:        
            self.appendNotes = notesAppend
            self.data = self.appendNotes
            
            if self.cmd == 'singleSample':
                self.Notes.setText(self.data)
            self.labCheckBoxUnchecked = True
            if DS.enableLabSample == "Yes":
                if self.Lab_checkbox.isChecked() or DS.confidence<=DS.confidenceThreshold:
                    if self.Lab_checkbox.isChecked():
                        self.labCheckBoxUnchecked = False
                    else:
                        pass
                    if self.labCheckBoxUnchecked and DS.confidence<=DS.confidenceThreshold:
                        self.Lab_checkbox.toggle()
                    else:
                        pass
                    
                    self.secondMeasurement = 1
                    self.vialID = labID(self.log_q)
                    self.vialID.show()

                    self.vialID.sig_labID.connect(self.vialID_entered)
                    
                    self.vialID.sig_labIDCancelled.connect(self.Lab_ID_Cancelled)

                    # self.vialID.sig_labIDCancelled.connect(self.Lab_checkbox.toggle)                
                    # # self.vialID.sig_labIDCancelled.connect(self.storeData)   
                    # self.vialID.sig_labIDCancelled.connect(self.resultQ)
            else:
                # self.storeData()
                self.resultQ()

        else:
            self.timer_and_page_close() 
            
    def Lab_ID_Cancelled(self):
        self.lowConfidence = True
        self.show()
        self.Lab_checkbox.toggle()
        self.resultQ()
     

    def vialID_entered(self):
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:        
   
            self.show()
            self.Labanalyse_notrequired = False 
            self.log_q.put(["info","MT","Draining the sample to check in LAB Sample Vial"])
            QMessageBox.about(self, "Draining LAB SAMPLE" ,"Make sure that the vial ID "+DS.analyserLabSampleID+"_A is in place to collect the sample ") 
            QtWidgets.qApp.processEvents()
            self.statusDisplay.setText('Draining into lab sample vial')
            QtWidgets.qApp.processEvents()

            self.labSampleCollected = True
            self.L_sample = Valves(self.log_q, False, "lab", "postSolventSquirt")
            self.L_sample.operateValves()
            self.statusDisplay.setText('Drained')
            QtWidgets.qApp.processEvents() 

            # self.storeData()
            self.resultQ()
        else:
            self.timer_and_page_close() 


#Result files named using flight details and stored in the reuslts folder        
    def storeData(self):
        """
        Stores the data in a separate folder
        """  
        self.log_q.put(["debug","MT","########## STORING RESULTS###############"])
        now = datetime.datetime.now()
        self.now_str = str(now.strftime("%Y-%m-%d_%H_%M_%S"))  
        self.date_str = str(now.strftime("%Y-%m-%d"))  
        DS.messageType = 'Result'
        # if self.secondMeasurement==1:         
        if self.cmd == 'singleSample':
            empty_MS_notes = {"Notes":"notes"}
            self.notes_data = self.Notes.toPlainText()
            
            self.mynewLocation_notes = []
            self.myLocation_notes = empty_MS_notes
            self.myLocation_notes["Notes"] = self.notes_data

            directory = DS.resultsDirectory + 'Maintenance_data/SingleSample_data'
            self.log_q.put(["debug","MT","Creating a folder named SS_"+self.now_str]) 
            dir = os.path.join(directory, "SS_"+self.now_str)
                            
            if not os.path.exists(dir):
                os.makedirs(dir)
            self.source = DS.localRefFilesDirectory
            self.destination = DS.resultsDirectory + 'Maintenance_data/SingleSample_data/SS_'+self.now_str
                          
        else:
            directory = DS.resultsDirectory
            dir = os.path.join(directory, self.AN+'_'+self.Aircraft_ID+'_'+self.date_str)
                        
            if not os.path.exists(dir):
                os.makedirs(dir)
            self.source = DS.localRefFilesDirectory
            self.destination = DS.resultsDirectory + self.AN+'_'+self.Aircraft_ID+'_'+self.date_str
            self.log_q.put(["debug","MT","Destination folder name is "+self.destination])
        files = os.listdir(self.source)
                    
        x=[f.name for f in pathlib.Path(self.source).iterdir() if f.is_file()]
 
        for file in x:
            shutil.copy(DS.localRefFilesDirectory + 'dark.csv', self.destination)
            shutil.copy(DS.localRefFilesDirectory + 'reference.csv', self.destination)
            shutil.copy(DS.localRefFilesDirectory + 'sample.csv', self.destination)
        os.chdir(self.destination)
        y=os.listdir('.')

        self.log_q.put(["debug","MT","self.secondmeasurement_complete is "+str(self.secondmeasurement_complete)])
        if not self.secondmeasurement_complete:
            os.rename('dark.csv', 'dark_'+self.now_str+'.csv')
            os.rename('reference.csv', 'reference_'+self.now_str+'.csv')
            self.log_q.put(["debug","MT","Dark and reference files stored "])
        else:
            
            os.remove('dark.csv')
            os.remove('reference.csv')  
            self.log_q.put(["debug","MT","Dark and reference files removed "])
        os.rename('sample.csv', 'sample_'+self.now_str+'.csv')



        # if self.Labanalyse_notrequired:
            # if len(y) == 3:
                # os.rename('dark.csv', 'dark_'+self.now_str+'.csv')
                # os.rename('reference.csv', 'reference_'+self.now_str+'.csv')
                # os.rename('sample.csv', 'sample_'+self.now_str+'.csv')

            # else:
                # os.rename('sample.csv', 'sample_'+self.now_str+'.csv')
                # os.remove('dark.csv')
                # os.remove('reference.csv')

        # else:
            # if len(y) == 3:
                # os.rename('dark.csv', 'dark_'+self.now_str+'.csv')
                # os.rename('reference.csv', 'reference_'+self.now_str+'.csv')
                # os.rename('sample.csv', 'sample_'+DS.analyserLabSampleID+'.csv')

            # else:
                # os.rename('sample.csv', 'sample_'+DS.analyserLabSampleID+'.csv')
                # os.remove('dark.csv')
                # os.remove('reference.csv')

        self.log_q.put(["info","MT", 'Files moved to determined location']) 
        os.chdir("/home/debian/PSS/") 
        self.log_q.put(["debug","MT","########## RESULTS STORED ###############"])
        return
        # else:
            # self.resultQ()
            # self.valveSelection()        
        

    def resultQ(self):
        """
        Uploads the data to the cloud
        """  
        if DS.enableLabSample == "Yes":
            self.Lab_checkbox.setEnabled(False)
        sampleResult = []
        todaystr = str(datetime.date.today())
        tzoffset = datetime.datetime.now(timezone(DS.ourTimezone)).strftime('%z')
        if self.cmd == 'singleSample':
            result_format = '''{ "deviceId": "%s", "uploadDate": "%s", "messageType": "%s","resultStatus": "%s",
            "workOrderId": %d, "operatorId": %d,"flight":{"operatingAirlineCode":"%s", "flightDate":"%s",
            "flightNumber":"%s", "planeModel":"%s","planeSeries":"%s", "tailNumber":"%s"},"testDate":"%s",
            "regime":{"regimeId": %d,"RegimeInstanceId": "%s", "aircraftType": "%s", "aircraftConfig": "%s",
            "results":[{ "sampleDate": "%s","locationId": %d, "location1": "%s", "location2": "%s", "location3": "%s", 
            "surface": "%s", "wipeTime": %d,"padAge": %d, "result": %d, "confidence": %d, "analyserBatteryLevel": %d,
            "samplerBatteryLevel": %d, "samplerReconnectTime": %d,"samplerSampleStatus": %d, "labSampleID":"%s", "notes": "%s"}]}}'''
            
            sampleResult = result_format%(DS.deviceName, todaystr, DS.messageType, 'Ongoing', 
                                         self.totalTime_inSec, DS.totalTime.seconds,'QF', todaystr, 
                                        '102', DS.ourSiteIataCode, tzoffset, 
                                        'ABC', todaystr,
                                        DS.error, str(DS.samplerID), DS.analyserSolventID, DS.userID,  
                                        str(DS.sampleTime), int(DS.absorbance * 1000), self.cmd, self.cmd, self.cmd, 
                                        self.cmd, DS.samplerTriggerTime, DS.analyserPadAge,DS.result, DS.confidence, DS.analyserBattery, 
                                        DS.samplerBattery, DS.samplerReconnectTime, DS.samplerLastSampleStatus, DS.analyserLabSampleID, self.myLocation_notes["Notes"])
        
           
            
            with open(DS.resultsDirectory + 'Maintenance_data/SingleSample_data/SS_'+self.now_str+'/SS_'+self.now_str+'.json', "w", encoding = "utf-8") as json_dat:
                json.dump(sampleResult,json_dat, indent=2) 

            self.log_q.put(["info","MT",'SS_'+self.now_str+".json"+ ' file updated'])  
            self.telemetry_q.put(sampleResult)
            # self.telemetry_q.put(json.dumps(DS.format_dev_status()))  
            
        
        else:
            result_format = '''{ "deviceId": "%s", "uploadDate": "%s", "messageType": "%s","resultStatus": "%s",
            "workOrderId": %d, "operatorId": %d,"flight":{"operatingAirlineCode":"%s", "flightDate":"%s",
            "flightNumber":"%s", "planeModel":"%s","planeSeries":"%s", "tailNumber":"%s"},"testDate":"%s",
            "regime":{"regimeId": %d,"RegimeInstanceId": "%s", "aircraftType": "%s", "aircraftConfig": "%s",
            "results":[{ "sampleDate": "%s","locationId": %d, "location1": "%s", "location2": "%s", "location3": "%s", 
            "surface": "%s", "wipeTime": %d,"padAge": %d, "result": %d, "confidence": %d, "analyserBatteryLevel": %d,
            "samplerBatteryLevel": %d, "samplerReconnectTime": %d,"samplerSampleStatus": %d, "labSampleID":"%s", "notes": "%s"}]}}'''
            
            sampleResult = result_format%(DS.deviceName, todaystr, DS.messageType, 'Ongoing', 
                                         self.totalTime_inSec, DS.totalTime.seconds,self.workOrder["Flight"]["OperatingAirlineCode"], todaystr, 
                                        self.workOrder["Flight"]["FlightNumber"], DS.ourSiteIataCode, tzoffset, self.workOrder["Flight"]["TailNumber"], todaystr,                                        
                                        DS.error, str(DS.samplerID), DS.analyserSolventID,  
                                        DS.userID,  str(DS.sampleTime), int(DS.absorbance * 1000), self.Class, self.seatNumber,
                                        self.description, self.surface, 
                                        DS.samplerTriggerTime, DS.analyserPadAge,DS.result, DS.confidence, DS.analyserBattery, DS.samplerBattery, DS.samplerReconnectTime,
                                        DS.samplerLastSampleStatus, DS.analyserLabSampleID, self.data)
            with open(self.destination + '/' + 'sample_' + self.now_str + '.json', "w", encoding = "utf-8") as json_dat:
                json.dump(sampleResult,json_dat, indent=2)

            self.telemetry_q.put(sampleResult)
            # self.telemetry_q.put(json.dumps(DS.format_dev_status()))  
        
        self.valveSelection() 
        
#If the operator decides to test the sample in the lab before analysis, it can be done by selecting the "Lab sample" checkbox in the page
    def valveSelection(self):
        """
        Drain the sample
        """     
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents() 
        self.lab_rinse_cycle_no = 1
        self.secondmeasurement_complete= True
        if self.started:        
            if self.Labanalyse_notrequired:
    #Waste drain valve will be enabled if the "Lab sample" checkbox is not clicked
                QtWidgets.qApp.processEvents()
                self.statusDisplay.setText('Draining in Residual bladder')
                QtWidgets.qApp.processEvents()
                time.sleep(0.5)
                self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt2")
                if self.drainvalve.operateValves():
                    self.show()
                    self.statusDisplay.setText('Drained')
                    QtWidgets.qApp.processEvents()      
                else:
                    self.log_q.put(["error","MT",'---Error while draining after 2nd measurement. So results were uploaded and exiting to sampledevelopment page----'])
                    
                    self.drain_problem = True
                    self.Charger_Connected()
                    return
            else:
                pass

            if self.labSampleCollected:
                self.log_q.put(["info","MT",'-------------Entering Rinse cycle after Lab sample---------------']) 
                for self.lab_rinse_cycle_no in range (DS.lab_RinseCountReqd):
                    self.lab_rinse_cycle_no += 1
                    self.statusDisplay.setText('Rinsing lab sample tube. Rinse cycle '+str(self.lab_rinse_cycle_no)+' of '+str(DS.lab_RinseCountReqd))
                    QtWidgets.qApp.processEvents()
                    self.log_q.put(["info","MT",'lab_rinse_cycle_no = %d'%self.lab_rinse_cycle_no]) 
                    
                    QtWidgets.qApp.processEvents() 
                    DS.sampleRinseSquirtVolume = 0
                    x=True
                    while (x):                    
                        QtWidgets.qApp.processEvents()
                        if self.started:
                            self.fastRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","rinse") 
                            self.log_q.put(["debug","MT","Rinse cycle after lab sample, Sampler Fast Rotate Response = "+ str(self.fastRotateResponse)])
                            if self.fastRotateResponse == 1: ##Successful sampler rotation
                                DS.sampler_faultRetry = 0
                                x=False                                 
                                if self.lab_rinse_cycle_no == DS.lab_RinseCountReqd:
                                    QMessageBox.about(self, "Draining LAB SAMPLE" ,"Replace the vial ID "+DS.analyserLabSampleID+"_A with "+DS.analyserLabSampleID+"_B to collect the residual solvent ") 
                                    QtWidgets.qApp.processEvents()
                                    QtWidgets.qApp.processEvents()
                                    self.drainvalve = Valves(self.log_q, False, "lab", "labRinse") 
                                else:
                                    self.drainvalve = Valves(self.log_q, False, "Rinse_after_labSample", "Rinse_after_labSample")     
                                if not self.drainvalve.operateValves():
                                    x= False
                                    self.log_q.put(["info","MT",'---Error while draining in valveSelection Module, in labSampleCollected, logging out----'])
                                    self.drain_problem = True
                                    self.Charger_Connected()
                            elif self.fastRotateResponse == 2: ##Sampler rotation error
                                pass
                            elif self.fastRotateResponse == 3:  ##Sampler error unrecovered                        
                                x = False   
                                self.samplerError()                            
                            else: ##Sampler disconnected
                                self.samplerNotPresent()
                        else:
                            x = False
                            self.timer_and_page_close()
                            return                            
                    
                self.labSampleCollected = False
            else:
                self.rinse()
                self.statusDisplay.setText('Sampler pad rinsed')
                QtWidgets.qApp.processEvents()
                self.statusDisplay.setText('Draining rinsed solvent')
                QtWidgets.qApp.processEvents()
                self.drainvalve = Valves(self.log_q, False, "waste", "rinse") 
                if self.drainvalve.operateValves():
                    self.statusDisplay.setText('Solvent drained')
                    QtWidgets.qApp.processEvents()  
                else:
                    self.log_q.put(["error","MT",'---Error while draining in valveSelection Module, else statement, logging out----'])
                    self.drain_problem = True
                    self.Charger_Connected()                    
                
            QtWidgets.qApp.processEvents()        
            self.checkRef()  
        else:
            self.timer_and_page_close()


    def rinse(self):
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:            
            self.log_q.put(["info","MT",'-------------RINSE cycle started---------------'])
            rinse_cycle_no = 1
            
            self.statusDisplay.setText('Sampler pad rinse in progress!! ')
            QtWidgets.qApp.processEvents() 
            DS.sampleRinseSquirtVolume = 0
            if self.lowConfidence:
                while 1:
                    self.lowConfidence = False
                    if rinse_cycle_no <=DS.rinseCountReqd:
                        self.log_q.put(["info","MT",'rinseCountReqd = %s'%str(DS.rinseCountReqd)])
                        self.log_q.put(["info","MT",'rinse_cycle_no = %s'%str(rinse_cycle_no)])
                       
                        self.statusDisplay.setText('Rinse in progress. Rinse cycle '+str(rinse_cycle_no)+' of '+str(DS.rinseCountReqd))
                        QtWidgets.qApp.processEvents()            
                        x=True
                        while (x):    
                            QtWidgets.qApp.processEvents()
                            if self.started:
                                self.fastRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","rinse")
                                self.log_q.put(["debug","MT","In rinse cycle, Sampler Fast Rotate Response = "+ str(self.fastRotateResponse)])
                                if self.fastRotateResponse == 1: ##Successful sampler rotation
                                    x=False                          
                                    DS.sampler_faultRetry = 0     
                                    rinse_cycle_no += 1                            

                                elif self.fastRotateResponse == 2: ##Sampler rotation error
                                    pass
                                elif self.fastRotateResponse == 3:  ##Sampler error unrecovered                        
                                    x = False  
                                    self.samplerError()
                                    rinse_cycle_no += 10 ###large enough number to break
                                    break
                                else: ##Sampler disconnected
                                    self.samplerNotPresent()
                                    break
                            else:
                                x=False
                                self.timer_and_page_close()
                                return                                
                    else:
                        break            
            
            else:
                x=True
                while (x):    
                    QtWidgets.qApp.processEvents()
                    if self.started:
                        self.fastRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","rinse")
                        self.log_q.put(["debug","MT","In rinse cycle, Sampler Fast Rotate Response = "+ str(self.fastRotateResponse)])
                        if self.fastRotateResponse == 1: ##Successful sampler rotation
                            DS.sampler_faultRetry = 0
                            x=False
                        elif self.fastRotateResponse == 2: ##Sampler rotation error
                            pass
                        elif self.fastRotateResponse == 3:  ##Sampler error unrecovered                        
                            x = False  
                            self.samplerError()                    
                        else: ##Sampler disconnected
                            self.samplerNotPresent()
                    else:
                        x=False
                        self.timer_and_page_close()
                        return                        
                     
            self.log_q.put(["info","MT",'-------------RINSE cycle completed---------------'])
            self.show()
        else:
            self.timer_and_page_close() 
            

    def checkRef(self):
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started: 
            DS.calibrateVolume = 0
            self.statusDisplay.setText('Checking sampler pad after measurement.')
            QtWidgets.qApp.processEvents()        
            x=True
            while (x):    
                QtWidgets.qApp.processEvents()
               
                self.fastRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","calibrate")
                self.log_q.put(["debug","MT","In check reference, Sampler Fast Rotate Response = "+ str(self.fastRotateResponse)])
                if self.fastRotateResponse == 1: ##Successful sampler rotation
                    DS.sampler_faultRetry = 0
                    x=False
                elif self.fastRotateResponse == 2: ##Sampler rotation error
                    pass
                elif self.fastRotateResponse == 3:  ##Sampler error unrecovered                        
                    x = False  
                    self.samplerError()                    
                else: ##Sampler disconnected
                    self.samplerNotPresent()        
            self.spectroFound = True    
            self.checkRefAfterRinse()
       
        else:
            self.timer_and_page_close()       
       
    def checkRefAfterRinse(self):
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()        
        if self.started:        

            self.statusDisplay.setText('Setting operational temperature')
            QtWidgets.qApp.processEvents()  
############ if the system is idle for more than 5 mins, the LED heater turns OFF#######
    ######## This segment will turn ON the heater if the Led heater turns off ########
            temp = LED_Driver.getTemp('led',self.log_q)
            if temp < DS.targetTemp - 1:
                LED_Driver.LED_heaterON(self.log_q)
    ########################################################################################            
            
            checkLoop=True
            while checkLoop:
                LED_state = LED_Driver.LED_ON(self.log_q,False)###Checking LED is false
                self.log_q.put(["debug","MT","LED state (1-success, 2-Board error, 3-Sampler disconnected)"])
                self.log_q.put(["debug","MT","LED state = "+ str(LED_state)])
                if LED_state == 2:###LED heater error
                    checkLoop = False
                    QMessageBox.warning(self,"LED Error","LED Heater Error \n Contact Support")
                    QtWidgets.qApp.processEvents()
                    self.spectrometerNotFoundError() #exit is the only choice
                elif LED_state == 3: ###Sampler disconnected error
                    self.samplerNotPresent()
                    QtWidgets.qApp.processEvents()
                    if (time.time() > self.timeout):            
                        confirm = QMessageBox.question(self, 'Message',
                                    "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                    QMessageBox.No, QMessageBox.No)
                        QtWidgets.qApp.processEvents()
                        if confirm == QMessageBox.No:
                            checkLoop = False
                            x=False
                            self.samplerWillNotReturn = True
                            self.close_app()
                        else:
                            self.log_q.put(["debug","MT","Keep waiting for another timeout"])
                            self.timeout = time.time() + 30      
                else:### All requirements satisfied.
                    checkLoop = False
                    self.log_q.put(["info","MT","Capturing Reference spectrum after Rinse"])
                    self.statusDisplay.setText('Analysing sample after rinse...')
                    QtWidgets.qApp.processEvents()
                    self.referenceafterRinse = Capture(self.log_q)
                    self.referenceafterRinseCapture = self.referenceafterRinse.referenceAfterRinse()

                    LED_Driver.LED_OFF(self.log_q)
                           
                    if self.referenceafterRinseCapture:
                 
                        self.refComparison = Compare(self.log_q, False,False)###False=Calibrate check, False - LED check from Analyser GUI
                        (self.rinseComplete,  self.Variation, self.minVariation, self.maxVariation) = self.refComparison.variationCalculation()
                        self.log_q.put(["debug", "MT", 'Maximum variation between captured Reference spectrum and Factory Reference spectrum is ' + str(self.maxVariation)])
                        self.log_q.put(["debug", "MT", 'Minimum variation between captured Reference spectrum and Factory Reference spectrum is ' + str(self.minVariation)])
                        self.log_q.put(["debug", "MT", 'Variation values are ' + str(self.Variation)])
                       
                        self.drained =False
                       
                        if self.rinseComplete:
                            self.finalSteps()
                                           
                       
                        else:
                            enoughSolution = QMessageBox.question(self, "Check solution" ,"Enough Solution in the bowl?")
                            QtWidgets.qApp.processEvents()
                            self.log_q.put(["info", "MT", 'Checking whether there is enough solution in the bowl'])
                            if enoughSolution == QtWidgets.QMessageBox.Yes:
                                self.log_q.put(["debug", "MT", 'User confirmed there is enough solution inside the bowl. So the Sampler pad is dirty'])
                                if DS.analyserPadAge!=0:
                                    QMessageBox.about(self, "Dirty Sampler Pad" ,"Change Sampler Pad")                      
                                    DS.analyserPadsTotal+=1    #Updating device status values
                                    DS.analyserPadAge=0    #Updating device status values  
                                    self.statusDisplay.setText('Sampler pad changed')
                                    QtWidgets.qApp.processEvents()  
                                   
                                    self.statusDisplay.setText('Draining solvent')
                                    QtWidgets.qApp.processEvents()                    
                                    self.drainvalve = Valves(self.log_q, False, "waste", "calibrate")
                                    if self.drainvalve.operateValves():
                                        self.statusDisplay.setText('Drained')
                                        QtWidgets.qApp.processEvents()
                                   
                                        self.statusDisplay.setText('Checking new sampler pad')
                                        QtWidgets.qApp.processEvents()  
                                        # time.sleep(1)
                                        self.log_q.put(["info", "MT", 'Checking the new sampler pad is clean'])
                                        self.checkRef()
                                    else:
                                        self.log_q.put(["info","MT",'---Error while draining in checkRefAfterRinse Module, in enough solution section, going back----'])
                                        self.drain_problem = True
                                        self.Charger_Connected()
                                        return
                                else:
                                    self.log_q.put(["debug", "MT", 'It is a new sampler pad. So Remeasuring reference after rinse spectrum'])
                                    self.statusDisplay.setText('Draining Residual solvent')
                                    QtWidgets.qApp.processEvents()                    
                                    self.drainvalve = Valves(self.log_q, False, "waste", "calibrate")
                                    if self.drainvalve.operateValves():
                                        self.drained = True
                                        self.statusDisplay.setText('Drained')
                                        QtWidgets.qApp.processEvents()
                                        if self.rarRetry==0:
                                            self.log_q.put(["debug", "MT", 'Remeasuring reference after rinse spectrum'])
                                            self.rarRetry+=1
                                            self.checkRef()
                                        else:
                                            QMessageBox.warning(self, "Cal Failed" ,"Maximum retries exceeded! \n Redo the calibration")
                                            self.log_q.put(["debug", "MT", 'Retries exceeded. User instructed to redo the calibration'])
                                            self.finalSteps()
                                    else:
                                        self.log_q.put(["info","MT",'---Error while draining in checkRefAfterRinse Module, in enough solution section, going one page back----'])
                                        self.drain_problem = True
                                        self.Charger_Connected()
                                        return                                    
                            else:
                                self.log_q.put(["debug", "MT", 'User confirmed there is no enough solution inside the bowl. So the rewetting the pad'])
                                self.drained1 = True
                                self.checkRef()
                           
                    else:
                        self.spectrometerNotFoundError()                

        else:
            self.timer_and_page_close()  
          

    def finalSteps(self):
        if self.started:
            LED_Driver.LED_OFF(self.log_q)
            LED_Driver.LED_heaterOFF(self.log_q) #we've finished with the LEDs so turn heater off
            self.statusDisplay.setText('Draining solvent')
            QtWidgets.qApp.processEvents() 
            if self.drained:
                pass
            elif self.drained1:
                self.drainvalve = Valves(self.log_q, False, "waste", "rinse") 
            else:
                self.drainvalve = Valves(self.log_q, False, "waste", "refAfterRinse")      
            if self.drainvalve.operateValves():
                self.statusDisplay.setText('Solvent drained')
                QtWidgets.qApp.processEvents()  
                self.suppliesUpdated() 
                self.timer_and_page_close()         
                self.sig_measurementComplete.emit(self.seatNumber, self.description, self.surface, self.Class)   
            else:
                self.log_q.put(["info","MT",'---Error while draining in checkRefAfterRinse Module, in enough solution section, ----'])
                self.drain_problem = True
                self.Charger_Connected()
                return              
        else:
            self.timer_and_page_close()
            return            
        
    def suppliesUpdated(self):
        DS.analyserSolventCount= round(DS.analyserSolventRemaining/DS.sampleVolume)   #Updating device status values                   
        self.log_q.put(["info","MT","Solvent bag available for "+str(DS.analyserSolventCount)+" samples"])
        self.log_q.put(["info","MT","ANALYSER SOLVENT REMAINING  = "+str(round(DS.analyserSolventRemaining,1))])
        
        DS.analyserWasteCount= round(DS.analyserWasteRemaining/DS.sampleVolume)   #Updating device status values 
        self.log_q.put(["info","MT","Waste bag available for "+str(DS.analyserWasteCount)+" samples"]) 
        self.log_q.put(["info","MT","ANALYSER WASTE REMAINING  = "+str(round(DS.analyserWasteRemaining,1))])
 
        self.log_q.put(["info","MT",'-------------Exiting Sampling in '+self.cmd +'---------------'])
        
   
class addNotes(QWidget):
    sig_continue = pyqtSignal(str)

    def __init__(self, log_q, data, result, confidence):
        super (addNotes, self).__init__()
        addNotes.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q   
        self.data = data
        self.keyboard1 = VirtualKeyboard(self.data, False, log_q)
        self.keyboard1.sigInputString.connect(self.notesMaintenance)   
        
        Notes = QtWidgets.QLabel("Notes", self)
        Notes.move(10, 20)
        self.Notes = QtWidgets.QTextEdit(self)
        self.Notes.setGeometry(90, 20, 320, 100)
        self.Notes.setObjectName("textEdit")
        self.Notes.setText(self.data)
        self.promptLabel = QtWidgets.QLabel('Enter Notes then click Continue',self)
        self.promptLabel.setGeometry(10, 140, 400, 50)
        self.Notes.mousePressEvent = self.VKB1     

        self.PermDisplay = QtWidgets.QLabel(self)
        self.PermDisplay.setGeometry(10, 165, 460, 50)   
        self.PermDisplay.setText("Result: Permethrin : " + str(int(result)) + "  Confidence: " + str(int(confidence)))        
        
        self.Continue = QtWidgets.QPushButton("Continue", self)
        self.Continue.move(300,210)
        self.Continue.resize(self.Continue.minimumSizeHint())
        self.Continue.clicked.connect(self.closeWindow)
    def VKB1(self, event):
       
        if self.keyboard1.isHidden():
            self.keyboard1.show()
        else:
            self.keyboard1.hide()
            
    def VKBignore(self, event):
        pass


    def notesMaintenance(self, data):
        self.data = ' '+ data 
        self.log_q.put(["info","MT", 'Notes: '+self.data])        
        self.Notes.setText(self.data)        

    def closeWindow(self):
        self.close()
        self.Notes.mousePressEvent = self.VKBignore
        self.sig_continue.emit(self.Notes.toPlainText())