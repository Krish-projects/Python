
import csv
import numpy 
import os
import sys 
import time
import datetime


from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# print ("Spectrometer_capture.py first call startin at : startupTime",datetime.datetime.now())

import deviceStatus as DS 
import seabreeze.spectrometers as sb


from Adafruit_BBIO.SPI import SPI



import LED_Driver



class spectrum:

    def __init__(self,spectrometer):
        self.spectrometer=spectrometer
        self.wavelengths=self.spectrometer.wavelengths()
        self.reference=[]
    
            
class Capture(QtWidgets.QMainWindow):
    def __init__(self, log_q):
        super (Capture, self).__init__()
        self.log_q = log_q
        self.row_startEnd = False
        
##'SPECTROMETER PARAMETERS: Integration time: 2 s, Scans to Average: 1, Trigger mode: 0'    
    def initialise(self):
        x=True
        self.y=0
        while x:
            try:
            # self.log_q.put(["debug", "SC", '---------trying to Reinitialise------------']) 
                self.log_q.put(["debug", "SC", 'Initialising Spectrometer'])    
                self.spec=sb.Spectrometer.from_serial_number()
                self.log_q.put(["debug", "SC", 'Spectrometer serial number initialised'+str(self.spec)]) 
                self.spec.scans_to_average(1)
                self.log_q.put(["debug", "SC", 'Spectrometer scans to average initialised to 1'])
                self.spec.trigger_mode(0) 
                self.log_q.put(["debug", "SC", 'Spectrometer trigger mode initialised to 0']) 
                x = False
            except Exception:
                    errorState = self.Error()
                    if errorState:
                        pass
                    else:
                        self.log_q.put(["debug", "SC", '---------RETURNING FALSE!!!!!!!!!!!------------']) 
                        return(False)            
       
       
    def columnAssign(self):    
        # self.log_q.put(["debug", "SC", '---------Start of Column assign------------']) 
        Spectrum=spectrum(spectrometer=self.spec)       
        Spectrum.reference=self.get_spectrum()
        if self.row_startEnd:
            # self.log_q.put(["debug", "SC", '---------Start of capture------------']) 
            self.specStack= numpy.column_stack([Spectrum.wavelengths,Spectrum.reference])
            self.row_startEnd = False
            # self.log_q.put(["debug", "SC", '---------End of capture------------']) 
        else:
            self.specStack= numpy.column_stack([Spectrum.wavelengths[DS.RowStart:DS.RowEnd],Spectrum.reference[DS.RowStart:DS.RowEnd]])        
        # self.log_q.put(["debug", "SC", '---------End of Column assign------------']) 


    def opticalBenchParams(self):
        self.y=0
        # self.initialise()
        try:
            self.initialise()
            self.model_no = list(str(self.spec))        
            serial_no = ''
            for i in range(25):
                if i>=18 and i<24:
                    serial_no =serial_no+ self.model_no[i]
            print("serial_no=", serial_no)   
            DS.spectroSerialNumber = serial_no
            self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ serial_no])
            # set up Ethanol_Reference file for this spectrometers
            DS.spectroEthanolReference = "Ethanol_Reference_" + serial_no + ".csv"
            self.log_q.put(["debug", "SC", "Ethanol Reference file is: "+ DS.refFilesDirectory + DS.spectroEthanolReference])
            # if not os.path.isfile(DS.localRefFilesDirectory + DS.spectroEthanolReference):
                # self.log_q.put(["error", "SC", "Ethanol Reference " + DS.localRefFilesDirectory + DS.spectroEthanolReferencefile + " + not found"])
            # now find the parameters for this spectrometer in the Spectrometer_database.csv file
            try:
                with open(DS.refFilesDirectory + "Spectrometer_database.csv", 'r') as cfg_file:
                    reader = csv.reader(cfg_file, delimiter=',')
                    spectro = list(reader)
                    # print("spectro = ", spectro, "len(spectro) = ", len(spectro))
                    found_spectro = False
                    for column in range(len(spectro)):
                        if(spectro[column][0]==serial_no):
                            found_spectro = True
                            DS.integrationTime = int(spectro[column][2])
                            self.log_q.put(["debug", "SC", "integrationTime = %d"%DS.integrationTime])
                            DS.brightness255 = int(spectro[column][3])
                            self.log_q.put(["debug", "SC", "255 nm LED Brightness = %d"%DS.brightness255])
                            DS.brightness275 = int(spectro[column][4])
                            self.log_q.put(["debug", "SC", "275 nm LED Brightness = %d"%DS.brightness275])
                            DS.brightness285 = int(spectro[column][5])
                            self.log_q.put(["debug", "SC", "285 nm LED Brightness = %d"%DS.brightness285])
                            DS.brightness295 = int(spectro[column][6])
                            self.log_q.put(["debug", "SC", "295 nm LED Brightness = %d"%DS.brightness295])
                            
            except:
                self.log_q.put(["error", "SC", "Error opening Spectrometer_database.csv"])
                       
                return False
            if not found_spectro:
                self.log_q.put(["error", "SC", "No entry for spectrometer %s in Spectrometer_database.csv"%serial_no])
                return False
            
            self.spec.integration_time_micros(DS.integrationTime)
            self.log_q.put(["debug", "SC", 'Integration time initialised to %d'%DS.integrationTime])                
            self.spec.close()
            return(True)
        except Exception:
            self.errorState = self.Error()
            if self.errorState:
                pass
            else:
                self.log_q.put(["debug", "SC", '---------RETURNING FALSE!!!!!!!!!!!------------']) 
                return(False)          

    def darkSpectrum(self): 
        self.log_q.put(["debug", "SC", '---------Entering Dark Spectrum Module------------'])    
        self.x=True
        self.y=0
        self.initialise()
        self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ DS.spectroSerialNumber])  
        self.log_q.put(["debug", "SC", 'Integration time = %d'%DS.integrationTime])                
        while self.x:
            try: 
                self.spec.integration_time_micros(DS.integrationTime)
                
                i=0
                for i in range(10):

                    self.columnAssign()
                    
                    numpy.savetxt(DS.localRefFilesDirectory +'dark_'+str(i)+'.csv',self.specStack,delimiter=',')
      
                self.spec.close()     
                j=0
                for j in range(1,9):
                    if j<9:
                        data_file0 = numpy.loadtxt(DS.localRefFilesDirectory +'dark_'+str(j)+'.csv', delimiter=',')            
                        D0_wavelength = data_file0[:,0]
                        D0_intensity = data_file0[:,1]
                        j+=1
                        data_file1 = numpy.loadtxt(DS.localRefFilesDirectory +'dark_'+str(j)+'.csv', delimiter=',')            
                        D1_wavelength = data_file1[:,0]
                        D1_intensity = data_file1[:,1]              

                
                        if j==2:
                            dark_value = numpy.add(D0_intensity,D1_intensity)                        
                            self.specStack = numpy.column_stack([D1_wavelength,dark_value])
                                
                        else:
                            dark_value = numpy.add(dark_value,D1_intensity) 
                        if j == 9:
                            dark_value = dark_value/j                     
                            self.specStack = numpy.column_stack([D1_wavelength.round(decimals=2),dark_value.round(decimals=2)])
                       
                                
                with open(DS.localRefFilesDirectory +'dark.csv','wb') as f:
                    f.write(b'Wavelength,Dark_Intensity\n')
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()            
                self.close()
                self.log_q.put(["debug", "SC", '---------Exiting Dark Spectrum Module after succesful capture------------'])                
                return(True)
                
            except Exception as E:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:
                    self.log_q.put(["debug", "SC", '---------RETURNING FALSE!!!!!!!!!!!------------'+str(E)]) 
                    return(False)            
        
    def Reference(self):
        self.log_q.put(["debug", "SC", '---------Entering Reference Spectrum Module------------']) 
        self.x=True
        self.y=0
        while self.x:
            try:
                self.initialise()
                self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ DS.spectroSerialNumber])  
                self.log_q.put(["debug", "SC", 'Integration time = %d'%DS.integrationTime])                
                self.spec.integration_time_micros(DS.integrationTime)
                self.columnAssign()
                with open(DS.localRefFilesDirectory +'reference.csv','wb') as f:
                    f.write(b'Wavelength,Intensity\n')                   
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()            
                self.close()
                self.log_q.put(["debug", "SC", '---------Exiting Reference Spectrum Module after succesful capture------------'])                                
                return(True)
                
            except Exception:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:
                    return(False)

    def Sample(self): 
        self.log_q.put(["debug", "SC", '---------Entering Sample Spectrum Module------------']) 
        self.x=True
        self.y=0
        while self.x:
            try:
                self.initialise()
                self.spec.integration_time_micros(DS.integrationTime)
                self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ DS.spectroSerialNumber])  
                self.log_q.put(["debug", "SC", 'Integration time = %d'%DS.integrationTime])                

                self.columnAssign()
                with open(DS.localRefFilesDirectory +'sample.csv','wb') as f:
                    f.write(b'Wavelength,Intensity\n')
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()            
                self.close()
                self.log_q.put(["debug", "SC", '---------Exiting Sample Spectrum Module after succesful capture------------'])              
                return(True)
                
            except Exception:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:
                    return(False)
                
                
    def row_Start_End(self):
        self.log_q.put(["debug", "SC", '---------Entering into the Module that captures spectrum for row start and row end ------------']) 
        self.row_startEnd = True
        self.x=True
        self.y=0
        while self.x:
            try:
                self.initialise()   
                self.columnAssign()
                with open(DS.localRefFilesDirectory +'dark_raw.csv','wb') as f:
                    f.write(b'Wavelength,Intensity\n')
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()  
                self.log_q.put(["debug", "SC", '---------Exiting the Module after succesful capture------------'])  
                return(True)
                
            except Exception:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:
                    return(False)       

    def referenceAfterRinse(self):
        self.log_q.put(["debug", "SC", '---------Entering into the Module that captures spectrum after RINSE------------']) 
        self.x=True
        self.y=0
        while self.x:
            try:
                self.initialise()
                self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ DS.spectroSerialNumber])  
                self.log_q.put(["debug", "SC", 'Integration time = %d'%DS.integrationTime])                
                self.spec.integration_time_micros(DS.integrationTime)
                self.columnAssign()
                with open(DS.localRefFilesDirectory +'referenceAfterRinse.csv','wb') as f:
                    f.write(b'Wavelength,Intensity\n')                   
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()            
                self.close()
                self.log_q.put(["debug", "SC", '---------Exiting the Module after succesful capture------------'])  
                return(True)
                
            except Exception:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:                 
                    return(False)
                    
    def checkLEDs(self):
        self.log_q.put(["debug", "SC", '--------- Entering into the Module that captures spectrum to check LEDs ------------']) 
        self.x=True
        self.y=0
        while self.x:
            try:
                self.initialise()
                self.log_q.put(["debug", "SC", "Spectrometer Serial number = "+ DS.spectroSerialNumber])  
                self.log_q.put(["debug", "SC", 'Integration time = %d'%DS.integrationTime])                
                self.spec.integration_time_micros(DS.integrationTime)
                self.columnAssign()
                with open(DS.localRefFilesDirectory +'checkLEDs.csv','wb') as f:
                    f.write(b'Wavelength,Intensity\n')                   
                    numpy.savetxt(f,self.specStack.round(decimals=2),delimiter=",", fmt='%f')
                self.x=False
                self.spec.close()            
                self.close()
                self.log_q.put(["debug", "SC", '---------Exiting the Module after succesful capture------------'])  
                return(True)
                
            except Exception:
                self.errorState = self.Error()
                if self.errorState:
                    pass
                else:                 
                    return(False)                    
 
    def get_spectrum(self):
        self.intensities=self.spec.intensities()
        return self.intensities  
        
    def Error(self):
   
        self.y+=1
        self.log_q.put(["debug", "SC",'Y counter:'+str(self.y)])
        
        if self.y==5:
          
            LED_Driver.LED_OFF(self.log_q)
            self.x=False
            DS.logout_cause_value = 6
            self.log_q.put(["debug", "SC", '---------Exiting the Module due to capture FAIL------------']) 
            # self.spec.close() 
            self.close()
            return(False)
        else:  
            self.log_q.put(["debug", "SC", '---------Retrying------------']) 
            time.sleep(2)
            return(True)
 

