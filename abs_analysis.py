# -*- coding: utf-8 -*-
"""
Created on Thu Dec 20 14:55:52 2018

@author: markc

Copyright Atamo Pty Ltd, 2018

Mod 3/10/19 added weights to residual/error/confidence calculation

"""
import datetime
# print ("abs_analysis.py first call startin at : startupTime",datetime.datetime.now())

from scipy.optimize import least_squares
import numpy as np
import pandas as pd
import numpy.polynomial.polynomial as poly
import deviceStatus as DS


def init_wavelengths(wavelengths):
    """Initialise the set of wavelengths in the measurements.
       Must be called before any other functions.
    """
    global wave_index, npoints, known_abs, known_conc
    wave_index=[]
    for wave in wavelengths:
        wave_index = wave_index + [(round(float(wave * 10)) /10 )]
    npoints = len(wave_index)
    known_abs = pd.DataFrame(index = wave_index)
    known_conc = dict()
    return(wave_index)
   
def abs_fit_error(coef, wavelengths, target, known_abs):
    residual = target
    index = 0
    for known_name in known_abs.columns:
        residual = residual - coef[index] * known_abs[known_name]
        index = index + 1
    residual = residual - poly.polyval(wavelengths,coef[len(known_abs.columns):])
    return(residual)

def get_rms_pc_error(residual, base):
    frac = residual / base
    zero_spots = np.where(base == 0)[0]
    frac[zero_spots] = 0
    weight = resultdf['perm'] / np.amax(resultdf['perm'])
    # np.savetxt("frac.txt",frac)
    # np.savetxt("weight.txt",weight)
    # np.savetxt("resultdf.txt",resultdf['perm'])
    return(100. * np.sqrt(np.average(np.square(frac),weights = weight)))
    
def set_dark(dark_signal):
    """Set the measured dark current, passed as a list,
       to be subtracted from measurements
    """
    global dark
    if (len(dark_signal) == npoints):
        dark = pd.Series(dark_signal, index = wave_index)
    else:
        print("Error: abs_analysis: incorrect length of dark signal")

def set_ref(reference_signal):
    """Set the reference signal, passed as a list,
       dark not yet subtracted.
    """
    global ref
    if (len(reference_signal) == npoints):
        ref = pd.Series(reference_signal, index = wave_index) - dark
    else:
        print("Error: abs_analysis: incorrect length of reference signal")
        
def get_ref():
    """Return the actual reference spectrum after dark subtraction"""
    return(pd.tolist(ref))
    
def generate_known(known_name, concentration, measurement):
    """Used only in the lab, to generate a known absorbance spectrum from a measurement.
       known_name - string
       concentration - float
       measurement - list
    """
    

    raw = pd.Series(measurement, index = wave_index) - dark
    abs1 = -np.log10(raw/ref)
    if (np.nanmin(abs1) < 0 or abs1.isna):
        print("warning - calculated known absorbance less than zero. Clipping to zero")
        DS.log_q.put(["warning","UI","calculated known absorbance less than zero. Clipping to zero"])

        abs1 = np.clip(abs1, 0, a_max=None )
    conc_part = pd.Series([concentration], index = ['conc'])
    known_data = pd.concat([conc_part, abs1])
    known_data.name = known_name
    return(known_data)


def set_known(known_data):
    """Set a known absorbance curve and concentration from the named pandas series passed
       as "known_data".
       Note that the known absorbance spectrum is stored data from lab measurements,
       and the dark signal must already have been subtracted from the data.
       The name of the series is the name of the chemical.
       The first entry is the known concentration, index "conc".
       Absorbance measurements are [1:], indexed by wavelength.
    """
    global known_abs, known_conc
    name = known_data.name
    concentration = known_data.iloc[0]
    known_wavelengths = known_data.index[1:].astype(np.float)
    known_wavelengths = known_wavelengths.tolist()
    
    interp_known = np.interp(wave_index, known_wavelengths, known_data[1:])
    known_series = pd.Series(interp_known, index = wave_index)
    
    known_abs[name] = known_series
    known_conc[name] = concentration
    print("successfully loaded known curve " + name + " concentration " + str(concentration) + " mg/ml")
#    if (known_wavelengths == wave_index):
#        known_abs[name] = known_data[1:]
#        known_conc[name] = concentration
#        print("successfully loaded known curve " + name + " concentration " + str(concentration) + " mg/ml")
#    else:
#        print("Error: abs_analysis: incorrect wavelengths in known curve " + name)
#        print("curve wavelengths:\n", known_wavelengths)
#        print("initialised wavelengths:\n", wave_index)
    
def get_known(name):
    """Return the concentration and named known curve"""
    return(known_conc[name], known_abs[name][1:])

