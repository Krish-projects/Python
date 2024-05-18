import socket
import random
import time, datetime
import sys,os, shutil
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
from iothub_client import IoTHubClientRetryPolicy, GetRetryPolicyReturnValue

import csv
import _thread, cmd, threading

import pss_log
SERIAL_BAUD = 9600    #115200 #9600
import platform
import sys
import traceback
import Analyser_AzureIoT as IoT   #for all global variables
import json
import multiprocessing as mp
from multiprocessing import Value
import queue
import subprocess
import logging
import pss_log
import requests
import PSS_Charging as CH
import check_power_button as PB
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import deviceStatus as DS
import Adafruit_BBIO.GPIO as GPIO
import serial

#results_path = '/home/debian/PSS/Results/results/'
results_path = DS.resultsDirectory + 'results/'
logPath = DS.homeRwDirectory
#sent_results_path = '/home/debian/PSS/Results/sent_results/'
sent_results_path = DS.resultsDirectory + 'sent_results/'
#G_AN_STATUS = []

# print ("Analyser_cloud.py first call startin at : startupTime",datetime.datetime.now())

class cloud():
    def __init__(self, connection_str, telemetry_queue, internet_is_up, internet_is_down, prepare_for_sleep, preparing_for_sleep, ready_for_sleep, analyser_charge_queue, sampler_charge_queue, mp_status, log_queue):
        global message_counter    
        # print("In Analyser Cloud, Cloud starting at ", datetime.datetime.now())
        print ( "\nPython %s" % sys.version )
        print ( "IoT Hub Client for Python" )
        # set ourselves to low priority
        self.log_q = log_queue
        self.mp_status = mp_status
        global log
        log=pss_log.LoggerWrapper('AnalyserIoT', filename=logPath + 'AnalyserIoT.log',level=logging.DEBUG,console=True)
        self.telemetry_q = telemetry_queue
        self.internet_up = internet_is_up
        self.internet_down = internet_is_down
        preparing_for_sleep.value = 0
        self.internetIsUp = False #initialise to Internet down
        #self.preparing_to_sleep = False
        #self.log_q.put(["info","CL", "Process started"])
        pid=os.getpid()
        os.system("renice 20 -p %d"%pid)        #Put the main loop to loweest priority (IoTHub)
        self.log_q.put(["warning","CL", "Set main_loop:%d nice to 20"%pid])
        rSSH_queue = mp.Queue()
        IoT.init(connection_str, self.mp_status, rSSH_queue, self.log_q)
        message_counter = 0
        self.telemetry_unsent = []
        try:
            threading.Thread(name="Logger Thread", target=self.logger_thread, args=(log_queue,) ).start()
            self.log_q.put(["warning","CL","Starting Log Queue thread"])    
        except:
            self.log_q.put(["error","CL","Unable to start Log Queue thread!"])
        try:
            threading.Thread(name="Internet Thread", target=self.internet_thread, args=(log_queue, mp_status) ).start()
            self.log_q.put(["warning","CL","Starting Internet check thread"])    
        except:
            self.log_q.put(["error","CL","Unable to start Internet check thread!"])
        self.log_q.put(["warning","CL","Starting Analyser Charge thread"])    
        try:
            ach = CH.analyser_charge(analyser_charge_queue,log_queue)
        except:
            self.log_q.put(["error","CL","Unable to init Analyser Charge thread!"])
        try:
            # # threading.Thread(name="Analyser Charge Thread", target=ach.run() ).start()
            ach.start()
        except:
            self.log_q.put(["error","CL","Unable to start Analyser Charge thread!"])
        try:
            threading.Thread(name="Power Button Thread", target=PB.power_button_monitor, args=(log_queue,) ).start()
            self.log_q.put(["warning","CL","Starting Power Button monitor thread"])    
        except Exception as e:
            self.log_q.put(["error","CL","Unable to start Power Button monitor thread!" + str(e)])
        try:
            threading.Thread(name="Prepare for sleep Thread", target=self.prepare_for_sleep, args=(prepare_for_sleep, preparing_for_sleep, log_queue) ).start()
            self.log_q.put(["warning","CL","Starting Prepare for sleep thread"])    
        except:
           self.log_q.put(["error","CL","Unable to start Prepare for sleep thread!"])
        try:
            threading.Thread(name="ReverseSSH Thread", target=self.rSSH_thread, args=(log_queue, rSSH_queue) ).start()
            self.log_q.put(["warning","CL","Starting ReverseSSH thread"])    
        except:
           self.log_q.put(["error","CL","Unable to start ReverseSSH thread!"])
        # if result directories don't exist create them
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        os.makedirs(os.path.dirname(sent_results_path), exist_ok=True)
        # Start modem thread
        # self.telemetry_q.put('{"Hello":"Boys", "Goodbye":"Girls"}')

    def logger_thread(self, q):
        while True:
            record = q.get()    #format: ['error/warning/info/debug/', ID, str]
            try:
                ID = record[1]
                MSG = record[2]
            except:
                ID = 'IO'
                MSG = 'Exception in log' + str(record)
            # ID = record[1]
            # MSG = record[2]            
            if record[0]=='error':
                log.error(ID, MSG)
            if record[0]=='warning':
                log.warning(ID, MSG)
            if record[0]=='info':
                log.info(ID, MSG)
            if record[0]=='debug':
                log.debug(ID, MSG)
        return

    def prepare_for_sleep(self, prepare_for_sleep, preparing_for_sleep, log_q):
        event_is_set = prepare_for_sleep.wait()
        log_q.put(["debug","CL", "Got prepare for sleep event"])
        preparing_for_sleep.value = True
        #client = IoT.get_iot_client()
        #self.process_result_files(client, True)
        
        
    def internet_thread(self,log_q, mp_status, host="8.8.8.8", port=53, timeout=3):
        internetIsUp = False
        while True:
            try:
                # self.log_q.put(["error","CL","Internet check: "])
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
                # self.log_q.put(["error","CL","Internet OK: "])
                mp_status.connectionStatus = True
            except Exception as ex:
                mp_status.connectionStatus = False
            RSSI = self.getRSSI()   # update shared value so front end can display it
            DS.RSSI = RSSI
            # self.log_q.put(["info","CL","RSSI is: %s"%str(RSSI)])

            time.sleep(10)
            
    def rSSH_thread(self, log_q, rSSH_queue):
        while True:
            entry = rSSH_queue.get()
            try: # avoid a race
                if entry[0] == "Up":
                    log_q.put(["error","RS","Got RSSH Up event"])
                    try:
                        r = subprocess.Popen(["/home/debian/PSS/createreverse.sh",entry[1],entry[2]])
                    except Exception as e:
                        log_q.put(["error","CL","RSSH Up exception: " + str(e)])
                elif entry[0] == "Down":
                    log_q.put(["error","RS","Got RSSH Down event"])
                    try:
                        r = subprocess.run(["/home/debian/PSS/killreverse.sh",entry[1],entry[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except Exception as e:
                        log_q.put(["error","CL","RSSH Down exception: " + str(e)])
            except:
                pass
        time.sleep(2)
                

    def internet(self,log_q, host="8.8.8.8", port=53, timeout=3):
            try:
                # self.log_q.put(["error","CL","Checking Internet"])
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
                # self.log_q.put(["error","CL","Internet OK: "])
                return True
            except Exception as ex:
                self.log_q.put(["error","CL","Internet Down: "+str(ex)])
                return False

    def getRSSI(self):
        # get the info from the modem
        rssi = 0
        if os.path.exists('/dev/ttyACM2'): # if device not there no point in trying to read RSSI from it
            try:
                self.modemserial   = serial.Serial('/dev/ttyACM2',115200,timeout=1)
                self.modemserial.write("AT+CSQ\r\n".encode('ascii'))
                self.echocommand = self.modemserial.readline()
                self.response = self.modemserial.readline()
                self.newline = self.modemserial.readline()
                self.ack = self.modemserial.readline()
                # now dig out the RSSI from the surrounding guff
                self.response = self.response.decode('ascii')
                self.split_response = self.response.split()
                rssi =self.split_response[1].split(',')
                rssi = rssi[0]
                self.modemserial.close()
                DS.modemRSSI = int(rssi)   # update shared value so front end can display it
            except Exception as e:
                self.log_q.put(["debug","CL","getting RSSI exception: %s"%str(e)])
        return rssi

    def process_result_files(self, client, preparing_for_sleep, ready_for_sleep):
        # self.log_q.put(["debug","CL",'Processing Results in ' + results_path])
        for root, dirs, files in os.walk(results_path):
            #print (files)
            if files:
                for file in files:
    #                process_results(client, results_path + file)
                    self.log_q.put(["debug","CL",'Processing ' + file])
                    with open(results_path + file, 'r') as f:
                        message_content = f.read()
                    self.log_q.put(["debug","CL",message_content])
                    message_string = message_content
                    if self.send_to_iothub(message_string, client):
                        shutil.move(results_path + file, sent_results_path + file)
        #Process queued results
        # Process unsent telemetry list
        # self.log_q.put(["debug","CL","Processing unsent list"])
        entries = len(self.telemetry_unsent)
        # self.log_q.put(["debug","CL","Count of unsent results is" + str(entries)])
        fileCount = 0
        for entry in range (0, entries):
            data = self.telemetry_unsent.pop()
            self.log_q.put(["debug","CL","Attempting to send an entry from unsent list"])
            if self.send_to_iothub(data, client):
                self.log_q.put(["debug","CL","entry sent"])
            else:
            # if we're preparing for sleep then save failed transmits to disk
                if preparing_for_sleep.value:
                    newfile = time.strftime("%Y%m%d-%H%M%S") + "_" + str(fileCount)
                    fileCount += 1
                    with open(results_path + newfile, 'w') as f:
                        f.write(data)
                        self.log_q.put(["debug","CL","Saving result file to " + results_path + newfile])
                # if not preparing for sleep then append them to the resend list
                else:    
                    # sending failed, add it back to the end of the list
                    self.telemetry_unsent.append(data)
        # self.log_q.put(["debug","CL","Checking Telemetry Q"])
        while True:
            fileCount = 100 # used to append to filename to ensure it is unique
            try:
                data = self.telemetry_q.get_nowait()
                self.log_q.put(["debug","CL","Something in queue" + str(data)])
                if self.send_to_iothub(data, client):
                    self.log_q.put(["debug","CL","Something sent from q OK"])
                #else:
                else:    
                    if preparing_for_sleep.value:
                    #we're preparing for sleep so save to file
                        newfile = time.strftime("%Y%m%d-%H%M%S") + "_" + str(fileCount)
                        with open(results_path + newfile, 'w') as f:
                            f.write(data)
                            self.log_q.put(["debug","CL","Saving result file to " + results_path + newfile])
                #problem sending data from Q save as file to be processed next time
                    else:
                        self.log_q.put(["debug","CL","Problem sending, add to unsent list"])
                        self.telemetry_unsent.append(data)
            except queue.Empty:
                # self.log_q.put(["debug","CL","Nothing left in queue"])
                break
        if preparing_for_sleep.value == True:
            self.log_q.put(["debug","CL","We're ready for sleep"])
            ready_for_sleep.set()
            preparing_for_sleep.value = False
                
    def send_to_iothub(self, message_string, client):
        global message_counter
        message_counter = message_counter + 1
        self.log_q.put(["debug","CL","Message: " +message_string])
        # only worth trying to send if there is an internet connection
        if self.internet(self.log_q):
            try:
                message = IoT.IoTHubMessage(bytearray(message_string, 'utf8'))
            except:
                self.log_q.put(["error","CL","IoT SDK doesn't like this message"])
                return False
            message.message_id = "message_%d" % message_counter
            message.correlation_id = "correlation_%d" % message_counter
            # optional: assign properties
            prop_map = message.properties()
            if IoT.send_telemetry(client, message, IoT.send_confirmation_callback, message_counter):
                return True
            else:
                return False
        else:
            return False
    


    def iothub_client_sample_run(self, connection_str, telemetry_q, internet_up, internet_down, prepare_for_sleep, preparing_for_sleep, ready_for_sleep, mp_status, log_q):
        global G_AN_STATUS
        try:
    #   #    client = iothub_client_init()
            while not mp_status.connectionStatus:
                time.sleep(10) # no point progressing to connect if we don't have internet
                self.log_q.put(["error","CL", "No Internet, no point connecting to IoT Hub"])
                if preparing_for_sleep.value:
                # if we've never connected to the IoT Hub this will save all pending results
                # then set ready for sleep event so we can close down
                    self.process_result_files("", preparing_for_sleep, ready_for_sleep) # call with dummy client id
            IoT.Analyser_connect_IoTHub(self, connection_str)
            print ( "IoTHubClient is reporting state" )
            reported_state = IoT.format_conf_status()
            self.log_q.put(["info","CL", "IoTHubClient Reported State " + reported_state])
            IoT.G_CLIENT.send_reported_state(reported_state, len(reported_state), IoT.send_reported_state_callback, IoT.SEND_REPORTED_STATE_CONTEXT)
            self.internet_is_good = 1  
            last_internet_is_good=1
            g_firmware_version = 10
            # rpt_timeout = time.time() + IoT.G_STATUS.rpt_interval        # initialise report interval
            rpt_timeout = time.time() + 120
            #message_counter = 0
            while True:

                status_counter = 0
                self.process_result_files(IoT.G_CLIENT, preparing_for_sleep, ready_for_sleep)
                status = IoT.G_CLIENT.get_send_status()
                print ( "Send status: %s" % status )
                time.sleep(5)
                status_counter += 1
                if mp_status.connectionStatus:
                    # log_q.put(["debug","CL", "Internet is good"])
                    if mp_status.perform_updates:
                        IoT.perform_software_updates(self.log_q, mp_status)
                    if time.time()>rpt_timeout:        # GW timely report its status to IoTHub
                        if (IoT.g_callback_flag):        # During last two minutes, no GW call back happens, recover the GW connection.
                            self.log_q.put(["error","CL", "During last GW report interval, no GW call back, reconnect."])
                            IoT.Analyser_connect_IoTHub(self, connection_str)
                            self.log_q.put(["info","CL", "Report interval, Sending status"])
                            g_callback_flag=True
                            IoT.send_status()                # Every report interval, report status to IoTHub
                            rpt_timeout = time.time() + IoT.G_STATUS.rpt_interval        # by default, 5 minutes check once
                else:
                        self.log_q.put(["debug","CL","Internet no good"])
                    # else:
                        # log_q.put(["info","CL", "Report interval, do nothing, NO Internet"])

        except IoTHubError as iothub_error:
            self.log_q.put(["error","CL", "Unexpected error %s from IoTHub" % iothub_error] )
            return
        except KeyboardInterrupt:
            self.log_q.put(["error","CL","IoTHubClient sample stopped by keyboard input"] )


        


