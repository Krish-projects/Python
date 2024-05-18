#########################################################################################################################################################
# Sampler.py: interface module to communicate with the Sampler
# Created by: Licai Fang
# Date: 26/03/2019
# Function:
#    This module supplies with a simple interface to the Analyzer software to communicate with the Sampler.
#    It updates the current status of the Sampler either by sampling peroidcally or updating after every sampler command.
#    All sampler's functions are supplied with direct function calls. The function call can be set up a timeout
#    value. When a function is called, maybe the last command has not been finished, the function will be blocked 
#    until timeout and returns S_CMD_ERR_BUSY. Or there is something wrong with the Sampler and there is no feecback 
#    after exhaustedly status querying untill timeout happens, this will return S_CMD_ERR_NOFEEDBACK. If there 
#    is valid status received, it returns S_CMD_OK.
#
#    This module also takes charge of the Sampler charging function. When the driver is called with command, it will automatically running in "command mode".
#    The SERAIL communicatin between the Analyzer and the Sample will be established. The "command mode" will be end when the Analyzer read back the Status after 
#    issuing the command. When there is TIMEOUT and finishes all retries, it will also teminiate this "command mode". By default, the driver is in "charging mode"
#    where if the sampler is connected and the outside charge supplier is plugged, the Analyzer will supply the charging power to the Sampler and the Sampler itself
#    will determine if it will perform charge or not. It is worth noting that, under "charging mode", the Sampler's status will be updated with a lower refresh rate
#    than in "command mode".
# Usage:
#     Step 1: call Sampler_init(log_q) to initialise this module, where log_q is the log queue.
#     Step 2: call the following functions to send command to the Sampler:
#           S_cmd_Wipe(), S_cmd_Fast_rotate, S_cmd_Slow_rotate, S_cmd_Clear_faultlist  
#     Step 3: call S_cmd_Get_status() to check the real time status of the Sampler, it will return a dictionary
#               status_dict["sampler_id"]  = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#               status_dict["ver"]         = "x.x"         
#               status_dict["motor_speed"] = "xxxx"
#               status_dict["battery_p"]   = "xx"   
#               status_dict["battery_v"]   = "xx.xx"  
#               status_dict["dis2trigger"] = "xx" 
#               status_dict["trigger2dis"] = "xx" 
#               status_dict["wipe_count"]  = "xxxxxx"  
#               status_dict["spin_count"]  = "xxxxxx"  
#               status_dict["sample_state"]= "x"
#               status_dict["rotate_state"]= "x"
#               status_dict["fault_code_n"]= "xx"
#               status_dict["fault_code"]  = "0123456789abcdef"  
#               status_dict["last_cmd"]    = "ccccc"    
#               status_dict["last_cmd_ack"]= "ccccc"
#               status_dict["status"]      = "Disconnected"   # Ready, Busy, Disconnected
#       Note on S_cmd_Get_status(): After issuing function call to "S_cmd_Wipe(), S_cmd_Fast_rotate, S_cmd_Slow_rotate, S_cmd_Clear_faultlist", 
#               an internal flag (Event) will be raised which will be cleared when a Status packet has been received by the Analyzer. When the flag 
#               is set, the function call of "S_cmd_Get_status()" will be blocked. This will assure that S_cmd_Get_status() can read the real 
#               status of the Sampler.
#     Step 4: call Sampler_close() to gracefully teminiate Mulitiprocessing process and the internal log thread
# Implementation:
#    1) The module can only be initialised once. In initialisation, it will create a multiprocessing process. 
#       However, the main python script can access this module's status at any time and call the command 
#       directly without aware of the multiprocessing process.
#    2) Real time requirement: runs in a multiprocessing process and can be set with higher priority 
# Revision History:
#    V0.1    26/03/2019: first draft
#    V0.2    16/04/2019: Added sequence number tracking, added retry logic when CRC error OR the sampler is busy
#    V0.3    07/05/2019: Added "Reset" command for the Sampler
#    V0.4    10/05/2019: Merged sampler charging function in from PSS_Charging.py
#    V0.5    20/01/2020: Changed sampler charge signal from Active HIGH to Active LOW
#########################################################################################################################################################
import datetime
import os
import time
import sys
import serial
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import multiprocessing as mp

import threading
import logging
import pss_log

import crc8

# print ("Sampler.py first call startin at : startupTime",datetime.datetime.now())

import deviceStatus as DS


########### GLOBAL DEFINATION ############################
S_CMD_OK = 0
S_CMD_ERR_BUSY = 1
S_CMD_ERR_NOFEEDBACK = 2

S_RESPONSE_PKT_SOP=0x8c
S_RESPONSE_PKT_TYPE_OFFSET = 1
########### END OF GLOBAL DEFINATION #####################

