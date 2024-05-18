
import csv
import dateutil.parser
import sys 
import time


from Adafruit_BBIO.SPI import SPI
from datetime import datetime
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# print ("calibration.py first call startin at : startupTime",datetime.now())

#Python files download
#-----------
from Measurement import *
from Spectrometer_capture import Capture
from Valves_Pump_control import Valves



from CSV_Files_Compare import Compare
import deviceStatus as DS

import LED_Driver
#------------

        
class Window(QtWidgets.QMainWindow):

   
    
    def __init__(self, log_q, telemetry_q,charger_connected):
        super (Window, self).__init__()
        Window.setGeometry(self, 0, 22, 480, 250)
        self.seatNumber = '0' 
        self.NextSeatNumber = '0'         
        self.surface = '0' 
        self.Class = '0'     
        self.description = '0'  
        self.flightNumber='0'
        self.tailNumber = '0'      
        self.workOrder = '0' 
        self.deviceId = '0'         
        self.log_q = log_q
        self.data = ''
        self.telemetry_q = telemetry_q        
        self.calComplete = True    
        self.spectroFound = True  
        self.solventBagCounter = 0 
        self.redoCalibrateCounter = 0        
        self.started = True
        # self.topUpSoln = False
        self.quitMiddle = False   
        self.darkMeasured = False
        self.check_sampleWetExtractAndMeasure = True
        self.calSuccess = True
        self.timeout = time.time() + 30   
        self.charger_connected = charger_connected  
        self.drain_problem = False
        self.spectrometerError = False
        # self.cause_Of_logout = ["SAMPLER ERROR", "SAMPLER NOT RETURNING BACK", "LED HEATER ERROR" , "UNABLE TO DRAIN COMPELTELY", "SPECTROMETER NOT FOUND", "INSUFFICIENT SUPPLIES", "CHARGER CONNECTED"]
        # self.logout_cause_value = 0
        # self.home()      

        self.btn = QtWidgets.QPushButton("Quit", self)
        
        self.btn.clicked.connect(self.close_application)
        self.btn.resize(self.btn.sizeHint())
        self.btn.move(300, 210)

        self.calibrationRetryDisplay = QtWidgets.QLabel(self)
        self.calibrationRetryDisplay.move(40, 80)
        self.calibrationRetryDisplay.setGeometry(10, 80, 470, 90)
        self.calibrationRetryDisplay.setAlignment(Qt.AlignTop)
        self.calibrationRetryDisplay.setWordWrap(True)
        # self.calibrationRetryDisplay.hide()
        
        self.statusDisplay = QtWidgets.QLabel(self)
        self.statusDisplay.move(40, 105)
        self.statusDisplay.setGeometry(10, 105, 470, 90)
        self.statusDisplay.setAlignment(Qt.AlignTop)
        self.statusDisplay.setWordWrap(True)
        self.show()

        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            self.quitMiddle = False
            self.charger_connected.clear()
            self.log_q.put(["debug","CA","charger_connected event cleared... "])
            
            self.log_q.put(["debug","CA","!!!!!!!! CLOSING CALIBRATION WINDOW due to "+ DS.cause_Of_logout[DS.logout_cause_value]+" !!!!!!!"])
            self.close_application()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","CA","Timer started"])      

  
              
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","CA","!!!!!!!!!!! EXITING CALIBRATION PAGE !!!!!!!!"])
        self.close()
        return
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","CA","Timer stopped"])          

    # def Valve_Error(self):
        
        # self.quitMiddle = False
        # self.close_application()  

    def samplerConnectionCheck(self):
        """
        Checks whether the sampler is connected to the analyser
        """    
        x = True
        while x:
            status = Sampler.S_cmd_Get_status() 
            self.log_q.put(["debug","CA","---------------------START OF SAMPLER CONNECTION----------------" ])            
            if (status['status'] == 'Disconnected' and status['last_cmd'] == 'Wipe'):
                x=False
                pass
            elif (status['status'] == 'Disconnected' and status['last_cmd'] != 'Wipe'):
                self.statusDisplay.setText('Sampler not connected. Please return it back')
                QtWidgets.qApp.processEvents()            
                self.log_q.put(["debug","CA","--------------SAMPLER CONNECTION IN DISCONNECTED MODULE ----------------------"])

                time.sleep(0.5)
                if (time.time() > self.timeout):            
                    confirm = QMessageBox.question(self, 'Message',
                                "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                QMessageBox.No, QMessageBox.No)
                    QtWidgets.qApp.processEvents()
                    if confirm == QMessageBox.No:
                        x=False
                        DS.process_started = False
                        self.started = False
                        DS.logout_cause_value = 1
                        self.log_q.put(["debug","CA",'*********Closing Calibration window due to '+str(DS.cause_Of_logout[DS.logout_cause_value])+'*********'])           
                        self.timer_and_page_close() 

                    else:
                        self.log_q.put(["debug","CA","Keep waiting for another timeout"])
                        self.timeout = time.time() + 30      
            elif (status['status'] == 'Ready' or status['status'] == 'Busy'):  
                self.timeout = time.time() + 30
                self.log_q.put(["debug","CA","--------------SAMPLER CONNECTION IN READY MODULE ----------------------"])
                x=False
                pass 
            else:
                x=False
                pass  
            loop =  QtCore.QEventLoop()    
            QTimer.singleShot(1000, loop.quit)                



    def steps(self):
        """
        Returns the following values
        0,0 - Successful calibration steps executed (True)
        1 - Spectrometer error 
        2 - Charger connected / Sampler error / Sampler not returning back / Unable to drain completely / not interested in calibration retry
        3 - Calibration failed
        """
        self.quitMiddle = True
        LED_Driver.LED_heaterON(self.log_q) #turn heater on ready for using LEDs later
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()     
        if DS.process_started:         
            if self.started:
                self.darkMeasurement = self.dark()
                self.log_q.put(["debug","CA","Entering dark measurement"]) 
                if self.darkMeasurement == 1:
                    sampleWetExtractAndMeasure = self.sampleWetExtractAndMeasure()  
                    self.log_q.put(["debug","CA",'sampleWetExtractAndMeasure '+str(sampleWetExtractAndMeasure)])           
                    self.timer_and_page_close()
                    if sampleWetExtractAndMeasure:
                        
                        
                        if self.check_sampleWetExtractAndMeasure:
                            self.log_q.put(["debug","CA","Timer stopped while returning success response"])    
                            return 0
                        else:
                            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
                            return 3 #CALIBRATION FAILED  / Not interested in calibration retry
                    else:
                        self.log_q.put(["debug","CA","Timer stopped in steps function"])
                        if  self.drain_problem:
                            if self.calComplete:
                                self.log_q.put(["debug","CA","Calibration success but draining failed. So enabling NEXT button"])                                                                     
                                return 0
                            else:
                                self.log_q.put(["error","CA","Calibration Failed. Also, draining failed. So No retires"])
                                return 3 #CALIBRATION FAILED                             
                            
                        if DS.logout_cause_value != 3 and DS.logout_cause_value != 7 and (not self.spectrometerError):
                            drainvalve = Valves(self.log_q, False, "waste", "calibrate") #enable waste drain valve
                            drainvalve.operateValves()
                        DS.engineer = True
                        self.charger_connected.clear()
                        
                        if self.spectrometerError:
                            self.log_q.put(["debug","CA",'*********Closing Calibration window due to spectrometer error during reference measurement*********'])           
                            return 1
                        
                        self.log_q.put(["debug","CA",'*********Closing Calibration window due to '+str(DS.cause_Of_logout[DS.logout_cause_value])+'*********'])           
                        # self.timer_and_page_close()   
                        if DS.logout_cause_value != 7:
                            return 2 ###charger is connected / sampler error / Sampler not returning back / Unable to drain completely 
                        else:
                            return 3 #CALIBRATION FAILED 
                elif self.darkMeasurement == 0:
                    # self.calib_spectrometerNotFoundError()
                    return 1
                else: ##Process not started
                    self.log_q.put(["debug","CA",'*********Closing Calibration window due to '+str(DS.cause_Of_logout[DS.logout_cause_value])+'*********'])           
                    self.timer_and_page_close()                            
                    return 2 ###charger is connected / sampler error / Sampler not returning back / Unable to drain completely 
                return 0
     
            else: 
                self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
                return 2
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return 2             
               
        
    def sampleWetExtractAndMeasure(self):
        """
        This module performs wetting sampler pad, extracts it and measure the reference spectrum
        """
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()
        if DS.process_started:         
            if self.started:
            
                squirtSolvent_status = self.squirtSolvent()
                if squirtSolvent_status:
                    self.samplerConnectionCheck()
                    QtWidgets.qApp.processEvents()
                    if self.started:                 
                        reference = self.reference()
                        if reference:
                            return True
                        else:
                            return False
                    else:        
                        return False
                else:
                    return
                
            else:
                return 
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return False

    
            
        
    def dark(self):
        """
        Measures dark spectrum
        Returns 
        0 - False
        1 - True
        2 - Process not started
        """    
        if DS.process_started:         
            self.log_q.put(["debug", "CA", '........Calibration started.......'])   
            self.statusDisplay.setText('Calibration started...')
            QtWidgets.qApp.processEvents()    

            LED_Driver.LED_OFF(self.log_q)
      
            self.log_q.put(["debug", "CA", 'Capturing Dark spectrum...'])        
            self.statusDisplay.setText('Analysing dark measurement...')
            QtWidgets.qApp.processEvents()
            self.dark_capture = Capture(self.log_q) #Calls the dark file to capture dark spectrum
            self.spectroFound = self.dark_capture.darkSpectrum()
            if self.spectroFound:
                self.log_q.put(["debug", "CA", 'SUCCESS!!! Dark spectrum captured'])
                self.darkMeasured = True
                return(1)
            else: 
                self.calib_spectrometerNotFoundError() 
                return 0
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return 2                 


    def calib_spectrometerNotFoundError(self):
        """
        Unresponsive spectrometer during measurement will emit signal to return the analyser to the manufacturer
        """     
        QMessageBox.warning(self, "Spectrometer Error" ,"Spectrometer Error")
        self.log_q.put(["error", "CA", 'SPECTROMETER NOT FOUND!!!']) 
        QtWidgets.qApp.processEvents() 
        self.spectrometerError = True
        self.timer_and_page_close()         


        
    def squirtSolvent(self):
        """
        Wet the sampler pad
        """     
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()
        if DS.process_started:            
            if self.started:  
                self.darkMeasured = False
                self.statusDisplay.setText('Wetting and extracting sample from Sampler pad')
                QtWidgets.qApp.processEvents() 
                
      
                x=True
                while (x):                
                    samplerRotateFast_status = samplerComms.samplerRotate(self.log_q,"Fast","calibrate") 
                    self.log_q.put(["debug","CA","Rinsing the sampler pad and extracting the solvent for reference spectrum calibration. Fast rotate status = "+ str(samplerRotateFast_status)])  
                    if samplerRotateFast_status == 0: #### Sampler is disconnected
                        self.samplerNotPresent()
                        QtWidgets.qApp.processEvents()
                    elif samplerRotateFast_status == 2: ### Sampler is connected but the previous command resulted in error
                        pass
                    elif samplerRotateFast_status == 3: ### Sampler error unrecovered
                        self.samplerError()
                        x=False
                        self.started = False
                        
                        self.timer_and_page_close()                         
                        return False
                    else:##Sampler rotated without any error or disconnection
                        x=False 
                        return True
                 
            else:
                return 
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return False            
            
    def samplerError(self):
        QMessageBox.critical(self, 'Sampler Error',"Sampler error!!!! \n Contact Support.")
        QtWidgets.qApp.processEvents()
        
        self.log_q.put(["debug","MT","Sampler entered into unreceoverable state. Operator instructed to return it back to manufacturer." ])        
        drain = Valves(self.log_q, False, "waste", "calibrate")
        drain.operateValves()
        
        
        
    def reference(self):
        """
        Measures Reference spectrum
        """     
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()
        if DS.process_started:          
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
                        self.calib_spectrometerNotFoundError() #exit is the only choice
                         
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
                                self.quitMiddle = False
                                self.close_application()
                                return False
                            else:
                                self.log_q.put(["debug","MT","Keep waiting for another timeout"])
                                self.timeout = time.time() + 30      
                    else:### All requirements satisfied.
                        checkLoop = False
                        self.log_q.put(["debug", "CA", 'Capturing Reference spectrum...'])            
                        self.statusDisplay.setText('Analysing reference measurement...')
                        QtWidgets.qApp.processEvents()
                        
                        self.reference_capture = Capture(self.log_q) #Calls the reference file to capture reference spectrum
                        self.captureReference = self.reference_capture.Reference()
                        self.log_q.put(["debug", "CA", 'Trying to capture Reference spectrum...']) 
                        if self.captureReference:

                            self.log_q.put(["debug", "CA", 'SUCCESS!!!!Reference spectrum captured']) 
                            LED_Driver.LED_OFF(self.log_q)
                            if self.referenceCheck():
                                self.log_q.put(["debug", "CA", 'In SELF.REFERENCE, RETURNING TRUE']) 
                                return True
                            else:
                                self.log_q.put(["debug", "CA", 'In SELF.REFERENCE, RETURNING FALSE']) 
                                return False
                                
                        else:
                            self.calComplete = False
                            self.calib_spectrometerNotFoundError() 
                            self.valve_drain()        
                            return False

            else:
                self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
                return False
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return False             
        
    def referenceCheck(self):
        """
        Check the reference sepctrum
        """     
        self.samplerConnectionCheck()
        QtWidgets.qApp.processEvents()
        if DS.process_started:          
            if self.started:     
                self.log_q.put(["debug", "CA", 'Comparing Reference spectrum against standard reference spectrum'])    
                
                self.refComparison = Compare(self.log_q, True, False)###True=Calibrate check, False - LED check from Analyser GUI
                (self.calComplete,  self.Variation, self.minVariation, self.maxVariation) = self.refComparison.variationCalculation()
                self.log_q.put(["debug", "CA", 'Variation values are ' + str(self.Variation)])

                if self.calComplete:
                    self.log_q.put(["debug","CA","IntegrationTime is " + str(DS.integrationTime)]) 
                    self.log_q.put(["debug","CA","Calibration completed " ]) 
                    # self.log_q.put(["debug","CA","Moving to valve drain" ])
                    self.calSuccess = True
                    self.ResultQ()
                    if self.valve_drain():
                        self.log_q.put(["debug","CA","IN REFERENCE CHECK, Valve drain success" ])
                        return True
                    else:
                        self.log_q.put(["debug","CA","IN REFERENCE CHECK, Valve drain FAIL!!!" ])
                        return False
                else:
                    self.log_q.put(["info","CA","Checking calibration retries,Retry of calibration: "+str(self.redoCalibrateCounter)])
                    self.calibrationRetryDisplay.show()
                    self.calibrationRetryDisplay.setText('Calibration Retry # %d'%(self.redoCalibrateCounter+1))
                    QtWidgets.qApp.processEvents()
                    self.statusDisplay.setText('Invalid reference. Retrying calibration')
                    QtWidgets.qApp.processEvents()                    
                    if self.redoCalibrateCounter<2:
                        self.log_q.put(["debug", "CA", 'Maximum variation between captured Reference spectrum and Factory Reference spectrum is ' + str(self.maxVariation)])
                        self.log_q.put(["debug", "CA", 'Calibration not successful!!! Retrying calibration!!!!']) 
                        
                        self.redoCalibrateCounter+=1  
                        self.log_q.put(["info","CA","Retry of calibration, after adding: "+str(self.redoCalibrateCounter)])
                        if self.badReferenceSpectrum():
                            self.log_q.put(["info", "CA", 'IN REFERENCE CHECK, returning TRUE'])                     
                            return True
                        else:
                            self.log_q.put(["info", "CA", 'IN REFERENCE CHECK, returning FALSE '])                     
                            return False
                               
                                
                    else:
                        self.log_q.put(["info","CA","Calibration retried twice and still no valid reference spectrum. Need to investigate further. Operator instructed to return the analyser to the manufacturer!!!!"])
                        self.statusDisplay.setText('Number of retries exceeded. Change consummables and redo calibration.')
                        QtWidgets.qApp.processEvents()
                        # time.sleep(1)
                        QMessageBox.critical(self, "Calibration error" ,"Calibration error!!!! \n Change consummables and redo calibration.")
                        QtWidgets.qApp.processEvents()
                        self.calibrationRetryDisplay.setText('Calibration Failed!!!')
                        QtWidgets.qApp.processEvents()
                        
                        self.calComplete = False
                        LEDCheck = False    
                        DS.logout_cause_value = 7 
                        self.ResultQ()
                        if self.valve_drain():
                            self.log_q.put(["debug","CA","IN BAD REFERENCE SPECTRUM, Valve drain success" ])
                            if self.check_sampleWetExtractAndMeasure:
                                self.log_q.put(["debug","CA","IN REFERENCE CHECK, Valve drain success and reference spectrum retries SUCCESS" ])
                                return True
                            else:
                                self.log_q.put(["debug","CA","IN REFERENCE CHECK, Valve drain success but Returning False due to failure in retries" ])
                                return False                        
                        else:
                            self.log_q.put(["debug","CA","IN REFERENCE CHECK, Valve drain FAIL" ])
                            return False                    
                        
            else:
                self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
                return False
        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return False                        

               

    def samplerNotPresent(self):
        QMessageBox.warning(self, 'Message',"Sampler not in place. Return it back and try again")
        QtWidgets.qApp.processEvents()
        self.log_q.put(["debug","MT","Sampler is disconnected. Operator instructed to connect the sampler." ])
            
           
    def badReferenceSpectrum(self):
        """
        If the measured spectrum varies more than 50% of reference spectrum, redo the calibration
        """  
        if DS.process_started:         
            self.log_q.put(["info","CA","Bad reference spectrum"])   

            time.sleep(1)


            self.drainvalve = Valves(self.log_q, False, "waste", "calibrate")
            
            # self.drainvalve.operateValves()
            # self.topUpSoln = False
            
            if self.drainvalve.operateValves():
                self.topUpSoln = False
            else:
                self.log_q.put(["info", "CA", 'Drain error occured. Exitting']) 
                self.quitMiddle = False
                self.drain_problem = True
                self.close_application()  
                return False

            # self.log_q.put(["info","CA","Retry of calibration: "+str(self.redoCalibrateCounter)])
            # self.redoCalibrateCounter+=1
            self.check_sampleWetExtractAndMeasure = self.sampleWetExtractAndMeasure()
            if self.check_sampleWetExtractAndMeasure:
                self.log_q.put(["info", "CA", 'IN badReferenceSpectrum returning True']) 
                if self.redoCalibrateCounter==2:
                    self.check_sampleWetExtractAndMeasure = False
                return True
            else:
                self.log_q.put(["info", "CA", 'IN badReferenceSpectrum returning False']) 
                return False
            

        else:
            self.log_q.put(["error","CA","Process stopped due to "+str(DS.cause_Of_logout[DS.logout_cause_value])])
            return False                   
                    

    def valve_drain(self):
        """
        Drain through the valves
        """     
        # self.calSuccess = True
        
        LED_Driver.LED_OFF(self.log_q)
        self.log_q.put(["debug", "CA", 'Draining Residual solvent'])        
        self.statusDisplay.setText('Draining Residual solvent')
        QtWidgets.qApp.processEvents()
        
        self.drainvalve = Valves(self.log_q, False, "waste", "calibrate") #enable waste drain valve
        
   
        
        if self.drainvalve.operateValves():
        
            self.log_q.put(["debug", "CA", 'Residual solvent drained'])       
            self.statusDisplay.setText('Drained')
            QtWidgets.qApp.processEvents()
            if self.calComplete:
                self.log_q.put(["debug", "CA", 'Calibration Complete...']) 
                self.statusDisplay.setText('Calibration Complete...')
                QtWidgets.qApp.processEvents()
                # self.ResultQ()
                
            else:
                self.log_q.put(["debug", "CA", 'Calibration INCOMPLETE...']) 
                self.statusDisplay.setText('Calibration INCOMPLETE due to internal errors...')
                QtWidgets.qApp.processEvents()
                time.sleep(2) 
                self.calSuccess = False
                # self.ResultQ()
                # self.calibrationRetryDisplay.hide()
                
            
            self.suppliesUpdated()
            self.timer_and_page_close()
            return True
        else:
            self.log_q.put(["debug", "CA", 'Error while draining'])   
            self.drain_problem = True
            return False
        

        
    def suppliesUpdated(self):       
        """
        Update the available supplies 
        """     
        DS.analyserSolventCount= round(DS.analyserSolventRemaining/DS.sampleVolume)   #Updating device status values            
        self.log_q.put(["info","CA","Solvent bag available for "+str(DS.analyserSolventCount)+" samples"])
        self.log_q.put(["info","CA","ANALYSER SOLVENT REMAINING  = "+str(round(DS.analyserSolventRemaining,1))])
        
        DS.analyserWasteCount= round(DS.analyserWasteRemaining/DS.sampleVolume)   #Updating device status values 
        self.log_q.put(["info","CA","Waste bag available for "+str(DS.analyserWasteCount)+" samples"]) 
        self.log_q.put(["info","CA","ANALYSER WASTE REMAINING  = "+str(round(DS.analyserWasteRemaining,1))])     
        self.log_q.put(["info","CA",'-------------Exiting Calibration---------------'])
        

    def ResultQ(self):
        """
        Upload the result to the cloud 
        """      
        Cal_Q = []
        
        todaystr = str(datetime.date.today())
        tzoffset = datetime.datetime.now(timezone(DS.ourTimezone)).strftime('%z')
        if self.calSuccess:
            self.result = 'Calibration successful'
            DS.calibratedTime = time.time()
            calibrateTime = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_q.put(["info","CA","Calibration successful. Calibrated at %s, and the value is %s"%(str(calibrateTime),str(DS.calibratedTime))])
            
        else:
            self.result = 'Calibration failed!! See log file'


        result_format = '''{ "deviceId": "%s", "uploadDate": "%s", "messageType": "%s","resultStatus": "%s",
        "workOrderId": %d, "operatorId": %d,"flight":{"operatingAirlineCode":"%s", "flightDate":"%s",
        "flightNumber":"%s", "planeModel":"%s","planeSeries":"%s", "tailNumber":"%s"},"testDate":"%s",
        "regime":{"regimeId": %d,"RegimeInstanceId": "%s", "aircraftType": "%s", "aircraftConfig": "%s",
        "results":[{ "sampleDate": "%s","locationId": %d, "location1": "%s", "location2": "%s", "location3": "%s", 
        "surface": "%s", "wipeTime": %d,"padAge": %d, "result": %d, "confidence": %d, "analyserBatteryLevel": %d,
        "samplerBatteryLevel": %d, "samplerReconnectTime": %d,"samplerSampleStatus": %d, "labSampleID":"%s", "notes": "%s"}]}}'''
        
        Cal_Q = result_format%(DS.deviceName, todaystr, 'Result', 'Ongoing', 
                                    27, 27,'QF', todaystr, 
                                    '102', DS.ourSiteIataCode, tzoffset, 
                                    'ABC', todaystr,
                                    0, str(DS.samplerID), DS.analyserSolventID, DS.userID,  
                                    str(datetime.datetime.now(timezone(DS.ourTimezone)).isoformat()), 0, 0, self.result, self.result,
                                    str(self.maxVariation), DS.samplerTriggerTime, DS.analyserPadAge, 0, 0, DS.analyserBattery, 
                                    DS.samplerBattery, DS.samplerReconnectTime, DS.samplerLastSampleStatus, DS.analyserLabSampleID, 'Calibration')
        
        self.telemetry_q.put(Cal_Q)
        

       
     
    
    def close_application(self):
        self.log_q.put(["warning", "CA", 'QUIT button clicked!!!!'])    
        self.log_q.put(["warning", "CA", 'self.quitMiddle = '+str(self.quitMiddle)])    
        if self.quitMiddle:
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
     
          
            if choice == QtWidgets.QMessageBox.Yes:
                if self.started:
                    self.started = False
                self.log_q.put(["debug", "CA", 'Exiting the application.....']) 
                LED_Driver.LED_OFF(self.log_q)
                LED_Driver.LED_heaterOFF(self.log_q)
                if self.darkMeasured:
                    pass
                else:
                    self.drainvalve = Valves(self.log_q, False, "waste", "calibrate") #enable waste drain valve
                    self.drainvalve.operateValves()
                self.suppliesUpdated()
                self.timer_and_page_close()
                QtWidgets.qApp.processEvents()
                # self.sig_calibration_Close.emit()
            
            else:
                QtWidgets.qApp.processEvents()
                self.log_q.put(["debug", "CA", 'Exit cancelled'])                
                pass
        else:
            self.started = False
    
            self.log_q.put(["debug","CA",'*********Closing Calibration window due to '+str(DS.cause_Of_logout[DS.logout_cause_value])+'*********'])           
            self.timer_and_page_close()    
                        
