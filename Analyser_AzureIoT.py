#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import csv
import random
import time
import sys
sys.path.append('/home/debian/PSS/azure-iot-sdk-python/device/samples')
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
from iothub_client import IoTHubClientRetryPolicy, GetRetryPolicyReturnValue
from iothub_client_args import get_iothub_opt, OptionError
import subprocess
import json
import os
import shutil
import pss_log
import logging
import socket
import requests
import zlib
import tarfile
import _thread, cmd, threading
import deviceStatus as DS
import datetime
import Sampler_Load
import ipaddress
# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000
ANALYSER_CONTEXT_NUM = 200        #a unique number
METHOD_CONTEXT = 0
MAX_SIZE_DIRECT_METHOD=64000        #128Kbytes, reserve some space
MAX_TIMEOUT_DIRECT_METHOD=60        #How long we can wait for a command to finish
#IOT_HUB_CONNECTION_STR = "HostName=lcTestIoTHub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=BH8x7CE7hTpNltYetUs4tXksSGaIrO2LtM8rMJL1LXo="
IOT_HUB_CONNECTION_STR = "HostName=%s;SharedAccessKeyName=iothubowner;SharedAccessKey=%s"
#CONN_STR_TXT="HostName=lcTestIoTHub.azure-devices.net;DeviceId=%s;SharedAccessKey=%s"
CONN_STR_TXT="HostName=%s;DeviceId=%s;SharedAccessKey=%s"
# chose HTTP, AMQP, AMQP_WS or MQTT as transport protocol
PROTOCOL = IoTHubTransportProvider.MQTT
CONN_STR_FMT="HostName=%s;DeviceId=%s;SharedAccessKey=" #MNOjIEmOUMMBZ43ll/dA8pH9Rua6su/PGPfiuNRNI70="

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0
BLOB_CALLBACKS = 0
CONNECTION_STATUS_CALLBACKS = 0
TWIN_CALLBACKS = 0
SEND_REPORTED_STATE_CALLBACKS = 0
METHOD_CALLBACKS = 0

G_desired_last_version=0        #used to record last desired version
g_longrun_command = None

config_filename = 'cfg_file.csv'

# FIRMWARE upgrade states
FIRMWARE_IDLE = 0
FIRMWARE_DOWNLOADING = 1
FIRMWARE_DONE = 2
FIRMWARE_FAIL = 3


RECEIVE_CONTEXT = 0
MESSAGE_COUNT = 5
RECEIVED_COUNT = 0
CONNECTION_STATUS_CONTEXT = 0
TWIN_CONTEXT = 0
SEND_REPORTED_STATE_CONTEXT = 0

PROTOCOL = IoTHubTransportProvider.MQTT
#CONNECTION_STRING = "HostName=Atamo-PSS.azure-devices.net;DeviceId=Andrew-Test-01;SharedAccessKey=tJX1GpqDbtyEw7RJc6XOcYL90i8j2OgFPLKW5RW2OuE="
#CONNECTION_STRING = "HostName=Atamo-PSS.azure-devices.net;DeviceId=Andrew-Test-02;SharedAccessKey=QW+TB6UZ/1GpTr+kholAuNQb5dzNeoQQCg8EXBO+FCs="
#CONNECTION_STRING = "HostName=pss-rsrch-iot.azure-devices.net;DeviceId=mydevice;SharedAccessKey=HTPJLGByyFUpQ8o9t6Th0h6TNzoqBb27IFd5K3tPYRY="
# CONNECTION_STRING = "HostName=pss-rsrch-iot.azure-devices.net;DeviceId=mydevice;SharedAccessKey=Sx+nIPwo19yj4G6MSaSnT7QwXDIOAhk9mtPeo5zpCZU="
# CONNECTION_STRING = "HostName=pss-rsrch-iot.azure-devices.net;DeviceId=AndrewAnalyser;SharedAccessKey=CR1cZpae+XAP+tUxd1Zz3B9QHnVKqSBc3E5mC3lGqoQ="
#CONNECTION_STRING = "HostName=pss-rsrch-iot.azure-devices.net;DeviceId=PSSAnalyser001;SharedAccessKey=FjNgqbdYKL/1hIosGiZhrry+BOfI5QShQBsd7LLEjJg="
results_path = '/home/debian/PSS/results/'
sent_results_path = '/home/debian/PSS/sent_results/'
confirmation_received = 'Now'

# print ("Analyser_AzureIOT.py first call startin at : startupTime",datetime.datetime.now())


def init(connection_str, mp_status, rSSH_queue, log_queue):
    global gStartUpTime, log_q
    # print("Starting IoT as %s" % connection_str)
    gStartUpTime = time.time()
    log_q = log_queue
    log_q.put(["debug","IT","Starting IoT as " + connection_str])
    #global G_CLIENT
    G_CLIENT=None
    global G_CONNECTION
    G_CONNECTION=None
    global G_STATUS
    G_STATUS = conf_status(mp_status, rSSH_queue)
    
    global G_LED_QUEUE
    #G_LED_QUEUE = Queue.Queue(maxsize=30)

    global G_GUI_DEMO
    G_GUI_DEMO = 0
    
    global g_bt_download_time
    g_bt_download_time=0
    
    global g_bt_download_mac
    g_bt_download_mac=''
    
    global G_bootserver
    G_bootserver=None
    global G_gw_radio
    G_gw_radio=None
    
    global GW_firmware_state
    GW_firmware_state = FIRMWARE_IDLE
    # G_STATUS.firmware_state = FIRMWARE_IDLE
    
    global g_last_bt_rpt_time
    g_last_bt_rpt_time=0
    
    global g_stop_firmwareupgrade
    g_stop_firmwareupgrade={}

    global g_TIMEOUT_dict
    g_TIMEOUT_dict={}
    global g_STORM_dict
    g_STORM_dict={}
    
    global g_callback_flag
    g_callback_flag = True        #Assigned True in main loop every GW rpt_interval, clear at GW call back

