#Enters the maintenance mode
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys 
import time

import matplotlib.pyplot as plt
import numpy as np

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# print ("Maintenance_Window.py first call startin at : startupTime",datetime.datetime.now())
from AnalyserTest_GUI import GUI_AnalyserTest
from Calibration import Window
from Measurement import Measure
from samplertestmode import SamplerTestGUI
from Status_Window import Status_Window
from Valves_Pump_control import Valves
from Perform_Updates import PerformUpdatesGUI


import AnalyserSamplerComms as samplerComms
import deviceStatus as DS 
import LED_Driver
import Sampler

class Maintenance_Window(QWidget):


    sig_MW_noSupplies_Close = pyqtSignal()
    sig_MW_Close = pyqtSignal()
    sig_MW_SpectrometerError = pyqtSignal()

    def __init__(self, log_q, telemetry_q, deviceID, mp_status, charger_connected):
        super (Maintenance_Window, self).__init__()
        Maintenance_Window.setGeometry(self, 0, 22, 480, 250)

        self.charger_connected = charger_connected
        self.seatNumber = '0' 
        self.nextSeatNumber = '0'
        self.surface = '0' 
        self.Class = '0'     
        self.description = '0'  
        self.AN='0'
        self.Aircraft_ID = '0'      
        self.workOrder = '0' 
        self.data = ''
        self.deviceId = deviceID        
        self.telemetry_q = telemetry_q
        self.log_q = log_q
        self.mp_status = mp_status        
        self.singleSampleBtn = False      
        self.home()
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","MW","charger_connected event cleared... "])
            self.log_q.put(["debug","MW","!!!!!!!! CLOSING MAINTENANCE WINDOW !!!!!!!"])
            self.close_application()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","MW","Timer started"])
        
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","MW","!!!!!!!!!!! EXITING MAINTENANCE WINDOW PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","MW","Timer stopped"])         
        