g_s_timeout = 2              #default timeout, can be changed by Sampler_init; Every function call can specify specific timeout value, but will not impact this value.    
g_serial_read_timeout = 1  #serial port read timeout, should be less than g_s_timeout (It seems the Sampler has a longer lantency before it can response the "Status" qurey when it is running command like "fast_rotate")
PERIODICAL_TIME = 0.2        #periodically query status
#-----------------------------------The following runs as multiprocessing process --------------------------------------------------------------------------------------------------------
SHOULD_RUN_ONLY_ONCE = 1
g_cmd_seq = 32      #from Space to 126 of ~

#----------------------------------- State Machine --------------------------
CHARGER_IDLE                = 1
CHARGER_CMD_MODE            = 2     #When the driver receives a command (not Status)
CHARGER_WIPE_W_DISCONNECT   = 3     #waiting for disconnect the Sampler to get sample
CHARGER_WIPE_DISCONNECT     = 4     #If the command is "Wipe", waiting for disconnect event to this state. Then when reconnected, jump to CHARGER_CONNECT
CHARGER_CONNECT             = 5     #If no charger plug or disconnected, jump to IDLE
########################################################SAMPLER RESPONSE FORMAT ##########################################################################################################
#SOP|packet_type "s"|length (2) "xx"|sampler id (32) "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"|firmware version (3) "x.x"|actual motor speed (4) "xxxx"|battery remaining (%) (2) "xx"  
# 0 |1              |2         3    |4                                               35|36  37                  38|39   40 41                 42|43                          44
#battery volts (5) "xx.xx"|time - disconnect to trigger (seconds) (2) "xx"|time - trigger to reconnect (seconds) (2) "xx"|total wipe count (6) "xxxxxx"|total spin count (6) "xxxxxx"
#45 46 47 48            49|50                                           51|52                                          53|54 55 56 57 58             59|60 61 62 63 64             65
#sample state (1) "x"   ("R"=valid, "T"=timeout, "C"=clear, "E"=error)|rotate state (1) "x" ("A"=active, "F"=finished, "E"=error)|fault list - variable length - see below|crc (2) "xx"
#66                                                                   |67                                                        |68                                    69
def update_sampler_status(mp_s_status, rd_str,mp_log_queue):
    a_length = len(rd_str)
    pkt=''
    # mp_log_queue.put(["warning", "SA","rd_str = "+str(rd_str)])
    for i in range(a_length-1):
        if rd_str[i]==S_RESPONSE_PKT_SOP:  #get SOP
            pkt = rd_str[i:]
            if(pkt[S_RESPONSE_PKT_TYPE_OFFSET]==ord('B')):
                mp_log_queue.put(["debug", "SA","update_sampler_status: cmd response: "+chr(pkt[S_RESPONSE_PKT_TYPE_OFFSET]) + " SEQ: " + str(pkt[-2]) + " the Sampler is busy!"])
                return 1            #cmd is busy, should retry by the driver
            if(pkt[S_RESPONSE_PKT_TYPE_OFFSET]==ord('c') or pkt[S_RESPONSE_PKT_TYPE_OFFSET]==ord('r') or pkt[S_RESPONSE_PKT_TYPE_OFFSET]==ord('w')):
                mp_s_status.last_cmd_ack = pkt[S_RESPONSE_PKT_TYPE_OFFSET]      #update command response
                mp_log_queue.put(["debug", "SA","update_sampler_status: cmd response: "+chr(pkt[S_RESPONSE_PKT_TYPE_OFFSET]) + " SEQ: " + str(pkt[-2])])
                return 0
            if( pkt[S_RESPONSE_PKT_TYPE_OFFSET]==ord('s')):       #status response
                mp_s_status.sampler_id  = pkt[4:36]
                mp_s_status.ver         = pkt[36:39]
                mp_s_status.motor_speed = pkt[39:43]
                mp_s_status.battery_p   = pkt[43:46]            #percentage
                mp_s_status.battery_v   = pkt[46:51]
                mp_s_status.dis2trigger = pkt[51:53]
                mp_s_status.trigger2dis = pkt[53:55]
                mp_s_status.wipe_count  = pkt[55:61]
                mp_s_status.spin_count  = pkt[61:67]
                mp_s_status.sample_state= chr(pkt[67])               #"R"=valid, "T"=timeout, "C"=clear, "E"=error
                mp_s_status.rotate_state= chr(pkt[68])               #"A"=active, "F"=finished, "E"=error
                mp_s_status.fault_code_n= int(pkt[69:71],16)            #'00' shows no error code ###gets the data as integer
                if(pkt[69]!=ord('0') or pkt[70]!=ord('0')):
                    mp_s_status.fault_code  = pkt[71:]          #varable length string, two bytes for one fault code
                    mp_log_queue.put(["warning", "SA","Fault occured. No. of faults = "+str(mp_s_status.fault_code_n)+" Fault codes are "+str(mp_s_status.fault_code.decode("utf-8"))])
                # mp_log_queue.put(["debug", "SA","update_sampler_status: cmd response: "+chr(pkt[S_RESPONSE_PKT_TYPE_OFFSET]) + "SEQ: " + str(pkt[-2])])
            else:
                mp_log_queue.put(["error", "SA","update_sampler_status: NOT STATUS, NOT CMD_RESPONSE |"  +chr(pkt[S_RESPONSE_PKT_TYPE_OFFSET])])
                
    # mp_log_queue.put(["debug", "SA","update_sampler_status:" + " SEQ: " + str(pkt[-2]) +"| "+ str(pkt)])
    return 0

