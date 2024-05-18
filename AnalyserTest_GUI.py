import numpy as np
import os
import sys
import time
import serial

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.UART as UART
import deviceStatus as DS 
import Pump_controller_driver as PC
import seabreeze.spectrometers as sb


import LED_Driver
import Sampler

from CSV_Files_Compare import Compare
from Spectrometer_capture import Capture
from Valves_Pump_control import Valves

class GUI_AnalyserTest(QWidget):
    sig_AT_spectrometerError = pyqtSignal()
    
    def __init__(self, log_q):
        super (GUI_AnalyserTest, self).__init__()
        GUI_AnalyserTest.setGeometry(self, 0, 22, 480, 272)
        self.log_q = log_q
        
        self.log_q.put(["debug", "SC", '///////// Opening Analyser Test GUI Page /////////////'])    

        self.textLabel = QLabel('Analyser Debug',self)
        self.textLabel.setGeometry(130,0,260,25)

        self.sprayButton = QtWidgets.QPushButton("spray", self)  		
        self.sprayButton.resize(self.sprayButton.sizeHint())  	       
        self.sprayButton.setGeometry(50, 30, 70, 30)
        self.sprayButton.clicked.connect(self.doSpray)          
  	
        self.bigSprayButton = QtWidgets.QPushButton("SPRAY", self)
        self.bigSprayButton.resize(self.bigSprayButton.sizeHint())
        self.bigSprayButton.setGeometry(130, 30, 70, 30)
        self.bigSprayButton.clicked.connect(self.doBigSpray)          

        self.drainButton = QtWidgets.QPushButton("Drain", self)
        self.drainButton.resize(self.drainButton.sizeHint())
        self.drainButton.setGeometry(210, 30, 70, 30)  	
        self.drainButton.clicked.connect(self.drain)
        
        self.checkLED = QtWidgets.QPushButton("Check LEDs", self)
        self.checkLED.resize(self.checkLED.sizeHint())
        self.checkLED.move(330, 30)
        self.checkLED.clicked.connect(self.checking_LEDs)  

        self.LED_255 = QtWidgets.QLabel(self)
        self.LED_255.setGeometry(310, 80, 180, 50)    

        self.LED_275 = QtWidgets.QLabel(self)
        self.LED_275.setGeometry(310, 110, 180, 50)      

        self.LED_285 = QtWidgets.QLabel(self)
        self.LED_285.setGeometry(310,  140, 180, 50) 

        self.WLength = QtWidgets.QLabel("nm",self)
        self.WLength.setGeometry(320, 50, 80, 50)  

        self.VariationPercent = QtWidgets.QLabel("% Diff",self)
        self.VariationPercent.setGeometry(400, 50, 80, 50)    

        self.dispenseLabel = QLabel('Dispense',self)
        self.dispenseLabel.setGeometry(25,70,110,30)
        self.dispenseOpenButton = QtWidgets.QPushButton("Open", self)
        self.dispenseOpenButton.setGeometry(130,70,70,30)
        self.dispenseOpenButton.clicked.connect(self.doOpenDispense)
        self.dispenseCloseButton = QtWidgets.QPushButton("Close", self)
        self.dispenseCloseButton.setGeometry(210,70,70,30)
        self.dispenseCloseButton.clicked.connect(self.doCloseDispense )   

        self.sampleLabel = QLabel('Lab',self)
        self.sampleLabel.setGeometry(25,105,130,30)
        self.sampleOpenButton = QtWidgets.QPushButton("Open", self)
        self.sampleOpenButton.setGeometry(130,105,70,30)
        self.sampleOpenButton.clicked.connect(self.doOpenLabSample) 
        self.sampleCloseButton = QtWidgets.QPushButton("Close", self)
        self.sampleCloseButton.setGeometry(210,105,70,30)
        self.sampleCloseButton.clicked.connect(self.doCloseLabSample)         

        self.wasteLabel = QLabel('Waste',self)
        self.wasteLabel.setGeometry(25,140,110,30)
        self.wasteOpenButton = QtWidgets.QPushButton("Open", self)
        self.wasteOpenButton.setGeometry(130,140,70,30)
        self.wasteOpenButton.clicked.connect(self.doOpenWaste) 
        self.wasteCloseButton = QtWidgets.QPushButton("Close", self)
        self.wasteCloseButton.setGeometry(210,140,70,30)
        self.wasteCloseButton.clicked.connect(self.doCloseWaste)    

        self.exitLabel = QLabel('Exit',self)
        self.exitLabel.setGeometry(25,175,110,30)
        self.exitOpenButton = QtWidgets.QPushButton("Open", self)
        self.exitOpenButton.setGeometry(130,175,70,30)
        self.exitOpenButton.clicked.connect(self.doOpenExit) 
        self.exitCloseButton = QtWidgets.QPushButton("Close", self)
        self.exitCloseButton.setGeometry(210,175,70,30)
        self.exitCloseButton.clicked.connect(self.doCloseExit)           
        
        self.checkLED_board = QtWidgets.QPushButton("LED board", self)
        self.checkLED_board.resize(self.checkLED_board.sizeHint())
        self.checkLED_board.move(140, 210)
        self.checkLED_board.clicked.connect(self.checking_LED_board)   
        
        self.StartTemp = QtWidgets.QLabel(self)
        self.StartTemp.setGeometry(310, 180, 260, 50)    

        self.EndTemp = QtWidgets.QLabel(self)
        self.EndTemp.setGeometry(310, 210, 260, 50) 
        
        self.quitButton = QtWidgets.QPushButton("Quit", self)
        self.quitButton.resize(self.quitButton.sizeHint())
        self.quitButton.move(25, 210)
        self.quitButton.clicked.connect(self.doTidyExit)       
        
        LED_Driver.LED_heaterOFF(self.log_q)
        
        self.dispenseValve = False
        self.enableLabSample = False
        self.valve_blocked = False
    

    def doSpray(self):   
        self.sprayButton.setEnabled(False)
        # self.log_q.put(["info","AT","Operator instructed to remove sampler and place a paper to check the spray pattern"])
        # QMessageBox.about(self,"Remove Sampler", "Remove Sampler to perform pump test.\n Place a paper to observe the spray pattern.")
        # QtWidgets.qApp.processEvents()
        # QtWidgets.qApp.processEvents()
        # drain = Valves(self.log_q,True, "Nozzle_check", "Nozzle_check")
        # drain.operateValves()
        # # QMessageBox.about(self,"Replace Sampler", "Replace the sampler back.")
        # QtWidgets.qApp.processEvents()
        # self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")

        # if self.drainvalve.operateValves():
            # self.squirtButton.setEnabled(True)
        # else:
            # self.valve_blocked = True
            # self.log_q.put(["info","AT","Received incomplete drain"])
            # self.close()
            # return
        self.log_q.put(["info","AT","Operator instructed to place paper over bowl to check the spray pattern"])
        confirm = QMessageBox.question(self, 'Message',
            "Hold paper over bowl to observe spray pattern", QMessageBox.Ok |
            QMessageBox.Cancel, QMessageBox.Cancel)
        if confirm == QMessageBox.Ok:
            # QtWidgets.qApp.processEvents()
            self.log_q.put(["debug","AT","Test squirt1"])
            QtWidgets.qApp.processEvents()
            # Valves(self.log_q,True, "preSolventSquirt", "preSolventSquirt")
            PC.PC_wet()
            QtWidgets.qApp.processEvents()
            # self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")
        self.sprayButton.setEnabled(True)            
 
    def doBigSpray(self):  
        self.bigSprayButton.setEnabled(False)
        self.log_q.put(["info","AT","Operator instructed to place paper over bowl to check the spray pattern"])
        confirm = QMessageBox.question(self, 'Message',
            "About to squirt, cover bowl then press OK", QMessageBox.Ok |
            QMessageBox.Cancel, QMessageBox.Cancel)
        if confirm == QMessageBox.Ok:
            # QtWidgets.qApp.processEvents()
            self.log_q.put(["debug","AT","Test squirt3"])
            QtWidgets.qApp.processEvents()
            # Valves(self.log_q,True, "preSolventSquirt", "preSolventSquirt")
            PC.PC_calibrate()
            QtWidgets.qApp.processEvents()
            # self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")
        self.bigSprayButton.setEnabled(True)
        
    def drain(self):  
        self.drainButton.setEnabled(False)
        self.log_q.put(["info","AT","Drain solvent from sampler tube"])
        QtWidgets.qApp.processEvents()
        self.drainvalve = Valves(self.log_q, False, "waste", "AnalyserTest_GUI")
        
        self.drainvalve.operateValves()
        self.log_q.put(["info","AT","Drain complete"])
        self.drainButton.setEnabled(True)
        
        # if self.drainvalve.operateValves():
            # self.log_q.put(["info","AT","Drain complete"])
            # self.drainButton.setEnabled(True)
        # else:
            # self.valve_blocked = True
            # self.log_q.put(["info","AT","Received incomplete drain"])
            # self.close()
            # return        

    def valve_status(self):### This function will be checked in maintainence window
        if self.valve_blocked:
            return False
        else:
            return True             

    def checking_LED_board(self):
        self.checkLED_board.setEnabled(False)    
        currentTemp = LED_Driver.getTemp('led',self.log_q)
        self.log_q.put(["info", "UV","Current Board Temperature = %s °C" %str(round(currentTemp,1))])
        self.StartTemp.setText("StartTemp: %s°C"%str(round(currentTemp,1)))
        self.EndTemp.setText("End:")
        QtWidgets.qApp.processEvents()        
        LED_Driver.LED_heaterON(self.log_q)
        time.sleep(10)
        newTemp = LED_Driver.getTemp('led',self.log_q)
        self.log_q.put(["info", "UV","Board Temperature after 10 sec = %s °C" %str(round(newTemp,1))])
        self.EndTemp.setText("End: %s°C"%str(round(newTemp,1)))
        self.checkLED_board.setEnabled(True)
        
    def doOpenDispense(self):  
        self.dispenseOpenButton.setEnabled(False)
        self.log_q.put(["info","AT","Open Dispense valve button clicked"])
        GPIO.output("P9_25", GPIO.HIGH)#Open dispense valve
        self.dispenseCloseButton.setEnabled(True)    
        self.dispenseOpenButton.setEnabled(True)        
        
    

        
    def doCloseDispense(self):  
        self.dispenseCloseButton.setEnabled(False)
        self.log_q.put(["info","AT","Close Dispense valve button clicked"])
        GPIO.output("P9_25", GPIO.LOW)#Close dispense valve 
        self.dispenseOpenButton.setEnabled(True)    
        self.dispenseCloseButton.setEnabled(True)         

    def doOpenWaste(self):
        self.log_q.put(["info","AT","Open Waste valve button clicked"])
        GPIO.output("P9_24", GPIO.HIGH)#Open waste valve
        self.wasteOpenButton.setEnabled(False)
        self.wasteCloseButton.setEnabled(True) 

    def doCloseWaste(self):
        self.log_q.put(["info","AT","Close Waste valve button clicked"]) 
        self.wasteCloseButton.setEnabled(False)
        GPIO.output("P9_24", GPIO.LOW)#Close waste valve
        self.wasteOpenButton.setEnabled(True)
        self.wasteCloseButton.setEnabled(True)
        
    def doOpenLabSample(self):
        self.log_q.put(["info","AT","Open Lab Sample valve button clicked"])  
        self.sampleOpenButton.setEnabled(False)
        self.sampleCloseButton.setEnabled(True)
        self.enableLabSample = True
        # self.valveCheck()
        GPIO.output("P9_28", GPIO.HIGH) # Open lab valve
        
    def doCloseLabSample(self):
        self.log_q.put(["info","AT","Close Lab Sample valve button clicked"])  
        GPIO.output("P9_28", GPIO.LOW)#Close lab valve
        self.sampleOpenButton.setEnabled(True)
        self.sampleCloseButton.setEnabled(False)
        
    def doOpenExit(self):
        self.log_q.put(["info","AT","Open Exit valve button clicked"])  
        GPIO.output("P9_27", GPIO.HIGH)#Open valve connecting tube and exit valves on valve connecting tube and exit valves
        self.exitOpenButton.setEnabled(False)
        self.exitCloseButton.setEnabled(True)
        

        
    def doCloseExit(self):
        self.exitCloseButton.setEnabled(False)
        self.log_q.put(["info","AT","Close Exit valve button clicked"])  
        GPIO.output("P9_27", GPIO.LOW)#Close valve connecting tube and exit valves
        self.exitOpenButton.setEnabled(True)
        self.exitCloseButton.setEnabled(True)    

    def checking_LEDs(self):
        self.checkLED.setEnabled(False)
        confirm = QMessageBox.question(self, 'Message',
        "About to squirt, cover bowl then press OK", QMessageBox.Ok |
        QMessageBox.Cancel, QMessageBox.Cancel)
        QtWidgets.qApp.processEvents()
        if confirm == QMessageBox.Ok:
            self.log_q.put(["info","AT","Check LEDs button clicked"])
            self.LED_255.setText("")
            self.LED_275.setText("")
            self.LED_285.setText("")
            QtWidgets.qApp.processEvents() 
            valve = Valves(self.log_q,True, "calibrate", "calibrate")
            valve.operateValves()
        
