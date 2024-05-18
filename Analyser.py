# Login page for the PSS - GUI
import cmd 
import csv
import datetime
import getpass
import json
import logging
import os
from warnings import _OptionError
import requests
import shutil
import subprocess
import sys
import threading 
import time 


from multiprocessing import Value
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap

#Python files downloaded
#------------
import Analyser_Cloud
import pss_log
import Sampler


import Analyser_AzureIoT as IoT   #for all global variables
import deviceStatus as DS
import multiprocessing as mp
import numpy as np
import pandas as pd
import Pump_controller_driver as PC
import LED_Driver


from VirtualKeyboard import VirtualKeyboard
from Job_selection import Job_selection
from Maintenance_Window import Maintenance_Window
from samplertestmode import SamplerTestGUI
from Spectrometer_capture import Capture
from Status_Window import Status_Window

#------------

# class charger_connectivity(QWidget):
    # def __init__(self, log_q):
        # super(charger_connectivity, self).__init__()
        # # self.log_q.put(["debug","AN","Entered Charger connection module check"])
        # self.log_q = log_q
        # self.connectivity()
        
    # def connectivity(self):
        # if DS.analyserCharging == 1:
            # if DS.engineer:
                # pass
            # else:
                # confirm = QMessageBox.question(self, 'Charger Connected',
                    # "Charger connection detected. Do you want to logout? ", QMessageBox.Yes | 
                    # QMessageBox.No, QMessageBox.No)
                # QtWidgets.qApp.processEvents()    
                # if confirm == QMessageBox.Yes:
                    # self.log_q.put(["debug","AN","User decided to log out"])
                    # DS.process_started = False
                    # DS.engineer = True
                # else:
                    # pass  
        # QTimer.singleShot(2000, self.connectivity)                        
    
class statusGui(QWidget):

    def __init__(self, log_q, mp_status, charger_connected):
        """
        This module displays the Logo, Sampler and Analyser battery levels
        """
        super(statusGui, self).__init__()
        self.log_q = log_q
        self.mp_status = mp_status
        self.charger_connected = charger_connected
        self.home()
    def home(self):
        # Initialise status bar display
        self.setGeometry(0, 0, 480, 22)
        self.setFont(QtGui.QFont('Ariel', 12))
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        pixmap = QPixmap('Atamo_Analytics_Logo_small.jpg')
        logolabel = QLabel(self)
        logolabel.setPixmap(pixmap)
        logolabel.resize(pixmap.width(),pixmap.height())
        logolabel.move(0, 0)
        self.connLabel = QLabel(self)
        self.connLabel.setText('Internet')
        self.connLabel.move(110,0)
        self.connValueGood = QLabel(self)
        self.connValueGood.setPixmap(QPixmap('greendot.jpg'))
        self.connValueBad = QLabel(self)
        self.connValueBad.setPixmap(QPixmap('reddot.jpg'))
        self.connValueGood.setGeometry(175,0,20,20)
        self.connValueBad.setGeometry(175,0,20,20)
        # self.moRSSIValue = QtWidgets.QLabel(str(DS.modemRSSI), self)
        # self.moRSSIValue.setGeometry(195,0,80,20)
        self.RSSIValue0 = QLabel(self)
        self.RSSIValue0.setPixmap(QPixmap('RSSI0.jpg'))
        self.RSSIValue1 = QLabel(self)
        self.RSSIValue1.setPixmap(QPixmap('RSSI1.jpg'))
        self.RSSIValue2 = QLabel(self)
        self.RSSIValue2.setPixmap(QPixmap('RSSI2.jpg'))
        self.RSSIValue3 = QLabel(self)
        self.RSSIValue3.setPixmap(QPixmap('RSSI3.jpg'))
        self.RSSIValue4 = QLabel(self)
        self.RSSIValue4.setPixmap(QPixmap('RSSI4.jpg'))
        self.RSSIValue0.setGeometry(195,0,20,20)
        self.RSSIValue1.setGeometry(195,0,20,20)
        self.RSSIValue2.setGeometry(195,0,20,20)
        self.RSSIValue3.setGeometry(195,0,20,20)
        self.RSSIValue4.setGeometry(195,0,20,20)
        self.tempValueCold = QLabel(self)
        self.tempValueCold.setPixmap(QPixmap('bluetemp.jpg'))
        self.tempValueGood = QLabel(self)
        self.tempValueGood.setPixmap(QPixmap('greentemp.jpg'))
        self.tempValueHot = QLabel(self)
        self.tempValueHot.setPixmap(QPixmap('redtemp.jpg'))
        self.tempValueCold.setGeometry(215,0,20,20)
        self.tempValueGood.setGeometry(215,0,20,20)
        self.tempValueHot.setGeometry(215,0,20,20)
        self.anBattLabel = QLabel(self)
        self.anBattLabel.setText('Analyser')
        self.anBattLabel.move(235,0)
        self.anBattValue = QtWidgets.QLabel(str(DS.analyserBattery), self)
        self.anBattValue.setGeometry(305,0,80,20)
        self.anChargeValue = QLabel(self)
        self.anChargeValue.setGeometry(350,0,20,20)
        self.anChargeValue.setPixmap(QPixmap('battery-charging.jpg'))
        self.saBattLabel = QLabel(self)
        self.saBattLabel.setText('Sampler')
        self.saBattLabel.move(365,0)
        self.saBattValue = QtWidgets.QLabel("99%", self)
        self.saBattValue.setGeometry(435,0,80,20)
        self.samplerID = ''
        self.counter = 0
        
        self.updateStatusBar()
        
    def updateStatusBar(self):
        """
        This function updates Sampler and Analyser battery levels
        """    
        # Check and display Internet, Analyser and Sampler status

        status = Sampler.S_cmd_Get_status()
        # self.log_q.put(["debug","AN", "Status: " + str(status)])
        if (status['status'] == 'Ready'):
            if status['fault_code_n'] > 0:
                faultList = status['fault_code']
                self.log_q.put(["debug","AN", "Status is: " + str(status)])
                self.log_q.put(["debug","AN", "Fault list length: " + str(status['fault_code_n'])])
                self.log_q.put(["debug","AN", "Fault list: " + str(faultList)])
                # clear Fault List
                Sampler.S_cmd_Clear_faultlist()
                for i in range (0,status['fault_code_n']):
                    #get next Fault code
                    faultCode = chr(faultList[2*i]) + chr(faultList[(2*i)+1])
                    self.log_q.put(["error","AN","Got Sampler Fault Code " + faultCode])
            try:
                DS.samplerBattery = status["battery_p"]
                DS.samplerID = status["sampler_id"].decode("utf-8")
                self.mp_status.samplerID = DS.samplerID
                self.mp_status.sampler_ver = status["ver"].decode("utf-8")
                # self.log_q.put(["debug","AN","Sampler ver: "+self.mp_status.sampler_ver])
            except Exception as e:
                self.log_q.put(["error","AN", "Sampler status exception: " + str(e)])
                self.log_q.put(["error","AN", "Sampler status: " + str(status)])
            if not self.samplerID == DS.samplerID:
                self.samplerID = DS.samplerID
                if self.counter==0:
                    self.counter+=1
                else:
                    QMessageBox.information(self, "New sampler" ,"New sampler detected")
                    self.supplyAvailability = Status_Window(self.log_q, self.charger_connected)
                    self.supplyAvailability.show()
                    self.supplyAvailability.resetSamplerpadValue()
                    self.supplyAvailability.hide()
                    
        else:
            DS.samplerBattery = 0
            self.mp_status.sampler_ver = ""
        if mp_status.connectionStatus == 1:
            self.connValueGood.show()
            self.connValueBad.hide()
        else:
            self.connValueGood.hide()
            self.connValueBad.show()
        self.anBattValue.setText(str(DS.analyserBattery) + '%')
        if (DS.analyserBattery < DS.analyserBatteryThreshold):
            self.anBattValue.setStyleSheet('QLabel{color: red}')
            self.anBattValue.setFont(QtGui.QFont('Ariel', 12))
        else:
            self.anBattValue.setStyleSheet('QLabel{color: black}')
            self.anBattValue.setFont(QtGui.QFont('Ariel', 12))

        if (DS.samplerBattery == 0):
            self.saBattValue.setText('')
        else:
            self.saBattValue.setText(str(DS.samplerBattery) + '%')
        if (DS.samplerBattery < DS.samplerBatteryThreshold):
            self.saBattValue.setStyleSheet('QLabel{color: red}')
            self.saBattValue.setFont(QtGui.QFont('Ariel', 12))
            
        else:
            self.saBattValue.setStyleSheet('QLabel{color: black}')
            self.saBattValue.setFont(QtGui.QFont('Ariel', 12))
        if DS.analyserCharging == 1:
            self.anChargeValue.show()
            if DS.engineer:
                pass
            else:
                confirm = QMessageBox.question(self, 'Charger Connected',
                    "Charger connection detected. Do you want to logout? ", QMessageBox.Yes | 
                    QMessageBox.No, QMessageBox.No)
                QtWidgets.qApp.processEvents()    
                if confirm == QMessageBox.Yes:
                    self.log_q.put(["debug","AN","User decided to log out"])
                    DS.process_started = False
                    DS.logout_cause_value = 5
                    self.charger_connected.set() 
                else:
                    while True:
                        # time.sleep(1)
                    
                        if DS.analyserCharging == 1:
                            QMessageBox.warning(self, "charger conected" ,"Disconnect the charger")
                            QtWidgets.qApp.processEvents()  
                            # time.sleep(1)
                        else:
                            
                            DS.process_started = True
                            break
        else:
            DS.process_started = True
            self.anChargeValue.hide()
        # Display modem RSSI
        self.RSSIValue0.hide()
        self.RSSIValue1.hide()
        self.RSSIValue2.hide()
        self.RSSIValue3.hide()
        self.RSSIValue4.hide()
        rssi = DS.modemRSSI
        if rssi < 10:
            self.RSSIValue0.show()
        elif rssi < 15:
            self.RSSIValue1.show()
        elif rssi < 20:
            self.RSSIValue2.show()
        elif rssi < 25:
            self.RSSIValue3.show()
        else:
            self.RSSIValue4.show()
        # self.moRSSIValue.setText(str(DS.modemRSSI))
        temp = LED_Driver.getTemp('led',self.log_q)
        # Display LED board temperature icon
        self.tempValueCold.hide()
        self.tempValueGood.hide()
        self.tempValueHot.hide()
        if temp < DS.targetTemp - 1:
            self.tempValueCold.show()
        elif temp > DS.targetTemp - 1 and temp < DS.targetTemp + 1:
            self.tempValueGood.show()
        else:
            self.tempValueHot.show()

        QTimer.singleShot(2000, self.updateStatusBar)
        
