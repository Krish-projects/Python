# PSS LED Board Driver
''' Controls whether LED readings are taken or not
    if board temp is in target range then sets mp_LED_ready event
    if this event is set readings can be made. When temp is outside target range
    mp_LED_ready event is cleared and LEDs won't be used
    Temperature is monitored by hardware. Heater is turned on
    when app is started and chip controls temp using tOts (over temperature)
    and tHys (hysteresis) parameters which are set during init
    Heater is turned OFF on exit
    '''

# Library Import
import os
import sys
import time
import datetime



import Adafruit_GPIO.I2C as I2C
import Adafruit_BBIO.PWM as PWM
import Adafruit_BBIO.GPIO as GPIO
import deviceStatus as DS 

import Sampler

GPIO.setup("P9_16", GPIO.OUT) ##Heater

# import pss_log




###############   ADC Module  ################################################ 
ADC= I2C.get_i2c_device(address=0x6E,busnum=2)
ADC_CONFIG = 0x98 ##channel 1, one-shot conversion, 16 bit, PGAx1
            
def checkBit(byte, bit):
        # internal method for reading the value of a single bit within a
        # byte
    if byte & (1 << bit):
        return 1
    else:
        return 0        
    
def get_LED_volts(channel, log_q):
    ADC.write8(ADC_CONFIG, value=0)    
    config = ADC_CONFIG
    if channel == 1:
        config = 0x98
    if channel == 2:
        config = 0xB8
    if channel == 3:
        config = 0xD8
    if channel == 4:
        config = 0xF8

    while True:
        adcValue = ADC.readList(register = config, length=3)
        a = adcValue[0]                     
        b = adcValue[1]                       
        c = adcValue[2]
                       
        if checkBit(c, 7) == 0:
            break        
   
    dataValue= (a<<8)|b

    LSB = (2*2.048)/pow(2,16)   #formula:LSB = (2*Vref)/2^N N=16
    value = round((dataValue*LSB) ,3)
    # log_q.put(["info", "UV","---------------  Value received = %f ---------------"%value])
    return value
    
############################################################################    

###################   DAC Module     #######################################    

DAC= I2C.get_i2c_device(address=0x60,busnum=2)
REG_WRITEALLDAC    = 0x50    
def set_LED_drive(percentage1,percentage2,percentage3,percentage4, log_q):
    """
    Percentage brightness values are converted to 12 bit
    12 bit data is converted into 16 bit by shifting right by 8 bits AND FF
    Parameters are presented in wavelength order but have to be written in
    order governed by LED location D1 - 285, D2 - 275, D3 - 255, D4 - 295
    """

    D1_brightness = round((percentage1/100)*4095)
    D2_brightness = round((percentage2/100)*4095)  
    D3_brightness = round((percentage3/100)*4095)
    D4_brightness = round((percentage4/100)*4095)    
    bright_bin = [(D1_brightness>>8)&0xFF,D1_brightness&0xFF, (D2_brightness>>8)&0xFF,D2_brightness&0xFF,
                    (D3_brightness>>8)&0xFF,D3_brightness&0xFF, (D4_brightness>>8)&0xFF,D4_brightness&0xFF]
    log_q.put(["info", "UV","Brightness values: 255nm = %d , 275nm = %d, 285nm = %d , 295nm = %d" %(percentage3, percentage2, percentage1, percentage4)])
    DAC.writeList(REG_WRITEALLDAC,bright_bin)
    
    # This section commented out. Uncomment to access LED voltages
    # ###Get the voltage across each channel###
    # channel_1_V = 0
    # channel_2_V = 0
    # channel_3_V = 0
    # channel_4_V = 0    
    # cycles=10
    # for i in range(cycles):
        # getTemp('led',log_q)
        # channel_1_V += get_LED_volts(1,log_q)
        # channel_2_V += get_LED_volts(2,log_q)
        # channel_3_V += get_LED_volts(3,log_q)
        # channel_4_V += get_LED_volts(4,log_q)  
        # # log_q.put(["info", "UV","Voltage values: Channel_1 = %f , Channel_2 = %f, Channel_3 = %f , Channel_4 = %f" %(channel_1_V, channel_2_V, channel_3_V, channel_4_V)])
        # time.sleep(0.1)
        
    # log_q.put(["info", "UV","Average Voltage values: Channel_1 = %f , Channel_2 = %f, Channel_3 = %f , Channel_4 = %f" %(channel_1_V/cycles, channel_2_V/cycles, channel_3_V/cycles, channel_4_V/cycles)])
#################################################################################

    
#################  Temperature Sensor  ###########################################   
ledTemp= I2C.get_i2c_device(address=0x4F,busnum=2) 
ambientTemp= I2C.get_i2c_device(address=0x4F,busnum=1)
REG_temp_cutOFF = 0x03
cutOFF_temp = [0x32,0x00] ### 50C for example
def set_tempcutOFF(cutoffTemp, log_q):
    '''
    Set the hardware temperature cuttoff
    Heater is turned on, and left on and we rely on the hardware
    cutoff to control the temperature.
    OTS (over temperature) and HYS (hysteresis) are set to the same 
    value to limit the temperature swing
    '''
    temp_cutOFF = ledTemp.readU16(register=0x03)
    print("Default tOts = ", str(temp_cutOFF))
    ledTemp.writeList(REG_temp_cutOFF, [cutoffTemp,0])
    tOts = ledTemp.readU16(register=0x03)
    print("tOts = ", str(tOts))
    tHys = ledTemp.readU16(register=0x02)
    print("Default tHys = ", str(tHys))
    ledTemp.writeList(0x02, [cutoffTemp-0,0])
    tHys = ledTemp.readU16(register=0x02)
    print("tHys = ", str(tHys))
    tIdle = ledTemp.readU16(register=0x04)
    print("tIdle = "+str(tIdle))
    log_q.put(["info", "UV","Set temp cutoff to %d, %d"%(cutoffTemp,cutoffTemp)])

