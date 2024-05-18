#Enters the maintenance mode
import datetime
import sys 
import time

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# print ("StatusWindow.py first call startin at : startupTime",datetime.datetime.now())

import LED_Driver
import Sampler

import AnalyserSamplerComms as samplerComms
import deviceStatus as DS
import Pump_controller_driver as PC


from CSV_Files_Compare import Compare
from deviceDetails import devDetails
from Spectrometer_capture import Capture
from Valves_Pump_control import Valves
from VirtualKeyboard import VirtualKeyboard



def samplerPresent(timeout):
# Just check if there is a Sampler
    """
    0 - Sampler present
    1 - Sampler disconnected but not timedout
    2 - Sampler disconnected and timedout
    """
    # timeout = time.time() + 30
    status = Sampler.S_cmd_Get_status()
    if status['status'] == 'Disconnected':
        if (time.time() > timeout):
        
            return 2 # Sampler not present and timedout
        else:
            return 1 # Sampler not present but not timedout
    else:
        return 0 # Sampler present

      
        
class Status_Window(QWidget):

    sig_availableSupplies = pyqtSignal()
    sig_SpectrometerError = pyqtSignal()
    sig_Sampler_will_not_return = pyqtSignal() ###This signal will be used to logout user if the charger is connected.

    def __init__(self, log_q, charger_connected):
        super (Status_Window, self).__init__()
        Status_Window.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q
        self.charger_connected = charger_connected
        self.started = True         
        self.rarRetry = 0
        self.samplerError = False
        self.sampler_will_not_return = False
        
        
        self.cause_Of_logout = ["SAMPLER ERROR", "SAMPLER NOT RETURNING BACK", "LED HEATER ERROR" , "UNABLE TO DRAIN COMPLETELY", "INSUFFICIENT SUPPLIES", "CHARGER CONNECTED"]
        self.logout_cause_value = 0
        self.log_q.put(["debug","JS","@@@@@@@@ Opening Status Window @@@@@@@@@"])
        self.home()
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
      

    def home(self): 
        """
        Display the available supplies.
        1. Displays solvent bag capacity to sample, (Samples)
        2. Displays waste bag capacity to drain, (Samples)
        3. Displays sampler pad age, (number of samples taken)
        
        Pushbuttons:
        1. New Bag - resets the bag volume to full/empty
        2. New pad - resets the sampler pad age to 0 and starts rinse and measure process to check the clenaliness of the new sampler pad
        3. Device details - Migrates to new page that displays analyser and sampler details
        4. Ok - exits the page
        """
        
        self.titleText = QtWidgets.QLabel("Available Supplies", self)
        self.titleText.move(50, 20)
        self.titleText.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        
        self.serialNo = QtWidgets.QLabel("Serial No.", self)
        self.serialNo.move(260, 20)
        self.serialNo.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))  

        self.serialValue_solvent = QtWidgets.QLabel("", self)
        self.serialValue_solvent.setGeometry(270, 80,150,30)
        self.serialValue_solvent.setAlignment(Qt.AlignTop)        
        # self.serialValue_solvent.move(250, 60)
        self.serialValue_solvent.setFont(QtGui.QFont("Arial", 14))        

        # self.serialValue_residual = QtWidgets.QLabel("", self)
        # self.serialValue_residual.setGeometry(250, 95,150,30)
        # self.serialValue_residual.setAlignment(Qt.AlignTop)        
        # self.serialValue_residual.move(250, 95)
        # self.serialValue_residual.setFont(QtGui.QFont("Arial", 14))        

        self.soln_bladder = QtWidgets.QLabel("Solvent", self)
        self.soln_bladder.move(10, 60)
        self.soln_bladder.setFont(QtGui.QFont("Arial", 14))        
        
        self.soln_bladder_value = QtWidgets.QLabel(self)
        self.soln_bladder_value.setGeometry(140, 60,50,30)
        self.soln_bladder_value.setAlignment(Qt.AlignTop)
        DS.analyserSolventCount = DS.analyserSolventRemaining/DS.sampleVolume #solventCount
        self.soln = round(DS.analyserSolventCount)
        self.soln_bladder_value.setText(str(self.soln)) 
        self.log_q.put(["info","SW","ANALYSER SOLVENT Count = "+str(self.soln)])  
        self.log_q.put(["info","SW","ANALYSER SOLVENT remaining = "+str(round(DS.analyserSolventRemaining,1))])          

        self.soln_bladder_samples = QtWidgets.QLabel("Samples", self)
        self.soln_bladder_samples.move(170, 60)
        self.soln_bladder_samples.setFont(QtGui.QFont("Arial", 14)) 

        self.Reset_soln_bladder_value = QtWidgets.QPushButton("NEW BAGS", self)    
        self.Reset_soln_bladder_value.move(360, 75)
        self.Reset_soln_bladder_value.setFont(QtGui.QFont("Arial", 14))         

        self.waste_bladder = QtWidgets.QLabel("Residual", self)
        self.waste_bladder.move(10, 95)
        self.waste_bladder.setFont(QtGui.QFont("Arial", 14))  
      
        self.waste_bladder_value = QtWidgets.QLabel(self)
        self.waste_bladder_value.setGeometry(140, 95,50,30)
        self.waste_bladder_value.setAlignment(Qt.AlignTop)
        DS.analyserWasteCount = DS.analyserWasteRemaining/DS.sampleVolume #wasteCount
        self.waste = round(DS.analyserWasteCount)
        self.waste_bladder_value.setText(str(self.waste))
        self.log_q.put(["info","SW","ANALYSER WASTE Count = "+str(self.waste)])
        self.log_q.put(["info","SW","ANALYSER WASTE remaining = "+str(round(DS.analyserWasteRemaining,1))])          
        self.serialValue_solvent.setText(DS.analyserSolventID)
        # self.serialValue_residual.setText(DS.analyserWasteID)
        
        self.waste_bladder_samples = QtWidgets.QLabel("Samples", self)
        self.waste_bladder_samples.move(170, 95)
        self.waste_bladder_samples.setFont(QtGui.QFont("Arial", 14))

        # self.Reset_waste_bladder_value = QtWidgets.QPushButton("NEW BAG", self)    
        # self.Reset_waste_bladder_value.move(360, 90)
        # self.Reset_waste_bladder_value.setFont(QtGui.QFont("Arial", 14))         
        
        self.sampler_pad = QtWidgets.QLabel("Sampler Pad", self)
        self.sampler_pad.move(10, 130)
        self.sampler_pad.setFont(QtGui.QFont("Arial", 14))

        
        self.sampler_pad_counts = QtWidgets.QLabel(self)
        self.sampler_pad_counts.setGeometry(140, 130,50,30)
        self.sampler_pad_counts.setAlignment(Qt.AlignTop)
        self.samplerPad = DS.analyserPadAge        
        self.sampler_pad_counts.setText(str(self.samplerPad))
        self.log_q.put(["info","SW","analyserPadAge = "+str(self.samplerPad)])

        self.sampler_pad_samples = QtWidgets.QLabel("Samples", self)
        self.sampler_pad_samples.move(170, 130)
        self.sampler_pad_samples.setFont(QtGui.QFont("Arial", 14)) 
        
        self.Reset_sampler_pad_counts = QtWidgets.QPushButton("NEW PAD", self)    
        self.Reset_sampler_pad_counts.move(360, 125)
        self.Reset_sampler_pad_counts.setFont(QtGui.QFont("Arial", 14))
                                
        self.ok = QtWidgets.QPushButton("OK", self)
        self.ok.move(300,200)
        self.ok.resize(self.ok.minimumSizeHint())
        self.ok.clicked.connect(self.close_window)

        
        self.dDetails = QtWidgets.QPushButton("Device Details", self)
        self.dDetails.move(100,200)
        self.dDetails.resize(self.dDetails.minimumSizeHint())
        self.dDetails.clicked.connect(self.deviceDetails)        
        
        self.Reset_soln_bladder_value.clicked.connect(self.initiatePrimeAndDrain)        
        # self.Reset_waste_bladder_value.clicked.connect(self.resetWasteValue)
        self.Reset_sampler_pad_counts.clicked.connect(self.resetSamplerpadValue)  

        self.rinseDisplay = QtWidgets.QLabel(self)
        self.rinseDisplay.setGeometry(10, 150, 460, 50)    
        self.rinseDisplay.setWordWrap(True)

        
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            self.timer_and_page_close()
            self.charger_connected.clear()
            self.log_q.put(["debug","SW","charger_connected event cleared... "])
            self.log_q.put(["debug","SW","!!!!!!!! CLOSING STATUS WINDOW !!!!!!!"])
            self.SN_samplerWillNotReturn()
        self.Timer.start(1000)    

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","SW","Timer started"])

    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","SW","!!!!!!!!!!! EXITING STATUS WINDOW PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","SW","Timer stopped"])  