def append_crc(packet_send):
    
    hash = crc8.crc8()
    hash.update(packet_send)
    m = hash.hexdigest()#.encode('ascii')
    if ord(m[0]) > 96:                          #this step is necessary because the crc8 module outputs the ascii characters in lower case
        m0 = chr(ord(m[0]) - 32)                #convert to upper case
    else:
        m0 = m[0]                               #else just copy the value
    if ord(m[1]) > 96:
        m1 = chr(ord(m[1]) - 32)
    else:
        m1 = m[1]
    m = m0 + m1
    packet_send = packet_send + m.encode('ascii')       #concat crc onto end of command
    return packet_send

def crc_response(packet_receive,mp_log_queue):
    start=999
    try:
        for index in range (0,len(packet_receive)-1):       
            if packet_receive[index] == 0x8c:    
                start=index        
                lhigh=packet_receive[start+2]-48            #requires data length ascii hex characters to be in upper case Sampler side
                if lhigh>9:
                    lhigh-=7
                llow=packet_receive[start+3]-48
                if llow>9:
                    llow-=7
                length=16*lhigh+llow
                break
        if start<999:
            packet=packet_receive[start:start+length+4]
            packetcrc=packet_receive[start+length+4:start+length+6].decode("utf-8")
            hash=crc8.crc8()
            hash.update(packet)
            calccrc=hash.hexdigest().upper()
      
            if calccrc == packetcrc:
                return 1
            else:
                return 0
        else:
            mp_log_queue.put(["error", "SA","crc_response: Can't find packet start"])
            return 0
    except:
        mp_log_queue.put(["error", "SA","crc_response: Exception when finding packet start"])
        return 0
def chk_expected_above_got(s_seq, got):      #32,.....126
    if(s_seq==32 and (got==126 or got==125)):
        return 1
    if(s_seq>got):
        return 1;
    
    return 0
      
def s_check_crc(sampler_sp, rd_str,mp_log_queue,s_seq):
    ret = crc_response(rd_str,mp_log_queue)
    if(ret!=1):     #crc error
        mp_log_queue.put(["error", "SA","CRC error: "+str(rd_str)])
    elif(chk_expected_above_got(s_seq,rd_str[-2])):   #check sequence number, if it inside a window, waiting for match
        mp_log_queue.put(["error", "SA","SEQ error, expected:%d, got:%d "%(s_seq, rd_str[-2])+str(rd_str)])
        try:
            for i in range(3):
                set_TxE(0)
                rd_str =  sampler_sp.readline()
                if(len(rd_str)==1 and rd_str[0]==0):    #read serial TIMEOUT
                    pass
                else:
                    mp_log_queue.put(["error", "SA","SEQ error, FIXIING: expected:%d, got:%d "%(s_seq, rd_str[-2])+str(rd_str)])
                set_TxE(1)
                time.sleep(0.5)
        except:
            pass
    # mp_log_queue.put(["debug", "SA","s_check_crc: %d"%(ret)])
    return ret


def set_TxE(x):
    if x==0:
        GPIO.output("P9_12", GPIO.LOW)
    else:
        GPIO.output("P9_12", GPIO.HIGH)
    return x

