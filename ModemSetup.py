#!/usr/bin/python
# ##################################################################################################
# After bring up Modem, send a email to display the IP address
# ##################################################################################################
import socket
import os
import time
import csv
# import subprocess
# from sys import platform
import Adafruit_BBIO.GPIO as GPIO
# import serial,time

import smtplib
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_AnalyserNo():
    with open('/home/debian/PSS/cfg_file.csv', 'r') as f:
        alllines = csv.reader(f, delimiter='\t')
        device=''
        for line in alllines:
            if(line[0] =='DeviceName'):
                print("Device is: "+ line[1])
                device= line[1]
    return device

def send_ip_email():
    server = smtplib.SMTP()
    server.connect("smtp.gmail.com",587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login("alfresco@atamo.com.au", "Globebicyclet03")
    IP=get_ip()
    #msg = 'Analyser:' + IP +'\n' + get_AnalyserNo()  # The /n separates the message from the headers
    msg = "Hello!" + IP +'\n' + get_AnalyserNo()  # The /n separates the message from the headers
    print("before sending .............")
    server.sendmail("alfresco@atamo.com.au", "andrew.holmes@atamo.com.au", msg)
    server.quit()
    print("after sending .............")
    return

def internet(host="8.8.8.8", port=53, timeout=5):
    for i in range(3):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception as ex:
            print (ex)
            #return False
    return False

def BringUpModem():
    try:
        # start by diasabling modem then turning off power
        # this is in case this is a restart rather than just a start
        GPIO.setup("P8_13",GPIO.OUT)
        GPIO.output("P8_13",GPIO.LOW)        #modem disable
        GPIO.setup("P8_16",GPIO.OUT)
        GPIO.output("P8_16",GPIO.LOW) #3.7V OFF
        time.sleep(1) # Wait a bit
        GPIO.output("P8_16",GPIO.HIGH) #3.7V ON
        time.sleep(0.6)
        GPIO.output("P8_13",GPIO.HIGH)        #modem enable

    except:
        print("error happened when opening GPIO")
    print("enabled modem!!!! waiting for some time")
    wait_modem_time=time.time()
    while(1):
        ttyACM0_ready=os.system("ls /dev/ttyACM0")
        if(ttyACM0_ready==0):
            print("/dev/ttyACM0 there but still need to wait a while")
            time.sleep(10)
            break;
        time.sleep(1)
        if(time.time()-wait_modem_time >=15):
            print("Waited too long time to open modem")
            exit(1)
    print("Found /dev/ttyACM0")
    try:        
        # os.system("/sbin/ifconfig wlan0 down")
        # print("Ifconfig WLAN0 DOWN")
        # time.sleep(5)
        print("Dialing with WVDIAL")
        os.system("wvdial &")
        time.sleep(2)
        time.sleep(10)
        os.system("/sbin/route add default dev ppp0")
    except:
        print("Something is wrong with the modem")
    print("Changed default dev to ppp0!")
    return
BringUpModem()
    
time.sleep(60)
print("Sending ip address"+ get_ip())
try:
    send_ip_email()
except:
    print("!!Something wrong when sending ip address via email")
while(1):
    if(not internet()):
        break   #let systemd to restart
    time.sleep(60)

exit(1)