#Options in the maintenance mode: 1. Calibrate, 2. Single Sample, 3. Cancel
    def home(self):
        """
        Options in the maintenance mode: 
        1. Calibrate, 
        2. Single Sample, 
        3. Cancel
        """

        self.log_q.put(["debug","MW",'***********Opening Maintenance window**************'])

        self.calibrationRequiredLabel = QLabel('Calibration Required',self)
        self.calibrationRequiredLabel.move(40,20)
        self.calibrationRequiredLabel.hide()        
        calibrate = QtWidgets.QPushButton("Calibrate", self)
        calibrate.resize(calibrate.sizeHint())
        calibrate.move(40, 150)
        # calibrate.clicked.connect(self.Calibrate)
        calibrate.clicked.connect(self.enableCalibrate)        
        
        self.SS = QtWidgets.QPushButton("Single Sample", self)
        self.SS.resize(self.SS.sizeHint())
        self.SS.move(40, 50)
        self.SS.clicked.connect(self.timer_and_page_close)
        self.SS.clicked.connect(self.enableSingleSample)   

        UP = QtWidgets.QPushButton("Perform Updates", self)
        UP.resize(UP.sizeHint())
        UP.move(40, 100)
        UP.clicked.connect(self.performUpdates)
        UP.setEnabled(False)
        # UP.setEnabled(True)
        self.log_q.put(["debug","MW",'mp_status is updates_pending: ' + str(self.mp_status.updates_pending) + "sampler_req: "+ str(self.mp_status.sampler_req)])
        if (self.mp_status.updates_pending):
            UP.setEnabled(True)

        testSampler = QtWidgets.QPushButton("Sampler Test", self)
        testSampler.resize(testSampler.sizeHint())
        testSampler.move(270, 50)
        testSampler.clicked.connect(self.SamplerTesting)    

        testAnalyser = QtWidgets.QPushButton("Analyser Test", self)
        testAnalyser.resize(testAnalyser.sizeHint())
        testAnalyser.move(270, 100)
        testAnalyser.clicked.connect(self.AnalyserTesting)          
        
        cancel = QtWidgets.QPushButton("Cancel", self)
        cancel.resize(cancel.sizeHint())
        cancel.move(270, 200)
        cancel.clicked.connect(self.close_app)

        self.time_diff = int(time.time()-DS.calibratedTime)
        self.log_q.put(["info","FD","time_diff = %d, time.time()=%f, DS.calibratedTime = %f"%(self.time_diff,time.time(),DS.calibratedTime)])

        if self.time_diff>DS.calibrationTimeLimit:
            # QMessageBox.warning(self,"Recalibrate", "Calibration timeout. \n Redo calibration")
            self.log_q.put(["debug","MW","Calibration performed over 4 hours ago. Operator instructed to recalibrate."])
            self.SS.setEnabled(False) 
            self.calibrationRequiredLabel.show()
        
        if DS.CDC_software == "Yes":   
    #Push button for Status display
            self.btnStatus = QtWidgets.QPushButton("Status", self)
            self.btnStatus.clicked.connect(self.statusScreen)
            self.btnStatus.move(270, 150)         
        
        if DS.engineer:
            testSampler.show()
            testAnalyser.show()
        else:
            testSampler.hide()
            testAnalyser.hide()
        
        self.show()
        
    def statusScreen(self):
        """
        Display Status screen
        """   
        if DS.process_started:       
            # display Status screen
            self.timer_and_page_close()           
            self.log_q.put(["debug","MW",'------------ Opening Status window -------------------']) 
            self.S_page = Status_Window(self.log_q)
            self.S_page.show()

            self.S_page.sig_availableSupplies.connect(self.enableTimer)
            self.S_page.sig_SpectrometerError.connect(self.enableTimer)
            self.S_page.sig_Sampler_will_not_return.connect(self.close_application)        
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return 
 
    def performUpdates(self):
        # signal the backend to perform any pending updates (Sampler and Analyser)
        Sampler.Sampler_close()
        self.log_q.put(["debug","MW","Entering test page"])
        self.updateFirmware = PerformUpdatesGUI(self.log_q, self.mp_status)
        self.updateFirmware.show()
        self.updateFirmware.sig_PerformUpdatesGUI_closed.connect(self.restart_sampler)
        
 
    def SamplerTesting(self):
        if DS.process_started:
            Sampler.Sampler_close()
            self.log_q.put(["debug","MW","Entering Sampler test page"])
            self.TestSampler = SamplerTestGUI(self.log_q)
            self.TestSampler.show()
            self.TestSampler.sig_SamplerTestGUI_closed.connect(self.restart_sampler)
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return            
        
    def AnalyserTesting(self):
        if DS.process_started:  
            self.log_q.put(["debug","MW","Entering Analyser test page"])
            self.TestAnalyser = GUI_AnalyserTest(self.log_q)
            self.TestAnalyser.show()
            self.TestAnalyser.sig_AT_spectrometerError.connect(self.enableTimer)
            if not self.TestAnalyser.valve_status():
                self.log_q.put(["debug","MW","Received response as "+ DS.cause_Of_logout[DS.logout_cause_value]+"..."])
                
                self.close_application()                
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return         

    def restart_sampler(self):
        time.sleep(1)
        Sampler.Sampler_init(self.log_q)      
        time.sleep(2)
               