#Exit the page                
    def close_window(self):
        
        self.started = False
        self.timer_and_page_close()         
        self.log_q.put(["debug","SW",'------------ Closing Status window -------------------']) 
        self.sig_availableSupplies.emit()
        
    def close_window_sampler_error(self):
        self.started = False
    
        if self.samplerError:
            QMessageBox.critical(self, 'Sampler Error',"Sampler error!!!! \n Contact Support.")
            QtWidgets.qApp.processEvents()
            DS.logout_cause_value = 0
            self.log_q.put(["debug","SW","Sampler entered into unrecoverable state. Operator instructed to return it back to manufacturer." ])                                
            self.log_q.put(["debug","SW","DS.logout_cause_value = %d" %DS.logout_cause_value ])                    
            drain = Valves(self.log_q, False, "waste", "rinse")
            if drain.operateValves():
                pass
            else:
                self.log_q.put(["debug","SW","DS.logout_cause_value = %d" %DS.logout_cause_value ])                    
            self.log_q.put(["debug","SW","Logging out of this window due to "+DS.cause_Of_logout[DS.logout_cause_value]+" !!!!!!!!" ])                    
            
        elif self.sampler_will_not_return:
            self.log_q.put(["debug","SW","DS.logout_cause_value = %d" %DS.logout_cause_value ])                    
            
            self.log_q.put(["debug","SW","Logging out of this window due to "+DS.cause_Of_logout[DS.logout_cause_value]+" !!!!!!!!" ])                    
            
            
        self.close_window()    
        # self.timer_and_page_close() 
        # self.sig_Sampler_will_not_return.emit()
        
    def SN_samplerWillNotReturn(self):
        self.sampler_will_not_return = True
        self.close_window_sampler_error()         

    
    def initiatePrimeAndDrain(self):
        """
        Primes pump from new solvent bag then drains into new residual bag
        then resets appropriate counters
        """
        if DS.process_started:       
            self.log_q.put(["debug","SW","Solvent RESET button clicked" ])
            # self.Reset_soln_bladder_value.setEnabled(False)
            self.timer_and_page_close()
            QtWidgets.qApp.processEvents()
            
            DS.analysersolventTotal+=1    #Increment the total solvent bags used   
            DS.analyserwasteTotal+=1    #Increment the total waste solvent bags used                
            
            
            self.serial_no_page = serialNumber(self.log_q, self.charger_connected)
            # self.serial_no_page.show()
            self.serial_no_page.sig_serialNumber_entered.connect(self.display_serial_number)
            self.serial_no_page.sig_SamplerError.connect(self.sampler_Error_received)
            self.serial_no_page.sig_SN_sampler_will_not_return.connect(self.SN_samplerWillNotReturn)
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return       
            
    def display_padAge(self):
            self.sampler_pad_counts.setText(str(DS.analyserPadAge))
            self.log_q.put(["debug","SW","Pad Age set to "+str(DS.analyserPadAge)])
        
    def display_serial_number(self):
        if DS.process_started:  
            self.enableTimer()
            self.serialValue_solvent.setText(DS.analyserSolventID)
            # self.serialValue_residual.setText(DS.analyserWasteID)
            
            QtWidgets.qApp.processEvents()
            
            DS.analyserSolventCount = DS.analyserSolventRemaining/DS.sampleVolume #solventCount
            self.log_q.put(["debug","SW","sampleVolume = "+ str(DS.sampleVolume)])          
            self.soln_bladder_value.setText(str(round(DS.analyserSolventCount))) 
            self.log_q.put(["info","SW","Solvent bag replaced"])
            self.log_q.put(["info","SW","analyserSolventCount = "+str(DS.analyserSolventCount)])
            self.log_q.put(["debug","SW","ANALYSER SOLVENT remaining = "+str(round(DS.analyserSolventRemaining,1)) ])        
            
            DS.analyserWasteCount = round(DS.analyserWasteRemaining/DS.sampleVolume)
            self.waste_bladder_value.setText(str(round(DS.analyserWasteCount)))               
            self.waste = round(DS.analyserWasteRemaining/DS.sampleVolume)
            self.log_q.put(["info","SW","Residual bag replaced"])
            self.log_q.put(["info","SW","analyserWasteCount = "+str(DS.analyserWasteCount)])
            self.log_q.put(["debug","SW","ANALYSER WASTE remaining = "+str(round(DS.analyserWasteRemaining,1)) ])
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return     
 
        
    def sampler_Error_received(self):
        self.samplerError = True   
        self.close_window_sampler_error()        
        

    def resetSamplerpadValue(self):
        """
        Resets the sampler pad age and starts rinsing and measuring the new sampler pad
        """    
        if DS.process_started:       
            self.log_q.put(["debug","SW","Sampler Pad RESET button clicked" ])
            DS.analyserPadsTotal+=1    #Updating device status values
            self.new_sampler_pad_page = newSamplerPad(self.log_q, self.charger_connected)
            self.sampler_pad_counts.setText(str(DS.analyserPadAge))
            self.log_q.put(["debug","SW","Sampler Pad count RESET to " +str(DS.analyserPadAge)])
            # self.serial_no_page.show()
            self.new_sampler_pad_page.sig_padReplaced.connect(self.display_padAge)
            self.new_sampler_pad_page.sig_SamplerError.connect(self.sampler_Error_received)
            self.new_sampler_pad_page.sig_SN_sampler_will_not_return.connect(self.SN_samplerWillNotReturn)
            self.new_sampler_pad_page.sig_NS_spectrometerError.connect(self.spectrometerNotFoundError)

            # self.Reset_sampler_pad_counts.setEnabled(False)
            QtWidgets.qApp.processEvents()
            
    def deviceDetails(self):
        """
        Migrates to the page that displays the sampler and analyser details
        """     
        if DS.process_started:          
            self.timer_and_page_close()             
            self.log_q.put(["debug","SW",'@@@@@@@ Opening device details window @@@@@@@@@@@'])        
            self.devDetails = devDetails(self.log_q, self.charger_connected)
            self.devDetails.show()
            self.devDetails.sig_devDetails.connect(self.enableTimer)        
            if self.devDetails.charger_connected_LOGOUT():
                self.started = False
                self.SN_samplerWillNotReturn()
            
                
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return 
 
    def isSamplerPresent(self):
        QMessageBox.warning(self, 'Message',"Sampler not in place. Return it and try again")
        QtWidgets.qApp.processEvents()
        self.log_q.put(["debug","SW","Sampler is disconnected. Operator instructed to connect the sampler." ])
        
 