def send_cmd_to_sampler(sampler_sp,cmd,mp_log_queue):
    global g_cmd_seq
    Reset           = b'\x8C' + 'T'.encode('ascii') + '00'.encode('ascii')           
    Wipe            = b'\x8C' + 'W'.encode('ascii') + '07'.encode('ascii') +'0120'.encode('ascii') +'01'.encode('ascii')+DS.WipeRotations.encode('ascii')
    Status          = b'\x8C' + 'S'.encode('ascii') + '00'.encode('ascii')
    Fast_rotate_General     = b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '6000'.encode('ascii') + '07'.encode('ascii')
    Fast_rotate_Calibrate     = b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '6000'.encode('ascii') + '12'.encode('ascii')
    Fast_rotate_Sample     = b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '6000'.encode('ascii') + '09'.encode('ascii')
    Slow_rotate     = b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '0120'.encode('ascii') + '06'.encode('ascii')
    Clear_faultlist = b'\x8C' + 'C'.encode('ascii') + '00'.encode('ascii')           
    
    if(cmd=="Reset"):
        cmd_bin = Reset
    elif(cmd=="Wipe"):
        cmd_bin = Wipe
    elif (cmd =='Status'):
        cmd_bin = Status
    elif (cmd =='Fast_rotate_General'):
        cmd_bin = Fast_rotate_General
    elif (cmd =='Fast_rotate_Calibrate'):
        cmd_bin = Fast_rotate_Calibrate       
    elif (cmd =='Fast_rotate_Sample'):
        cmd_bin = Fast_rotate_Sample        
    elif (cmd =='Slow_rotate'):
        cmd_bin = Slow_rotate
    elif (cmd =='Clear_faultlist'):
        cmd_bin = Clear_faultlist
    else:
        #ERROR COMMAND
        mp_log_queue.put(["error", "SA","send_cmd_to_sampler: ERROR COMMAND"])
        return
    
    set_TxE(1)    #Set invalid high (valid signal)
    
    charge = b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00' + b'\x00' + b'\x00'+ b'\x00' + b'\x00'+ b'\x00' + b'\x00'
    eol_char = '\n'.encode('ascii')
    seq_char = chr(g_cmd_seq).encode('ascii')
    sampler_sp.write(charge+append_crc(cmd_bin)+ seq_char + eol_char)       #After CRC, before EOL, we added sequence number for debug purpose
    time.sleep(0.1) 
    # mp_log_queue.put(["info", "SA","send_cmd_to_sampler: "+cmd +"SEQ:" +str(g_cmd_seq) +str(charge+append_crc(cmd_bin)+ seq_char + eol_char)])

    g_cmd_seq += 1          #command sequence number ranging from 32 to 126
    if(g_cmd_seq ==127):
        g_cmd_seq = 32
    
    ret = g_cmd_seq
    if(ret==32):
        ret = 126
    else:
        ret -= 1
    return  ret

def wait_Invalidz_zero():   #If Invalidz is zero and the Analyzer is not driving the bus, this means the Sampler is ready for receiving new data.
    timeout_start = time.time() #current time
    t_out = 1  #timeout
    ser_invalidz=GPIO.input("P9_15")            
    while ((ser_invalidz == 1) and (time.time() < timeout_start + t_out)):                #test while and if loop, both should work
        ser_invalidz=GPIO.input("P9_15")            
    if(ser_invalidz == 1):          #after reading a line from the Sampler, the Sampler SHOULD release the half-duplex serial line and ser_invalidz = 0
        mp_log_queue.put(["error","SA","After Sending cmd: Invalidz line is high, must be low."])   
    return

def set_sampler_priority(log_q, nice_value=-20):
    """
    Setup Sampler driver process to run at higher priority, by issuing command "renice -20 -p PID"
    """
    pid=os.getpid()
    os.system("renice -20 -p %d"%pid)                   #setup radio_tx_loop to the highest priority
    log_q.put(['warning',"SA","Set Sampler_drive :%d nice to -20"%pid])    

def check_charger():
    """"
    Is used to check whether or not the charger plug pack is connected
    """
    value=ADC.read("P9_33")     #check charger plug pack
    if value>0.2:
        return True
    else:
        return False

def charge_s_enable(on_off):
    """
    Is used to switch the charge signal to the sampler on and off
    """
    if on_off==1:
        GPIO.output("P8_15",GPIO.LOW)
    elif on_off==0:
        GPIO.output("P8_15",GPIO.HIGH)
    else:
        self.log_q.put(["debug","SC","Invalid input in charge_s_enable, function doing nothing"])
    
