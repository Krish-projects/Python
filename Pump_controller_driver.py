## PSS Pump Controller Driver
#########################################################################################################################################################
# Pump_controller_driver.py: interface module to communicate with the pump to dispense precise amount of ethanol
# Created by: Radha Krishnan Nachimuthu
# Date: 21/01/2020
# Function:
#   This module provides a simple interface to the PSS software to communicate with the pump to dispense precise amount of ethanol.
#   Ethanol dispense is happens during the following processes:
#   1. Calibration
#   2. Wet the sampler pad for sampling
#   3. Extract the sample from the sampler pad
#   4. Rinse
#
#
#   Usage: To be updated


# Library Import
import datetime
import os
import pyvesc
import serial
import threading
import time

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.UART as UART
import Adafruit_BBIO.ADC as ADC
import multiprocessing as mp

from pyvesc import GetValues, SetRPM, SetCurrent, SetCurrentBrake, Alive

GPIO.setup("P8_19", GPIO.OUT) ##Power pin for pump controller

import deviceStatus as DS 

# Set your serial port here (either /dev/ttyX or COMX)
UART.setup("UART2")
serialport = '/dev/ttyO2'
BR = 115200
serial_tOut = 0.05
g_s_timeout = 2
Pump_RPM = 4000
PC_resp_len = 78
PC_resp_Tout = 8
PC_stopping_RPM = 500
PC_BrakeCurrent = 1800
counter = 0

rsense=0.01
event_starting_time = time.perf_counter() 

def set_pump_priority(log_q, nice_value=-18):
    """
    Setup Pump controller driver process to run at higher priority, by issuing the command "renice -18 -p PID"
    """
    pid=os.getpid()
    os.system("renice -18 -p %d"%pid)                   #setup radio_tx_loop to the highest priority

    log_q.put(['warning',"PC","Set Pump controller :%d nice to -18"%pid]) 
    
 