##### This is a new Feature to rinse and measure the sampler pad when RESET button was clicked by the user. ##########

    # def checkRef(self):
        # if DS.process_started:     
            # self.checkRefAfterRinse()
        # else:
            # self.log_q.put(["debug","SW","Charger is connected." ])
            # return       
        

        
                
    def spectrometerNotFoundError(self):
        """
        Unresponsive spectrometer during measurement will emit signal to return the analyser to the manufacturer
        """        
        if self.started:   
            QMessageBox.warning(self, "Spectrometer Error" ,"Spectrometer Error")
            self.log_q.put(["error", "SW", '-----SPECTROMETER NOT FOUND!!!------']) 
            QtWidgets.qApp.processEvents()        
            # self.timer_and_page_close()
            # self.rinseDisplay.setText("Draining waste solvent")
            # QtWidgets.qApp.processEvents()
            drain = Valves(self.log_q, False, "waste", "postSolventSquirt")
            drain.operateValves()
            DS.analyserSolventCount= round(DS.analyserSolventRemaining/DS.sampleVolume)   #Updating device status values    
                    
            self.log_q.put(["info","SW","Solvent bag available for "+str(DS.analyserSolventCount)+" samples"])
            self.log_q.put(["info","SW","ANALYSER SOLVENT REMAINING  = "+str(round(DS.analyserSolventRemaining,1))])
            
            DS.analyserWasteCount= round(DS.analyserWasteRemaining/DS.sampleVolume)   #Updating device status values 
            self.log_q.put(["info","SW","Waste bag available for "+str(DS.analyserWasteCount)+" samples"]) 
            self.log_q.put(["info","SW","ANALYSER WASTE REMAINING  = "+str(round(DS.analyserWasteRemaining,1))])
      
            
            # self.sig_SpectrometerError.emit()      
        else:
            return            
        
 
        
        
    # def suppliesUpdated(self):
        # """
        # Updates the supplies
        # """    
        # DS.analyserSolventCount= round(DS.analyserSolventRemaining/DS.sampleVolume)   #Updating device status values    
        # self.soln_bladder_value.setText(str(DS.analyserSolventCount))
      
        # self.log_q.put(["info","SW","Solvent bag available for "+str(DS.analyserSolventCount)+" samples"])
        # self.log_q.put(["info","SW","ANALYSER SOLVENT REMAINING  = "+str(round(DS.analyserSolventRemaining,1))])
        
        # DS.analyserWasteCount= round(DS.analyserWasteRemaining/DS.sampleVolume)   #Updating device status values 
        # self.waste_bladder_value.setText(str(DS.analyserWasteCount))
        # self.log_q.put(["info","SW","Waste bag available for "+str(DS.analyserWasteCount)+" samples"]) 
        # self.log_q.put(["info","SW","ANALYSER WASTE REMAINING  = "+str(round(DS.analyserWasteRemaining,1))])
 
        # self.log_q.put(["info","SW",'-------------Exiting sample pad rinse and check --------------'])
            
            
            
