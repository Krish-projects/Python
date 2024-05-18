#This file displays the list of jobs available for the operator
# from datetime import date, datetime, timedelta
import datetime
import dateutil.parser
import json
import logging
import requests
import subprocess
import sys 
import time
import threading

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pytz import timezone
# print ("Jobselection.py first call startin at : startupTime",datetime.datetime.now())

import Adafruit_BBIO.GPIO as GPIO

#Python files download
#----
from Flight_details import GetPlaneId
from locationDetails import edit_locationDetails
from Maintenance_Window import Maintenance_Window
from Spectrometer_capture import Capture
from Status_Window import Status_Window

import deviceStatus as DS
import LED_Driver

import Sampler
#----

GPIO.setup("P9_28", GPIO.OUT) ##Lab Drain valve (valve 2 in schematic)
GPIO.setup("P9_24", GPIO.OUT) ##Waste Drain valve (valve 1 in schematic)
GPIO.setup("P9_25", GPIO.OUT) ##Dispense valve (valve 3 in schematic)
GPIO.setup("P9_27", GPIO.OUT) ##valve connecting tube and exit valves

class Job_selection(QWidget):

    sig_jobSelection_Close = pyqtSignal()
    sig_jobselectspectroError = pyqtSignal()
    # sig_JS_chargerConnected = pyqtSignal()


    def __init__(self, deviceId, telemetry_q, log_q, user, password, mp_status, charger_connected):
        super(Job_selection, self).__init__()
        self.log_q = log_q
        self.telemetry_q = telemetry_q
        self.deviceId = deviceId
        self.user = user
        self.password = password
        self.charger_connected = charger_connected
        #initialise date variables to start as today
        self.targetDate = datetime.datetime.now(tz=timezone(DS.ourTimezone)).isoformat()
        self.log_q.put(["debug","JS","targetDate: " + str(self.targetDate)])
        #and ability to add/subtract a day from current target
        self.one_day = datetime.timedelta(days=1)
        Job_selection.setGeometry(self, 0, 22, 480, 250)
        self.no_Supplies = False
        self.Update = False
        self.enter = True    
        # self.start_process = True
        self.loadJob()
        self.mp_status = mp_status
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.check_charger_connectivity)
        self.check_charger_connectivity()
        
    def check_charger_connectivity(self):
        if self.charger_connected.is_set():
            # self.no_Supplies = True
            DS.engineer = True
            
            self.noSupplies()
            self.charger_connected.clear()
            
        self.Timer.start(1000)

    def loadJob(self):
        """
        Displays the following options:
        1. Displays the downloaded / created workorders
        2. Previous day / Next day - displays previous / next day workorders when clicked
        3. Status - displays the supply availability
        4. Maintenance - Takes to the maintenance page
        5. Create - Allows operator to create own workorder 
        6. Flip - Flips the screen and stores the choice for the operator
        7. Exit - Logs out the user 
        """
        if DS.process_started:
            self.textLabel = QLabel('Select Flight to Test',self)
            self.textLabel.setGeometry(30,10,460,25)
    # button for previous day
            self.btnPrevious = QtWidgets.QPushButton("Previous Day", self)
            self.btnPrevious.clicked.connect(self.previousDay)
            self.btnPrevious.resize(self.btnPrevious.sizeHint())
            self.btnPrevious.move(20, 120)        
            
            

    # button for next day
            self.btnNext = QtWidgets.QPushButton("Next Day", self)
            self.btnNext.clicked.connect(self.nextDay)
            self.btnNext.resize(self.btnNext.sizeHint())
            self.btnNext.move(350, 120)  

    #Push button for Status display
            self.btnStatus = QtWidgets.QPushButton("Status", self)
            self.btnStatus.clicked.connect(self.statusScreen)
            self.btnStatus.setGeometry(QRect(10, 210, 80, 35)) 

    #Push button for maintenance mode
            self.btnMaintenance = QtWidgets.QPushButton("Maintenance", self)
            self.btnMaintenance.clicked.connect(self.maintenanceScreen)
            self.btnMaintenance.setGeometry(QRect(100, 210, 145, 35))        

    #Push button to create work order
            self.btnCreate = QtWidgets.QPushButton("Create", self)
            self.btnCreate.clicked.connect(self.createWO)
            self.btnCreate.setGeometry(QRect(255, 210, 80, 35))
            
    #Push button for Flip screen
            self.btnFlip = QtWidgets.QPushButton("Flip", self)
            self.btnFlip.clicked.connect(self.flipScreen)
            self.btnFlip.setGeometry(QRect(345, 210, 60, 35)) 
     
    #Push button for page Exit 
            self.btnExit = QtWidgets.QPushButton("Exit", self)
            self.btnExit.clicked.connect(self.close_application)
            self.btnExit.setGeometry(QRect(415, 210, 60, 35))
             
            self.table = QtWidgets.QTableWidget(self)
            self.table.setGeometry(QtCore.QRect(180, 50, 140, 150))
            self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            self.table.setColumnCount(5)
            if DS.downloadWOs != "Yes":
                self.jobSelect = []
                self.btnNext.setVisible(False)
                self.btnPrevious.setVisible(False)
                self.displayWorkOrders()
                self.show
                
            else:
                self.table.setVisible(False)
                self.btnCreate.setVisible(False)
                self.textLabel.setVisible(False)
                self.btnExit.setVisible(False)
                self.btnMaintenance.setVisible(False)
                self.btnStatus.setVisible(False)
                self.btnFlip.setVisible(False)        
                # Prepare progress dialog 
                # timer is started to tun while separate thread used to perform blocking get request
                # thread signals completion by setting woprogress flag non-zero
                self.show()
                
                self.timer = QBasicTimer()
                self.step = 0
                self.progressBar = QProgressDialog("Downloading Work Orders", "Cancel", 0, 100)
                self.progressBar.setGeometry(20,100,420,100)
                self.progressBar.show()
                self.woprogress = 0
                self.timer.start(1000,self)
                self.cancelPressed = 0 #used when user hits cancel during HTTP request
                #kick off HTTP request (POST) for RegimeInstance
                self.thread = threading.Thread(target=self.getWorkOrders)
                self.thread.start()
                

            self.table.cellClicked.connect(self.cell_is_clicked)        
            self.show()
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return

    def enableTimer(self):
        self.show()
        self.Timer.start(1000)
        self.log_q.put(["debug","JS","Timer started"])

    def createWO(self):

        """
        Migrates to workorder page 
        """
        # charger_connected = self.check_charger_connectivity()
        if DS.process_started:
            self.log_q.put(["debug","JS","Entering create workorder..."])
            self.timer_and_page_close()
            self.createwo = edit_locationDetails(self.log_q, "WorkOrder", "", "", "", "", "", self.charger_connected)

            self.createwo.sig_workorder_Complete.connect(self.updateWO)
            self.createwo.sig_editClose.connect(self.enableTimer)
            self.createwo.sig_charger_connected.connect(self.noSupplies)
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return
        
    def updateWO(self,  flight, rego):
        """
        Updates workorder and display  
        """  
        if DS.process_started:        
            self.show()
            self.Update = True
            self.flight = flight
            self.rego = rego
            self.workorderid = '12345'
            todaystr = str(datetime.date.today())
            # self.log_q.put(["debug","JS","In update WO, DS.planenumberAndrego: "+str(DS.planenumberAndrego)])        
            # self.log_q.put(["debug","JS","In update WO, length(DS.planenumberAndrego): "+str(len(DS.planenumberAndrego))])        
            self.newWorkOrder = {"WorkOrderId":self.workorderid, "ModifiedDate":todaystr, "OperatorName":DS.userID,
            "Flight":{"ModifiedDate":todaystr, "FlightNumber":self.flight, "FlightDate": str(self.targetDate), "PlaneSeries": 'Unknown',
            "TailNumber":self.rego, "IsDeleted":False, "PlaneModel":'Unknown',"OperatingAirlineCode": "QANTAS"},
            "WorkOrderDateTime":str(datetime.datetime.now()),
            "OrganisationId":"6c891030-a596-42e0-bb1c-ceed0805fdbf", "id":"adc23408-dda7-4f20-b657-e5b5c936cabf", "SiteId":"7fa5affe-6ac9-4208-88d0-1868ced5a301", "RegimeId":"326762ab-978e-480e-ba1d-d7760f33af61",
            "DeviceName":DS.deviceName, "OrganisationName": 'Atamo', "IsDeleted":False, "SiteIataCode":DS.ourSiteIataCode, "SiteName":DS.ourTimezone  }

            self.enter = False
            self.jobSelect.append(self.newWorkOrder)
                   
            self.displayWorkOrders()
            self.filterWorkOrders()
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return        
        
        

    def getWorkOrders(self):
        # run as separate thread to perform (blobking) get request
        dummyWoList = []
        self.log_q.put(["debug","JS","Downloading Work Orders from SMP"])
        QtWidgets.qApp.processEvents()
        payload = {'code':'muGtGpMvKxvd5fL5ObqFFQydyEhZxsyfCaQ4V9uJB0/IMjFdhNinXw=='}
        url = 'https://apssworkorderapi.azurewebsites.net/api/workorders/location/' + DS.ourSiteIataCode
        headers = {'Authorization':'Bearer 5b401066-9040-449a-a493-2588c9eb3b50', 'Accept':'application/json', 'Content-Type':'application/json'}
        try:
            self.r = requests.get(url, headers = headers, params = payload, timeout = 30)
            self.log_q.put(["error","JS","self.r: %s" % self.r])
            if self.r.status_code == requests.codes.ok:
                self.jobSelect = json.loads(self.r.text)
                
            else:
                choice = QtWidgets.QMessageBox.question(self, 'Sad API response ' + str(self.r.status_code), 'Sad API response ' + str(self.r.status_code), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                self.jobSelect = dummyWoList
            self.woprogress = 1
        except requests.exceptions.RequestException as e:
            self.log_q.put(["error","JS","Requests Exception: %s" % e])
            self.e = e
            # QtWidgets.QMessageBox.about(self, "Error" ,"No Internet Connectivity, continuing.")
            self.jobSelect = dummyWoList
            self.woprogress = 2

       
        # self.woprogress = 1


    def timerEvent(self, e):
        # timer runs while blobking get request performed in separate thread
        # timer waits for completion flag (woprogress) to be non zero
        if self.step >= 100:
            QtWidgets.QMessageBox.about(self, "Error" ,"No Internet Connectivity, continuing.")
            self.timer.stop()
            self.woprogress = 1
            # self.noSupplies()
            # return
        if self.woprogress == 0:
            self.step = self.step + 2
            self.progressBar.setValue(self.step)
            if self.progressBar.wasCanceled():
                # if cancel pressed just show an empty list
                self.log_q.put(["error","JS","Cancel pressed 1, woprogress: "+str(self.woprogress)])
                self.cancelPressed = 1
                # self.timer.stop()
                self.jobSelect = [] #dummy WOList
                self.woprogress = 1
                # self.close_application()
                self.progressBar.hide()
        else:

            # if self.cancelPressed == 1:
                # # user has pressed cancel during HTTP request. Ignore response and continue
                # self.log_q.put(["error","JS","Cancel pressed 2, woprogress: "+str(self.woprogress)])
                # return
                
            # else:
            if self.woprogress == 2:
                self.log_q.put(["error", "JS", "Exception from SMP getting WOs " + str(self.e)])
                QtWidgets.QMessageBox.about(self, "Error", "No Internet Connectivity, continuing.")
                self.woprogress = 1 # then continue
            if self.woprogress == 1:
                self.log_q.put(["debug","JS","Got Work Order list"])
                self.displayWorkOrders()
                self.filterWorkOrders()
                DS.planenumberAndrego = []
                self.progressBar.setValue(100)
                self.timer.stop()
                self.progressBar.hide()
                # # # initialise pump controller
                # # self.log_q.put(["info","JS","Starting pump controller"])
                # # PC.PC_driverInit(self.log_q)  

                return

            else:
                self.log_q.put(["error", "JS", "Exception from SMP getting WOs " + str(self.e)])
                QtWidgets.QMessageBox.about(self, "Error", "No Internet Connectivity, continuing.")
                self.show()
                self.timer.stop()
                self.progressBar.hide()
                return                    
            
            return

    def filterWorkOrders(self):
        """
        filter rows in Work Order table to only shows those where column 4 (FlightDate) is targetDate[:10] 
        """    
    # filter rows in Work Order table (self.table) to only shows those where column 4 (FlightDate) is targetDate[:10]
        allRows = self.table.rowCount()
        count=0
        self.textLabel.setText('Select Flight from ' + self.targetDate[:10] + ' to Test')
        self.textLabel.update()
        for row in range(allRows):
            date = self.table.item(row, 4).text()
            try:
                # try to catch silly dates that have been entered in the SMP
                flightDate = str(dateutil.parser.parse(date).astimezone(timezone(DS.ourTimezone)))[:10]
            except Exception as e:
                self.log_q.put(["debug","JS",'astimezone exception: '+ str(e)])
                self.log_q.put(["debug","JS",'Failing date: '+ str(date)])
                flightDate = '2000-01-01' # ignore this one for now
            if flightDate == str(self.targetDate)[:10]: # find entries for our date
                self.table.setRowHidden(row, False)
                
            else:
                self.table.setRowHidden(row, True)
                
        self.table.update()

    def displayWorkOrders(self):
        """
        Display workorders 
        """      
        #starts with data from SMP in self.jobSelect
        #extracts relevant rows into table to display Work Orders
        #start with targetdate as today (but allow operator to move forward and backward)
        x = len(self.jobSelect)
        # self.log_q.put(["debug","JS",'length '+ str(x)])
        horHeaders = ['Site', 'Airline', 'Flight', 'WorkOrderId']
        
        row = 0
        if x != 0:
            if self.enter:
                for index in range(0,x):
                    self.Job_Select = self.jobSelect[index]
                    if self.Job_Select['Flight'] != None :

                            self.table.insertRow(row)
                            self.table.setItem(row, 0, QTableWidgetItem(self.Job_Select['SiteName']))
                            self.table.setItem(row, 1, QTableWidgetItem(self.Job_Select['Flight']['OperatingAirlineCode']))
                            self.table.setItem(row, 2, QTableWidgetItem(self.Job_Select['Flight']['FlightNumber']))
                            self.table.setItem(row, 3, QTableWidgetItem(self.Job_Select['WorkOrderId']))
                            self.table.setItem(row, 4, QTableWidgetItem(self.Job_Select['Flight']['FlightDate']))
                            row += 1
                        
      
            if self.Update:
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(self.newWorkOrder['SiteName']))
                self.table.setItem(row, 1, QTableWidgetItem(self.newWorkOrder['Flight']['OperatingAirlineCode']))
                self.table.setItem(row, 2, QTableWidgetItem(self.newWorkOrder['Flight']['FlightNumber']))
                self.table.setItem(row, 3, QTableWidgetItem(self.newWorkOrder['WorkOrderId']))
                self.table.setItem(row, 4, QTableWidgetItem(self.newWorkOrder['Flight']['FlightDate']))
                row += 1
                
                
        else:
            self.textLabel.setText("No Work Orders Available")
       
        self.table.setHorizontalHeaderLabels(horHeaders)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(1, True)
        self.table.setColumnHidden(3, True)
        self.table.setColumnHidden(4, True)
        self.table.setVisible(False)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.setVisible(True)
        if DS.downloadWOs == 'Yes':
            self.btnNext.setVisible(True)
            self.btnPrevious.setVisible(True)
        self.textLabel.setVisible(True)
        self.btnExit.setVisible(True)
        self.btnMaintenance.setVisible(True)
        self.btnStatus.setVisible(True)
        self.btnFlip.setVisible(True)  
        self.btnCreate.setVisible(True)       