def run_pump(cmd, mp_log_q, mp_pumpstatus):
    """
    Run the pump 
    """
    global counter
    global PC_resp_Tout
    
    GPIO.setup("P9_25", GPIO.OUT) ##Dispense valve (valve 3 in schematic)
    GPIO.output("P9_25", GPIO.HIGH)##Turn on dispense valve    
    rx_buffer = b''
    data = b''
    ADC.setup()

    
    if cmd == "Wet_Pad":
        # count = 30
        count = int(DS.sampleSquirtVolume/DS.pumpDispense_per_rev)
       
    
    elif cmd == "Sample_Extract":
        # count = 55
        count = int((DS.postSamplingSolventVolume/3)/DS.pumpDispense_per_rev)
    
    elif cmd == "Calibrate":
        # count = 450
        count = int(DS.calibrateVolume/DS.pumpDispense_per_rev)

    elif cmd == "Rinse":
        # count = 140
        count = int(DS.sampleRinseSquirtVolume/DS.pumpDispense_per_rev)

    elif cmd == "bagChange":
        # count = 320
        count = int(DS.resetSolventBagVolume/DS.pumpDispense_per_rev)
        
    else:
        count = 0
        
    if (count == 0):
        exit()
  
    mp_log_q.put(["info", "PC","Command is %s and the count value is %d"%(cmd,count)])
    RPM = pyvesc.encode(SetRPM(Pump_RPM))
    mp_pumpstatus.rev_tgt = count
    # mp_log_q.put(["info", "PC","Command is %s" %(RPM)])
    # pump.write(RPM)
    target_tachometerRev = 0
    start_time = time.perf_counter()
    cmd_received = True
    
    connection_retry = 0
    response_counter = 0
    ADCList = []
    # counter = 0
    while cmd_received:
        pump.write(RPM)
        rx_buffer = b''
        pump.write(pyvesc.encode_request(Alive))
        command = pyvesc.encode_request(GetValues)
        pump.write(command)
        data = pump.read(PC_resp_len)   
        rx_buffer += data
        
        data = b''
        # start_time = time.perf_counter()
        
        if len(rx_buffer)>=PC_resp_len:
            # mp_log_q.put(["error", "PC","Pump data buffer: %s"%str(rx_buffer)]) #include for debug
            mp_pumpstatus.pump_status = "Connected" 
            (response, consumed) = pyvesc.decode(rx_buffer)
            # if counter <= 2:
                # # PC_resp_Tout = 8
                # response = None
                # # counter = 0
            # counter+=1
            # # mp_log_q.put(["error", "PC","PC_resp_Tout: %s"%str(PC_resp_Tout)]) #include for debug
            # mp_log_q.put(["error", "PC","counter: %s"%str(counter)])
            # mp_log_q.put(["info", "PC","response is "+str(response)+", Consumed is "+str(consumed)])
            if response != None:
                # mp_log_q.put(["info", "PC","response.rpm is "+str(response.rpm)+", response.tachometer is "+str(response.tachometer)])
                rx_buffer = rx_buffer[consumed:]
                # mp_log_q.put(["info", "PC","response is "+str(response)+", Consumed is "+str(consumed)])
                
                
                try:
                    if (target_tachometerRev == 0):
                        target_tachometerRev = response.tachometer + count
                        mp_log_q.put(["info", "PC","target_tachometerRev is %d"%target_tachometerRev])
                       
                        
                    else:
                        mp_pumpstatus.RPM = response.rpm
                        mp_pumpstatus.pump_rotate_state = 'A'
                        # mp_log_q.put(["info", "PC","PC status values WHILE RUNNING are %s"%str(mp_pumpstatus)])

                        stop_time = time.perf_counter()
                        # mp_log_q.put(["info", "PC","start_time = %s, stop_time = %s, stop_time-start_time = %s"%(str(start_time),str(stop_time),str(stop_time-start_time))])
                        # mp_log_q.put(["info", "PC","time so far = %s"%(str(round(stop_time-start_time,4)))])
                        value=ADC.read("P9_35") #1.0 means 1.8V
                        # mp_log_q.put(["info", "PC","Value= "+str(value)])
                        # voltage=value*1.8
                        # mp_log_q.put(["info", "PC","Voltage= "+ str(voltage)])
                        # current=round(voltage/(20*rsense),3)
                        ADCList.append(value)
                        # mp_log_q.put(["info", "PC","ADC value= "+str(value)])
                        # mp_log_q.put(["info", "PC","Length of Current List = "+str(len(currentList))])
                        if (stop_time-start_time)>PC_resp_Tout:
                            mp_pumpstatus.pump_rotate_state = 'T'
                            mp_pump_timeout_event.set()  
                            mp_log_q.put(["info", "PC","PUMP CONTROLLER TIMEOUT!"])
                            # retry = False
                            cmd_received = False
                            
                            mp_log_q.put(["info", "PC","breaking the loop"])
                            break
                        
                        if(response.tachometer > target_tachometerRev-10):
                            
                            if(response.rpm > PC_stopping_RPM):
                                # mp_log_q.put(["info", "PC","STOPPING PUMP!!!!!"])
                                pump.write(pyvesc.encode(SetRPM(0)))
                                pump.write(pyvesc.encode(SetCurrent(0)))
                                pump.write(pyvesc.encode(SetCurrentBrake(PC_BrakeCurrent)))
                                
                                mp_pumpstatus.pump_rotate_state = 'A'
                                # mp_log_q.put(["info", "PC","PC status values before stopping are %s"%str(mp_pumpstatus)])
                                
                            else:
                                pump.write(pyvesc.encode(SetRPM(0)))
                                pump.write(pyvesc.encode(SetCurrent(0)))
                                stop_time = time.perf_counter()
                                cmd_received = False
                                GPIO.output("P9_25", GPIO.LOW)##Turn off dispense valve    
             
                                
                                mp_pump_complete_event.set()
                                mp_log_q.put(["info", "PC","PUMP CONTROLLER COMPLETE!"])
                                mp_pumpstatus.pump_rotate_state = 'F'
                                actual_rev = int(response.tachometer) - target_tachometerRev + count
                                mp_log_q.put(["info", "PC","Revs target/actual/delta =  %s/%s/%s"%(str(count),str(actual_rev),str(actual_rev-count))])
                                mp_log_q.put(["info", "PC","pumping time = %s"%str(round(stop_time-start_time,4))])
                                ADCList.pop() # ignore last reading
                                ADCSum = sum(ADCList)
                                ADCAverage = round(ADCSum/len(ADCList),3)
                                # mp_log_q.put(["info", "PC","Sum of Current = %s"%str(currentSum)])
                                # mp_log_q.put(["info", "PC","Current Calculations"])
                                # mp_log_q.put(["info", "PC","Length of Current List = "+
                                # str(len(currentList))])
                                mp_log_q.put(["info", "PC","ADC Average = %s"%str(ADCAverage)])
                                mp_pumpstatus.rev = actual_rev                        
                                # mp_log_q.put(["info", "PC","PC status values after stopping are %s"%str(mp_pumpstatus)])
            
                               
                           
                    connection_retry =0
                    time.sleep(0.05)
                    # retry = False
                except Exception as e:
                    connection_retry+=1
                    time.sleep(0.5)
                    if (connection_retry>=4):
                        mp_log_q.put(["info", "PC","Exception was: "+str(e)])
                        # retry = False
                        cmd_received = False
                        mp_log_q.put(["info","PC","In exception, mp_pump_Unresponsive_event is set"])
                        mp_pump_Unresponsive_event.set()
            else:                    
                mp_log_q.put(["info", "PC","Retrying for NONE RESPONSE from pump controller. Response_counter = %d"%response_counter])
                response_counter+=1
                if response_counter >= 2:                            
                        cmd_received = False
                        # response = 1
                        mp_pump_Unresponsive_event.set()  
                        mp_log_q.put(["info","PC","In else, mp_pump_Unresponsive_event is set"])
        else:            # buffer too short
            connection_retry+=1
            # time.sleep(0.5)
            mp_log_q.put(["error", "PC","Pump data buffer too short: %s"%str(rx_buffer)])
            stop_time = time.perf_counter()
            # mp_log_q.put(["info", "PC","start_time=%s"%str(start_time)])
            # mp_log_q.put(["info", "PC","stop_time=%s"%str(stop_time)])  
            # mp_log_q.put(["info", "PC","stop_time-start_time=%s"%str(stop_time-start_time)])
            if (connection_retry>=4 and (stop_time-start_time)>PC_resp_Tout):
                cmd_received = False
                mp_pumpstatus.pump_rotate_state = 'T'
                mp_pumpstatus.pump_status = "Disconnected" 
                mp_pump_Unresponsive_event.set()
                mp_log_q.put(["info","PC","In data buffer short, mp_pump_Unresponsive_event is set"])
            
            

  
    