class Shutdown(QWidget):
    def __init__(self):
        super (Shutdown, self).__init__()
        Shutdown.setGeometry(self, 0, 22, 480, 250)
        msgLabel = QtWidgets.QLabel("Shutting down, Please Wait")
        msgLabel.setGeometry(self,120, 50, 200, 40)
        
class Login(QtWidgets.QMainWindow):
    
    
    
    def __init__(self, deviceId, telemetry_q, log_queue, user, password, prepare_for_sleep, mp_status, charger_connected):

        
        super (Login, self).__init__()
        self.log_q = log_queue
        self.telemetry_q = telemetry_q
        self.deviceId = deviceId
        self.callingUser = user
        self.prepare_for_sleep = prepare_for_sleep
        self.mp_status = mp_status
        self.data = ''
        self.charger_connected = charger_connected

        self.keyboard1 = VirtualKeyboard(self.data, False, self.log_q) # Separate class to enable Virtual Keyboard
        self.keyboard2 = VirtualKeyboard(self.data,False, self.log_q) #Separate class to enable Keyboard in password entry mode
       
        self.keyboard1.sigInputString.connect(self.Login_ID)
        self.keyboard2.sigInputString.connect(self.Password)

        Login.setGeometry(self, 0, 22, 480, 250)
        self.setWindowTitle("Aircraft details")
        self.setWindowIcon(QtGui.QIcon('Atamo.jpeg'))

        self.spectro_ = Capture(self.log_q)
        self.opticalBenchData = self.spectro_.opticalBenchParams()
        if self.opticalBenchData:
            pass
        else:
            self.errorPage()


        self.spectroFound = self.spectro_.row_Start_End()
        with open(DS.localRefFilesDirectory +'dark_raw.csv','r') as f:
            reader=csv.reader(f)
            next(reader,None)
            wavelength=list(reader)
            
        while 1:
            # print(len(wavelength))
            self.log_q.put(["error", "AN", "len(wavelength) = %d"%len(wavelength)])
            for i in range(1,len(wavelength)):
                wavelength_value = float(wavelength[i][0])
                

                if (wavelength_value)>250.0 and (wavelength_value)<250.5:
                    start_row = i
                    
                    # print("start_column",start_row, wavelength_value, wavelength[i][1])
                    self.log_q.put(["error", "AN", "Start Row = %d, Wavelength_value = %f, wavelength[i][1] = %f"%(start_row, float(wavelength_value), float(wavelength[i][1]))])
                    DS.RowStart = start_row
                    self.log_q.put(["debug", "AN", "Row start number = %d"%DS.RowStart])

                if (wavelength_value)>299.5:
                    end_row = i+1
                    # print("end_column",end_row, wavelength_value, wavelength[i][1])
                    
                    if (end_row-start_row)<110:
                        end_row+=1
                    self.log_q.put(["error", "AN", "end_row = %d, Wavelength_value = %f, wavelength[i][1] = %f"%(end_row, float(wavelength_value), float(wavelength[i][1]))])
                    DS.RowEnd = end_row 
                    self.log_q.put(["debug", "AN", "Row end number = %d"%DS.RowEnd])
                    break
            # print("length = ",(end_row-start_row))
            self.log_q.put(["error", "AN", "length = "+str(end_row-start_row)])
            break
        
        self.home(log_queue)

    
    def home(self, log_q):
    
        """
        This function prompts the user to enter his credentials or shutdown the system
        """  
        
        userIDLabel = QtWidgets.QLabel("User ID", self)

        userIDLabel.move(20, 57)
        self.userIDValue = QtWidgets.QLineEdit(self)
        self.userIDValue.setGeometry(120, 50, 200, 40)     
     
        
        passwordLabel = QtWidgets.QLabel("Password", self)
        passwordLabel.move(10, 127)
        self.passwordValue = QtWidgets.QLineEdit(self)
        self.passwordValue.setGeometry(120, 120, 200, 40) 
        self.passwordValue.setEchoMode(0)        


        
        self.login = QtWidgets.QPushButton("Login", self)
        self.login.resize(self.login.sizeHint())
        self.login.move(120, 180)
        self.userID = self.userIDValue.text()
        #now move on the Job Selection
        self.login.clicked.connect(self.JS)

        shutdown = QtWidgets.QPushButton("Shutdown", self)
        shutdown.resize(shutdown.sizeHint())
        shutdown.setGeometry(340, 210, 120, 35)
        shutdown.clicked.connect(self.shutdown)
      

        
        self.userIDValue.mousePressEvent = self.VKB1        
        self.passwordValue.mousePressEvent = self.VKB2
        if self.compareFiles('/etc/X11/xorg.conf','/etc/X11/xorg.conf.ud'):
            #if we're upside down rejig the touch pointer
            self.log_q.put(["debug","AN","Run touch flip command"])
            proc = subprocess.run('/home/debian/PSS/FixTouchUd.sh', stderr=subprocess.PIPE)
            self.log_q.put(["debug","AN","flip script result %s" % proc.stdout])
            proc = subprocess.run('/home/debian/PSS/FixTouchUd.sh', stderr=subprocess.PIPE)
            self.log_q.put(["debug","AN","flip script result %s" % proc.stdout])
        else:
            self.log_q.put(["debug","AN","No need to run touch flip command"])
        
        if user != '':
            self.log_q.put(["debug","AN","logging in directly as " + user + '/' + password])
            self.userID = user
            self.userPassword = password
            self.JS()
            
        self.show()
        

        
    def shutdown(self):
        """
        This function shutdown the system
        """      
        #user has pushed "Shutdown" button prepare for sleep
        confirm = QMessageBox.question(self, 'Message',
                    "Are you sure you want to power off?", QMessageBox.Yes | 
                    QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.prepare_for_sleep.set()
            
    def authenticate(self):
        """
        This function authenticate the user id and password
        """      
        userIDTrailer = ''
        userIDHeader = ''
        self.log_q.put(["debug","AN","Screen or file for login, self.userID is " + self.userIDValue.text()])
        if self.callingUser == '':
            self.log_q.put(["debug","AN","logging in with credentials from screen"])
            #------bodge to check non-empty username
            if self.userIDValue.text() == '':
                return False
            else:
                if self.passwordValue.text() == 'BIGDOG' or self.passwordValue.text() == 'BIGENG':
                    self.userID = self.userIDValue.text()
                    self.userPassword = self.passwordValue.text()
                    if self.passwordValue.text() == 'BIGENG':
                        DS.engineer = True
                    else:
                        DS.engineer = False
                    return True
                else:
                    return False
        else:
            return True
        # full authorisation commented out below-------------------------------
        # self.userID = self.userIDValue.text()
        # self.userPassword = self.passwordValue.text()
            # userIDTrailer = '@atamo.com.au' #add trailer if user entered from screen
            # userIDHeader = 'pss.'
            # self.userID = userIDHeader + self.userID + userIDTrailer
        # self.log_q.put(["debug","AN","Authenticating %s with %s header %s trailer %s" % (self.userID, self.userPassword, userIDHeader, userIDTrailer)])
        # #------------Uncomment for no authentication---------------------------
        # # return True
        # #---------------------------------------
        # headers = {'Authorization':'Bearer 5b401066-9040-449a-a493-2588c9eb3b50', 'Accept':'application/json', 'Content-Type':'application/json'}
        # url = 'https://apssloginapi.azurewebsites.net/api/users/verify/?code=1nQS/6f2fKKZ0EXwwQ6proNVPk7YETnbXweaJGZyX14GdriPYxCPng=='
        # # userIDTrailer = '@test.com'
        # payload={'Username':self.userID,'Password':self.userPassword}
        # # self.r = requests.post(url, json = payload, headers = headers, timeout=60)
        # try:
            # self.r = requests.post(url, json = payload, headers = headers, timeout=60)
            # self.log_q.put(["debug","AN","Authentication %s" % self.r.text])
            
            # if self.r.status_code == requests.codes.ok:
                # self.log_q.put(["debug","AN","Authenticated %s" % self.userID])
                # # print('got from API ', self.r.text)
                # # jobSelect = json.loads(json_JS.read())
                # # print('WO list length ', x)
                # # print(self.jobSelect)
                # return True

            # else:
                # self.log_q.put(["debug","AN","Authentication for %s failed with %s" % (self.userID, self.r.status_code)])
                # return False
            
        # except requests.exceptions.RequestException as e:
            # self.log_q.put(["error","AN","Authenticate Requests Exception: %s" % e])
            # self.e = e
            # return False
        # end of full authorisation commented out section-----------------------------
 
        
    def fixscreen(self):
        """
        This function checks the screen orientation for the user
        """       
        self.log_q.put(["debug","AN","fixing screen orientation for %s" % self.userID])
        if os.path.isfile("/home/debian/PSS/xfiles/" + self.userID + ".xfile"):
            self.log_q.put(["debug","AN","we have an xfile"])
            # user has a preference file, use items
            if not self.compareFiles("/etc/X11/xorg.conf","/home/debian/PSS/xfiles/" + self.userID + ".xfile"):
                self.log_q.put(["debug","AN","we need to change the x file"])
                confirm = QMessageBox.question(self, 'Message',
                    "It looks like you prefer screen flipped. Do you want to flip it?", QMessageBox.Yes | 
                    QMessageBox.No, QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    self.log_q.put(["debug","AN","User confirms screen flip"])
                    #initiate script to modify xorg config then restart X/this application
                                #save credentials in login.txt file
                    credString = self.userID + ' ' + self.userPassword
                    with open('/home/debian/PSS/login.txt', 'w+') as loginFile:
                        loginFile.write(credString)
                    subprocess.run('/home/debian/PSS/flipscreen.sh')
                else:
                    confirm = QMessageBox.question(self, 'Message',
                        "Do you want to make this your new preference?", QMessageBox.Yes | 
                        QMessageBox.No, QMessageBox.No)
                    if confirm == QMessageBox.Yes:
                        self.log_q.put(["debug","AN","User confirms screen flip"])
                        subprocess.call(['cp','/etc/X11/xorg.conf','/home/debian/PSS/xfiles/'+self.userID+'.xfile'])
                        #initiate script to modify xorg config then restart X/this application
                                    #save credentials in login.txt file
                    else:
                        self.log_q.put(["debug","AN","User decided against screen flip"])
            else:
                self.log_q.put(["debug","AN","no need to change screen orientation"])
        else:
            self.log_q.put(["debug","AN","we don't have an xfile"])
        
    def compareFiles(self, fl1, fl2):
        """
        This function compares the files for display orientation
        """    
        file1 = open(fl1, 'r')
        file2 = open(fl2, 'r')
        lines1=file1.readlines()
        lines2=file2.readlines()
        file1.close()
        file2.close()
        if lines1 == lines2:
            return True 
        else:
            return False

    def navigate(self):
        if not self.authenticate():
            self.log_q.put(["error", "AN", "Authentication failed."])
            QtWidgets.QMessageBox.about(self, "Error" ,"Invalid User or Password")
            self.show()
        else:
            #------------------Comment for no modem--------------------------------------

            # LED_Driver already started, turn heater on to get LED board warming up
            self.log_q.put(["error", "AN", "Authentication OK."])
            LED_Driver.LED_heaterON(self.log_q)

            self.fixscreen() #flip screen if required for this user
            # disable Sampler charge code (automatic because DS.userID not empty
            # enable Sampler driver
            self.show()
            self.test()        
        
#Calls Job_selection.py file to display the list of jobs
    def JS(self):


        if DS.analyserCharging == 1:
            if self.passwordValue.text() == 'BIGENG':
                # DS.engineer = True
                self.navigate()
            else:
            
                QtWidgets.QMessageBox.warning(self, "Charger connected" ,"Disconnect the charger")
            
        else:
            if self.passwordValue.text() != 'BIGENG':
                DS.engineer = False
            self.navigate()
        


    def test(self):
        #first have to verify login details by authenticating with SMP
        #but first clear credentials on GUI in case we exit back to login screen
        self.userIDValue.setText('')
        self.keyboard1.clearInput()
        self.passwordValue.setText('')
        self.keyboard2.clearInput()
        DS.userID = self.userID
        DS.process_started = True
        # if there is a Sampler connected then clear fault list before starting session
        status = Sampler.S_cmd_Get_status()
        if status["status"] != "Disconnected":
            Sampler.S_cmd_Clear_faultlist()

        if (self.mp_status.updates_pending):
            QMessageBox.warning(self,"Updates Pending","Software Updates Pending\nPlease go to Maintenance->Updates")

        if DS.CDC_software == "Yes":       
            self.M_page = Maintenance_Window(self.log_q, self.telemetry_q, self.deviceId, self.mp_status, self.charger_connected)
            self.M_page.show()

            self.M_page.sig_MW_Close.connect(self.show)
          
            self.M_page.sig_MW_noSupplies_Close.connect(self.show)
            self.M_page.sig_MW_SpectrometerError.connect(self.errorPage)
        
        
        else:
            self.log_q.put(["error", "AN", "Starting Job Selection"])
            self.Job_select = Job_selection(self.deviceId, self.telemetry_q, self.log_q, self.userID, self.userPassword, self.mp_status, self.charger_connected)
            self.Job_select.show()
            
            self.Job_select.sig_jobSelection_Close.connect(self.show)    
            self.Job_select.sig_jobselectspectroError.connect(self.errorPage)  

    def errorPage(self):
        self.log_q.put(["error","AN",'Unresponsive Spectrometer. Replace the spectrometer'])
        QMessageBox.critical(self,"EEEK","Unresponsive Spectrometer!!! \nContact Support.")
        sys.exit(1)    


#VKB1 and VKB2 to show or hide the keyboard depending on the necessity        
    def VKB1(self, event):
        
        if self.keyboard1.isHidden():
            self.keyboard1.show()
            self.log_q.put(["debug","AN",'User ID Virtual keyboard enabled'])
        else:
            self.keyboard1.hide()

            
    def VKB2(self, event):
        
        if self.keyboard2.isHidden():
            self.keyboard2.show()
            self.log_q.put(["debug","AN",'Password Virtual keyboard enabled'])
        else:
            self.keyboard2.hide()
        
        
    def Login_ID(self, data):
        self.log_q.put(["info","AN",'User ID entered: '+data])
        self.userIDValue.setText(data)
        
        DS.userID = data
        
    def Password(self, data):
        self.log_q.put(["info","AN",'Password entered: '+data]) 
        self.passwordValue.setText(data)
        self.passwordValue.setEchoMode(self.passwordValue.Password)        

# def wait_internet_up(internet_is_up, log_q):
    # """
    # Wait for internet up event
    # """

    # log_q.put(["debug","AN","wait_for_internet_up starting"])
    # while True:
        # event_is_set = internet_is_up.wait()
        # DS.connectionStatus = 1
        # #clear the event
        # internet_is_up.clear()
    # return

# def wait_internet_down(internet_is_down, log_q):
    # """
    # Wait for internet down event
    # """

    # log_q.put(["debug","AN","wait_for_internet_down starting"])
    # while True:
        # event_is_set = internet_is_down.wait()
        # DS.connectionStatus = 0
        # #clear the event
        # internet_is_down.clear()
        # log_q.put(["debug","AN","internet_down " + str(event_is_set)])
    # return

def wait_ready_for_sleep(ready_for_sleep, log_q):
    log_q.put(["debug","AN","wait_ready_for_sleep starting"])
    while True:
        event_is_set = ready_for_sleep.wait()
        log_q.put(["debug","AN","ready_for_sleep " + str(event_is_set)])
        with open("status.json","w") as statusfile:
            jsonStatus = json.dump(DS.format_sleep_status(), statusfile)
        log_q.put(["debug","AN","Status as we sleep: " +str(jsonStatus)])
        time.sleep(1)
        subprocess.run(["shutdown", "now"])
    return

def event_on_idle(sleep_event, log_q):
    log_q.put(["debug","AN","event on idle starting"])
    heaterTurnedOff = False
    while True:
        idle = float(subprocess.check_output('xprintidle').strip())
        # log_q.put(["debug","AN","Idle counter: %f LED temp: %f"%(idle,LED_Driver.getTemp('led',log_q))])
        if idle < 300000 and heaterTurnedOff == True:
            LED_Driver.LED_heaterON(log_q) # if idle for more than 5 minutes turn heater off
            heaterTurnedOff = False
        elif idle > 300000 and heaterTurnedOff == False:
            LED_Driver.LED_heaterOFF(log_q) # if idle for more than 5 minutes turn heater off
            log_q.put(["debug","AN","Heater turned OFF on idle"])
            heaterTurnedOff = True
        idle = 1000

        if idle > 3600000 and not sleep_event.is_set():
            # save status parameters to disk
            log_q.put(["debug","AN","Time to prepare for sleep"])

            sleep_event.set()
        # else:
        time.sleep(2)
    return
    
def analyserChargeHandler(q, log_q):
    log_q.put(["debug","AN","Analyser Charge Handler starting"])
    while True:
        record = q.get()    #format: ['error/warning/info/debug/', ID, str]
        try:
            charging = record[2]
            voltage = record[1]
            level = record[0]
        except:
            log_q.put(["error","AN","Badly formed Analyser charge update %s" % str(record)])

        DS.analyserCharging = charging
        DS.analyserBattery = level
        DS.analyserVoltage = voltage
        time.sleep(2)
    return

def samplerChargeHandler(q, log_q):
    log_q.put(["debug","AN","Sampler Charge Handler starting"])
    while True:
        record = q.get()    #format: ['error/warning/info/debug/', ID, str]
        try:
            charging = record[1]
            level = record[0]
        except:
            log_q.put(["error","AN","Badly formed Sampler charge update %s" % str(record)])
        log_q.put(["debug","AN","Got Sampler charge update %s" % str(record)])
        DS.samplerCharging = charging
        # only set Sampler battery level if it is a sensible value (>0)
        if level != 0:
            DS.samplerBattery = level
        time.sleep(2)
    return

def loadConfigParameters(log_queue):
    with open(config_filename, 'rt') as cfg_file:
        spamreader = csv.reader(cfg_file, delimiter='\t')
        for row in spamreader:
            if len(row) > 0: #catch and ignore accidental empty row
                log_queue.put(["info","IT",row])
                if(row[0]=='DeviceID'):
                    deviceId = row[1]  #UUID
                if(row[0]=='SiteKey'):
                    DS.SiteKey = row[1]  #UUID
                if(row[0]=='Site'):
                    DS.Site = row[1]
                if(row[0]=='AN_No'):
                    analyserNo = row[1]
                if(row[0]=='Board_type'):
                    boardType = row[1]
                if(row[0]=='Site'):
                    site = row[1]
                if(row[0]=='SiteKey'):
                    siteKey = row[1]
                if(row[0]=='DeviceName'):
                    DS.deviceName = row[1]
                if(row[0]=='siteIataCode'):
                    DS.ourSiteIataCode = row[1]
                if(row[0]=='timezone'):
                    DS.ourTimezone = row[1]
                if(row[0]=='TargetTemp'):
                    DS.targetTemp = int(row[1])
                if(row[0]=='calibrationFactor'):
                    DS.calibrationFactor = float(row[1])   
                if(row[0]=='CDC_software'):
                    DS.CDC_software = str(row[1]) 
                if(row[0]=='pumpDispense_per_rev'):
                    DS.pumpDispense_per_rev = float(row[1])                
    with open(params_filename, 'rt') as cfg_file:
        spamreader = csv.reader(cfg_file, delimiter='\t')
        for row in spamreader:
            if len(row) > 0: #catch and ignore accidental empty row
                log_queue.put(["info","IT",row])
                if(row[0]=='analyserSolventCapacity'):
                    DS.analyserSolventCapacity = int(row[1])
                if(row[0]=='analyserWasteCapacity'):
                    DS.analyserWasteCapacity = int(row[1])
                if(row[0]=='analyserBatteryThreshold'):
                    DS.analyserBatteryThreshold = int(row[1])
                if(row[0]=='samplerBatteryThreshold'):
                    DS.samplerBatteryThreshold = int(row[1])
                if(row[0]=='sampleSquirtVolume'):
                    DS.sampleSquirtVolume = float(row[1])
                if(row[0]=='postSamplingSolventVolume'):
                    DS.postSamplingSolventVolume = float(row[1])
                if(row[0]=='sampleRinseSquirtVolume'):
                    DS.sampleRinseSquirtVolume = float(row[1])
                if(row[0]=='sampleRinseSquirtVolume'):
                    DS.sampleRinseSquirtVolume = float(row[1])
                if(row[0]=='calibrateVolume'):
                    DS.calibrateVolume = float(row[1])
                if(row[0]=='resetSolventBagVolume'):
                    DS.resetSolventBagVolume = float(row[1])
                if(row[0]=='labSampleVolume'):
                    DS.labSampleVolume = float(row[1])                
                if(row[0]=='analyserSolventThreshold'):
                    DS.analyserSolventThreshold = int(row[1])
                if(row[0]=='analyserWasteThreshold'):
                    DS.analyserWasteThreshold = int(row[1])
                if(row[0]=='referenceThreshold_positive'):
                    DS.referenceThreshold_positive = int(row[1])
                if(row[0]=='referenceThreshold_negative'):
                    DS.referenceThreshold_negative = int(row[1])                
                if(row[0]=='confidenceThreshold'):
                    DS.confidenceThreshold = int(row[1])
                if(row[0]=='padAgeThreshold'):
                    DS.padAgeThreshold = int(row[1])
                if(row[0]=='rinseCountReqd'):
                    DS.rinseCountReqd = int(row[1])
                if(row[0]=='lab_RinseCountReqd'):
                    DS.lab_RinseCountReqd = int(row[1])    
                if(row[0]=='WipeRotations'):
                    DS.WipeRotations = row[1]   
                if(row[0]=='totalSamplingLocations'):
                    DS.totalSamplingLocations = row[1] 
                if(row[0]=='calConstant'):
                    DS.calConstant = row[1]
                if(row[0]=='ledSettleTime'):
                    DS.ledSettleTime = float(row[1])        
                if(row[0]=='calibrationTimeLimit'):
                    DS.calibrationTimeLimit = float(row[1])  
                if(row[0]=='enableLabSample'):
                    DS.enableLabSample = str(row[1])    
                if(row[0]=='downloadWOs'):
                    DS.downloadWOs = str(row[1])
                if(row[0]=='LEDs'):
                    DS.LEDs = row[1]

               
                 



    cfg_file.close()
    try:
        log_queue.put(["info","AS","Site IATA Code is %s" % DS.ourSiteIataCode])
        log_queue.put(["info","AS","Timezone is %s" % DS.ourTimezone])
        if deviceId == '':
            log_queue.put(["error","AN","No deviceId in cfg file"])
        if DS.analyserSolventCapacity == '':
            log_queue.put(["error","AN","No analyserSolventCapacity in cfg file"])
        else:
            log_queue.put(["debug","AN","analyserSolventCapacity is " + str(DS.analyserSolventCapacity)])
        if DS.analyserWasteCapacity == '':
            log_queue.put(["error","AN","No analyserWasteCapacity in cfg file"])
        else:
            log_queue.put(["debug","AN","analyserWasteCapacity is " + str(DS.analyserWasteCapacity)])
        if DS.analyserBatteryThreshold == '':
            log_queue.put(["error","AN","No analyserBatteryThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","analyserBatteryThreshold is " + str(DS.analyserBatteryThreshold)])
        if DS.samplerBatteryThreshold == '':
            log_queue.put(["error","AN","No samplerBatteryThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","samplerBatteryThreshold is " + str(DS.samplerBatteryThreshold)])
        if DS.sampleSquirtVolume == '':
            log_queue.put(["error","AN","No sampleSquirtVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","sampleSquirtVolume is " + str(DS.sampleSquirtVolume)])
        if DS.postSamplingSolventVolume == '':
            log_queue.put(["error","AN","No postSamplingSolventVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","postSamplingSolventVolume is " + str(DS.postSamplingSolventVolume)])
        if DS.sampleRinseSquirtVolume == '':
            log_queue.put(["error","AN","No sampleRinseSquirtVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","sampleRinseSquirtVolume is " + str(DS.sampleRinseSquirtVolume)])
        if DS.calibrateVolume == '':
            log_queue.put(["error","AN","No calibrateVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","calibrateVolume is " + str(DS.calibrateVolume)])
        if DS.resetSolventBagVolume == '':
            log_queue.put(["error","AN","No resetSolventBagVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","resetSolventBagVolume is " + str(DS.resetSolventBagVolume)])              
        if DS.labSampleVolume == '':
            log_queue.put(["error","AN","No labSampleVolume in cfg file"])
        else:
            log_queue.put(["debug","AN","labSampleVolume is " + str(DS.labSampleVolume)])            
        if DS.analyserSolventThreshold == '':
            log_queue.put(["error","AN","No analyserSolventThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","analyserSolventThreshold is " + str(DS.analyserSolventThreshold)])
        if DS.analyserWasteThreshold == '':
            log_queue.put(["error","AN","No analyserWasteThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","analyserWasteThreshold is " + str(DS.analyserWasteThreshold)])
        if DS.referenceThreshold_positive == '':
            log_queue.put(["error","AN","No referenceThreshold_positive in cfg file"])
        else:
            log_queue.put(["debug","AN","referenceThreshold_positive is " + str(DS.referenceThreshold_positive)])
        if DS.referenceThreshold_negative == '':
            log_queue.put(["error","AN","No referenceThreshold_negative in cfg file"])
        else:
            log_queue.put(["debug","AN","referenceThreshold_negative is " + str(DS.referenceThreshold_negative)])
        
        if DS.confidenceThreshold == '':
            log_queue.put(["error","AN","No confidenceThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","confidenceThreshold is " + str(DS.confidenceThreshold)])
        if DS.padAgeThreshold == '':
            log_queue.put(["error","AN","No padAgeThreshold in cfg file"])
        else:
            log_queue.put(["debug","AN","padAgeThreshold is " + str(DS.padAgeThreshold)])
        if DS.rinseCountReqd == '':
            log_queue.put(["error","AN","No rinseCountReqd in cfg file"])
        else:
            log_queue.put(["debug","AN","rinseCountReqd is " + str(DS.rinseCountReqd)])
        if DS.Site == '':
            log_queue.put(["error","AN","No Site in cfg file"])
        else:
            log_queue.put(["debug","AN","Site is " + str(DS.Site)])
        if DS.SiteKey == '':
            log_queue.put(["error","AN","No SiteKey in cfg file"])
        else:
            log_queue.put(["debug","AN","SiteKey is " + str(DS.SiteKey)])
            
        if DS.targetTemp == 0:
            log_queue.put(["error","AN","No targetTemp in cfg file"])
        else:
            log_queue.put(["debug","AN","targetTemp is " + str(DS.targetTemp)])
            
        if DS.lab_RinseCountReqd == '':
            log_queue.put(["error","AN","No lab_RinseCountReqd in cfg file"])
        else:
            log_queue.put(["debug","AN","lab_RinseCountReqd is " + str(DS.lab_RinseCountReqd)])
        if DS.WipeRotations == '':
            log_queue.put(["error","AN","No WipeRotations in cfg file"])
        else:
            log_queue.put(["debug","AN","WipeRotations is " + str(DS.WipeRotations)])
        if DS.totalSamplingLocations == '':
            log_queue.put(["error","AN","No totalSamplingLocations in cfg file"])
        else:
            log_queue.put(["debug","AN","totalSamplingLocations is " + str(DS.totalSamplingLocations)])            
        if DS.calConstant == '':
            log_queue.put(["error","AN","No calConstant in cfg file"])
        else:
            log_queue.put(["debug","AN","calConstant is " + str(DS.calConstant)]) 
        if DS.ledSettleTime == 99:
            log_queue.put(["error","AN","No ledSettleTime in cfg file"])
        else:
            log_queue.put(["debug","AN","ledSettleTime is " + str(DS.ledSettleTime)])                        
        if DS.calibrationFactor == '':
            log_queue.put(["error","AN","No calibrationFactor in cfg file"])
        else:
            log_queue.put(["debug","AN","calibrationFactor is " + str(DS.calibrationFactor)])                                    
        if DS.pumpDispense_per_rev == '':
            log_queue.put(["error","AN","No pumpDispense_per_rev in cfg file"])
        else:
            log_queue.put(["debug","AN","pumpDispense_per_rev is " + str(DS.pumpDispense_per_rev)])             
            
        if DS.calibrationTimeLimit == '':
            log_queue.put(["error","AN","No calibrationTimeLimit in cfg file"])
        else:
            log_queue.put(["debug","AN","calibrationTimeLimit is " + str(DS.calibrationTimeLimit)]) 
            
        if DS.enableLabSample == '':
            log_queue.put(["error","AN","No enableLabSample in cfg file"])
        else:
            log_queue.put(["debug","AN","enableLabSample is " + str(DS.enableLabSample)])             
        if DS.CDC_software == '':
            log_queue.put(["error","AN","No CDC_software in cfg file"])
        else:
            log_queue.put(["debug","AN","CDC_software is " + str(DS.CDC_software)])             
        if DS.downloadWOs == '':
            log_queue.put(["error","AN","No downloadWOs in cfg file"])
        else:
            log_queue.put(["debug","AN","downloadWOs is " + str(DS.downloadWOs)])             

        if DS.LEDs == '':
            log_queue.put(["error","AN","No LEDs in cfg file"])
        else:
            DS.LEDs = (list(DS.LEDs.split(",")))
            log_queue.put(["debug","AN","LEDs are %s and length = %d " %(str(DS.LEDs), len(DS.LEDs))]) 
            DS.LEDs = [int(i) for i in DS.LEDs]
            log_queue.put(["debug","AN","LEDs are %s and length = %d " %(str(DS.LEDs), len(DS.LEDs))]) 
        # if DS.LED_275 == '':
            # log_queue.put(["error","AN","No LED_275 in cfg file"])
        # else:
            # log_queue.put(["debug","AN","LED_275 is " + str(DS.LED_275)])             
        # if DS.LED_285 == '':
            # log_queue.put(["error","AN","No LED_285 in cfg file"])
        # else:
            # log_queue.put(["debug","AN","LED_285 is " + str(DS.LED_285)])             
            
    except Exception as e:
        log_queue.put(["error","AN","Problem reading compulsary parameters. Fix cfg_file.csv file." + str(e)])

    
if __name__ == '__main__':
    
    log_queue = mp.Queue()
    DS.log_q = log_queue
    DS.log_q.put(["debug","AN","Hello folks"])
    rx_queue = mp.Queue()
    telemetry_queue = mp.Queue()
    analyser_charge_queue = mp.Queue()
    sampler_charge_queue = mp.Queue()
    internet_up = mp.Event()
    internet_down = mp.Event()
    prepare_for_sleep = mp.Event()
    preparing_for_sleep = Value('i', 0)
    ready_for_sleep = mp.Event()
    charger_connected = mp.Event()
    # read device parameters from config file
    ATCA_SUCCESS = 0x00
    global gSite
    global gSiteKey
    global G_STATUS
    #sort screen out
    CONN_STR_FMT="HostName=%s;DeviceId=%s;SharedAccessKey="
    config_filename = 'cfg_file.csv'
    params_filename = 'params_file.csv'
    status_filename = 'status.json'
            #sys.exit(1)
    site='pss-rsrch-iot.azure-devices.net'
    siteKey='HTPJLGByyFUpQ8o9t6Th0h6TNzoqBb27IFd5K3tPYRY='
    # Initialise crypto chip
    # #initialise some constants

    DS.deviceName = ''
    deviceId = ''
    
    try:
        log_queue.put(["debug","AN","Starting to open login file user"])
        with open('/home/debian/PSS/login.txt', 'r') as loginfile:
            data = loginfile.read().replace('\n','')

            user, password = data.split(' ',1)
        log_queue.put(["debug","AN","Starting user: %s" % user])
        log_queue.put(["debug","AN","Deleting login.txt"])
        os.remove('/home/debian/PSS/login.txt')
    except:
        user = ""
        password = ""
        log_queue.put(["debug","AN","No starting user"])
    
    log_queue.put(["info","IT",'Reading config file...'])
# Check that essential files exist 
    loadConfigParameters(log_queue)
    
    
    #initialise some constants
    DS.sampleVolume = (DS.sampleSquirtVolume + (2*DS.postSamplingSolventVolume) + (DS.sampleRinseSquirtVolume) + DS.calibrateVolume)
    log_queue.put(["info","IT",'Sample Volume is ' + str(DS.sampleVolume)])
    DS.analyserSolventCount =  (DS.analyserSolventCapacity/DS.sampleVolume)
    log_queue.put(["info","IT",'Analyser Solvent Count is ' + str(DS.analyserSolventCount)])    
    DS.analyserWasteCount = (DS.analyserWasteCapacity/DS.sampleVolume)  
    log_queue.put(["info","IT",'Analyser Waste Count is ' + str(DS.analyserWasteCount)])    
    connection_str= CONN_STR_FMT%(DS.Site,DS.deviceName)
    connection_str= connection_str + DS.SiteKey
    
    
    
    try:
        # (IoT.CONNECTION_STRING, IoT.PROTOCOL) = IoT.get_iothub_opt(sys.argv[1:], IoT.CONNECTION_STRING, IoT.PROTOCOL)
        (connection_str, IoT.PROTOCOL) = IoT.get_iothub_opt(sys.argv[1:], connection_str, IoT.PROTOCOL)
    except _OptionError as option_error:
        sys.exit(1)
    # initialise shared namespace 
    mp_status = mp.Manager().Namespace()
    mp_status.sampler_ver = ""
    mp_status.samplerID = "123"
    mp_status.perform_updates = False
    mp_status.updates_pending = False
    mp_status.firmware_req = ""
    mp_status.sampler_req = ""
    mp_status.connectionStatus = 0 # initialise Internet state to DOWN (False)
    mp_status.samplerUpdateStatusGood = False
    mp_status.updateStatusGood = False
    analyser_cloud = Analyser_Cloud.cloud(connection_str, telemetry_queue, internet_up, internet_down, prepare_for_sleep, preparing_for_sleep, ready_for_sleep, analyser_charge_queue, sampler_charge_queue, mp_status, log_queue)

    cloud_process = mp.Process(name="Analyser Cloud Process",target=analyser_cloud.iothub_client_sample_run, args=(connection_str, telemetry_queue, internet_up, internet_down, prepare_for_sleep, preparing_for_sleep, ready_for_sleep, mp_status,log_queue ), daemon = True)
    cloud_process.start()
    log_queue.put(['warning','UI', 'Started cloud process'])
    
    #initialise Sampler driver
    log_queue.put(["info","AN","Starting Sampler driver"])
    Sampler.Sampler_init(log_queue)

    app = QtWidgets.QApplication(sys.argv)   
    styleSheet = """
    QScrollBar:vertical{width:30px}
    QScrollBar:horizontal{height:30px}
    QMesssageBox{background-color:#333333}
    QCheckBox:indicator{width:40px}
    QCheckBox:indicator{height: 40px}
    """   
    app.setFont(QtGui.QFont('Ariel', 16))
    app.setStyleSheet(styleSheet)
    

    GUI = Login(deviceId, telemetry_queue, log_queue, user, password, prepare_for_sleep, mp_status, charger_connected)
 
    
    
    
# read current values of status variables (saved at each sleep)
    try:
        with open(status_filename ) as status_file:
            sleep_status = json.load(status_file)
        log_queue.put(["debug","AN","Starting status %s" % str(sleep_status)])
        DS.samplerTotalWipeCount = sleep_status["samplerTotalWipeCount"]
        DS.samplerTotalSpinCount = sleep_status["samplerTotalSpinCount"]
        DS.analyserSamplesTotal = sleep_status["analyserSamplesTotal"]
        DS.analyserPadAge = sleep_status["analyserPadAge"]
        DS.analysersolventTotal = sleep_status["analysersolventTotal"]
        DS.analyserPadsTotal = sleep_status["analyserPadsTotal"]
        DS.analyserSolventRemaining = sleep_status["analyserSolventRemaining"]
        DS.analyserwasteTotal = sleep_status["analyserwasteTotal"]
        DS.analyserWasteRemaining = sleep_status["analyserWasteRemaining"]
        DS.analyserLabSampleCount = sleep_status["analyserLabSampleCount"]
        DS.analyserBattery = sleep_status["analyserBattery"]
        DS.analyserSolventID = sleep_status["analyserSolventID"]
        log_queue.put(["debug","AS","Starting aBatt: " + str(DS.analyserBattery)])
    except: #no status file
        log_queue.put(["debug","AS","No status file"])   

    statusBar = statusGui(log_queue, mp_status, charger_connected)
    statusBar.show()    
    
    # check_charger_connected = charger_connectivity(log_queue)
    
    essential_files_folder = '/home/debian/PSS/CSV_files/'
    essential_files = ['DOP.csv','known_DOP.csv','Permethrin.csv','known_perm.csv','Spectrometer_database.csv']
    log_queue.put(["debug","AN","Checking for essential_files"])
    for file in essential_files:
        essential_file = essential_files_folder + file
        
        exists = os.path.isfile(essential_files_folder + file)
        if not exists:
            log_queue.put(["error","AN",file + " is missing"])
            confirm = QMessageBox.critical(statusBar,"EEEK","Essential file missing!!!!\nContact Support.")
            sys.exit(1)


    # try:
        # threading.Thread(name="Internet Up handler",target=wait_internet_up, args=(internet_up,log_queue)).start()
    # except Exception as ex:
        # log_queue.put(["error","AN","Problem starting Internet Up Event thread" + str(ex)])
    # try:
        # threading.Thread(name="Internet Down handler",target=wait_internet_down, args=(internet_down,log_queue)).start()
    # except Exception as ex:
        # log_queue.put(["error","AN","Problem starting Internet Down Event thread" + str(ex)])
    try:
        threading.Thread(name="Ready For Sleep handler",target=wait_ready_for_sleep, args=(ready_for_sleep,log_queue)).start()
        preparing_for_sleep = Value('i', 0)
    except Exception as ex:
        log_queue.put(["error","AN","Problem starting Ready For Sleep Event thread" + str(ex)])
    try:
        threading.Thread(name="Sleep handler",target=event_on_idle, args=(prepare_for_sleep, log_queue)).start()
    except Exception as ex:
        log_queue.put(["error","AN","Problem starting Idle Event thread" + str(ex)])
    try:
        threading.Thread(name="Analyser Charge Handler",target=analyserChargeHandler, args=(analyser_charge_queue,log_queue)).start()
    except Exception as ex:
        log_queue.put(["error","AN","Problem starting Analyser Charge Handler thread" + str(ex)])
    
    # start LED Driver ready for later use
    log_queue.put(["info","AN","Starting LED driver"])
    LED_Driver.set_tempcutOFF(DS.targetTemp,log_queue)
    LED_Driver.LED_heaterON(log_queue)
    
    # initialise pump controller
    log_queue.put(["info","AN","Starting pump controller"])
    PC.PC_driverInit(log_queue)
                    
    sys.exit(app.exec_())

 

