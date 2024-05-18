import sys 
import time
import os
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import deviceStatus as DS
import Sampler


class devDetails(QWidget):
    """This module displays the following information to the operator
        Analyser details:
        Analyser ID:
        Software Version:
        Battery %: 
        Battery Voltage:        
        
        Sampler Details:
        Sampler ID:
        Software Version:
        Battery %: 
        Battery Voltage:
        Sampler Status:
        Last operation details namely:
        Total Wipe Count:
        Total Spin Count:
        """
        
    sig_devDetails = pyqtSignal()
    
    
    def __init__(self, log_q, charger_connected):
        super (devDetails, self).__init__()
        devDetails.setGeometry(self, 0, 22, 480, 250)
        self.log_q = log_q   

        self.charger_connected = charger_connected  
        status = Sampler.S_cmd_Get_status()

        self.ok = QtWidgets.QPushButton("OK", self)
        self.ok.move(200,220)
        self.ok.resize(self.ok.minimumSizeHint())
        self.ok.clicked.connect(self.close_window)        
        
        self.analyserDetails = QtWidgets.QLabel("ANALYSER", self)
        self.analyserDetails.move(160, 0)
        self.analyserDetails.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))        
        
        self.a_ID = QtWidgets.QLabel("ID: " + DS.deviceName, self)
        self.a_ID.move(10, 30)
        self.a_ID.setFont(QtGui.QFont("Arial", 14))  

        self.a_SW = QtWidgets.QLabel("S/W Version: "+ str(DS.firmware_ver), self)
        self.a_SW.move(10, 60)
        self.a_SW.setFont(QtGui.QFont("Arial", 14))  

        self.a_B_P = QtWidgets.QLabel("Battery: " + str(DS.analyserBattery) + '% : '+ str(float(round(DS.analyserVoltage,2)))+' V', self)
        self.a_B_P.move(250, 30)
        self.a_B_P.setFont(QtGui.QFont("Arial", 14))  
       
        self.a_SN = QtWidgets.QLabel("Spectro #: "+ str(DS.spectroSerialNumber), self)
        self.a_SN.move(250, 60)
        self.a_SN.setFont(QtGui.QFont("Arial", 14))          

        self.samplerDetails = QtWidgets.QLabel("SAMPLER", self)
        self.samplerDetails.move(160, 80)
        self.samplerDetails.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))        
        
        self.s_ID = QtWidgets.QLabel("ID: " + str(DS.samplerID), self)
        self.s_ID.move(10, 110)
        self.s_ID.setFont(QtGui.QFont("Arial", 14))  

        self.s_SW = QtWidgets.QLabel("S/W Version: ", self)
        self.s_SW.move(10, 140)
        self.s_SW.setFont(QtGui.QFont("Arial", 14))  
        
        self.s_TWC = QtWidgets.QLabel("Total Wipe Count: ", self)
        self.s_TWC.move(10, 170)
        self.s_TWC.setFont(QtGui.QFont("Arial", 14))  

        
        self.s_B_P = QtWidgets.QLabel("Battery: ", self)
        self.s_B_P.move(250, 140)
        self.s_B_P.setFont(QtGui.QFont("Arial", 14))  
      
        self.s_SC = QtWidgets.QLabel("Total Spin Count: ", self)
        self.s_SC.move(250, 170)
        self.s_SC.setFont(QtGui.QFont("Arial", 14))  
      
        if status['status'] != "Disconnected":
            self.s_SC.setText("Total Spin Count: " + str(status["spin_count"]))
            self.s_B_P.setText("Battery: " + str(status["battery_p"])+'% : '+str(float(status["battery_v"]))+' V')
            self.s_TWC.setText("Total Wipe Count: " + str(status["wipe_count"]))
            self.s_SW.setText("S/W Version: " + str(float(status["ver"])))
            

        self.s_SS = QtWidgets.QLabel("Status:             ", self)
        self.s_SS.setGeometry(10, 200, 250, 20)
        self.s_SS.setFont(QtGui.QFont("Arial", 14))  
      
        self.charger_is_connected = False
        self.updateConnectionStatus()
        
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)        
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():

            DS.engineer = True
            
            self.charger_is_connected = True
            self.charger_connected.clear()
            self.log_q.put(["debug","DD","charger_connected event cleared... "])
            self.log_q.put(["info","DD","!!!!!!!! CLOSING DEVICE DETAILS WINDOW !!!!!!!"])
            self.timer_and_page_close()
        self.Timer.start(1000)     

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","DD","Timer started"])   

    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page
        """
        
        self.timer_stop()
        self.log_q.put(["debug","DD","!!!!!!!!!!! EXITING DEVICE DETAILS PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","DD","Timer stopped"])    

    def charger_connected_LOGOUT(self):
        if self.charger_is_connected:
            return True
        else:
            return False

    def updateConnectionStatus(self):
        status = Sampler.S_cmd_Get_status()
        if (status['status'] == 'Ready'):
            self.s_SS.setText("Status: Connected")
        else:
            self.s_SS.setText("Status: Disconnected")
        QTimer.singleShot(1000, self.updateConnectionStatus)
        
#Exit the page                
    def close_window(self):
        self.close()
        self.log_q.put(["info","DD","@@@@@@@@@@@ Closing Device Details Window @@@@@@@@@@@"])        
        self.sig_devDetails.emit()        