class serialNumber(QWidget):
    sig_serialNumber_entered = pyqtSignal()
    # sig_no_enough_supplies = pyqtSignal()
    sig_SamplerError = pyqtSignal()
    sig_SN_sampler_will_not_return = pyqtSignal()
    

    def __init__(self, log_q, charger_connected):
        super (serialNumber, self).__init__()
        serialNumber.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q
        self.charger_connected = charger_connected
        # QMessageBox.about(self, "Change Bags" ,"Change Solvent and residual bags then click OK to enter Serial Number.") 
        # QtWidgets.qApp.processEvents() 
        
        self.okButton = QtWidgets.QPushButton("OK", self)
        self.okButton.move(250,200)
        self.okButton.resize(self.okButton.minimumSizeHint())
        self.okButton.clicked.connect(self.close_window)
        self.okButton.setEnabled(False)

        self.cancelButton = QtWidgets.QPushButton("Cancel", self)
        self.cancelButton.move(150,200)
        self.cancelButton.resize(self.cancelButton.minimumSizeHint())
        self.cancelButton.clicked.connect(self.close_window)   

        self.infoLabel = QtWidgets.QLabel("Change Solvent and Residual bags\nthen press Continue\nto enter Serial Number\n and prepare new bags", self)
        self.infoLabel.setGeometry(10,10,450,100)
        self.infoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.infoLabel.setWordWrap(True)
        # self.infoLabel.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))          
        
        self.ser_No_solvent_label = QtWidgets.QLabel("New Bag Serial Number ", self)
        self.ser_No_solvent_label.move(50, 120)
        self.ser_No_solvent_label.setFont(QtGui.QFont("Arial", 14))    

        self.solvent_ser_No_btn = QtWidgets.QLabel("", self)
        self.solvent_ser_No_btn.setGeometry(270, 120,150,30)
        self.solvent_ser_No_btn.setAlignment(Qt.AlignTop)  
        self.solvent_ser_No_btn.setFont(QtGui.QFont("Arial", 14))
        
        self.continueButton = QtWidgets.QPushButton("Continue", self)    
        self.continueButton.move(250, 200)
        self.continueButton.setFont(QtGui.QFont("Arial", 14))     
        self.continueButton.clicked.connect(self.enter_Serial_number)

        # self.ser_No_Residual_label = QtWidgets.QLabel("Residual Bag", self)
        # self.ser_No_Residual_label.move(80, 130)
        # self.ser_No_Residual_label.setFont(QtGui.QFont("Arial", 14))       

        # self.residual_ser_No_btn = QtWidgets.QLabel("", self)
        # self.residual_ser_No_btn.setGeometry(220, 130,150,30)
        # self.residual_ser_No_btn.setAlignment(Qt.AlignTop)  
        # self.residual_ser_No_btn.setFont(QtGui.QFont("Arial", 14))

        self.statusDisplay = QtWidgets.QLabel(self)
        self.statusDisplay.move(50, 105)            
        self.statusDisplay.setGeometry(50, 160, 390, 50) 
        self.statusDisplay.setAlignment(Qt.AlignTop)        
        self.statusDisplay.setWordWrap(True)       
        
        self.start_process = True
  
    
        self.keyboard_1 = VirtualKeyboard(DS.analyserSolventID, False, log_q)
        self.keyboard_1.sigInputString.connect(self.solvent_number_entry)  
        
        
        self.show()
        
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","SW","charger_connected event cleared... "])
            self.log_q.put(["debug","SW","!!!!!!!! CLOSING SERIAL NUMBER WINDOW !!!!!!!"])
            self.timer_and_page_close()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","SW","Timer started"])      
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
               
        self.log_q.put(["debug","SW","!!!!!!!!!!! EXITING SERIAL NUMBER PAGE !!!!!!!!"])
        self.close()
        self.sig_SN_sampler_will_not_return.emit() 
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","SW","Timer stopped"]) 

    def VKB1(self):
        if DS.process_started:          
            if self.keyboard_1.isHidden():
                self.log_q.put(["debug","SN", 'Virtual Keyboard enabled to enter Solvent bag Serial Number'])
                self.keyboard_1.show()
            else:
                self.keyboard_1.hide()
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return 
 
    def enter_Serial_number(self):
        if DS.process_started:        
            self.VKB1()
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return 

    def solvent_number_entry(self, data):
        self.keyboard_1.hide()
        if DS.process_started:        
            if data != "":
                QtWidgets.qApp.processEvents()
                self.log_q.put(["info","SN", 'Solvent Bag Serial Number: '+data])
                self.cancelButton.setEnabled(False)
                self.continueButton.setEnabled(False)
                DS.analyserSolventID = data #solventID
                DS.analyserWasteID = data #wasteID = data
                self.log_q.put(["info","SN", 'DS.analyserSolventID: '+DS.analyserSolventID]) 
                self.log_q.put(["info","SN", 'DS.analyserWasteID: '+DS.analyserWasteID]) 
                self.solvent_ser_No_btn.setText(DS.analyserSolventID)  
                # self.residual_ser_No_btn.setText(DS.analyserWasteID)
                resetSolnValue = self.primeAndDrain()
                if resetSolnValue == 0:
                    self.statusDisplay.setText("Bag preparation complete")
                    self.continueButton.hide()
                    self.okButton.show()
                    self.okButton.setEnabled(True)
                    QtWidgets.qApp.processEvents()            
                    self.log_q.put(["info","SN", 'Pump priming and draining completed!!!!!!!!!!!!!']) 
                    self.log_q.put(["debug","SN","ANALYSER SOLVENT remaining = "+str(round(DS.analyserSolventRemaining,1)) ])        
                    self.log_q.put(["debug","SN","ANALYSER WASTE remaining = "+str(round(DS.analyserWasteRemaining,1)) ])
                    self.close_window()
                elif resetSolnValue == 1:

                    # self.timer_and_page_close()
                    self.log_q.put(["info","SN", 'Drain Error!!!!!!!!!!!!!']) 
                    self.log_q.put(["debug","SN","ANALYSER SOLVENT remaining = "+str(round(DS.analyserSolventRemaining,1)) ])        
                    self.log_q.put(["debug","SN","ANALYSER WASTE remaining = "+str(round(DS.analyserWasteRemaining,1)) ])
                    self.close_window()                    
                
                else: ### Sampler error occured
                    self.log_q.put(["info","SN", 'SAMPLER ENTERED INTO ERROR!!!!!!!!!!!!!']) 
                    self.timer_stop()                    
                    self.sig_SamplerError.emit()
                    self.timer_and_page_close()

            else:
                self.log_q.put(["info","SN", 'Entered data is empty: '+data])
                QtWidgets.QMessageBox.warning(self, "Entry is empty", "Please enter the Bag ID")
                QtWidgets.qApp.processEvents()
      
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return         
             
             
    def primeAndDrain(self):
        """
        Primes pump from new solvent bag then drains into new residual bag
        Return Values:
        0 - Success
        1 - Sampler will not return
        2 - Sampler Error
        """
        if DS.process_started:         
            self.log_q.put(["debug","SN","Solvent RESET button clicked" ])
            QtWidgets.qApp.processEvents()
            # self.VKB1()
            # self.keyboard_1.sigInputString.connect(self.solvent_number_entry)
            # Only proceed if Sampler present
            self.timeout = time.time() + 30
            pumpConnected = True
            while pumpConnected:
                
                if samplerPresent(self.timeout)==1:
                    QMessageBox.warning(self, 'Message',"Sampler not in place. Return it and try again")
                    QtWidgets.qApp.processEvents()
                    self.log_q.put(["debug","SW","Sampler is disconnected. Operator instructed to connect the sampler." ])
                    
                
                elif samplerPresent(self.timeout)==2:
                    confirm = QMessageBox.question(self, 'Message',
                                "Sampler not in place. Do you want to replace it and continue?", QMessageBox.Yes | 
                                QMessageBox.No, QMessageBox.No)
                    if confirm == QMessageBox.No:
                        self.log_q.put(["debug","SW","User confirmed that the sampler will not return!!!"])
                        QtWidgets.qApp.processEvents()
                        pumpConnected = False
                        return 1

                    else:
                        QtWidgets.qApp.processEvents()
                        self.log_q.put(["debug","SW","Keep waiting for another timeout"])
                        self.timeout = time.time() + 30                  
                else: #the sampler is in place

                    DS.resetSolventBagVolume = 0                
                    x=True
                    while x:
                        
                        self.log_q.put(["info","SN","DS.sampleVolume = "+str(DS.sampleVolume)])
                        DS.analyserSolventRemaining = DS.analyserSolventCapacity ####Clean solvent available for sampling
                        DS.analyserWasteRemaining = DS.analyserWasteCapacity ####Waste solvent stored after sampling
                        QtWidgets.qApp.processEvents()
                        self.statusDisplay.setText("Preparing solvent bag")
                        QtWidgets.qApp.processEvents()
                        samplerRotate_status = samplerComms.samplerRotate(self.log_q,"Fast","bagChange")
                        self.log_q.put(["debug","SN","Reset Soln value, Sampler Fast Rotate_status = "+ str(samplerRotate_status)])
                        if samplerRotate_status == 1: ###Sampler rotated well
                            x=False
                            ######### PUMP PRIMED AND RESETTING VALUES #############
                            self.log_q.put(["info","SN", 'Pump priming complete'])
                            self.statusDisplay.setText("Preparing residual bag")
                            QtWidgets.qApp.processEvents()                    
                            self.drainvalve = Valves(self.log_q,False, "waste", "bagChange") 
                            # self.drainvalve.operateValves()
                            # self.log_q.put(["info","SN", 'Draining Complete'])
                            # pumpConnected = False
                            # return 0                            
                            if not self.drainvalve.operateValves():
                                self.log_q.put(["debug","SW","ERROR WHILE DRAINING!!!!" ])
                                
                                return 1      
                            else:
                                self.log_q.put(["info","SN", 'Draining Complete'])
                                pumpConnected = False
                                return 0
                            ########################################################                  
                            
                        elif samplerRotate_status == 2: ###Sampler resulted error whule executing the rotate command
                            pass
                        elif samplerRotate_status == 3:  ##Sampler error unrecovered
                            x = False 
                            pumpConnected = False
                            return 2

                            # self.close_window()
                        else: ### Sampler disconnected
                            
                            QMessageBox.warning(self, 'Message',"Sampler not in place. Return it and try again")
                            QtWidgets.qApp.processEvents()
                            self.log_q.put(["debug","SN","Sampler is disconnected. Operator instructed to connect the sampler." ])
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            
            return 1             
   
    def close_window(self):
        self.timer_stop()               
        self.log_q.put(["debug","SW","!!!!!!!!!!! EXITING SERIAL NUMBER PAGE !!!!!!!!"])   
        self.close()###This explicit close is required.
        self.sig_serialNumber_entered.emit()

      
