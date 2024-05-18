
import numpy as np
import os
import sys 
import datetime


# print ("CSV_Files_Compare.py first call startin at : startupTime",datetime.datetime.now())

import deviceStatus as DS


class Compare():
    def __init__(self, log_q, calibrate,LED_Check):
        self.log_q = log_q    
        self.values=[260.0, 270.0, 282.0]
        self.factory_val=[]
        self.measured_val=[]
        self.refAfterRinse_val=[]
        self.variance = []
        self.measured_val_WL = []
        self.measured_val_intensity = []
        self.calibrate = calibrate
        self.LED_Check = LED_Check
        

    def measuredValues(self):
        """
        Checks the values for 260nm, 270nm and 282nm in reference.csv or referenceafterrinse.csv 
        """
        if self.LED_Check:
            measured = np.genfromtxt(DS.localRefFilesDirectory + 'checkLEDs.csv', delimiter=',', skip_header = 1)
            
            self.measured_val_WL = DS.factory_val_WL
            
            self.log_q.put(["debug", "FC", 'self.measured_val_WL = ' + str(self.measured_val_WL)])
            for max_val in range(len(self.measured_val_WL)):
                for i, row in enumerate(measured):
                    for j, column in enumerate(row):
                    
                        
                        if self.measured_val_WL[max_val] == column:
                            self.measured_val_intensity.append( row[1])           
            self.log_q.put(["debug", "FC", 'self.measured_val_intensity = ' + str(self.measured_val_intensity)])
        
        else:
            if self.calibrate:
                measured = np.genfromtxt(DS.localRefFilesDirectory + 'reference.csv', delimiter=',', skip_header = 1)
            else:
                measured = np.genfromtxt(DS.localRefFilesDirectory + 'referenceAfterRinse.csv', delimiter=',', skip_header = 1)

            for v in self.values:
                for x in range(0,46):
                    x=x*.01
                    value = v+x
                    for i, row in enumerate(measured):
                        for j, column in enumerate(row):
                            if value == column:
                                self.measured_val.append( row[1])
                                

            if self.calibrate:
                self.log_q.put(["debug", "FC", 'Measured intensities during calibration, 260nm, 270nm, 280nm = ' + str(self.measured_val)])
            else:
                self.log_q.put(["debug", "FC", 'Measured intensities after rinsing, 260nm, 270nm, 280nm = ' + str(self.measured_val)])
            
    


    def factoryValues(self):
        """
        Checks the values for 260nm, 270nm and 282nm in Ethanol reference.csv
        """    
        factory = np.genfromtxt(DS.refFilesDirectory + DS.spectroEthanolReference, delimiter=',', skip_header = 1)
        ER_wavelength = factory[:,0]
        ER_intensity = factory[:,1]
        for v in self.values:
            for x in range(0,46):
                x=x*.01
                value = v+x
                for i, row in enumerate(factory):
                    for j, column in enumerate(row):
                        if value == round(column, 2): # compare against ref wavelength to 2 places
                            self.factory_val.append( row[1])
                            
        print(self.factory_val)
        self.log_q.put(["debug", "FC", 'Factory measured intensities, 260nm, 270nm, 282nm = ' + str(self.factory_val) ])


    def variationCalculation(self):
        """
        Calculates the variance for 260nm, 270nm and 282nm
        """       
        true=0
        
        # self.factoryValues()
        

        self.measuredValues()

        if self.LED_Check:
            for i in range(len(self.measured_val_WL)):
                self.log_q.put(["debug", "FC", 'DS.factory_val_intensity[i]= %s, self.measured_val_intensity[i] = %s' %( str(DS.factory_val_WL[i]),str(self.measured_val_intensity[i]))])
                difference = np.subtract(DS.factory_val_intensity[i], self.measured_val_intensity[i])
                variation = np.divide(difference,DS.factory_val_intensity[i]) 
                variation = variation*100 
                self.variance.append(variation)  
            self.log_q.put(["debug", "FC", 'Variation of individual , %s nm = %s' %( str(DS.factory_val_WL),str(np.round(self.variance,2)))])
            return (np.round(self.variance,2))
        else:
            self.factoryValues()
            for i in range(3):
                difference = np.subtract(self.factory_val[i], self.measured_val[i])
                self.log_q.put(["debug", "FC", 'Ref value %d: %d'%(i,self.factory_val[i])])
                self.log_q.put(["debug", "FC", 'Measured value %d: %d'%(i,self.measured_val[i])])
                variation = np.divide(difference,self.factory_val[i]) 
                variation = variation*100 
                self.variance.append(variation)
            min_var = self.variance[0]-2.5
            max_var = self.variance[0]+2.5
            
            self.log_q.put(["debug", "FC", 'Variation of individual , 260nm, 270nm, 282nm = = ' + str(np.round(self.variance,2))])
            self.log_q.put(["debug", "FC", 'Minimum variation = ' + str(min_var) ])
            self.log_q.put(["debug", "FC", 'Maximum variation = ' + str(max_var) ])

            
            for i in range(3):
                if (np.round(self.variance[i],0)<=DS.referenceThreshold_positive and np.round(self.variance[i],0)>=DS.referenceThreshold_negative):
                    true += 1
                    self.log_q.put(["debug", "FC", 'Within limits' ])              
                    
                else:
                    self.log_q.put(["debug", "FC", 'Outside limits' ])
               
            if true == 3:
                self.log_q.put(["debug", "FC", 'In CSV compare file, Calibration success' ])
                return(True, np.round(self.variance,2), min_var, max_var)
            else:
                self.log_q.put(["debug", "FC", 'In CSV compare file, Calibration Failed' ])
                return(False, np.round(self.variance,2), min_var, max_var)             
  