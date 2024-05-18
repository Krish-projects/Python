# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 14:09:18 2018

@author: markc
"""
import datetime
import os


import pandas as pd

import abs_analysis as ab
from PSS_make_knowns import makeKnown
import deviceStatus as DS

import sys




class dataAnalyse():
    def __init__(self, log_q):
        super (dataAnalyse, self).__init__()
        self.log_q = log_q

    def intensity_from_file(self,filename):
        rawdf = pd.read_csv(filename)
        if len(rawdf['Intensity']) != 110:
            print('Intensity length error in ' + filename + 'length is: ',len(rawdf['Intensity']))
        return rawdf['Intensity']

    def dark_from_file(self,filename):
        rawdf = pd.read_csv(filename)
        if len(rawdf['Dark_Intensity']) != 110:
            print('Dark length error in ' + filename + 'length is: ',len(rawdf['Dark_Intensity']))
        return rawdf['Dark_Intensity']





    def results(self):
        """
        Reads the data and calculates the concentration of permethrin 
        """


        #get the wavelengths
        rawdf = pd.read_csv(DS.localRefFilesDirectory + 'dark.csv', index_col=0)

        wavelengths = rawdf.index.tolist()
        wavelengths = ab.init_wavelengths(wavelengths)
        #Generate known files for permethrin and DOP
        # self.makeknowns = makeKnown()
        # self.makeknowns.filesGenerate()
        #get the known curves
        
        rawdf = pd.read_csv(DS.refFilesDirectory + 'known_perm.csv', header = 0, index_col =0)
        rawser = pd.Series(rawdf[rawdf.columns[0]], name = rawdf.columns[0])
        ab.set_known(rawser)

        
        rawdf = pd.read_csv(DS.refFilesDirectory + 'known_DOP.csv', header = 0, index_col =0)
        rawser = pd.Series(rawdf[rawdf.columns[0]], name = rawdf.columns[0])
        ab.set_known(rawser)

        #initialise dark and reference
        
        dark = self.dark_from_file(DS.localRefFilesDirectory + 'dark.csv')
        ab.set_dark(dark.tolist())
        
        ref = self.intensity_from_file(DS.localRefFilesDirectory + 'reference.csv')
        ab.set_ref(ref.tolist())

        #analyse a sample
        
        sample = self.intensity_from_file(DS.localRefFilesDirectory + 'sample.csv')
        (conc, error, confidence, av_abs) = ab.analyse_sample(sample.tolist())
#### Concentration conversion from mg/ml to mg/m2
####    conc(perm mg/m2) = conc(perm mg/ml)*(volume/Area of sampler pad/1000)*1000
####    Sampelr pad area = pi*d^2/4   -----d = 0.058 m
####    volume = DS.actual rev*0.0161875
####    1 rev of pump dispenses 0.0161875 ml of solvent
        totalSolventVolume = DS.postSamplingSolventVolume
        # calibrationFactor = float(DS.calibrationFactor)
        self.log_q.put(["info","UI","DS.postSamplingSolventVolume = %s, totalSolventVolume = %s"%(str(DS.postSamplingSolventVolume), str(totalSolventVolume))])
        self.log_q.put(["info","UI","DS.calibrationFactor = %s"%(str(DS.calibrationFactor))])
        self.log_q.put(["info","UI","Permethrin : "+str(conc['perm'])+" mg/ml, DOP : "+ str(conc['DOP'])])        
        conc['perm'] = (conc['perm']*(((totalSolventVolume)/(3.14*(0.058*0.058)/4)/1000))*1000/float(DS.calibrationFactor))
        conc['DOP'] = (conc['DOP']*(((totalSolventVolume)/(3.14*(0.058*0.058)/4)/1000))*1000/float(DS.calibrationFactor))	
        self.log_q.put(["info","UI","Permethrin : "+str(round(conc['perm'],3))+" mg/m2, DOP : "+ str(conc['DOP'])+" Confidence : "+ str(round(confidence))+" Absorbance : "+ str(round(av_abs,3))])   
        perm = round(conc['perm'],3)
        dop = round(conc['DOP'], 3)
        conf = round(confidence)
        abs = round(av_abs,3)
        return(perm, conf, error, abs)
        