class newSamplerPad(QWidget):
    sig_padReplaced = pyqtSignal()
    # sig_no_enough_supplies = pyqtSignal()
    sig_SamplerError = pyqtSignal()
    sig_SN_sampler_will_not_return = pyqtSignal()
    sig_NS_spectrometerError = pyqtSignal()
    

    def __init__(self, log_q, charger_connected):
        super (newSamplerPad, self).__init__()
        newSamplerPad.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q
        self.charger_connected = charger_connected
        # QMessageBox.about(self, "Change Bags" ,"Change Solvent and residual bags then click OK to enter Serial Number.") 
        # QtWidgets.qApp.processEvents() 
        self.rarRetry = 0
        
        self.okButton = QtWidgets.QPushButton("OK", self)
        self.okButton.move(250,200)
        self.okButton.resize(self.okButton.minimumSizeHint())
        self.okButton.clicked.connect(self.close_window)
        self.okButton.setEnabled(False)

        self.cancelButton = QtWidgets.QPushButton("Cancel", self)
        self.cancelButton.move(150,200)
        self.cancelButton.resize(self.cancelButton.minimumSizeHint())
        self.cancelButton.clicked.connect(self.close_window)   

        self.infoLabel = QtWidgets.QLabel("Fit new Sampler pad, attach Sampler to Analyser then press Continue", self)
        self.infoLabel.setGeometry(10,10,450,100)
        self.infoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.infoLabel.setWordWrap(True)
        # self.infoLabel.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))          
        
        
        self.continueButton = QtWidgets.QPushButton("Continue", self)    
        self.continueButton.move(250, 200)
        self.continueButton.setFont(QtGui.QFont("Arial", 14))     
        self.continueButton.clicked.connect(self.doNewSamplerPad)

        self.statusDisplay = QtWidgets.QLabel(self)
        self.statusDisplay.move(50, 105)            
        self.statusDisplay.setGeometry(50, 160, 390, 50) 
        self.statusDisplay.setAlignment(Qt.AlignTop)        
        self.statusDisplay.setWordWrap(True)       
        
        self.start_process = True
  
    
        self.show()
        
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            
            self.charger_connected.clear()
            self.log_q.put(["debug","SW","charger_connected event cleared... "])
            self.log_q.put(["debug","SW","! CLOSING NEW PAD WINDOW !"])
            self.timer_and_page_close()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","SW","Timer started"])      
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
               
        self.log_q.put(["debug","SW","!! EXITING NEW PAD PAGE !"])
        self.close()
        self.sig_SN_sampler_will_not_return.emit() 
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","SW","Timer stopped"]) 
        
    def close_window(self):
        self.timer_stop()               
        self.log_q.put(["debug","SW","!!!!!!!!!!! EXITING NEW PAD PAGE !!!!!!!!"])   
        self.close()###This explicit close is required.
        # DS.process_started = False
        self.started = False
        self.sig_padReplaced.emit()

    def doNewSamplerPad(self):
        self.continueButton.setEnabled(False)
        if DS.process_started:         
            self.log_q.put(["debug","SN","New Pad button clicked" ])
            QtWidgets.qApp.processEvents()
            # Only proceed if Sampler present
            self.timeout = time.time() + 30
            # samplerGone = True
            # while samplerGone:
                # samplerState = samplerPresent(self.timeout)
            if Sampler.S_cmd_Get_status()['status'] == 'Disconnected':
                if not self.isSamplerPresent():
                    self.close_window()
                    return# don't proceed no sampler, user says quit

            #the sampler is in place
            DS.analyserPadAge = 0
            self.samplerPad = DS.analyserPadAge        
            # self.sampler_pad_counts.setText(str(self.samplerPad))   
            self.log_q.put(["info","SW","Sampler pad Replaced"])
            self.log_q.put(["info","SW","samplerPad = "+str(self.samplerPad)])
            LED_Driver.LED_heaterON(self.log_q)
            # first check spray pattern on new dry pad
            PC.PC_wet() # do a short spray
            confirm = QMessageBox.question(self, 'Message',
                        "Remove Sampler, check spray pattern then replace.\nIs spray pattern OK?", QMessageBox.Yes | 
                        QMessageBox.No, QMessageBox.No)
            if confirm == QMessageBox.No:
                # here if the spray pattern is not good
                # QMessageBox.about(self,'Message', "Exit and clean spray nozzle")
                self.infoLabel.setText('Spray pattern problem\nPress OK then clean nozzle')
                self.continueButton.setVisible(False)
                self.okButton.setVisible(True)
                self.okButton.setEnabled(True)
                return
            self.infoLabel.setText('Spray pattern check OK\nContinuing with pad rinse and check')
            self.log_q.put(["debug","SW","Spray pattern check OK. Continuing with pad rinse and check" ])
            if not self.rinsePad():
                self.log_q.put(["debug","SW","In self.rinsePad, False received"])
                self.close_window()
                return # sad end to rinse pad operation don't proceed
            self.drainvalve = Valves(self.log_q, False, "waste", "rinse")
            if self.drainvalve.operateValves():
                self.checkRefAfterRinse()
            else:
                self.log_q.put(["debug","SW","ERROR WHILE DRAINING!!!!. So going back to previous page" ])
                self.close_window()
                
                return
            self.log_q.put(["info","SW","Sampler Pad age = "+str(DS.analyserPadAge)])
            QtWidgets.qApp.processEvents()
            self.close_window()
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return 1

    def rinsePad(self):
        """
        Rinse the pad
        """    
        self.started = True
        if DS.process_started:       
            # Only proceed if Sampler present
            do_rinse = True
            while do_rinse:
                self.log_q.put(["debug","SW","In rinsePAd,Sampler.S_cmd_Get_status()['status'] =%s"%str(Sampler.S_cmd_Get_status()['status'] )])
                if Sampler.S_cmd_Get_status()['status'] == 'Disconnected':
                    sample_check = self.isSamplerPresent()
                    self.log_q.put(["debug","SW","In rinsePAd,sample_check =%s"%str(sample_check)])
                    if not sample_check:
                        self.log_q.put(["debug","SW","Returning False"])
                        return False #user says no sampler, exit with sadness
                    # self.isSamplerPresent()
                    
                
                else: #the sampler is in place        
                    QtWidgets.qApp.processEvents()        
                    if self.started:
                        do_rinse = False
                        self.log_q.put(["info","SW",'-------------Entering new sample pad rinse and check --------------'])
                        self.log_q.put(["info","SW",'-------------New sampler pad rinse cycle started---------------'])
                        rinse_cycle_no = 1
                        DS.sampleRinseSquirtVolume = 0
                        while 1:
                            if rinse_cycle_no <=DS.rinseCountReqd:
                                self.log_q.put(["info","SW",'rinseCountReqd = %s'%str(DS.rinseCountReqd)])
                                self.log_q.put(["info","SW",'rinse_cycle_no = %s'%str(rinse_cycle_no)])
                            
                                self.infoLabel.setText('Rinsing new sampler pad.')
                                QtWidgets.qApp.processEvents()  
                                
                                x=True
                                while (x):     
                                    QtWidgets.qApp.processEvents()
                                    
                                    self.fastRotateResponse = samplerComms.samplerRotate(self.log_q,"Fast","rinse")
                                    self.log_q.put(["debug","SW","Rinse cycle fast rotate response = "+ str(self.fastRotateResponse)])
                                    if self.fastRotateResponse == 0:##Sampler disconnected
                                        if not self.isSamplerPresent():
                                            x=False
                                            # self.samplerError=True
                                            # self.close_window()
                                            # rinse_cycle_no += 10 ###large enough number to break
                                            self.log_q.put(["info","SW",'Quitting after losing Sampler'])
                                            return False # tell our parent not to continue
                                            
                                    elif self.fastRotateResponse == 2:### Rotate state is error
                                        pass
                                    elif self.fastRotateResponse == 3:  ##Sampler error unrecovered 
                                        
                                        x=False
                                        self.samplerError=True
                                        self.close_window()
                                        rinse_cycle_no += 10 ###large enough number to break
                                        self.log_q.put(["info","SW",'rinse_cycle_no = %s'%str(rinse_cycle_no)])
                                        break
                                    else: ####Response == 1, ##Sampler successfully executed command
                                       
                                        x=False
                                        rinse_cycle_no +=1 
                                        DS.sampler_faultRetry = 0

                            else:
                                break
                            self.log_q.put(["info","SW",'------------- New sampler pad rinse complete ---------------'])
                            self.infoLabel.setText('Draining after rinse')
                            # self.show()
                            return True
                    else:
                        self.timer_and_page_close()  
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return False        
    def checkRefAfterRinse(self):
        """
        Checks whether the sampler pad is clean
        """ 
        if DS.process_started:      
            # Only proceed if Sampler present
            while True:
                self.timeout = time.time() + 30
                if Sampler.S_cmd_Get_status()['status'] == 'Disconnected':
                    if not self.isSamplerPresent():
                        return # no sampler and user says it isn't coming back
                    
                
                else: #the sampler is in place     
                    QtWidgets.qApp.processEvents()        
                    if self.started: 
                        DS.sampleRinseSquirtVolume = 0
                        x=True
                        while (x):            
                            self.infoLabel.setText('Checking new sampler pad.')
                            QtWidgets.qApp.processEvents() 
      

                            samplerRotateFast_status = samplerComms.samplerRotate(self.log_q,"Fast","calibrate") 
                            self.log_q.put(["debug","SW","Checking reference after rinse. Fast rotate status = "+ str(samplerRotateFast_status)])  
                            if samplerRotateFast_status == 0: #### Sampler is disconnected
                                if not self.isSamplerPresent():
                                    return  # sampler gone user says it isn't coming back
                            elif samplerRotateFast_status == 2: ### Sampler is connected but the previous command resulted in error
                                pass
                            elif samplerRotateFast_status == 3: ### Sampler error unrecovered

                                x=False
                                self.samplerError=True
                                self.close_window()
                            else:##Sampler rotated without any error or disconnection
                        ############ if the system is idle for more than 5 mins, the LED heater turns OFF#######
                        ######## This segment will turn ON the heater if the Led heater turns off ########
                                temp = LED_Driver.getTemp('led',self.log_q)
                                if temp < DS.targetTemp - 1:
                                    LED_Driver.LED_heaterON(self.log_q)
                        ########################################################################################
                                self.timeout = time.time() + 30 
                                x=False                                
                                checkLoop=True
                                while checkLoop:
                                    LED_state = LED_Driver.LED_ON(self.log_q,False)###Checking LED is false
                                    self.log_q.put(["debug","MT","LED state (1-success, 2-Board error, 3-Sampler disconnected)"])
                                    self.log_q.put(["debug","MT","LED state = "+ str(LED_state)])
                                    if LED_state == 2:###LED heater error
                                        checkLoop = False
                                        DS.logout_cause_value = 2
                                        QMessageBox.warning(self,"LED Error","LED Heater Error \n Contact Support")
                                        QtWidgets.qApp.processEvents()
                                        self.sig_NS_spectrometerError.emit() #exit is the only choice
                                    elif LED_state == 3: ###Sampler disconnected error
                                        if not self.isSamplerPresent():
                                            return False # user says Sampler not coming back, exit with sadness
                                        QtWidgets.qApp.processEvents()
                                    else:### All requirements satisfied.
                                        checkLoop = False
                                    self.infoLabel.setText('Checking new sampler pad.')
                                    QtWidgets.qApp.processEvents()
                                    self.log_q.put(["info","SW","Capturing Reference spectrum after Rinse"]) 
                                    # self.rinseDisplay.setText('Analysing sample after rinse...')
                                    # QtWidgets.qApp.processEvents()
                                    self.referenceafterRinse = Capture(self.log_q)
                                    self.referenceafterRinseCapture = self.referenceafterRinse.referenceAfterRinse()
                                    self.infoLabel.setText('Analysing results from new pad')

                                    LED_Driver.LED_OFF(self.log_q)  
                                
                                    
                                    if self.referenceafterRinseCapture:
           
                                        self.refComparison = Compare(self.log_q, False, False)###False=Calibrate check, False - LED check from Analyser GUI
                                        (self.rinseComplete,  self.Variation, self.minVariation, self.maxVariation) = self.refComparison.variationCalculation()
                                        self.log_q.put(["debug", "SW", 'Maximum variation between captured Reference spectrum and Factory Reference spectrum is ' + str(self.maxVariation)])
                                        self.log_q.put(["debug", "SW", 'Minimum variation between captured Reference spectrum and Factory Reference spectrum is ' + str(self.minVariation)])
                                        self.log_q.put(["debug", "SW", 'Variation values are ' + str(self.Variation)])
                                        
                                        self.drained =False
                                        
                                        if self.rinseComplete:
                                            self.finalSteps()

                                            # self.log_q.put(["debug","SW","Final steps complete"]) 
                                        
                                        else:
                                            enoughSolution = QMessageBox.question(self, "Check solution" ,"Enough Solution in the bowl?")
                                            QtWidgets.qApp.processEvents() 
                                            self.log_q.put(["info", "SW", 'Checking whether there is enough solution in the bowl']) 
                                            if enoughSolution == QtWidgets.QMessageBox.Yes:
                                                self.log_q.put(["debug", "SW", 'User confirmed there is enough solution inside the bowl. So the Sampler pad is dirty']) 
                                                if DS.analyserPadAge!=0:
                                                    QMessageBox.about(self, "Dirty Sampler Pad" ,"Change Sampler Pad")                       
                                                    DS.analyserPadsTotal+=1    #Updating device status values
                                                    DS.analyserPadAge=0    #Updating device status values   
                                                    self.infoLabel.setText('Sampler pad changed')
                                                    QtWidgets.qApp.processEvents()  
                                                    
                                                    self.infoLabel.setText('Draining solvent')
                                                    QtWidgets.qApp.processEvents()                    
                                                    self.drainvalve = Valves(self.log_q, False, "waste", "rinse")
                                                    if not self.drainvalve.operateValves():
                                                        self.log_q.put(["debug","SW","ERROR WHILE DRAINING!!!!" ])
                                                        self.close_window()
                                                        return
                                                    else:
                                                        self.infoLabel.setText('Drained')
                                                        QtWidgets.qApp.processEvents()
                                                    
                                                        self.infoLabel.setText('Checking new sampler pad')
                                                        QtWidgets.qApp.processEvents()   
                                                        # time.sleep(1)
                                                        self.log_q.put(["info", "SW", 'Checking the new sampler pad is clean']) 
                                                        self.checkRef()
                                                else:
                                                    self.log_q.put(["debug", "SW", 'It is a new sampler pad. So Remeasuring reference after rinse spectrum']) 
                                                    self.infoLabel.setText('Draining solvent')
                                                    QtWidgets.qApp.processEvents()                    
                                                    self.drainvalve = Valves(self.log_q, False, "waste", "rinse")
                                                    if not self.drainvalve.operateValves():
                                                        self.log_q.put(["debug","SW","ERROR WHILE DRAINING!!!!" ])
                                                        self.close_window()
                                                        return
                                                    else:
                                                        self.infoLabel.setText('Drained')
                                                        QtWidgets.qApp.processEvents()
                                                        if self.rarRetry<3:
                                                            self.log_q.put(["debug", "SW", 'Remeasuring reference after rinse spectrum']) 
                                                            self.rarRetry+=1
                                                            self.checkRef()
                                                        else:
                                                            QMessageBox.warning(self, "LED error" ,"Maximum retries exceeded! \n Redo the calibration")
                                                            self.log_q.put(["debug", "SW", 'Retries exceeded. User instructed to redo the calibration']) 
                                                            self.finalSteps()

                                                    
                                            else:
                                                self.log_q.put(["debug", "SW", 'User confirmed there is no enough solution inside the bowl. So the rewetting the pad']) 
                                                
                                                self.checkRef()
                                            
                                    else:
                                        self.sig_NS_spectrometerError.emit()                

                    else:
                        return 
                    break
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return                  

    def finalSteps(self):
        if DS.process_started:    
            LED_Driver.LED_OFF(self.log_q)
            LED_Driver.LED_heaterOFF(self.log_q)
            self.infoLabel.setText('Draining solvent')
            QtWidgets.qApp.processEvents() 

            self.drainvalve = Valves(self.log_q, False, "waste", "calibrate") 
            if not self.drainvalve.operateValves():
                self.log_q.put(["debug","SW","ERROR WHILE DRAINING!!!!" ])
                self.close_window()
                # self.close()                
                return
            else:
            
                self.infoLabel.setText('Solvent drained')
                QtWidgets.qApp.processEvents()  
                self.infoLabel.setText('')
                QtWidgets.qApp.processEvents()
                self.close()                
                return
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            self.close()                
            return

    def isSamplerPresent(self):
        self.log_q.put(["debug","SW","Sampler disconnected. Ask operator what to do." ])
        waiting = True
        while waiting:
            confirm = QMessageBox.question(self, 'Message',
                        "Sampler not in place. Replace it then press OK, or press Cancel to quit", QMessageBox.Ok | 
                        QMessageBox.Cancel)
            QtWidgets.qApp.processEvents()
            if confirm == QMessageBox.Cancel:
                self.log_q.put(["debug","SW","Exit, sampler not present, user quits"])
                QtWidgets.qApp.processEvents()
                return False
            else:
                self.log_q.put(["debug","SW","User says keep waiting"])
                QtWidgets.qApp.processEvents()
                time.sleep(3) # wait a while to allow Sampler to connect
                self.timeout = time.time() + 30  
                self.log_q.put(["debug","SW","Timeout updated"])
                self.log_q.put(["debug","SW","Sampler.S_cmd_Get_status()['status'] =%s"%str(Sampler.S_cmd_Get_status()['status'])])
                if not Sampler.S_cmd_Get_status()['status'] == 'Disconnected':
                    self.log_q.put(["debug","SW","Sampler is connected back"])
                    return True # Sampler is back let's go
        return True
    def checkRef(self):
        if DS.process_started:     
            self.checkRefAfterRinse()
        else:
            self.log_q.put(["debug","SW","Charger is connected." ])
            return       

            