#Calls the calibration module  
    def enableCalibrate(self):
        self.singleSampleBtn = False
           
        self.availableSupplies()

        
    def Calibrate(self):
        """
        Migrate to Calibration page
        """  
        if DS.process_started:    
            self.log_q.put(["info","MW", 'CALIBRATION clicked']) 
            self.timer_and_page_close()
            self.calibrate = Window(self.log_q, self.telemetry_q, self.charger_connected)
            self.Calibration_steps = self.calibrate.steps()
            self.log_q.put(["info","MW", 'self.Calibration_steps = %d'%self.Calibration_steps])
            
            if self.Calibration_steps == 0: ### Successful completion
                self.enableTimer()
                self.SS.setEnabled(True)
                self.calibrationRequiredLabel.hide()
                # self.show()
            elif self.Calibration_steps == 1:  ##received spectrometer error
                
                self.log_q.put(["debug","MW","Received response as "+ DS.cause_Of_logout[DS.logout_cause_value]+"..."])
                self.enableTimer()
            
            elif self.Calibration_steps == 3: ### Received calibration error
                self.enableTimer()
            
            else: ## ==2, Charger connected / Sampler error / Sampler not returning back / Unable to drain completely 
  
                self.log_q.put(["debug","MW","Received response as "+ DS.cause_Of_logout[DS.logout_cause_value]+"..."])
                
                self.close_application()
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return         
 
#Enters the Single sample mode 
    def enableSingleSample(self):
        if DS.process_started: 
            self.singleSampleBtn = True 
            self.time_diff = int(time.time()-DS.calibratedTime)
            self.log_q.put(["info","MW","time_diff = %d, time.time()=%f, DS.calibratedTime = %f"%(self.time_diff,time.time(),DS.calibratedTime)])        
            time_diff_sec = self.time_diff%(24*3600)
            time_hours = time_diff_sec//3600  ###extracting hours from time difference
            time_diff_sec%= 3600 ##Getting remaining time in sec
            time_min = time_diff_sec//60 ###Extracting mins
            time_diff_sec %= 60 ##Getting remaining time in sec
            self.log_q.put(["info","MW","Calibration performed %d:%02d:%02d H:M:S ago. So continuing next step."%(time_hours,time_min,time_diff_sec)])
            self.availableSupplies()
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return             
                   
        
    def MW_spectrometerError(self):
        self.timer_and_page_close()
        self.log_q.put(["debug","MW",'*********Closing Maintenance window due to '+ DS.cause_Of_logout[DS.logout_cause_value]+' *********'])          
        # self.sig_MW_SpectrometerError.emit()        
                        