######## This segment will turn ON the heater if the Led heater turns off ########
        temp = LED_Driver.getTemp('led',self.log_q)
        if temp < DS.targetTemp - 1:
            LED_Driver.LED_heaterON(self.log_q)
########################################################################################            
        checkLoop=True
        while checkLoop:
            LED_state = LED_Driver.LED_ON(self.log_q,True)###Checking LED is True
            self.log_q.put(["debug","AT","LED state (1-success, 2-Board error, 3-Sampler disconnected)"])
            self.log_q.put(["debug","AT","LED state = "+ str(LED_state)])
            if LED_state == 2:###LED heater error
                checkLoop = False
                QMessageBox.warning(self,"LED Error","LED Heater Error \n Contact Support")
                QtWidgets.qApp.processEvents()
                self.calib_spectrometerNotFoundError() #exit is the only choice
   
            else:### All requirements satisfied.
                checkLoop = False
                self.log_q.put(["debug", "AT", 'Capturing Reference spectrum...'])            

                
                self.LEDCheckCapture = Capture(self.log_q) 
                self.spectroFound = self.LEDCheckCapture.checkLEDs()
                self.log_q.put(["debug", "AT", 'Trying to capture Reference spectrum...']) 
                if self.spectroFound:

                    self.log_q.put(["debug", "AT", 'SUCCESS!!!!Reference spectrum captured']) 
                    LED_Driver.LED_OFF(self.log_q)
                    self.spectrumCheck()
                    QtWidgets.qApp.processEvents()
                    GPIO.output("P9_27", GPIO.HIGH)#Open valve connecting tube and exit valves on valve connecting tube and exit valves
                    GPIO.output("P9_24", GPIO.HIGH)#Close waste valve
                    time.sleep(20)
                    GPIO.output("P9_24", GPIO.LOW)#Close waste valve
                    GPIO.output("P9_27", GPIO.LOW)#Open valve connecting tube and exit valves on valve connecting tube and exit valves
                    
                    
                else:                         
                    self.calib_spectrometerNotFoundError()         
        self.checkLED.setEnabled(True)
 
    def calib_spectrometerNotFoundError(self):
        """
        Unresponsive spectrometer during measurement will emit signal to return the analyser to the manufacturer
        """     
        self.log_q.put(["error", "AT", 'SPECTROMETER NOT FOUND!!!']) 
        QtWidgets.qApp.processEvents()        
        self.close()            
        # self.sig_AT_spectrometerError.emit() 
        
    def spectrumCheck(self):
        
        lowWavelength = []
        highWavelength = []
        factory_val_WL = []
        factory_val_intensity = []
        list = []
        DS.factory_val_WL = []
        DS.factory_val_intensity = []
        
        self.log_q.put(["error", "AT", 'DS.LEDs = %s, Len(DS.LEDs)= %d'%(str(DS.LEDs),len(DS.LEDs))]) 
        self.log_q.put(["error", "AT", 'DS.LEDs = %s'%(str(DS.LEDs))]) 
        for i in DS.LEDs:

            lowWavelength.append(i-5)
            highWavelength.append(i+5) 
            # self.log_q.put(["error", "AT", 'lowWavelength = %d, highWavelength= %d'%((lowWavelength[i]),(highWavelength[i]))]) 
        self.log_q.put(["error", "AT", 'lowWavelength = %s, highWavelength= %s'%(str(lowWavelength),str(highWavelength))]) 
        
        values = np.genfromtxt(DS.refFilesDirectory + DS.spectroEthanolReference, delimiter=',', skip_header = 1)
        
        for k in range(len(DS.LEDs)):
            for i, row in enumerate(values):                          

               
                for j, column in enumerate(row):


                    if (lowWavelength[k] <= round(column, 2) and highWavelength[k]>=round(column, 2)): # compare against ref wavelength to 2 places
                        factory_val_intensity+=[row[1]]
                        factory_val_WL+=[row[0]]
                        factory_val = np.column_stack([factory_val_WL,factory_val_intensity])
                        list = factory_val
            max_value=max(factory_val_intensity)
            
            for x in range(len(factory_val_intensity)):
                if factory_val_intensity[x] == max_value:
                    DS.factory_val_WL += [round(factory_val_WL[x],2)]
                    DS.factory_val_intensity += [max_value]
                    # print("max WL=",DS.factory_val_WL[x],"max_value",max_value)
                    self.log_q.put(["error", "AT", 'max WL = %f, max_value= %d'%(factory_val_WL[x],max_value)]) 
            # np.savetxt(DS.localRefFilesDirectory +'values_'+str(k)+'.csv',factory_val,delimiter=",", fmt='%f')
            factory_val_WL = []
            factory_val_intensity = []        
        self.log_q.put(["error", "AT", 'Outside loop, max WL = %s, max_value= %s'%(str(DS.factory_val_WL),str(DS.factory_val_intensity))]) 
        
        
        self.refComparison = Compare(self.log_q, False,True)###False=Calibrate check, True - LED check from Analyser GUI
        self.variance = self.refComparison.variationCalculation()
        self.LED_255.setText("%s =%s"%(str(DS.factory_val_WL[0]),str(self.variance[0])))
        self.LED_275.setText("%s =%s"%(str(DS.factory_val_WL[1]),str(self.variance[1])))
        self.LED_285.setText("%s =%s"%(str(DS.factory_val_WL[2]),str(self.variance[2])))
        
        
    def doTidyExit(self):
        # Quit button pressed
        # drain then close all valves
        # then close
        self.quitButton.setEnabled(False)
        self.drainvalve = Valves(self.log_q, False, "waste", "postSolventSquirt1")
        GPIO.output("P9_25", GPIO.LOW)#Close dispense valve
        GPIO.output("P9_27", GPIO.LOW)#Close valve connecting tube and exit valves
        GPIO.output("P9_28", GPIO.LOW)#Close lab valve
        GPIO.output("P9_24", GPIO.LOW)#Close waste valve
        self.log_q.put(["info","AT","Drain complete"])
       

        self.close()        
   