def send_confirmation_callback(message, result, user_context):
    global confirmation_received, log_q
    log_q.put(['debug','IT', "Conf is: %s" % confirmation_received])
    confirmation_received = result
    log_q.put(['debug','IT',  "Confirmation[%d] received for message with result = %s" % (user_context, result)] )
    map_properties = message.properties()
    log_q.put(['debug','IT', "    message_id: %s" % message.message_id ])
    log_q.put(['debug','IT', "    correlation_id: %s" % message.correlation_id] )
    key_value_pair = map_properties.get_internals()
    log_q.put(['debug','IT', "    Properties: %s" % key_value_pair ])
    log_q.put(['debug','IT', "Conf: %s" % (confirmation_received)])
        

def send_reported_state_callback(status_code, user_context):
    global log_q
    log_q.put(['debug','IT', "Confirmation[%d] for reported state received with:" % (user_context) ])
    log_q.put(['debug','IT', "    status_code: %d" % status_code] )
    if(status_code !=200 and status_code !=204):    #200:ok, 204:accepted |Gateway POST has some problem, try to reconnect
        g_TIMEOUT_dict['AN']=True
        log_q.put(['debug','IT', "STATUS ERROR FOUND, set flag in g_TIMEOUT_dict !!"])
    else:
        g_gw_callback_flag = False            # clear flag to show call back has been called and connection to IoTHub is good.

def receive_message_callback(message, counter):
    """
    For IoT hub send message to Gateway, NO USE by now
    """
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "Received Message [%d]:" % counter )
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    return IoTHubMessageDispositionResult.ACCEPTED

def device_twin_callback(update_state, payload, user_context):
    """
    IoT Hub ---> Analyser, sending commands, configuration
    """
    global TWIN_CALLBACKS, log_q
    global G_SENSOR_CONF
    log_q.put(["debug","IT", "Twin callback called with:"])
    log_q.put(["debug","IT", "updateStatus: %s" % update_state ])
    log_q.put(["debug","IT", "context: %s" % user_context ])
    log_q.put(["debug","IT", "payload: %s" % payload ])
    TWIN_CALLBACKS += 1
    log_q.put(["debug","IT", "Total calls confirmed: %d\n" % TWIN_CALLBACKS ])
    
    log_q.put(["debug","IT","------------------Device Twin Callback----------"])
    log_q.put(["warning","IT","Updating Device Twin"])
    parsing_device_twin(payload)
    log_q.put(["warning","IT","Exiting Device Twin Callback"])
    return


def device_method_callback(method_name, payload, user_context):
    import base64

    global METHOD_CALLBACKS
    log_q.put(["debug", "IT", "\nMethod callback called with:\nmethodName = %s\npayload = %s\ncontext = %s" % (method_name, payload, user_context) ])
    METHOD_CALLBACKS += 1
    log_q.put(["debug", "IT", "Total calls confirmed: %d\n" % METHOD_CALLBACKS ])
    device_method_return_value = DeviceMethodReturnValue()
    mystr=b"This is astring \r\n"
    end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(mystr)) +"\" }"
#    end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(mystr.encode('UTF-8').decode('ascii'))) +"\" }"
    log_q.put(["debug", "IT",end_str])
    device_method_return_value.response = end_str #"{ \"Response\": i"+ base64.b64encode(mystr) +"\"Delete Device successed.\" }" #% payload
    device_method_return_value.status = 200
    j=json.loads(payload)
    if 'cmd' in j:
        cmd_str=j['cmd'] 
    if(method_name == "ExePython"):
        log_q.put(["warning", "IT","Received ExePython command: "+cmd_str])
        try:
            p_code=base64.b64decode(cmd_str)
            log_q.put(["warning", "IT","Received ExePython command " +p_code])
            d_str=do_exec_python(p_code)  
        except:
            log_q.put(["warning","IT","Received ExePython command, exception happened!"])
            d_str="!!!exec python exception happened!!!!"
        
        end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(d_str.encode('utf-8'))) +"\" }"
        device_method_return_value.response = end_str 
        return device_method_return_value
    if(method_name == "DiagnoseGW"):
        log_q.put(["warning","IT","Received DiagnoseGW command, reporting..."])
        d_str=do_diagnose()
        device_method_return_value.response = "{ \"Response\": \"Success!\n%s\" }" % d_str
        end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(d_str.encode('utf-8'))) +"\" }"
        #print("Returning: " + end_str)
        device_method_return_value.response = end_str 
        return device_method_return_value
    if(method_name == "ExeCmd"):
        log_q.put(["warning","IT","Received Execmd"])
        d_str=do_execmd(cmd_str)
        device_method_return_value.response = "{ \"Response\": \"Success!\n%s\" }" % d_str
        log_q.put(["warning","IT","Received ExeCmd command of %s, reporting..."%(cmd_str)])
        end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(d_str.encode('utf-8'))) +"\" }"
        device_method_return_value.response = end_str
        return device_method_return_value    
    if(method_name == "ExeCmdLongRun"):
        d_str=do_execmd_longrun(cmd_str)
        device_method_return_value.response = "{ \"Response\": \"Success!\n%s\" }" % d_str
        log_q.put(["warning","IT","Received ExeCmdLongRun command of %s, reporting..."%(cmd_str)])
        end_str="{ \"Response\" : "+"\""+ str(base64.b64encode(d_str.encode('utf-8'))) +"\" }"
        device_method_return_value.response = end_str
        return device_method_return_value    
    if(method_name == "RestartService"):
        log_q.put(["error","IT","Received RestartService command, resarting..."])
        os._exit(1)        #let systemd service restart the service automatically
        
    if(method_name == "RebootGW"):
        log_q.put(["error","IT","Received RebootGW command, rebooting..."])
        time.sleep(10)
        os.system("reboot")
        #os._exit(1)        #let systemd se    
    return device_method_return_value