def getTemp(device, log_q):
    """
    Read the temperature register (address=0x00)
    """
    """
    Read the temperature register (address=0x00)
    If device is 'ambient' get the temperature from the Analyser pcb otherwise
    get the temperature of the LED board
    """
    if device == 'ambient':
        deviceSpec = ambientTemp
    else:
        deviceSpec = ledTemp
    temperature=deviceSpec.readList(register=0x00,length = 2)
    a = temperature[0]
    b = temperature[1]    
    value = a<<8|b  ##concatenate a and b
    value = value>>5  ##discard last 5 bits as they are useless
    # log_q.put(["info", "UV","---------------  Value = %f deg C ---------------" %value])
    temp=int(value)*0.125
    # if count == 10:
    # log_q.put(["info", "UV","---------------  Board Temperature = %s deg C ---------------" %str(round(temp,3))])

    return temp 
##################################################################################    

###############################  Heater Module  ##################################
    
def set_heater_PWM(cmd, log_q):
    """
    This function turns ON/OFF the heater. The frequency should be in the order of 1000. The duty cycle sets the amount of heat output.
    """
    if cmd == "HeaterON":
        GPIO.output("P9_16", GPIO.HIGH)##Enabling Heater
        log_q.put(["info", "UV","-----  Heater ON  -----"])
    else:
        GPIO.output("P9_16", GPIO.LOW)##Disabling Heater
        log_q.put(["info", "UV","-----  Heater OFF  -----"])
##################################################################################

 
######################  Functions associated with Analyser calls  ###################### 


def LED_heaterON(log_q):
    set_heater_PWM("HeaterON", log_q)
    # log_q.put(["info", "UV","Heater On"])
    return 

def LED_heaterOFF(log_q):
    set_heater_PWM("HeaterOFF", log_q)
    # log_q.put(["info", "UV","Heater Off"])
    return
    
def LED_ON(log_q,LED_check):
    """
    Returns 1 - if LEDs turned ON
    Returns 2 - if LED board error
    Returns 3 - if Sampler is not connected
    """
    #wait for LEDs to reach target temperature then turn them on
    # LED_Check = LED_check
    log_q.put(["info", "UV","LED_Check = %s )"%str(LED_check)])
    startTemp = getTemp('led',log_q)
    log_q.put(["info", "UV","Temp is %f)"%startTemp])
    if startTemp>=DS.targetTemp-1 and startTemp<DS.targetTemp+1: #in target range
        log_q.put(["info", "UV","LEDs on target temp. Checking sampler connection and temperature rise"])
    else:
        log_q.put(["info", "UV","Waiting for LED target temp"])
    for count in range (1000): # allow about 100 secs for temp to reach target
        temp = getTemp('led',log_q)
        if temp>=DS.targetTemp-1 and temp<DS.targetTemp+1: #in target range
            if LED_check:
                set_LED_drive(DS.brightness285,DS.brightness275,DS.brightness255,DS.brightness295, log_q)
                # set_LED_drive(0,27,0,0, log_q)
                # now wait until LEDs have been turned on (LED_onTime > 0) and been on for ledSettleTime
                time.sleep(DS.ledSettleTime)
                # self.get_LED_volts(1,log_q)
                return 1
            else:
                if samplerConnectionCheck(log_q):
                    log_q.put(["info", "UV","Temp target (count = %d reached turning on LEDs)"%count])
                    log_q.put(["info", "UV","Setting LEDs to: %d %d %d %d"%(DS.brightness255,DS.brightness275,DS.brightness285,DS.brightness295)])            
                    set_LED_drive(DS.brightness285,DS.brightness275,DS.brightness255,DS.brightness295, log_q)
                    # now wait until LEDs have been turned on (LED_onTime > 0) and been on for ledSettleTime
                    # set_LED_drive(0,0,0,90, log_q)
                    time.sleep(DS.ledSettleTime)
                    return 1
                else:
                    return 3
                
        elif count == 100 and not getTemp('led',log_q) > startTemp and startTemp < DS.targetTemp-1:
            # here if temp not rising when it should be
            log_q.put(["info", "UV","LED board temp not rising after %d secs"%int(count/10)])
            return 2
        time.sleep(0.1) # wait a little bit before trying again
    log_q.put(["info", "UV","LED board target temp not reached after %d secs"%int(count/10)])
    return 2 # retries expired, didn't reach target
    
def LED_OFF(log_q):
    log_q.put(["info", "UV","LEDs OFF"])
    set_LED_drive(0,0,0,0, log_q)
    return
   
            
def samplerConnectionCheck(log_q):
    """
    Checks whether the sampler is connected to the analyser
    """

    status = Sampler.S_cmd_Get_status()
    
    log_q.put(["debug","UV","Checking SAMPLER CONNECTION before TURNING ON LEDs" ])            
    
    if status['status'] == 'Disconnected':
        log_q.put(["debug","UV","--------------  SAMPLER IS DISCONNECTED  ----------------------"])
        return False #### Sampler is disconnected and a popup will be displauyed in the measurement file.
                        
    else:
        log_q.put(["debug","UV","--------------  SAMPLER IS CONNECTED. SO TURNING ON LEDs  ----------------------"])
        return True 