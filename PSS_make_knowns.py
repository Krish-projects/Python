# -*- coding: utf-8 -*-
"""
Created on Thu 27 Dec 14:09:18 2018

@author: markc, changes by: Radha Krishnan N
"""
import datetime

# print ("PSS_make_knowns.py first call startin at : startupTime",datetime.datetime.now())


import os
import pandas as pd
import abs_analysis as ab

class makeKnown():


    def dark_from_file(self,filename):
        rawdf = pd.read_csv(filename)
        
        if len(rawdf['Dark_Intensity']) != 110:
            print('Dark length error in ' + filename + 'length is: ',len(rawdf['Dark_Intensity']))
        return rawdf['Dark_Intensity']

    def intensity_from_file(self,filename):
        rawdf = pd.read_csv(filename)
        if len(rawdf['Intensity']) != 110:
            print('Intensity length error in ' + filename + 'length is: ',len(rawdf['Ethanol_Intensity']))
        return rawdf['Intensity']

    def filesGenerate(self):
        os.chdir("/home/debian/PSS/CSV_files" )
        os.listdir('.')

        #get the wavelengths
        rawdf = pd.read_csv('dark.csv', index_col=0)
        wavelengths = rawdf.index.tolist()
        wavelengths = ab.init_wavelengths(wavelengths)

        #initialise dark and reference
        dark = self.dark_from_file('dark.csv')
        ab.set_dark(dark.tolist())
        ref = self.intensity_from_file('reference.csv')
        ab.set_ref(ref.tolist())

        # generate the known files
        known_perm = ab.generate_known('perm', 0.1245, self.intensity_from_file('Permethrin.csv').tolist())

        known_perm.to_csv('known_perm.csv', index = True, header = True, index_label = 'wavelength')

        known_DOP = ab.generate_known('DOP', 0.256, self.intensity_from_file('DOP.csv').tolist())

        known_DOP.to_csv('known_DOP.csv', index = True, header = True, index_label = 'wavelength')

    def Error(self):
        QMessageBox.about(self, "Calculation Error" ,"LEDs may not be working correctly")     
        self.close()