def parsing_device_twin(payload):
    global G_desired_last_version, log_q
    log_q.put(["info","IT","parsing_device_twin called!"])
    j=json.loads(payload)
    log_q.put(["debug","IT",'j'])
    log_q.put(["debug","IT",j])
    j2=j
    if 'desired' in j:      #we found that first connection, we got 'desired':...., later modification, we only get the real changed value
        j2 = j['desired']
        G_desired_this_version = j2['$version']
        log_q.put(["debug","IT","Desired version is "+str(G_desired_this_version)])
        if(G_desired_last_version==G_desired_this_version):
            log_q.put(["debug","IT","We think nothing changed"])
            return      #nothing changed from last download
        else:
            G_desired_last_version = G_desired_this_version
    try:
        if G_STATUS.rpt_interval != j2['RptInterval']:
            log_q.put(["info","IT",'Got changed report interval, now ' + str(j2['RptInterval'])])
            G_STATUS.rpt_interval           = j2['RptInterval']
    except:
        pass

    log_q.put(["debug","FW",'Checking vers '])
    firmware_req=G_STATUS.firmware_ver #initialise to current version
    sampler_req=G_STATUS.sampler_ver #initialise to current version
    try:
        sampler_req        = j2['SamplerVer']        #10,11,12 =>V1.0, V1.1, V1.2
        log_q.put(["debug","FW",'Wanting Sampler ver ' + sampler_req])
    except Exception as e:
        # log_q.put(["debug","FW",'Sampler ver exception ' + sampler_req + ' ' + str(e)])
        pass

    try:
        firmware_req        = j2['FirmwareVer']        #10,11,12 =>V1.0, V1.1, V1.2
        log_q.put(["debug","FW",'Wanting Analyser version ' + firmware_req])
    except Exception as e:
        # log_q.put(["debug","FW",'Analyser ver exception ' + firmware_req] + ' ' + str(e))
        pass

    try:
        G_STATUS.firmware_crc        = j2['FirmwareCRC']
    except:
        pass
    
    try:
        G_STATUS.download_URL           = j2['DownloadURL']
    except:
        pass    


    try:
        G_STATUS.upload_URL           = j2['UploadURL']
    except:
        pass    

    try:
        G_STATUS.log_level           = j2['LogLevel']
        change_log_level(G_STATUS.log_level)
    except:
        pass 

    try:
        G_STATUS.RSSHIP = j2['RSSHIP']
        log_q.put(["debug","FW",'Got changed RSSHIP now: '+ G_STATUS.RSSHIP])
    except:
        pass

    try:
        G_STATUS.RSSHPort = j2['RSSHPort']
        log_q.put(["debug","FW",'Got changed RSSHPort now: '+ G_STATUS.RSSHPort])
    except:
        pass

    try:
        desiredRSSHStatus = j2['RSSHStatus']
        if G_STATUS.RSSHStatus != desiredRSSHStatus:
            change_RSSHStatus(desiredRSSHStatus)
            G_STATUS.RSSHStatus = desiredRSSHStatus
    except:
        # log_q.put(["debug","FW",'RSSHStatus exception: ' + str(e) + desiredRSSHStatus])
        pass

    try:
        log_q.put(["debug","FW","sampler_req " + sampler_req + " sampler_ver "+G_STATUS.sampler_ver])
        if(firmware_req !=G_STATUS.firmware_ver):
            G_STATUS.mp_status.updates_pending = True
            G_STATUS.mp_status.firmware_req = firmware_req
            # G_STATUS.firmware_ver = firmware_req
            log_q.put(["debug","FW",'Wanting Analyser ' + firmware_req])
        if(sampler_req !=G_STATUS.sampler_ver and G_STATUS.sampler_ver != ""): 
    # here if required ver is different to current and current isn't default ("")
            log_q.put(["debug","FW",'Wanting Sampler ' + sampler_req + ' got '+G_STATUS.sampler_ver])
            try:
                G_STATUS.mp_status.updates_pending = True
                G_STATUS.mp_status.sampler_req = sampler_req
                log_q.put(["debug","FW",'mp_status is updates_pending: ' + str(G_STATUS.mp_status.updates_pending) + "sampler_req: "+ str(G_STATUS.mp_status.sampler_req)])
            except Exception as e:
                log_q.put(["debug","FW",'mp_status exception: '+str(e)])
    except Exception as e:
        log_q.put(["debug","FW","Exception: " + str(e)])
    log_q.put(["debug","IT","Exiting parsing_device_twin"])
    return