#Exit the page  
    def noSupplies(self):
        """
        Indicate no enough supplies 
        """       
        self.no_Supplies = True
        self.close_application()
        
    def timer_and_page_close(self):
        """
        This module is to stop the timer and close the page

        As a preventive mesure the valves are closed
        """
        GPIO.output("P9_27", GPIO.LOW)##Turn oFF valve connecting tube and exit valves
        GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve    
        GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve   
        GPIO.output("P9_25", GPIO.LOW)##Turn oFF Dispense valve        
        self.timer_stop()
        self.log_q.put(["debug","JS","!!!!!!!!!!! EXITING JOB SELECTION PAGE !!!!!!!!"])
        self.close()
        

    def timer_stop(self):
        """
        This function is to stop the timer when it migrates to the next page
        """
        self.Timer.stop()
        self.log_q.put(["debug","JS","Timer stopped"])           
        
      
    def close_application(self):
        '''
        As a preventive mesure the valves are closed
        '''
        GPIO.output("P9_27", GPIO.LOW)##Turn oFF valve connecting tube and exit valves
        GPIO.output("P9_24", GPIO.LOW)##Turn oFF waste valve    
        GPIO.output("P9_28", GPIO.LOW)##Turn oFF lab valve   
        GPIO.output("P9_25", GPIO.LOW)##Turn oFF Dispense valve   
        if self.no_Supplies:
            self.log_q.put(["info","JS", '.........Exiting the application due to '+ DS.cause_Of_logout[DS.logout_cause_value]+' .....'])  
            self.log_q.put(["debug","JS",'*********Closing Job Selection window*********'])              
            LED_Driver.LED_heaterOFF(self.log_q)
            self.timer_and_page_close()              
            # set userID empty so sampler charge code is enabled
            DS.userID = ''
            self.sig_jobSelection_Close.emit()            
        else:
            if (self.mp_status.updates_pending):
                QMessageBox.warning(self,"Updates Pending","Software Updates Pending\nPlease go to Maintenance->Updates")
        
            choice = QtWidgets.QMessageBox.question(self, 'Exit!', "Are you sure you want to Exit?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            self.log_q.put(["warning","JS", 'EXIT button clicked!!!!'])               
            if choice == QtWidgets.QMessageBox.Yes:
                self.log_q.put(["info","JS", '.........Exiting the application.....'])  
                self.log_q.put(["debug","JS",'*********Closing Job Selection window*********'])              
                LED_Driver.LED_heaterOFF(self.log_q)
                DS.engineer = True
                self.timer_and_page_close()
                # set userID empty so sampler charge code is enabled
                DS.userID = ''
                self.sig_jobSelection_Close.emit()

#This function is invoked when the the SPECTROMETER is unresponsive
    def Jobselect_spectrometerError(self):
        self.sig_jobselectspectroError.emit() 
        pass        
        
    def maintenanceScreen(self):
        # charger_connected = self.check_charger_connectivity()
        if DS.process_started:  
            self.timer_and_page_close()
            self.M_page = Maintenance_Window(self.log_q, self.telemetry_q, self.deviceId, self.mp_status, self.charger_connected)
            self.M_page.show()
            
            self.M_page.sig_MW_Close.connect(self.enableTimer)
          
            self.M_page.sig_MW_noSupplies_Close.connect(self.noSupplies)
            self.M_page.sig_MW_SpectrometerError.connect(self.show)
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return        
            
        
    def statusScreen(self):
        """
        Display Status screen
        """   
        # charger_connected = self.check_charger_connectivity()
        if DS.process_started: 
            # display Status screen
            self.timer_and_page_close()          
            self.log_q.put(["debug","SW",'------------ Opening Status window -------------------']) 
            self.S_page = Status_Window(self.log_q, self.charger_connected)
            self.S_page.show()

            self.S_page.sig_availableSupplies.connect(self.enableTimer)
            # self.S_page.sig_SpectrometerError.connect(self.Jobselect_spectrometerError)
            self.S_page.sig_SpectrometerError.connect(self.enableTimer)
            self.S_page.sig_Sampler_will_not_return.connect(self.noSupplies)
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return         
        
    def flipScreen(self):
        """
        User has requested flip screen. Get confirmation first
        """     
    # user has requested flip screen. Get confirmation first
        confirm = QMessageBox.question(self, 'Message',
            "Are you sure you want to flip the screen? This operation will take about 30 seconds", QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.log_q.put(["debug","JS","User requests screen flip"])
            #save credentials in login.txt file
            credString = self.user + ' ' + self.password
            self.log_q.put(["debug","JS","After User requests screen flip"])
            with open('/home/debian/PSS/login.txt', 'w+') as loginFile:
                loginFile.write(credString)
            #now create this user's flip preference file
            subprocess.call(['cp','/etc/X11/xorg.conf.alt','/home/debian/PSS/xfiles/'+self.user+'.xfile'])
            #initiate script to modify xorg config then restart X/this application
            subprocess.call('/home/debian/PSS/flipscreen.sh')

    def previousDay(self):
        """
        Here when user clicks button to show WOs from previous day
        Subtract one day from target and run filter again
        """      
        # Here when user clicks button to show WOs from previous day
        # subtract one day from target and run filter again
        self.targetDate = str(dateutil.parser.parse(self.targetDate).astimezone(timezone(DS.ourTimezone)) - self.one_day)
        self.filterWorkOrders()

    def nextDay(self):
        """
        Here when user clicks button to show WOs from next day
        Add one day from target and run filter again
        """       
        # Here when user clicks button to show WOs from next day
        # add one day from target and run filter again
        self.targetDate = str(dateutil.parser.parse(self.targetDate).astimezone(timezone(DS.ourTimezone)) + self.one_day)
        self.filterWorkOrders()
        
    def cell_is_clicked(self, row, column):
        """
        Identify the row and column that is been clicked by the operator
        """     
        # charger_connected = self.check_charger_connectivity()
        if DS.process_started:     
            #Identify the row and column that is been clicked by the operator
            row = self.table.currentRow()
            self.SelectedItem = self.table.item(row, 3)
            self.SelectedWorkOrder = self.SelectedItem.text()
            self.SelectedFlightNumber = self.table.item(row, 2).text()
            
            self.log_q.put(["debug","JS","Selected Flight: %s" % self.SelectedFlightNumber])
     
            self.log_q.put(["debug","JS","Selected Workorder = "+str(self.SelectedWorkOrder)])
            self.PlaneID_page1(self.SelectedFlightNumber, self.SelectedWorkOrder)
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return              
     
#Opens the "Flight_details.py" file to enter the flight details
    def PlaneID_page1(self, flight, workOrder):
        # charger_connected = self.check_charger_connectivity()
        if DS.process_started:   
            WorkOrderDetails = 0

            self.timer_and_page_close()           
            self.plane_ID = GetPlaneId(flight, workOrder, self.deviceId, self.telemetry_q, self.log_q, self.charger_connected)
            self.plane_ID.show()
            self.plane_ID.sig_flightDetails_Close.connect(self.enableTimer)
            
            self.plane_ID.sig_Cancel_Finish.connect(self.show)
            self.plane_ID.sig_noFromSupplies.connect(self.noSupplies) 
            self.plane_ID.sig_flightSpectroError.connect(self.Jobselect_spectrometerError)        
        else:
            self.log_q.put(["debug","JS","Charger connected..."])
            return 


 