def sampler_driver(mp_cmd_queue,mp_rsp_queue,mp_s_status, mp_log_queue,mp_sync_status_event):
    set_sampler_priority(mp_log_queue)      #setup priority to highest
    
    mp_log_queue.put(["info", "SA","sampler_driver entered!"])
    GPIO.setup("P9_12", GPIO.OUT)
    GPIO.setup("P9_15", GPIO.IN)   
    GPIO.setup("P8_15", GPIO.OUT)   
    y=GPIO.input("P9_15")
   
    sampler_sp=serial.Serial(port = "/dev/ttyO4", baudrate=115200,timeout=g_serial_read_timeout)
    
    s_time=time.time()
    slow_status_count=0     #used to reduce the status sampling rate when in "Charging mode"
    Status_cmd_issued = False
    charging_mode = False
    TXE_Q=[]
    charger_state = CHARGER_IDLE
    while(1):
        try:
            cmd = mp_cmd_queue.get(True, PERIODICAL_TIME)       #block until an item is avaliable or TIMEOUT
            if(cmd=='Status'):                                  #Status check is performed by default
                cmd = ''
                Status_cmd_issued = True
            else:
                Status_cmd_issued = False
        except:     #TIMEOUT happens for periodcally checking status
            cmd = ''
        
        charger_connected =  check_charger()   
        check_after_cmd = False
        if(cmd !=''):       #get a command to go
            charger_state = CHARGER_CMD_MODE                    #entering command mode
            charge_s_enable(0) 
            set_TxE(1)    #Set invalid low (no valid signal)
            time.sleep(0.2)
            if(charging_mode == True):
                mp_log_queue.put(["warning","SA","Entering command mode:%d %s"%(charger_connected,mp_s_status.status)])  
                
            slow_status_count = 0
            charging_mode = False
            ser_retry =0                                            #retry counter used to setup status to "Disconnected"
            while (ser_retry<4):
                s_seq = send_cmd_to_sampler(sampler_sp,cmd,mp_log_queue)
                TXE_Q.append('-')
                mp_s_status.last_cmd    = cmd
                mp_sync_status_event.set()          #flag used to update real time status from the Sampler ---------START-----------
                mp_log_queue.put(["warning","SA","mp_sync_status_event: set  ->"])
                check_after_cmd = True
                received_rsp = False

                if(cmd=='Reset'):                                  #We have to waiting for 3 seconds for a RESET to be finished.
                    mp_log_queue.put(["warning","SA","Sampler is reseting..."])    
                    mp_s_status.status = 'Busy'
                    time.sleep(3)       #waiting for the Sampler is ready.
                    s_seq = send_cmd_to_sampler(sampler_sp,'Status',mp_log_queue)   #Check the status after Reset
                    
                set_TxE(0)    #Set invalid low (no valid signal)
                TXE_Q.append('_')
                rd_str =  sampler_sp.readline() 
                if(len(rd_str)==1 and rd_str[0]==0):         #TIMEOUT happens
                    mp_log_queue.put(["warning","SA","TIMEOUT when performing cmd: %s No.%d"%(cmd,ser_retry)])    
                    ser_retry += 1
                else:
                    if(s_check_crc(sampler_sp,rd_str,mp_log_queue,s_seq)):        #check received response: lenth >10, crc should be good
                        received_rsp = True
                        s_busy = update_sampler_status(mp_s_status, rd_str,mp_log_queue)    #Log status, then check if the Sampler is busy
                        if(s_busy==1):
                            ser_retry += 1
                            mp_log_queue.put(["warning","SA","Retry command %s because of Sampler is busy! No.%d"%(cmd, ser_retry)])    
                            mp_s_status.status = 'Busy'
                            # time.sleep(2)
                        else:
                            if(mp_s_status.status == 'Disconnected' or mp_s_status.status == 'Busy'):      #Log this message once (changing from Disconnected to Connected)
                                mp_log_queue.put(["warning","SA","Change connection status to Connected No.%d"%(ser_retry)])    
                                mp_s_status.status = 'Ready'
                            ser_retry = 100                      #big enough value to break from the while loop
                    else:   
                        mp_log_queue.put(["error","SA","CRC error when running command %s No.%d"%(cmd,ser_retry)])    
                        ser_retry += 1                   
                wait_Invalidz_zero()
                set_TxE(1)
                TXE_Q.append('-')
                
            if(ser_retry==4):                    
                mp_s_status.status = 'Disconnected'
                mp_log_queue.put(["warning","SA","Connection status is: Disconnected as CRC error"])    
            ser_retry = 0
            
            
            if(received_rsp):
                mp_rsp_queue.put("SUCC|" + cmd)
            else:
                mp_rsp_queue.put("FAIL|" + cmd)
        else:   #cmd = '', in "Charging mode"
            slow_status_count += 1
            # print("%d %s %d"%(slow_status_count, mp_s_status.status, charger_connected))
            can_charge = (charger_state == CHARGER_CONNECT) or (cmd=='' and mp_s_status.status != 'Disconnected')
            if(charger_connected and can_charge and slow_status_count>=15):
                set_TxE(0)    #Set invalid low (no valid signal)
                TXE_Q.append('_')
                charge_s_enable(1)
                if(charging_mode == False):
                    mp_log_queue.put(["warning","SA","Changed to Charging mode"])    
                charging_mode = True
            elif(not charger_connected or mp_s_status.status == 'Disconnected'):                
                if(charging_mode == True):
                    mp_log_queue.put(["warning","SA","Exit from  Charging mode:%d %s"%(charger_connected,mp_s_status.status)])    
                    charge_s_enable(0)                
                    set_TxE(1)    #Set invalid low (no valid signal)
                    TXE_Q.append('-')
                    charging_mode = False
                    slow_status_count = 0
        
        if(cmd=='Wipe' and charger_state == CHARGER_CMD_MODE and mp_s_status.status != 'Disconnected'):
            charger_state = CHARGER_WIPE_W_DISCONNECT        #watiing for disconnect    
        elif (cmd!='' and charger_state == CHARGER_CMD_MODE):
            charger_state = CHARGER_CONNECT        #watiing for disconnect

        if(charger_state == CHARGER_WIPE_W_DISCONNECT and mp_s_status.status == 'Disconnected'):
            charger_state = CHARGER_WIPE_DISCONNECT        #watiing for disconnect
        
        if(charger_state == CHARGER_WIPE_DISCONNECT and mp_s_status.status != 'Disconnected'):
            charger_state = CHARGER_CONNECT                #
        
        if(charger_state == CHARGER_CONNECT and (not charger_connected or mp_s_status.status == 'Disconnected')):
            charger_state = CHARGER_IDLE                   #
        # print("charger_state: %d"%(charger_state))
            
        if((slow_status_count%5==0) or slow_status_count<10 or Status_cmd_issued or  check_after_cmd):                            #always TRUE: periodically query status or after sending a command
            charge_s_enable(0) 
            set_TxE(1)    #Set invalid low (no valid signal)
            time.sleep(0.2)
            ser_retry =0                                            #retry counter used to setup status to "Disconnected"
            while (ser_retry<2):
                s_seq = send_cmd_to_sampler(sampler_sp,'Status',mp_log_queue)
                received_rsp = False
    
                set_TxE(0)    #Set invalid low (no valid signal)
                TXE_Q.append('_')
                rd_str =  sampler_sp.readline()                 #If disconnected, there is an timeout
                
                if(len(rd_str)==1 and rd_str[0]==0):            #TIMEOUT happens
                    mp_log_queue.put(["warning","SA","Status TIMEOUT %d"%(ser_retry)])  
                    ser_retry += 1
                else:
                    if(s_check_crc(sampler_sp,rd_str,mp_log_queue,s_seq)):       #check received response: lenth >10, crc should be good
                        received_rsp = True
                        update_sampler_status(mp_s_status, rd_str,mp_log_queue)
                        if(mp_s_status.status == 'Disconnected'):
                            mp_log_queue.put(["warning","SA","Status change Connected No.%d"%(ser_retry)])    
                            mp_s_status.status = 'Ready'
                        ser_retry = 100                      #big enough value to break from the while loop
                        mp_sync_status_event.clear()        #flag used to update real time status from the Sampler -------------END-------
                        # mp_log_queue.put(["warning","SA","mp_sync_status_event: cleard! --|____________________________________________>"])
                    else:
                        mp_log_queue.put(["error","SA","CRC error when performing Status Query No.%d"%(ser_retry)])   
                        ser_retry += 1
                wait_Invalidz_zero()
                set_TxE(1)
                TXE_Q.append('-')
                        
            if(ser_retry==2):                    
                mp_s_status.status = 'Disconnected'
                mp_log_queue.put(["warning","SA","Status Disconnected"])    
            ser_retry = 0
        #print(TXE_Q)
        if(len(TXE_Q)>=100):
            TXE_Q=[]
                
    return