def analyse_sample(measurement):
    """Analyse the measured sample, passed as a list.
       Dark should not have been subtracted.
       Returns:
           component_concentrations (a dict)
           max_error (%max error in curve fit)
           confidence (%)
    """
    # sig_error= QtCore.pyqtSignal()
    global sample, npoints, wavelengths, known_abs, resultdf
    component_conc = dict()
    if (len(measurement) == npoints):
        sample = pd.Series(measurement, index = wave_index) - dark
        sample = np.clip(sample, 1, a_max=None )
        sample = -np.log10(sample/ref)
        # check deleted(commented) to allow for a broadly contaminated reference
        #if (np.nanmin(sample) < 0):
        #    print("warning - calculated sample absorbance less than zero. Clipping to zero")
        #    DS.log_q.put(["warning","UI","calculated sample absorbance less than zero. Clipping to zero"])
        #    sample = np.nan_to_num(sample)
        #    sample = np.clip(sample, 0, a_max=None )
    else:
        print("Error: abs_analysis: incorrect length of measured signal")
        return
    sample = pd.Series(sample, index = wave_index)
    narrowband = True
	
    if narrowband:
        #start_wavelength = 260
        end_wavelength = 285
        start_wavelength = 255
        #end_wavelength = 290
        first_row = 0
        last_row = 0
        # wavelengths are in ascending order
        for wlength in wave_index:
            if (wlength <= start_wavelength):
                first_row = wlength
            if (wlength >= end_wavelength) and (last_row == 0):
               last_row = wlength
        print('wavelengths of interest: ', first_row, ' - ', last_row, ' nm')
        # drop unwanted wavelengths
        first_pos = known_abs.index.get_loc(first_row, method='nearest')
        known_abs.drop(known_abs.index[0:first_pos],inplace=True)
        last_pos = known_abs.index.get_loc(last_row, method='nearest')
        known_abs.drop(known_abs.index[last_pos+1:len(known_abs.index)],inplace=True)
        sample.drop(sample.index[0:first_pos],inplace=True)
        sample.drop(sample.index[last_pos+1:len(sample.index)],inplace=True)
        wavelengths = sample.index
        npoints = len(wavelengths)
        #print('sizes: ', n_wavelengths, len(dfcut), len(perm_ref), len(phthalate_ref))
        #myplot(absdf,'narrowband filtered abs',2250)

    resultdf = pd.DataFrame(index = wavelengths)
    degree = 2
    # number of known species
    n_known = len(known_abs.columns)
    bounds=([0] * n_known + [0] + [-np.inf] +[0],np.inf)
    coef_init = np.array([0.] * (n_known + degree + 1))
    coef_init[0] = 1.
    coef_init[-1] = 1.
    ls_result = least_squares(abs_fit_error,coef_init, \
                           args=(wavelengths, sample, known_abs), \
                           bounds=bounds)
    polyfix = poly.polyval(wavelengths,ls_result.x[n_known:])
    resultdf['fit'] = polyfix
    index = 0
    for known_name in known_abs.columns:
        resultdf['fit'] = ls_result.x[index] * known_abs[known_name] + resultdf['fit']
        resultdf[known_name] = ls_result.x[index] * known_abs[known_name]
        component_conc[known_name] = ls_result.x[index] * known_conc[known_name]
        index = index + 1
#        if(col == 'Per:DOP - 1:1'):
#            dfbroken['perm'] = result.x[0] * perm_ref
#            dfbroken['phth'] = result.x[1] * DOP_ref
#            dfbroken['poly'] = poly.polyval(wavelengths,result.x[2:])
#            dfbroken['orig'] = dfmeas[col]
#            dfbroken['fit'] = dffit[col]
    resultdf['residual'] = ls_result.fun
    resultdf['poly'] = polyfix
    resultdf['actual'] = sample
    
    rms_pc_residual = get_rms_pc_error(ls_result.fun, sample)
    rms_pc_error = get_rms_pc_error(ls_result.fun, resultdf['perm'])

    #print("resid, err: ", rms_pc_residual, rms_pc_error)    
    max_error = round(rms_pc_error, 1)
    confidence = round(100 - 2 * rms_pc_residual)

    #critical region for accurate results
    critical_region = sample
    start_wavelength = 255
    end_wavelength = 285
    first_row = 0
    last_row = 0
    # wavelengths are in ascending order
    for wlength in wave_index:
        if (wlength <= start_wavelength):
            first_row = wlength
        if (wlength >= end_wavelength) and (last_row == 0):
           last_row = wlength
    #print('wavelengths of interest: ', first_row, ' - ', last_row, ' nm')
    # drop unwanted wavelengths
    first_pos = known_abs.index.get_loc(first_row, method='nearest')
    last_pos = known_abs.index.get_loc(last_row, method='nearest')
    critical_region.drop(sample.index[0:first_pos],inplace=True)
    critical_region.drop(sample.index[last_pos+1:len(sample.index)],inplace=True)
    av_abs = np.average(critical_region)

    coeff = ls_result.x
    print(coeff)
    status = ls_result.status
    if(max_error > 100):
        max_error = 100
    if(confidence < 0):
        confidence = 0
    if(ls_result.status <= 0):
        print('fit error', ls_result.status)
        print('fit coefficients:\n', ls_result.x)
    #return(component_conc, max_error, confidence, av_abs, resultdf)
    return(component_conc, max_error, confidence, av_abs)