def pump_Controller(mp_cmd_q, mp_pumpstatus, mp_log_q, mp_pump_complete_event, mp_pump_timeout_event, mp_pump_Unresponsive_event):
    set_pump_priority(mp_log_q)      #setup priority to third highest
    mp_log_q.put(["info", "PC","Pump_Controller_driver entered!"])
    
    while(1):

        cmd = mp_cmd_q.get(True)
        # mp_log_q.put(["info", "PC","Command is %s"%cmd])
        if (cmd == "Wet_Pad"):
       
            run_pump("Wet_Pad", mp_log_q, mp_pumpstatus)
                           
        elif (cmd=="Sample_Extract"):
            run_pump("Sample_Extract", mp_log_q, mp_pumpstatus)
                           
        elif (cmd == "Calibrate"):
            run_pump("Calibrate", mp_log_q, mp_pumpstatus) 
                          

        elif (cmd == "Rinse"):
            run_pump("Rinse", mp_log_q, mp_pumpstatus)

        elif (cmd == "bagChange"):
            run_pump("bagChange", mp_log_q, mp_pumpstatus)                         
            
            
        else:  ###NONE
            run_pump("None", mp_log_q, mp_pumpstatus) 
            # mp_log_q.put(["info", "PC","Pump status values are %s"%str(mp_pumpstatus)])