#-----------------------------------End of  multiprocessing process -------------------------------------------------------------------------------------------------------------
def forward_log_thread(log_q, mp_log_q, forward_log_kill_event):
    while (not forward_log_kill_event.is_set()):
        record = mp_log_q.get()    #format: ['error/warning/info/debug/', ID, str]
        log_q.put(record)
        time.sleep(0.01)
    log_q.put(["error","SA","forward_log_thread: kill command received"])    
def Sampler_init(log_q, timeout=1):    #default timeout =1
    global SHOULD_RUN_ONLY_ONCE
    # if(SHOULD_RUN_ONLY_ONCE!=1):
        # log_q.put(["error","SA","Sampler_init: CAN RUN ONLY ONCE:%d"%(SHOULD_RUN_ONLY_ONCE)]) 
        # raise ValueError('CAN RUN ONLY ONCE')
    
    # SHOULD_RUN_ONLY_ONCE = 2
    global sampler_process
    global log_thread  
    global forward_log_kill_event
    
    global g_Sampler_Status
    global g_s_timeout
    global g_log_q

    global mp_cmd_queue
    global mp_rsp_queue
    global mp_log_queue
    global mp_s_status
    global mp_sync_status_event
    #s_ser=serial.Serial(port = "/dev/ttyO4", baudrate=115200,timeout=10)
    g_s_timeout = timeout
    g_log_q = log_q

    ADC.setup()

    mp_log_queue = mp.Queue()
    mp_cmd_queue = mp.Queue(1)      #maxium size equals to 1
    mp_rsp_queue = mp.Queue(1)      #maxium size equals to 1
    mp_s_status  = mp.Manager().Namespace()
    mp_sync_status_event = mp.Event() #flag used to wait for fetching status from the sampler after issuing an command
    
    forward_log_kill_event =  mp.Event() #flag used to terminate log thread
    
    #Intialise mp_s_status
    mp_s_status.sampler_id  = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    mp_s_status.ver         = "x.x"
    mp_s_status.motor_speed = "xxxx"
    mp_s_status.battery_p   = "xx"                  #percentage
    mp_s_status.battery_v   = "xx.xx"
    mp_s_status.dis2trigger = "xx"
    mp_s_status.trigger2dis = "xx"
    mp_s_status.wipe_count  = "xxxxxx"
    mp_s_status.spin_count  = "xxxxxx"
    mp_s_status.sample_state= "x"                   #"R"=valid, "T"=timeout, "C"=clear, "E"=error
    mp_s_status.rotate_state= "x"                   #"A"=active, "F"=finished, "E"=error
    mp_s_status.fault_code_n= "xx"                  #'00' shows no error code
    mp_s_status.fault_code  = "0123456789abcdef"    #varable length string, two bytes for one fault code
    mp_s_status.last_cmd    = "ccccc"               #"Clear_faultlist","Wipe","Fast_rotate","Slow_rotate"
    mp_s_status.last_cmd_ack= "ccccc"               #"c"              ,"w"   ,"r"          ,"r"
    mp_s_status.status   = 'Disconnected'

    try:
        log_thread = threading.Thread(name="Logger Thread", target=forward_log_thread, args=(g_log_q, mp_log_queue,forward_log_kill_event) )
        log_thread.start()
    except Exception as ex:
        g_log_q.put(["error","SA","Sampler_init: exception when starting forward_log_thread: " + str(ex)])    
    

    try:
        sampler_process = mp.Process(target=sampler_driver, args=(mp_cmd_queue,mp_rsp_queue,mp_s_status, mp_log_queue,mp_sync_status_event))
        sampler_process.start()
        g_log_q.put(["warning", "SA","Sampler: warning: started sampler process!"])    
    except:
        g_log_q.put(["error","SA","!Sampler: Error: unable to start sampler process!"])    
    return
