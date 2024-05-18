import sys
import time
import datetime

import Adafruit_BBIO.GPIO as GPIO

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
# print ("Valves pump control.py first call startin at : startupTime",datetime.datetime.now())


import deviceStatus as DS 
import Pump_controller_driver as PC

import Sampler
import serial



GPIO.setup("P9_28", GPIO.OUT) ##Lab Drain valve (valve 2 in schematic)
GPIO.setup("P9_24", GPIO.OUT) ##Waste Drain valve (valve 1 in schematic)
GPIO.setup("P9_25", GPIO.OUT) ##Dispense valve (valve 3 in schematic)
GPIO.setup("P9_27", GPIO.OUT) ##valve connecting tube and exit valves
GPIO.setup("P9_29", GPIO.IN) ##Bubble detector


tOut = 0.5
# pump_dispenseVolume = 0.01641318

class Valves(QWidget):
    def __init__(self, log_q, dispense_flag, cmd_1, cmd_2):
        """
        Operates the pumps and valves
        1. Presolvent squirt, Post solvent squirt, rinse and calibrate - Turn on valve and pump
        2. Waste - Turn on waste valve and bubble detector
        3. Lab - Turn on lab sample valve
        """
        super (Valves, self).__init__()
        Valves.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q
        self.cmd_1 = str(cmd_1)
        self.cmd_2 = str(cmd_2)
        self.flag = dispense_flag 
        self.log_q.put(["info","VP","------------Starting Valve operation-------------"]) 
        self.log_q.put(["info","VP","Valve commands: cmd 1 : %s, cmd 2: %s, flag : %s"%(self.cmd_1, self.cmd_2,str(self.flag))]) 
        # self.operateValves()
        
    def operateValves(self):

        if self.flag:####this flag is set, whenever the pump controller is invoked 
            
            if self.cmd_1 == "preSolventSquirt":
                self.log_q.put(["info","VP","-----Start of PRESOLVENT SQUIRT------"])
 
                PC.PC_wet()
                self.pump_Controller_function()
     
                ##Update DEVICE STATUS
                      
                
                self.log_q.put(["info","VP","sampleSquirtVolume = "+ str(DS.sampleSquirtVolume)])
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"]) 
                self.log_q.put(["info","VP","-----End of PRESOLVENT SQUIRT------"])

            elif self.cmd_1 == "postSolventSquirt":
                self.log_q.put(["info","VP","-----Start of POSTSOLVENT SQUIRT------"])

                for i in range(3):
                    self.log_q.put(["info","VP","postSolventSquirt counter = "+ str(i)])
                    PC.PC_sample()
                    self.pump_Controller_function()
                                        
                ##Update DEVICE STATUS
                 
                
                self.log_q.put(["info","VP","postSamplingSolventVolume = "+ str(DS.postSamplingSolventVolume)])
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"]) 
                self.log_q.put(["info","VP","-----End of POSTSOLVENT SQUIRT------"])
                
            elif self.cmd_1 == "rinse":
                self.log_q.put(["info","VP","-----Start of "+str(self.cmd_1)+" SQUIRT------"])   
 
                PC.PC_rinse()
                self.pump_Controller_function()
                
                 
                # DS.analyserWasteRemaining-=DS.sampleRinseSquirtVolume 
                
                self.log_q.put(["info","VP","sampleRinseSquirtVolume = "+ str(DS.sampleRinseSquirtVolume)])                
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"]) 
                self.log_q.put(["info","VP","-----End of "+str(self.cmd_1)+" SQUIRT------"])                

            elif self.cmd_1 == "calibrate":
                self.log_q.put(["info","VP","-----Start of "+str(self.cmd_1)+" SQUIRT------"])   
                
                PC.PC_calibrate()
                self.pump_Controller_function()
                
                       
                # DS.analyserSolventRemaining = round(DS.analyserSolventRemaining) 
                # DS.analyserWasteRemaining = round(DS.analyserWasteRemaining)
                self.log_q.put(["info","VP","calibrateVolume = "+ str(DS.calibrateVolume)])
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"]) 
                self.log_q.put(["info","VP","-----End of "+str(self.cmd_1)+" SQUIRT------"])     
                
            elif self.cmd_1 == "bagChange":
    
                self.log_q.put(["info","VP","-----Start of "+str(self.cmd_1)+" SQUIRT------"])   
                
                PC.PC_solventBagChange()
                self.pump_Controller_function()               
                 
                # DS.analyserSolventRemaining-=DS.resetSolventBagVolume     #Updating device status values        
                # DS.analyserSolventRemaining = round(DS.analyserSolventRemaining) 
                # DS.analyserWasteRemaining = round(DS.analyserWasteRemaining)
                self.log_q.put(["info","VP","bag change Volume = "+ str(DS.resetSolventBagVolume)]) 
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))])                
                self.log_q.put(["info","VP","-----End of "+str(self.cmd_1)+" SQUIRT------"]) 

            elif self.cmd_1 == "Nozzle_check":
                self.log_q.put(["info","VP","-----Start of PUMP AND SPRAY PATTERN CHECK SQUIRT------"])


                for i in range(3):
                    PC.PC_sample()
                    self.pump_Controller_function()
                                        
                ##Update DEVICE STATUS
                 
                
                self.log_q.put(["info","VP","pump_and_spray_checkSolventVolume = "+ str(DS.postSamplingSolventVolume)])
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"]) 
                self.log_q.put(["info","VP","-----End of PUMP AND SPRAY PATTERN CHECK SQUIRT------"])
        
        
        else: ### if the function is to drain the solvent ### Returns TRUE or FALSE
            if self.cmd_1 == "waste": 
                self.log_q.put(["info","VP","-----Start of Waste drain------"])
 
                cmd_timeOut = time.time()+40
                i=0
                counter = 0
                enter=True
                while(enter):
                    QtWidgets.qApp.processEvents()
                    if (time.time()>cmd_timeOut):  
                        self.log_q.put(["debug","VP","In timeout module, BOTH WASTE AND EXIT VALVES ARE OPENED" ])
                        GPIO.output("P9_27", GPIO.HIGH)##Turn oFF valve connecting tube and exit valves
                        GPIO.output("P9_24", GPIO.HIGH)##Turn oFF waste valve    
                        
                        if counter!=0:
                            QMessageBox.critical(self, 'Message',"Draining issues. \n Try replacing Residual bag.")
                            QtWidgets.qApp.processEvents()
                            self.log_q.put(["debug","VP","DRAIN BLOCKED!!!!!Some blockage in the drain circuit." ])
                            enter=False
                            DS.logout_cause_value = 3
                            self.log_q.put(["debug","VP","DS.logout_cause_value = %d" %DS.logout_cause_value ])                    
                            GPIO.output("P9_27", GPIO.LOW)##Turn oFF valve connecting tube and exit valves
                            GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve    
                            GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve 
                            self.log_q.put(["debug","VP","In timeout module, ALL VALVES ARE CLOSED" ])
                            return False
                        else:
                            
                            GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve
                            GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve
                            self.log_q.put(["debug","VP","Timeout while draining. Adding some ethanol for draining." ])
                            QMessageBox.warning(self, 'Message',"Timeout while draining. \n Adding some ethanol for draining.")
                            QtWidgets.qApp.processEvents()
                            if self.cmd_2 == "AnalyserTest_GUI":
                                PC.PC_calibrate()
                                
                                pump=True
                                while pump:
                                    value = PC.PC_Events()
                                    self.log_q.put(["info","VP","Pump rotations = %s"%value]) 
                                    if(value==4):
                                        self.log_q.put(["info","VP","Sampler pad still wetting"])
                                        time.sleep(2)
                                    elif (value==2 or value==3):
                                        self.log_q.put(["info","VP","timeout EVENT set"])
                                        # self.log_q.put(["info","VP","Rewetting the pad. i = %d"%i])
                                        PC.PC_calibrate()
                                        pump=False                          
                                        
                                    else:
                                        self.log_q.put(["info","VP","Sampler pad wetted"])
                                        DS.actual_rev = value
                                        # DS.calibrateVolume = round((float(DS.actual_rev) * pump_dispenseVolume),1)
                                        DS.calibrateVolume = round((float(DS.actual_rev) * DS.pumpDispense_per_rev),1)
                                        self.log_q.put(["info","VP","DS.pumpDispense_per_rev = %f"%DS.pumpDispense_per_rev])
                                        self.log_q.put(["info","VP","Solvent dispensed during "+str(self.cmd_2)+" = %s, actual rev = %s"%(str(DS.calibrateVolume), str(DS.actual_rev))])                        

                                        pump=False
                            else:
                                rotate=True
                                while rotate:   
                                    QtWidgets.qApp.processEvents()
                                    response_FR = Sampler.S_cmd_Fast_rotate_General()
                                    time.sleep(2)
                                    self.log_q.put(["info","VP","response_FR "+str(response_FR)])   
                                    if (response_FR==2): ###There is a problem in sampler connection
                                        QMessageBox.warning(self, 'Message',"Sampler not in place. Return it and try again")
                                        QtWidgets.qApp.processEvents()
                                        self.log_q.put(["debug","VP","Sampler is disconnected. Operator instructed to connect the sampler." ])
                                    elif (response_FR==1):
                                        pass
                                    else:
                                        PC.PC_rinse()
                                        
                                        pump=True
                                        while pump:
                                            value = PC.PC_Events()
                                            self.log_q.put(["info","VP","Pump rotations = %s"%value]) 
                                            if(value==4):
                                                self.log_q.put(["info","VP","Sampler pad still wetting"])
                                                time.sleep(2)
                                            elif (value==2 or value==3):
                                                self.log_q.put(["info","VP","timeout EVENT set"])
                                                # self.log_q.put(["info","VP","Rewetting the pad. i = %d"%i])
                                                PC.PC_rinse()
                                                pump=False                          
                                                
                                            else:
                                                self.log_q.put(["info","VP","Sampler pad wetted"])
                                                DS.actual_rev = value
                                                # DS.calibrateVolume = round((float(DS.actual_rev) * pump_dispenseVolume),1)
                                                DS.calibrateVolume = round((float(DS.actual_rev) * DS.pumpDispense_per_rev),1)
                                                self.log_q.put(["info","VP","DS.pumpDispense_per_rev = %f"%DS.pumpDispense_per_rev])
                                                self.log_q.put(["info","VP","Solvent dispensed during CALIBRATE = %s, actual rev = %s"%(str(DS.calibrateVolume), str(DS.actual_rev))])                        

                                                pump=False

                                        rotate = False
                                Sampler_status_check_count = 0
                                while True:
                                    status = Sampler.S_cmd_Get_status()
                                    # self.log_q.put(["debug","VP", "Status: status['sample_state'] = %s, status['rotate_state'] = %s, status['status'] = %s"%(str(status['sample_state']), str(status['rotate_state']), str(status['status']))])
                                    if(status['status'] == 'Ready' and status['rotate_state'] != 'A'):                                   
                                        break
                                    else:
                                        Sampler_status_check_count+=1
                                        # self.log_q.put(["debug","VP", "Sampler_status_check_count = %s"%(str(Sampler_status_check_count))])
                                        if Sampler_status_check_count>=20:
                                            self.log_q.put(["debug","VP","Sampler Sending BUSY signal for long time." ])
                                            return False
                                            break
                                        else:
                                            time.sleep(1)
                                    
                                
                            cmd_timeOut = time.time()+40
                            counter+=1
                        # enter=False
                    else:                
                        GPIO.output("P9_27", GPIO.HIGH)##Turn on valve connecting tube and exit valves
                        # self.log_q.put(["info","VP","GPIO"+str(GPIO.input("P9_29"))])                
                        if GPIO.input("P9_29"):
                            GPIO.output("P9_24", GPIO.HIGH)##Turn on waste valve
                            
                            time.sleep(0.1)
                            
                            GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve
                            
                        else:
                            i+=1
                            GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve
                            
                            time.sleep(0.1)

                            GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                            
                            if i==10:
                                enter=False
                                i=0
                        time.sleep(0.4)


                    
                GPIO.output("P9_27", GPIO.LOW)##Turn oFF valve connecting tube and exit valves
                GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve    
                GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve 

               
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"])            
                self.log_q.put(["info","VP","-----End of "+str(self.cmd_1)+" - "+str(self.cmd_2)+" drain ------"])
                return True
            

                
            elif self.cmd_1 == "lab":
                self.log_q.put(["info","VP","-----Start of Lab sample drain------"])
                self.log_q.put(["info","VP","-----STEP1------"])
                GPIO.output("P9_27", GPIO.HIGH)##Turn on valve connecting tube and exit valves

                if self.cmd_2 == "labRinse":
                    GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                    self.log_q.put(["info","VP","----------STEP1: TURN ON LAB VALVE------------"])
                    time.sleep(3.2)
                  

                    GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                    self.log_q.put(["info","VP","----------STEP1: TURN OFF LAB VALVE AFTER 2.3 SEC------------"])
                    retry = 0
                    while True:
                    
                        check_Solution = QMessageBox.question(self, "Check solution" ,"Is there any solvent in the vial?")
                        QtWidgets.qApp.processEvents()
                        if check_Solution == QtWidgets.QMessageBox.Yes:
                            QtWidgets.qApp.processEvents()
                            self.log_q.put(["debug", "MT", 'There is solution in the vail. So start normal sequence']) 
                            break
                        else:
                            QtWidgets.qApp.processEvents()
                            GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                            self.log_q.put(["info","VP","----------STEP1A: TURN ON LAB VALVE------------"])
                            time.sleep(0.8)
                            GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                            self.log_q.put(["info","VP","----------STEP1A: TURN OFF LAB VALVE AFTER 2 SEC------------"])
                            retry+=1
                            if retry>=10:
                                retry = 0
                                QMessageBox.warning(self, "Check solution" ,"Retries exceeded. Not enough solution.")
                                QtWidgets.qApp.processEvents()
                                GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                                self.log_q.put(["info","VP","----------STEP1A: TURN ON LAB VALVE------------"])
                                time.sleep(2)
                                GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                                self.log_q.put(["info","VP","----------STEP1A: TURN OFF LAB VALVE AFTER 2 SEC------------"])
                                break
                        
                    self.log_q.put(["info","VP","-----STEP2------"])
                    
                    GPIO.output("P9_24", GPIO.HIGH)##Turn on waste valve
                    self.log_q.put(["info","VP","----------STEP2: TURN ON WASTE VALVE------------"])
                  
                    time.sleep(7)
                    GPIO.output("P9_24", GPIO.LOW)##Turn on waste valve 
                    GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve
                    self.log_q.put(["info","VP","----------STEP2: TURN ON LAB VALVE AFTER 2 SEC TIME DELAY------------"])
                     
                    time.sleep(3)
                    
                    GPIO.output("P9_24", GPIO.HIGH)##Turn on waste valve  

                    time.sleep(2)
                    
                    
                    DS.labSampleVolume = 1.5
                    DS.analyserWasteRemaining+= DS.labSampleVolume                    
                    self.log_q.put(["info","VP","DS.labSampleVolume = "+ str(DS.labSampleVolume)+" DS.sampleRinseSquirtVolume = "+str(DS.sampleRinseSquirtVolume)])
                    self.log_q.put(["info","VP","DS.sampleRinseSquirtVolume-DS.labSampleVolume = "+ str(DS.sampleRinseSquirtVolume-DS.labSampleVolume)])                    
                    
                    
                else:##post solvent squirt

                    GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                    self.log_q.put(["info","VP","----------STEP1: TURN ON LAB VALVE------------"])
                    time.sleep(2.7)
                    GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                    self.log_q.put(["info","VP","----------STEP1: TURN OFF LAB VALVE AFTER 2 SEC------------"])
                    retry = 0
                    while True:
                    
                        check_Solution = QMessageBox.question(self, "Check solution" ,"Is there any solvent in the vial?")
                        QtWidgets.qApp.processEvents()
                        if check_Solution == QtWidgets.QMessageBox.Yes:
                            QtWidgets.qApp.processEvents()
                            self.log_q.put(["debug", "MT", 'There is solution in the vail. So start normal sequence']) 
                            break
                        else:
                            QtWidgets.qApp.processEvents()
                            GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                            self.log_q.put(["info","VP","----------STEP1A: TURN ON LAB VALVE------------"])
                            time.sleep(0.8)
                            GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                            self.log_q.put(["info","VP","----------STEP1A: TURN OFF LAB VALVE AFTER 2 SEC------------"])
                            retry+=1
                            if retry>=10:
                                retry = 0
                                QMessageBox.about(self, "Check solution" ,"Retries exceeded. Not enough solution.")
                                QtWidgets.qApp.processEvents()
                                GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                                self.log_q.put(["info","VP","----------STEP1A: TURN ON LAB VALVE------------"])
                                time.sleep(2)
                                GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                                self.log_q.put(["info","VP","----------STEP1A: TURN OFF LAB VALVE AFTER 2 SEC------------"])                                
                                break
                                                        
                    self.log_q.put(["info","VP","-----STEP2------"])
                    GPIO.output("P9_24", GPIO.HIGH)##Turn on waste valve
                    self.log_q.put(["info","VP","----------STEP2: TURN ON WASTE VALVE------------"])
                   
                    time.sleep(7)
                    GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve
                    self.log_q.put(["info","VP","----------STEP2: TURN ON LAB VALVE AFTER 2 SEC TIME DELAY------------"])
                    
                    time.sleep(6)

                    DS.labSampleVolume = 1.5
                    DS.analyserWasteRemaining+= DS.labSampleVolume                    
                    self.log_q.put(["info","VP","DS.labSampleVolume = "+ str(DS.labSampleVolume)+" DS.postSamplingSolventVolume = "+str(DS.postSamplingSolventVolume)])
                    self.log_q.put(["info","VP","DS.postSamplingSolventVolume-DS.labSampleVolume = "+ str(DS.postSamplingSolventVolume-DS.labSampleVolume)])                    

                GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve
                GPIO.output("P9_27", GPIO.LOW)##Turn OFF valve connecting tube and exit valves        
                GPIO.output("P9_24", GPIO.LOW)##Turn OFF waste valve
                self.log_q.put(["info","VP","-----STEP2: TURN off CONNECTING VALVE, WASTE AND LAB VALVES------"])
                

                

                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"])            
                if self.cmd_2 == "labRinse":
                    self.log_q.put(["info","VP","----------End of "+str(self.cmd_2)+" drain ------------"])   
                else:
                    self.log_q.put(["info","VP","-----End of Lab sample drain------"])                
            
            elif self.cmd_1 == "Rinse_after_labSample":   
                self.log_q.put(["info","VP","-----In Rinse_after_labSample------"])
                self.log_q.put(["info","VP","-----Start of rinse drain------"])
                ##step1
               
                GPIO.output("P9_27", GPIO.HIGH)##Turn on valve connecting tube and exit valves
                GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve 
                self.log_q.put(["info","VP","----------STEP1: TURN ON LAB VALVE------------"])
                time.sleep(2.1)
                GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve 
                self.log_q.put(["info","VP","----------STEP1: TURN OFF LAB VALVE AFTER 2 SEC------------"])                
                self.log_q.put(["info","VP","-----STEP2------"])
                GPIO.output("P9_24", GPIO.HIGH)##Turn on waste valve
                self.log_q.put(["info","VP","----------STEP2: TURN ON WASTE VALVE------------"])
               
                time.sleep(7)
                GPIO.output("P9_28", GPIO.HIGH)##Turn on lab valve
                self.log_q.put(["info","VP","----------STEP2: TURN ON LAB VALVE AFTER 2 SEC TIME DELAY------------"])
                
                time.sleep(6)

                GPIO.output("P9_24", GPIO.LOW)##Turn on waste valve  
                GPIO.output("P9_27", GPIO.LOW)##Turn on valve connecting tube and exit valves 
                GPIO.output("P9_28", GPIO.LOW)##Turn OFF lab valve
                self.log_q.put(["info","VP","-----STEP4: TURN OFF CONNECTING VALVE, WASTE AND LAB VALVE------"])
                self.log_q.put(["info","VP","-----End of rinse drain------"])
                
                # DS.analyserWasteRemaining-= (DS.sampleRinseSquirtVolume)
                self.log_q.put(["info","VP","sampleRinseSquirtVolume = "+ str(DS.sampleRinseSquirtVolume)])                
                self.log_q.put(["info","VP","ANALYSER SOLVENT remaining "+ str(round(DS.analyserSolventRemaining,1))])
                self.log_q.put(["info","VP","Waste bag available for "+str(round(DS.analyserWasteRemaining,1))+" ml"])            
                self.log_q.put(["info","VP","-----End of "+str(self.cmd_1)+" - "+str(self.cmd_2)+" drain ------"])

            self.log_q.put(["info","VP","------------Valve operation completed-------------"])   

    def pump_Controller_function(self):
        timeout_counter = 0
        x=True
        while x:
            # time.sleep(2)
            self.log_q.put(["info","VP","In pump controller function"])
            value = PC.PC_Events()
            self.log_q.put(["info","VP","Pump rotations = %s"%value]) 
            if(value==4):
                self.log_q.put(["info","VP","Sampler pad still wetting"])
                time.sleep(2)
            elif (value==2 or value==3):
                
                self.log_q.put(["info","VP","timeout_counter : %s"%str(timeout_counter)]) 
                
                self.log_q.put(["info","VP","timeout EVENT set"])
                if self.cmd_1 == "preSolventSquirt":
                    PC.PC_wet()
                
                elif self.cmd_1 == "postSolventSquirt":
                    PC.PC_sample()
                
                elif self.cmd_1 == "rinse":
                    PC.PC_rinse()
                
                elif self.cmd_1 == "calibrate":
                    PC.PC_calibrate()
                    
                elif self.cmd_1 == "bagChange":
                    PC.PC_solventBagChange()
                
                
                
                if timeout_counter>=2:
                    QMessageBox.critical(self, 'Pump Error',"Pump error!!!!\n Contact Support.")
                    QtWidgets.qApp.processEvents()
                    self.log_q.put(["info","VP","Pump timed out during the command : %s"%self.cmd_1]) 
                    timeout_counter = 0
                    x=False                        
                timeout_counter+=1
            else:
                self.log_q.put(["info","VP","Sampler pad wetted"])
                DS.actual_rev = value
                Volume = 0
                # Volume = round((float(DS.actual_rev) * pump_dispenseVolume),1)
                Volume = round((float(DS.actual_rev) * DS.pumpDispense_per_rev),1)
                self.log_q.put(["info","VP","DS.pumpDispense_per_rev = %f"%DS.pumpDispense_per_rev])
                
                DS.analyserSolventRemaining-=Volume    #Updating device status values 
                DS.analyserWasteRemaining-=Volume
                self.log_q.put(["info","VP","Solvent dispensed during this SQUIRT = %s, actual rev = %s"%(str(Volume), str(DS.actual_rev))]) 
                if self.cmd_1 == "preSolventSquirt":
                    
                    DS.sampleSquirtVolume =DS.sampleSquirtVolume+ Volume
                    
                    self.log_q.put(["info","VP","Solvent dispensed during PRESOLVENT SQUIRT = %s, actual rev = %s"%(str(DS.sampleSquirtVolume), str(DS.actual_rev))]) 
                
                elif self.cmd_1 == "postSolventSquirt":
                    DS.postSamplingSolventVolume = DS.postSamplingSolventVolume+Volume
                    
                    self.log_q.put(["info","VP","Solvent dispensed during POSTSOLVENT SQUIRT = %s, actual rev = %s"%(str(DS.postSamplingSolventVolume), str(DS.actual_rev))]) 
                
                elif self.cmd_1 == "rinse":
                    DS.sampleRinseSquirtVolume =DS.sampleRinseSquirtVolume+ Volume        
                    self.log_q.put(["info","VP","Solvent dispensed during RINSE = %s, actual rev = %s"%(str(DS.sampleRinseSquirtVolume), str(DS.actual_rev))])                     
                
                elif self.cmd_1 == "calibrate":
                    DS.calibrateVolume = Volume
                    self.log_q.put(["info","VP","Solvent dispensed during CALIBRATE = %s, actual rev = %s"%(str(DS.calibrateVolume), str(DS.actual_rev))])                        
                
                elif self.cmd_1 == "bagChange":
                    DS.resetSolventBagVolume = DS.resetSolventBagVolume+Volume      
                    self.log_q.put(["info","VP","Solvent dispensed during change of bag = %s, actual rev = %s"%(str(DS.resetSolventBagVolume), str(DS.actual_rev))])                                        
                                
                x=False 

                
            