#Exit the page                
    def close_app(self):
        self.log_q.put(["warning","MW", 'EXIT button clicked!!!!']) 
        
        
        if DS.CDC_software == "Yes": 
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure you want to Exit?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                          
            if choice == QtWidgets.QMessageBox.Yes:  
                self.log_q.put(["debug","MW",'@@@@@@@@@@ YES button Clicked @@@@@@@@@@@@@@@'])                          
                self.log_q.put(["debug","MW",'*********Closing Maintenance window*********'])                          
                self.timer_and_page_close()    
                self.sig_MW_Close.emit()
            else:
                self.log_q.put(["debug","MW",'@@@@@@@@@@ NO button Clicked @@@@@@@@@@@@@@@'])                          
        else:
            self.log_q.put(["debug","MW",'*********Closing Maintenance window*********'])              
            self.timer_and_page_close()    
            self.sig_MW_Close.emit()                
        

			
    def close_application(self):
        self.timer_and_page_close()
        self.log_q.put(["debug","MW",'********* Closing Maintenance window due to '+ DS.cause_Of_logout[DS.logout_cause_value]+' *********'])          
        self.sig_MW_noSupplies_Close.emit()
        
        
        
    def availableSupplies (self):
        """
        Checks the supply availability
        """   
        if DS.process_started:         
            x=True
            self.NO = False
            while x==True:
                self.timer_and_page_close()               
                self.supplyAvailability = Status_Window(self.log_q, self.charger_connected)
                self.supplyAvailability.show()    
                self.log_q.put(["info","MW","Checking Supply availability"])
                self.log_q.put(["info","MW","Checking Battery Precent for analysis"])
                # self.log_q.put(["info","MW","DS.analyserBattery = %d, DS.samplerBattery = %d, DS.analyserCharging = %d"%(DS.analyserBattery, DS.samplerBattery, DS.analyserCharging)])    
                if (DS.analyserBattery <= DS.analyserBatteryThreshold or DS.samplerBattery <= DS.samplerBatteryThreshold) and DS.analyserCharging != 1:                
                    status = Sampler.S_cmd_Get_status()
                    if (status['status'] == 'Disconnected'):
                        pass
                    else:                   
                        QtWidgets.QMessageBox.warning(self, "Battery Level Critical" ,"Battery level low. Connect to the Charger")            
                        self.log_q.put(["info","MW","DS.analyserBattery = %d, DS.samplerBattery = %d, DS.analyserCharging = %d"%(DS.analyserBattery, DS.samplerBattery, DS.analyserCharging)])    
                        self.log_q.put(["info","MW","Battery level low. Operator instructed to connect to the Charger"])
                    x=False
                elif DS.analyserSolventRemaining <= DS.analyserSolventThreshold or DS.analyserWasteRemaining<=DS.analyserWasteThreshold:
                    self.log_q.put(["info","MW","Checking solvent availability for analysis"])   
                    QtWidgets.QMessageBox.warning(self, 'Change Solvent Bag!', "Not enough supplies to perform sampling. Please change Consummables. ")


                    x=False
                    # self.NO = True
                    break

                        
                elif DS.analyserPadAge>= DS.padAgeThreshold:
                    self.log_q.put(["info","MW","Sample pad needs changing"])   
                    QtWidgets.QMessageBox.question(self, 'Change Sample Pad!', "Sample pad needs changing.\nClick Yes when changed.")
                    # self.supplyAvailability.resetSamplerpadValue() 

                    x=False
                    # self.NO = True
                    break
                        
                else:    
                    self.log_q.put(["info","MW","Got enough supplies. Displaying the available supplies"]) 
                    x=False
            if self.NO:
                DS.logout_cause_value =  4
                self.checkStatus()
            else:
                self.supplyAvailability.sig_SpectrometerError.connect(self.enableTimer)
                
                self.supplyAvailability.sig_Sampler_will_not_return.connect(self.close_application)
                
                self.supplyAvailability.sig_availableSupplies.connect(self.enableTimer)     
                self.supplyAvailability.sig_availableSupplies.connect(self.checkStatus)  
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return             
            
            
    def checkStatus(self):
        if self.NO:
            self.log_q.put(["info","MW","Exiting due to insufficient supplies!!!"])
            self.supplyAvailability.close()
            self.timer_and_page_close()            
            DS.messageType = 'Sampling aborted due to insufficient supply'
            QtWidgets.QMessageBox.warning(self, "LOW SUPPLY" ,"Exiting due to insufficient supplies!!!")
            self.close_application()           

            
        else:
            self.timer_stop()  
            if self.singleSampleBtn:
                self.start()
            else:                
                self.Calibrate()
            
    def start(self):
        """
        Perform single sample
        """  
        if DS.process_started:       
            self.log_q.put(["info","MW", 'Single sample button clicked'])  
            self.timer_and_page_close()
          
            self.startMeasurement = Measure('singleSample', self.seatNumber, self.surface, self.Class, self.description, self.AN, self.Aircraft_ID, self.workOrder, self.deviceId, self.telemetry_q,self.log_q, self.data, self.nextSeatNumber, self.charger_connected)
            
            
            DS.samplingCount = 0   
            
            self.startMeasurement.sig_measurementComplete.connect(self.enableTimer)
            self.startMeasurement.sig_windowCancel.connect(self.enableTimer)        
            
             
            self.startMeasurement.sig_drain_problem.connect(self.enableTimer)
            self.startMeasurement.sig_SpectrometerError.connect(self.enableTimer)        
            self.startMeasurement.sig_samplerWillNotReturn.connect(self.close_application)                 
        else:
            self.log_q.put(["debug","MW","Charger connected..."])
            return 