def perform_software_updates(log_q, mp_status):
    log_q.put(["debug","IT","In perform updates function"])
    if not mp_status.sampler_req == "":
        try:
            if(download_firmware('Sampler',mp_status.sampler_req)):   #using DownloadURL+firmware_ver to download tgz file Sampler_*.*.tgz
                # do update
                log_q.put(["debug","FW","Sampler firmware download worked, let's use it"])
                S_L = Sampler_Load.Sampler_Update(log_q)
                if (S_L.main_fw_update(mp_status.sampler_req)):
                    log_q.put(["debug","FW","Sampler firmware update worked, let's go"])
                    G_STATUS.sampler_status = "FWUpgrade_Done"
                else:
                    G_STATUS.sampler_status = "FWUpgrade_Failed"
                    log_q.put(["debug","FW","Sampler firmware upgrade failed"])
            else:
                G_STATUS.sampler_status = "FWDownload_Failed"
                log_q.put(["debug","FW","Sampler firmware download Failed "])
        except Exception as e:
            G_STATUS.sampler_status = "FWUpgrade_Exception"
            log_q.put(["debug","FW","Exception getting download file: "+str(e)])
        mp_status.sampler_req = "" #clear sampler new version
    if not mp_status.firmware_req == "":
        # mp_status.updates_pending = True
        log_q.put(["debug","FW",'Wanting Analyser ' + mp_status.firmware_req])
        if (mp_status.perform_updates):
            #time to perform the update
            ver_str= get_verstr_from_ver(mp_status.firmware_req)
            log_q.put(["debug","FW",'Got Analyser' + ver_str])
            if(download_firmware('Analyser',ver_str)):   #using DownloadURL+firmware_ver to download tgz file PSS_Analyser_V*.*.tgz
                new_firmware_ver_filename="./"+ver_str+"/readme.txt"
                new_ver_str=fetch_firmware_version(new_firmware_ver_filename)         #check the version in V*.* directory
                new_ver = get_ver_from_str(new_ver_str)
                log_q.put(["warning","FW",'New ver ' + new_ver_str])
                if(new_ver == mp_status.firmware_req):
                    log_q.put(["warning","FW","Got correct firmware upgrade version"])
                    #find our deviceName and use it to get correct cfg_file
                    
                    try:
                        os.chmod('./' + ver_str + '/upgrade.sh',0o755)
                        log_q.put(['debug','FW',"chmod seems to have worked"])
                    except:
                        log_q.put(['debug','FW',"Oh dear, chmod didn't work"])
                        G_STATUS.status = "FWchmod error"
                    try:
                        log_q.put(['debug','FW',"About to run upgrade script"])
                        result = subprocess.run([DS.homeDirectory + ver_str + '/upgrade.sh', DS.deviceName], cwd=DS.homeDirectory +ver_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        log_q.put(['debug','FW',"Upgrade script run"])
                        # p.wait()
                        log_q.put(["debug","FW",'Script output: ' + str(result.stdout)])
                        if result.returncode != 0:
                            log_q.put(["debug","FW",'Script output: ' + str(result.stderr)])

                    except Exception as ex:
                        log_q.put(['error','FW',"Oh dear, upgrade script exception: " + str(ex)])
                        G_STATUS.status = "FWUpgrade exception"
                    new_ver_str=fetch_firmware_version("./readme.txt")         #check the version in V*.* directory
                    new_ver = get_ver_from_str(new_ver_str)
                    if(mp_status.firmware_req == new_ver):
                        log_q.put(["info","FW","Firmware upgrade success!"])
                        G_STATUS.status = "FWUpgrade_Done"
                        time.sleep(1)
                        send_status()  #send updated status to IoT Hub to say upgrade done
                        time.sleep(5) #give status a chance to get through
                        # restart the whole app to use the newly installed software
                        try:
                            r = subprocess.run(DS.homeDirectory + "restart.sh", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            mp_status.firmware_req = "" # clear new firmware version
                        except Exception as ex:
                            G_STATUS.status = "FWUpgrade restart exception"
                            mp_status.firmware_req = "" # clear new firmware version
                            log_q.put(['error','FW',"Oh dear, restart script exception: " + str(ex)])
                    else:
                        log_q.put(["warning","FW","Firmware upgrade Failed to copy files"])
                        G_STATUS.status = "FWUpgrade_FailCopy"
                else:
                    log_q.put(["error","FW","Got WRONG firmware upgrade version"])
                    G_STATUS.status = "GFUpgrade_WrongVersion"
            else:
                log_q.put(["error","FW","Analyser firmware download Failed "])
                
    mp_status.firmware_req == "" # we had one go, pass ot fail do not try again until retriggered
    mp_status.updates_pending = False
    mp_status.perform_updates = False
    if G_STATUS.status == "FWUpgrade_Done":
        mp_status.upgradeStatusGood = True
    else:
        mp_status.upgradeStatusGood = False
    if G_STATUS.sampler_status == "FWUpgrade_Done":
        mp_status.samplerUpgradeStatusGood = True
    else:
        mp_status.samplerUpgradeStatusGood = False
        
    send_status() #always update status in Device Twin
        
class conf_status:
    def __init__(self, mp_status, rSSH_queue):
        global gStartUpTime
        self.mp_status = mp_status # store mp_status (namespace) in G_STATUS for later use
        self.rpt_interval = (2*60)  #2 mininutes report GW status
        self.sampler_status = "Initialized"
        self.firmware_ver = ""
        self.sampler_ver = ""
        self.download_URL=""
        self.upload_URL=""
        self.status="Initialized"
        self.log_level="DEBUG"      #DEBUG, INFO, WARNING, ERROR, CRITICAL
        self.DeviceID  = 'Analyser'
        self.AN_No = '00'
        self.board_type='1'
        self.firmware_crc=''
        self.bbbUpTime=0
        self.upTime=time.time()-gStartUpTime
        self.IP='127.0.0.1'
        self.RSSHIP=''
        self.RSSHPort=0
        self.RSSHStatus='Down'
        self.CONN_STR=''
        self.rSSH_queue = rSSH_queue
        current_firmware_ver_filename="./readme.txt"
        ver_str=fetch_firmware_version(current_firmware_ver_filename)
        self.firmware_ver = get_ver_from_str(ver_str)
        self.sampler_ver = mp_status.sampler_ver
        log_q.put(["info","IT","sampler version: " + str(self.sampler_ver)])
        DS.firmware_ver = self.firmware_ver
        log_q.put(["info","IT","firmware version: " + str(self.firmware_ver)])
        self.crc_str=''
        self.SOFT_WDT_TIMEOUT=60*60 + 10*60


def fetch_firmware_version(filename):
    """
    Read readme.txt, get first line
    V1.1 Change List -> Return V1.1
    V1.2 Change List -> Retrun V1.2
    """
    import re
    f = open(filename, "r")
    content = f.read().splitlines()
    for line in content:
        m = re.search("(.+)\sChange list",line)  #+((d)<<8\s+|(d))",line)   #
        if(m):
            return m.group(1)
    return 'V1.0'

def get_ver_from_str(ver_str):
    """
    V1.1 => 11    V1.0 => 10    V1.2 => 12    V10.1 => 101    V10.2 => 102    V10.10 --> not support
    """
    if(ver_str[0]!="V"):    #invalid, return default 10
        return 10
    else:
        ret = ver_str[1:]
        ret = ret.split(' ')
        ret = ''.join(ret)
        return ret

def get_verstr_from_ver(ver):  #11->V1.1 121->V12.1

    #return "V"+str(int(ver/10))+"."+str(ver-10*(ver/10))
    return "V" + ver

def format_conf_status():
    global G_STATUS
    s_format = "{\"RptInterval\": %d, \"SamplerStatus\":\"%s\",\"FirmwareVer\": \"%s\",\"SamplerVer\": \"%s\",\"SamplerID\": \"%s\",\"FirmwareCRC\": \"%s\",\"Status\" : \"%s\",\"UpTime\": %d,\"DownloadURL\": \"%s\",\"IP\": \"%s\" ,\"RSSHIP\": \"%s\" ,\"RSSHPort\": \"%s\" ,\"RSSHStatus\": \"%s\" }"
    message = s_format%(G_STATUS.rpt_interval, G_STATUS.sampler_status,G_STATUS.firmware_ver, G_STATUS.mp_status.sampler_ver, G_STATUS.mp_status.samplerID, 
    G_STATUS.firmware_crc, G_STATUS.status, time.time() - gStartUpTime, G_STATUS.download_URL, get_ip().rstrip(), G_STATUS.RSSHIP, G_STATUS.RSSHPort, G_STATUS.RSSHStatus)
    G_STATUS.sampler_ver = G_STATUS.mp_status.sampler_ver
    G_STATUS.samplerID = G_STATUS.mp_status.samplerID
    return message

def check_conf_status_changed(s):
    global G_STATUS
    if G_STATUS.rpt_interval != s.rpt_interval :
        log_q.put(["info","IT","check_conf_status_changed: rpt_interval changed"])
        return True
    if G_STATUS.sampler_status != s.sampler_status :
        log_q.put(["info","IT","check_conf_status_changed: sampler_status changed"])
        return True
    if G_STATUS.firmware_ver != s.firmware_ver :
        log_q.put(["info","IT","check_conf_status_changed: firmware_ver changed"])
        return True
    if G_STATUS.mp_status.sampler_ver != s.sampler_ver :
        log_q.put(["info","IT","check_conf_status_changed: sampler_ver changed"])
        return True
    if G_STATUS.firmware_crc != s.firmware_crc :
        log_q.put(["info","IT","check_conf_status_changed: firmware_crc changed"])
        return True
    if G_STATUS.download_URL != s.download_URL :
        log_q.put(["info","IT","check_conf_status_changed: download_URL changed"])
        return True
    if G_STATUS.upload_URL != s.upload_URL :
        log_q.put(["info","IT","check_conf_status_changed: upload_URL changed"])
        return True
    if G_STATUS.status != s.status :
        log_q.put(["info","IT","check_conf_status_changed: status changed"])
        return True
    if G_STATUS.RSSHIP != s.RSSHIP :
        log_q.put(["info","IT","check_conf_status_changed: RSSHIP changed"])
        return True
    if G_STATUS.RSSHPort != s.RSSHPort :
        log_q.put(["info","IT","check_conf_status_changed: RSSHPort changed"])
        return True
    if G_STATUS.RSSHStatus != s.RSSHStatus :
        log_q.put(["info","IT","check_conf_status_changed: RSSHStatus changed"])
        return True
    return False

def send_status():
    global G_CLIENT, log_q
    reported_state=format_conf_status()
    log_q.put(["info","IT",reported_state])
    G_CLIENT.send_reported_state(reported_state, len(reported_state), send_reported_state_callback, SEND_REPORTED_STATE_CONTEXT+(ANALYSER_CONTEXT_NUM))
    return

def file_crc(fileName):
    global log_q
    log_q.put(["debug","FW","checking CRC of " + fileName])
    prev = 0
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)

# check the download file has the correct crc
def check_tgz_crc(tgz_name):
    global G_STATUS, log_q
    crc = file_crc(tgz_name)
    log_q.put(["debug","FW","CRC check, expected: "+G_STATUS.firmware_crc+' got '+crc])
    if(crc!= G_STATUS.firmware_crc):
        return False
    return True

import struct
from Crypto.Cipher import AES

def pad16(s):
    t = struct.pack('>I', len(s)) + s
    return t + bytes('\x00' * ((16 - len(t) % 16) % 16), 'UTF-8')

def unpad16(s):
    n = struct.unpack('>I', s[:4])[0]
    return s[4:n + 4]

class Crypt(object):
    def __init__(self, password):
        # password = pad16(password)
        self.cipher = AES.new(password, AES.MODE_ECB)

    def encrypt(self, s):
        s = pad16(s)
        return self.cipher.encrypt(s)

    def decrypt(self, s):
        t = self.cipher.decrypt(s)
        return unpad16(t)

def decypt_tgz(tgz_filename):
    from Crypto.Cipher import AES
    global log_q
    p = 'AnalyserFirmware@Atamo01'.encode()
    #p = 'PSSAnalyserFirmware@Atamo01'
    c = Crypt(p)

    f_rd = open(tgz_filename, "rb")
    log_q.put(["debug","IT",'filename ' + tgz_filename])
    f_wr = open("plain"+tgz_filename, "wb+")
    content = f_rd.read()
    ret=True
    try: 
        tgz_c = c.decrypt(content)
        log_q.put(["error","IT","Success when Decrypting tgz file:" + tgz_filename])
    except:
        ret = False
        log_q.put(["error","IT","Error when Decrypting tgz file:" + tgz_filename])
    f_wr.write(tgz_c)
    f_rd.close()
    f_wr.close()
    return ret

def download_firmware(device, ver_str):
    """
    Download file from download_URL+ Analyser_x_v**.tgz wgere v** is the ver_str
    It will check the current directory to see if this file has been downloaded, if yes, report "already_done". Or else report "new_done"
    """
    global log_q
    log_q.put(["debug","FW",'Really wanting ' + device + ' ' + ver_str])
    tgz_name=device + "_"+ver_str+".tgz"
    log_q.put(["info","FW","Downloading "+tgz_name])
    if(os.path.isfile(tgz_name) ):      #already downloaded, skip download
        log_q.put(["error","FW","Firmware file already downloaded"])
        if(check_tgz_crc(tgz_name)):# and (G_GW_STATUS.gw_status != "already_done")):
            if(decypt_tgz(tgz_name)):
                log_q.put(["info","FW","Decrypting done"])
                tar = tarfile.open("plain"+tgz_name)                    
                tar.extractall()
                tar.close()            
                G_STATUS.status = "FWalready_done"
                # send_status()
                log_q.put(["info","FW","Already has the tgz file, done."])
                return True
            else:
                G_STATUS.status = "Decrypt_error"
                # send_status()
                log_q.put(["error","FW","Firmware decryption error!"])
                return False
                
    else:
        log_q.put(["info","FW","Need to download"])
    full_url= G_STATUS.download_URL + tgz_name
    log_q.put(["info","FW","Download URL: "+full_url])
    try:
        r = requests.get(full_url)
    except requests.exceptions.RequestException as e:
        log_q.put(["error", "IT",str(e)])
        G_STATUS.status = "Fdownload_error"
        log_q.put(["error","FW","Downloading error..."])
        # send_status()
        return False
    if r.ok:
        open(tgz_name , 'wb').write(r.content) 
        log_q.put(["debug","FW","Checking CRC"])
        if(check_tgz_crc(tgz_name)):                    
            if(decypt_tgz(tgz_name)):
                try:
                    tar = tarfile.open("plain"+tgz_name)    
                except:
                    log_q.put("error","FW","Error when opening plain_" + tgz_name)
                    G_STATUS.status = "Fopen_error"
                    # send_status()
                    return
                tar.extractall()
                tar.close()    
                G_STATUS.status = "Fnew_done"
                log_q.put(["info","FW","Successfully downloaded and unzip file " + tgz_name])
                # send_status()
                return True
        else:
            log_q.put(["error","FW","CRC Error when opening " + tgz_name])
            G_STATUS.status = "Fcrc_error"
            # send_status()
            return False
    else:
        G_STATUS.status = "FWdownload_error"
        log_q.put(["error","FW","Download Error when Downloading " + tgz_name])
        # send_status()
        return False
    return False
    

def set_certificates(self, client):
    from iothub_client_cert import CERTIFICATES
    try:
        client.set_option("TrustedCerts", CERTIFICATES)
        self.log_q.put(["info", "IT", "set_option TrustedCerts successful" ])
    except IoTHubClientError as iothub_client_error:
        self.log_q.put(["error", "IT", "set_option TrustedCerts failed (%s)" % iothub_client_error ])

def iothub_client_init(self, contextNo, conn_str):
    # prepare iothub client
    client = IoTHubClient(conn_str, PROTOCOL)
    if client.protocol == IoTHubTransportProvider.HTTP:
        client.set_option("timeout", TIMEOUT)
        client.set_option("MinimumPollingTime", MINIMUM_POLLING_TIME)
    # set the time until a message times out
    client.set_option("messageTimeout", MESSAGE_TIMEOUT)
    # some embedded platforms need certificate information
    set_certificates(self, client)
    # to enable MQTT logging set to 1
    if client.protocol == IoTHubTransportProvider.MQTT:
        client.set_option("logtrace", 0)
    client.set_message_callback(
        receive_message_callback, contextNo)
    if client.protocol == IoTHubTransportProvider.MQTT or client.protocol == IoTHubTransportProvider.MQTT_WS:
        client.set_device_twin_callback(
            device_twin_callback, contextNo)
        client.set_device_method_callback(
            device_method_callback, contextNo)
    if client.protocol == IoTHubTransportProvider.AMQP or client.protocol == IoTHubTransportProvider.AMQP_WS:
        client.set_connection_status_callback(
            connection_status_callback, contextNo)

    retryPolicy = IoTHubClientRetryPolicy.RETRY_INTERVAL
    retryInterval = 100
    client.set_retry_policy(retryPolicy, retryInterval)
    self.log_q.put(["info", "IT", "SetRetryPolicy to: retryPolicy = %d" %  retryPolicy])
    self.log_q.put(["info", "IT", "SetRetryPolicy to: retryTimeoutLimitInSeconds = %d" %  retryInterval])
    retryPolicyReturn = client.get_retry_policy()
    self.log_q.put(["info", "IT", "GetRetryPolicy returned: retryPolicy = %d" %  retryPolicyReturn.retryPolicy])
    self.log_q.put(["info", "IT", "GetRetryPolicy returned: retryTimeoutLimitInSeconds = %d" %  retryPolicyReturn.retryTimeoutLimitInSeconds])

    return client 


def send_telemetry(client, message, send_confirmation_callback, message_counter):
    global confirmation_received, log_q
    confirmation_received = 'Now'
    conf_count = 0
    try:
        client.send_event_async(message, send_confirmation_callback, message_counter)
        log_q.put(["info","IT","IoTHubClient.send_event_async accepted message for transmission to IoT Hub."])
    except:
        log_q.put(["error","IT","!error send_telemetry: %s"%(message)])
    #wait for response
    while True:
        if confirmation_received == 'Now':
            conf_count += 1
            if conf_count < 30:
                time.sleep(1)
                log_q.put(["info","IT",'Conf count is %s' % str(conf_count)])
            else:
                # we've waited long enough for a confirmation, assume it isn't coming
                log_q.put(["error","IT","Timeout waiting for confirmation of message %d" % message_counter])
                return False
            #return
        #got a confirmation from IoT Hub
        else:
            if (str(confirmation_received) == "OK"):
                log_q.put(["info","IT","IoTHubClient.send_event_async accepted results message [%d] for transmission to IoT Hub." % message_counter ])
                print ('Upload of data complete')
                return True
            else:
                log_q.put(["error","IT","IoTHub doesn't like our transmission. Fix a problem"])
                return False

def get_iot_client():
    global G_CLIENT
    return G_CLIENT
                
def Analyser_connect_IoTHub(self, connection_str):
    """
    Connect GW to IoTHub
    """
    global G_CLIENT
    # global gSite
    # global gSiteKey
    AnalyserContextNo=ANALYSER_CONTEXT_NUM
    # ANALYSER_CONN_STR= CONN_STR_FMT%(gSite,G_STATUS.DeviceID)
    # ANALYSER_CONN_STR= GW_CONN_STR + G_STATUS.CONN_STR
    print("Connecting, Context " + str(AnalyserContextNo) + " Conn Str " + connection_str)
    G_CLIENT = iothub_client_init(self, AnalyserContextNo, connection_str)
    print("Client = " + str(G_CLIENT))
    return    

def change_RSSHStatus(status):
    # to do this we need a valid IP Address for the RSSH HostName
    log_q.put(["debug","IT","RSSHStatus changed: "+status])
    try:
        ipaddress.ip_address(G_STATUS.RSSHIP)
    except:
        log_q.put(["error","IT","Can't change RSSHStatus, no RSSHIP"])
        return
    try:
        if not int(G_STATUS.RSSHPort) > 49999 and int(G_STATUS.RSSHPort) < 51000:
            # we don't have a valid port
            log_q.put(["error","IT","Can't change RSSHStatus, no valid RSSHPort" + str(G_STATUS.RSSHPort)])
            return
    except:
        log_q.put(["error","IT","Can't change RSSHStatus, no valid RSSHPort" + str(G_STATUS.RSSHPort)])
        return
    # we seem to have an RSSHIP and a valid RSSHPort
    # do status change
    if status == "Up":
        # set up the reverseSSH tunnel
        try:
            log_q.put(["error","IT","Creating reverseSSH tunnel for: " + G_STATUS.RSSHIP + '/' + G_STATUS.RSSHPort])
            G_STATUS.rSSH_queue.put(["Up", G_STATUS.RSSHIP, G_STATUS.RSSHPort])
            # r = subprocess.Popen(["/home/debian/PSS/createreverse.sh",G_STATUS.RSSHIP,G_STATUS.RSSHPort])
            log_q.put(["error","IT","Created reverseSSH tunnel"])
        except Exception as e:
            log_q.put(["error","IT","Exception creating reverseSSH tunnel: " + str(e)])
    elif status == "Down":
        # tear down the reverseSSH tunnel
        try:
            log_q.put(["error","IT","Killing reverseSSH tunnel"])
            G_STATUS.rSSH_queue.put(["Down", G_STATUS.RSSHIP, G_STATUS.RSSHPort])
            # r = subprocess.run(["/home/debian/PSS/killreverse.sh",G_STATUS.RSSHIP,G_STATUS.RSSHPort], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            log_q.put(["error","IT","Exception killing reverseSSH tunnel: " + str(e)])
    else:
        # invalid RSSHStatus requests
        log_q.put(["error","IT","Invalid RSSHStatus request" + str(status)])
    

def change_log_level(level):
    """
    Changing log level
    """
    if (level == "DEBUG"):
        log_q.put(["warning","IT","Changing log level to DEBUG"])
        log.set_level(logging.DEBUG)
    elif (level == "INFO"):
        log_q.put(["warning","IT","Changing log level to INFO"]) 
        log.set_level(logging.INFO)
    elif (level == "WARNING"):
        log_q.put(["warning","IT","Changing log level to WARNING"])
        log.set_level(logging.WARNING)
    elif (level == "ERROR"):
        log_q.put(["warning","IT","Changing log level to ERROR"])
        log.set_level(logging.ERROR)
    elif (level == "CRITICAL"):
        log_q.put(["warning""IT","Changing log level to CRITICAL"])
        log.set_level(logging.CRITICAL)
    else:
        log_q.put(["error","IT","!Changing log level error %s"%level])



def get_ip():
    try:
        r = subprocess.run(["/home/debian/PSS/getIP.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_q.put(['info','IT',"getIP got: " + r.stdout.decode('utf-8')])
        if not r.stdout.decode('utf-8') == '':
            return r.stdout.decode('utf-8')
        else:
             return '127.0.0.1'
    except Exception as ex:
        log_q.put(['error','IT',"Oh dear, getIP script exception: " + str(ex)])
        return '127.0.0.1'

def get_cmd_output(cmd):
    """
    Get the output string from running the cmd
    """
    import platform
    import sys
    on_wsl = "microsoft" in platform.uname()[3].lower()    
    if sys.platform == "linux" or sys.platform == "linux2" or on_wsl:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.stdout.readlines()
    return ''

def do_diagnose():
    debug_str=[]
    cmd = ["df |grep mmcblk",  "cat /proc/meminfo |grep MemFree" , "ip a |grep ppp0", "tail -n 50 /home/debian/PSS/AnalyserIoT.log", "systemctl status DaviesRun","systemctl status DaviesModem","tail -n 50 /var/log/daemon.log"]
    for cmd1 in cmd:
        debug_str += get_cmd_output(cmd1)

    last_str=""
    for str1 in debug_str:
        print("A response line: " + str1.decode('UTF-8'))
        last_str+=str1.decode('UTF-8')

    return last_str

def do_execmd(cmd):
    debug_str=[]
    debug_str=get_cmd_output(cmd)
    last_str=""
    for str1 in debug_str:
        last_str+=str1.decode('UTF-8')

    return last_str
    #return last_str[-MAX_SIZE_DIRECT_METHOD:]

import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
#import StringIO
import contextlib

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old
def do_exec_python(p_code):
    log_q.put(["warning","PY",p_code])
    with stdoutIO() as s:
        exec(p_code)
    log_q.put(["warning","PY","exec result||| "+s.getvalue()])
    return s.getvalue()[-MAX_SIZE_DIRECT_METHOD:]    
# ------------------------------------- firmware version ---------------------


CMD_RUN_FILE_NAME="__cmd_run.txt"
import signal,threading
class ExeCmdLongRun(object):
    def __init__(self, cmd):
        self.cmd = cmd #+" > " + CMD_RUN_FILE_NAME
        self.process = None
        self.return_str = ''
        self.thread =None
        try:
            os.remove(CMD_RUN_FILE_NAME)
        except:
            pass

    def run(self):
        def target():
            self.process = subprocess.Popen(self.cmd +" > " + CMD_RUN_FILE_NAME, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,preexec_fn=os.setsid)

        self.thread = threading.Thread(target=target)
        self.thread.start()
        return self.cmd + " is running..."

    def check_running(self):
        return self.thread.is_alive()
    
    def get_output(self):
        try:
            f = open(CMD_RUN_FILE_NAME,'r')
            message = f. read()
            f.close()
        except:
            message=''
        return message[-MAX_SIZE_DIRECT_METHOD:]
    
    def kill_thread(self):
        self.thread.join()      #(self.timeout)
        try: #if self.thread.is_alive():
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.thread.join()
        except:
            pass
        return self.get_output()
    
def do_execmd_longrun(cmd):
    """
    Longrun command running control:
    r: xxxx -> Run command of xxxx, will kill old one before running
    k:            -> Kill command of xxxx if it is still running
    l:            -> list running command xxxx, or ''
    f:            -> Fetch screen output of the xxxx
    Hint: run a 'ls' as the last command will safely terminate longrun program
    """
    global g_longrun_command 
    c=cmd[0:2]
    if(c=='r:'):
        if(g_longrun_command !=None):
            try:
                ret=g_longrun_command.kill_thread()
            except:
                ret = "Nothing to kill"
        g_longrun_command=ExeCmdLongRun(cmd[2:])
        return g_longrun_command.run()
    
    if(g_longrun_command ==None):
        return "Not Initialized!"
    
    if(c=='k:'):
        try:
            ret=g_longrun_command.kill_thread()
        except:
            ret = "Nothing to kill"
        return ret
    
    if(c=='l:'):
        if g_longrun_command.check_running():
            return "Longrun program: " + g_longrun_command.cmd
        else:
            return "No longrun program"

    if (c=='f:'):
        return g_longrun_command.get_output()

    log_q.put(["error","IT", "Do_execmd_longrun got wrong command, ignore it"])
    return "Do_execmd_longrun got wrong command, ignore it"    