def forward_log_thread(log_q, mp_log_q, forward_log_kill_event):
    while (not forward_log_kill_event.is_set()):
        record = mp_log_q.get()    #format: ['error/warning/info/debug/', ID, str]
        log_q.put(record)
    log_q.put(["error","PC","forward_log_thread: kill command received"])  
 
######################  Functions associated with Pump controller calls  ###################### 
def PC_driverInit(log_q, timeout=1):           ##default timeout =1

    global pump_controller_driver_process
    global log_thread  
    global forward_log_kill_event    

    global g_s_timeout
    global g_log_q

    global mp_cmd_q
    global mp_log_q
    global mp_pumpstatus
    global mp_pump_Unresponsive_event
    global mp_pump_timeout_event
    global mp_pump_complete_event
    global mp_pump_cmd_event
    global pump
    global actual_rev
    
    actual_rev = 0
    
    g_s_timeout = timeout
    g_log_q = log_q


    mp_log_q = mp.Queue()
    mp_cmd_q = mp.Queue(1)                                  ## maxium size equals to 1
    mp_pumpstatus  = mp.Manager().Namespace()
    mp_pump_timeout_event = mp.Event()                      ## flag used to timeout when the controller is unresponsive
    mp_pump_complete_event = mp.Event()                     ## Flag used to wait until the Pump has dispensed the required amount of solvent
    mp_pump_Unresponsive_event = mp.Event()
    
    forward_log_kill_event =  mp.Event()                ## flag used to terminate log thread
    
    #Intialise status namespace
    mp_pumpstatus.RPM = "xxxx"            
    mp_pumpstatus.rev = actual_rev
    mp_pumpstatus.pump_status = "Disconnected"              ## Connected, Disconnected
    mp_pumpstatus.pump_rotate_state = "x"              ## "A"=active, "F"=finished, "T"=timeout    
    mp_pumpstatus.rev_tgt = "xxxx"           ## Target revolutions


    pump = serial.Serial(port = serialport, baudrate=BR, timeout = serial_tOut)
    GPIO.output("P8_19", GPIO.HIGH)##Turn on 12V supply to the Pump controller 

    try:
        log_thread = threading.Thread(name="Logger Thread", target=forward_log_thread, args=(g_log_q, mp_log_q,forward_log_kill_event))
        log_thread.start()
    except Exception as ex:
        g_log_q.put(["error","PC","Driver_init: exception when starting forward_log_thread: " + str(ex)])    
    

    try:
        pump_controller_driver_process = mp.Process(target=pump_Controller, args=(mp_cmd_q, mp_pumpstatus, mp_log_q, mp_pump_complete_event, mp_pump_timeout_event, mp_pump_Unresponsive_event))
        pump_controller_driver_process.start()
        g_log_q.put(["warning", "PC", "PC driver: warning: Pump controller driver process started!"])    

    except:
        g_log_q.put(["error", "PC", "PC driver: Error: unable to start Pump controller driver process!"])    
        
    value=ADC.read("P9_35") #1.0 means 1.8V
    # mp_log_q.put(["info", "PC","Value= "+str(value)])
    # voltage=value*1.8
    # mp_log_q.put(["info", "PC","Voltage= "+ str(voltage)])
    # current=round(voltage/(20*rsense),3)
    mp_log_q.put(["info", "PC","ADC value at init= "+str(value)])

    return

def PC_driver_close():
    global pump_controller_driver_process
    global log_thread
    global forward_log_kill_event
    global g_log_q
    forward_log_kill_event.set()    #force to terminiate the log thread
    time.sleep(1)
    pump_controller_driver_process.terminate()
    g_log_q.put(["error","PC","PC_driver_close: wait it close."])
    GPIO.output("P8_19", GPIO.LOW)##Turn off 12V supply to the Pump controller      
    pump_controller_driver_process.join()
    log_thread.join()
    g_log_q.put(["error","PC","PC_driver_close: DONE."]) 