def Sampler_close():
    global SHOULD_RUN_ONLY_ONCE
    # if(SHOULD_RUN_ONLY_ONCE!=2):
        # #log_q.put(["error","SA","Sampler_close: CAN ONLY RUN after call Sampler_Init:%d"%(SHOULD_RUN_ONLY_ONCE)]) 
        # raise ValueError('CAN ONLY RUN AFTER Sampler_Init')
    global sampler_process
    global log_thread
    global forward_log_kill_event
    global g_log_q
    # forward_log_kill_event.set()    #force to terminiate the log thread
    # time.sleep(1)
    sampler_process.terminate()
    g_log_q.put(["error","SA","Sampler_close: wait it close."])
    # print(forward_log_kill_event.is_set())
    sampler_process.join()
    # log_thread.join()
    # SHOULD_RUN_ONLY_ONCE = 1
    g_log_q.put(["error","SA","Sampler_close: DONE."])    
################################################The following are public functions for controling/monitoring the Sampler#################################################
def S_cmd_general(cmd,cmd_timeout=g_s_timeout):
    global mp_cmd_queue
    global mp_rsp_queue
    global g_log_q
    g_log_q.put(["info", "SA","S_cmd_general: cmd->%s with timeout setting:%d"%(cmd, cmd_timeout)])    
    t_out = g_s_timeout
    if(cmd_timeout!=g_s_timeout):
        t_out = cmd_timeout
    
    while(not mp_rsp_queue.empty()):
        t=mp_rsp_queue.get()
        g_log_q.put(["info", "SA","Got last CMD TIMEOUT RSP: %s"%(t)])
        

    try:
        #empty the rsp_queue caused by last TIMETOUT operation
        mp_cmd_queue.put(cmd, True, t_out)          #blocked call with timeout support
        
    except:
        g_log_q.put(["warning", "SA","mp_cmd_queue, TIMEOUT error!"])    
        return S_CMD_ERR_BUSY
    
    try:
        fd = mp_rsp_queue.get(True, t_out)
        g_log_q.put(["warning", "SA","mp_rsp_queue, get response "+fd])    
        return S_CMD_OK
    except:
        g_log_q.put(["warning", "SA","mp_rsp_queue, TIMEOUT error!"])    
        return S_CMD_ERR_NOFEEDBACK
        
    return S_CMD_OK

def S_cmd_Status(cmd_timeout=g_s_timeout):
    return S_cmd_general('Status',cmd_timeout)
    
def S_cmd_Reset(cmd_timeout=g_s_timeout):
    return S_cmd_general('Reset',cmd_timeout)

def S_cmd_Wipe(cmd_timeout=g_s_timeout):
    return S_cmd_general('Wipe',cmd_timeout)