def send_pump_command(cmd,cmd_timeout=g_s_timeout):
    global mp_cmd_queue
    global g_log_q
    global event_starting_time 
    

    
    g_log_q.put(["info", "PC","sendCmd: cmd->%s with timeout setting:%d"%(cmd, cmd_timeout)]) 

    t_out = g_s_timeout
    counter = 0
    try:
        event_starting_time = time.perf_counter()
        # g_log_q.put(["info", "PC","event_starting_time=%s"%str(event_starting_time)])        
        mp_cmd_q.put(cmd, True)          #blocked call with timeout support

    except:
        g_log_q.put(["Error", "PC","mp_cmd_queue, TIMEOUT error!"])    
        return 
            
    return



def PC_wet(cmd_timeout = g_s_timeout):
    return send_pump_command("Wet_Pad",cmd_timeout)

def PC_sample(cmd_timeout = g_s_timeout):
    return send_pump_command("Sample_Extract",cmd_timeout)
    
def PC_calibrate(cmd_timeout = g_s_timeout):
    return send_pump_command("Calibrate",cmd_timeout)
    
def PC_rinse(cmd_timeout = g_s_timeout):
    return send_pump_command("Rinse",cmd_timeout)

def PC_solventBagChange(cmd_timeout = g_s_timeout):
    return send_pump_command("bagChange",cmd_timeout)
   
def PC_Events():    
    global mp_pumpstatus
    global mp_pump_timeout_event
    global mp_pump_complete_event
    global g_log_q
    global actual_rev
    global counter
    global PC_resp_Tout
    
    global event_starting_time 
    
    
    if mp_pump_complete_event.is_set():   
        mp_pump_complete_event.clear()         
        return mp_pumpstatus.rev
    elif mp_pump_timeout_event.is_set():
        mp_pump_timeout_event.clear() 
        mp_pump_Unresponsive_event.clear() 
        g_log_q.put(["info", "PC","Restarting pump"])
        GPIO.output("P8_19", GPIO.LOW)##Turn OFF 12V supply to the Pump controller 
        time.sleep(1)
        GPIO.output("P8_19", GPIO.HIGH)##Turn on 12V supply to the Pump controller        
        g_log_q.put(["info", "PC","Pump RESTARTED"])
        g_log_q.put(["info", "PC","PUMP CONTROLLER Timeout EVENT CLEARED!!!"])
        return 2
    elif mp_pump_Unresponsive_event.is_set():
        mp_pump_Unresponsive_event.clear() 
        mp_pump_timeout_event.clear() 
        g_log_q.put(["info", "PC","Restarting pump"])
        GPIO.output("P8_19", GPIO.LOW)##Turn OFF 12V supply to the Pump controller 
        time.sleep(1)
        GPIO.output("P8_19", GPIO.HIGH)##Turn on 12V supply to the Pump controller        
        g_log_q.put(["info", "PC","Pump RESTARTED"])
        g_log_q.put(["info", "PC","PUMP CONTROLLER Unresponsive_timeout EVENT CLEARED!!!"])
        return 3        
    else:
        event_end_time = time.perf_counter()
        # g_log_q.put(["info", "PC","event_end_time-event_starting_time=%s"%str(event_end_time-event_starting_time)])
        # g_log_q.put(["info", "PC","event_end_time=%s"%str(event_end_time)])
        # g_log_q.put(["info", "PC","event_starting_time=%s"%str(event_starting_time)])
        if (event_end_time-event_starting_time)<PC_resp_Tout:
            return 4
        else:    
            return 3
            
def PC_getStatus():
    global g_log_q
    status_dict = {}
    status_dict["RPM"] = mp_pumpstatus.RPM
    status_dict["rev"] = mp_pumpstatus.rev
    status_dict["pump_rotate_state"] = mp_pumpstatus.pump_rotate_state
    status_dict["pump_status"] = mp_pumpstatus.pump_status

    g_log_q.put(["info", "PC","PC_getStatus: PC status requested"])   #log every second
    return status_dict

    