def S_cmd_Fast_rotate_General(cmd_timeout=g_s_timeout):
    return S_cmd_general('Fast_rotate_General',cmd_timeout)
    
def S_cmd_Fast_rotate_Calibrate(cmd_timeout=g_s_timeout):
    return S_cmd_general('Fast_rotate_Calibrate',cmd_timeout)    
    
def S_cmd_Fast_rotate_Sample(cmd_timeout=g_s_timeout):
    return S_cmd_general('Fast_rotate_Sample',cmd_timeout)    

def S_cmd_Slow_rotate(cmd_timeout=g_s_timeout):
    return S_cmd_general('Slow_rotate',cmd_timeout)

def S_cmd_Clear_faultlist(cmd_timeout=g_s_timeout):
    return S_cmd_general('Clear_faultlist',cmd_timeout)

def get_invalid_status_dict():
    status_dict = {}
    status_dict["sampler_id"]  = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    status_dict["ver"]         = "x.x"         
    status_dict["motor_speed"] = "xxxx"
    status_dict["battery_p"]   = "xx"   
    status_dict["battery_v"]   = "xx.xx"  
    status_dict["dis2trigger"] = "xx" 
    status_dict["trigger2dis"] = "xx" 
    status_dict["wipe_count"]  = "xxxxxx"  
    status_dict["spin_count"]  = "xxxxxx"  
    status_dict["sample_state"]= "x"
    status_dict["rotate_state"]= "x"
    status_dict["fault_code_n"]= "xx"
    status_dict["fault_code"]  = "0123456789abcdef"  
    status_dict["last_cmd"]    = "ccccc"    
    status_dict["last_cmd_ack"]= "ccccc"
    status_dict["status"]   = "Disconnected"
    return  status_dict   
def get_int(string):
    try:
        ret = int(string)
    except:
        ret = -1
    return ret
    
  
def S_cmd_Get_status():
    global mp_s_status
    global mp_sync_status_event
    global g_log_q
    tout_count=0
    while (mp_sync_status_event.is_set()):    #After a command is issuing, we need to update internal status from the sampler with command of "Status"
        time.sleep(0.1)
        tout_count += 1
        if(tout_count%10 == 0):
            g_log_q.put(["warning", "SA","S_cmd_Get_status: waiting for updating status from the Sampler"])   #log every second
        if(tout_count >= 100):
            g_log_q.put(["Error", "SA","S_cmd_Get_status: updating status from the Sampler TIMEOUT (10s)"])
            return get_invalid_status_dict()
    
    status_dict = {}
    #copy_status_from_namespace: mp_s_status
    status_dict["sampler_id"]  = mp_s_status.sampler_id  
    status_dict["ver"]         = mp_s_status.ver         
    status_dict["motor_speed"] = get_int(mp_s_status.motor_speed)
    status_dict["battery_p"]   = get_int(mp_s_status.battery_p)   
    status_dict["battery_v"]   = mp_s_status.battery_v   
    status_dict["dis2trigger"] = get_int(mp_s_status.dis2trigger)
    status_dict["trigger2dis"] = get_int(mp_s_status.trigger2dis)
    status_dict["wipe_count"]  = get_int(mp_s_status.wipe_count)
    status_dict["spin_count"]  = get_int(mp_s_status.spin_count)
    status_dict["sample_state"]= mp_s_status.sample_state
    status_dict["rotate_state"]= mp_s_status.rotate_state
    status_dict["fault_code_n"]= get_int(mp_s_status.fault_code_n)
    status_dict["fault_code"]  = mp_s_status.fault_code  
    status_dict["last_cmd"]    = mp_s_status.last_cmd    
    status_dict["last_cmd_ack"]= mp_s_status.last_cmd_ack
    status_dict["status"]      = mp_s_status.status     #'Ready', 'Busy', 'Disconnected''
    return status_dict
################################################       END OF    public functions for controling/monitoring the Sampler#################################################

def t_logger_thread(q,terminate_log_event):
    global log
    while True:
        try:
            record = q.get(True, 0.1)    #format: ['error/warning/info/debug/', ID, str]
            try:
                ID = record[1]
                MSG = record[2]
            except:
                ID = 'IO'
                MSG = 'Exception in log' + str(record)
            # ID = record[1]
            # MSG = record[2]            
            if record[0].lower()=='error':
                log.error(ID, MSG)
            if record[0].lower()=='warning':
                log.warning(ID, MSG)
            if record[0].lower()=='info':
                log.info(ID, MSG)
            if record[0].lower()=='debug':
                log.debug(ID, MSG)
        except:
            pass
            
        if (terminate_log_event.is_set()):   #
            # print("received the terminate_log_event")
            break
    # print("t_logger_thread, recevied terminate command")
    return


