

#!/usr/bin/env python3
import socket
import threading
import time
import subprocess
ACPID_SOCKETFILE = "/var/run/acpid.socket"
RECV_SIZE = 4096

class power_button():
    def __init__(self, log_q):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.connect(ACPID_SOCKETFILE)
        self.s.settimeout(None)
        self.pkt    =b''
        self.flag   = False     #button push flag
        self.log_q = log_q
        self.log_q.put(["debug","PB","Starting power button thread"])
        try:
            bt_thread = threading.Thread(name="Button Checking Thread", target=self.checking, args=() )
            bt_thread.start()
        except Exception as ex:
            self.log_q.put(["error","PB","power_button_init: exception when starting power_button_thread: " + str(ex)])    

    def checking(self):
        try:
            while True:
                data = self.s.recv(RECV_SIZE)
                self.pkt += data
                if(self.pkt[len(self.pkt)-1]==ord('\n')):
                    self.log_q.put(["debug","PB",self.pkt])
                    self.pkt = b''
                    self.flag = True
        except:
            self.s.close()
            raise
    def read(self):
        if self.flag == True:
            self.flag = False
            return True
        else:
            return False

    def monitor(self, pb, log_q):
        screenOn = True
        while (1):
            flag = pb.read()
            if(flag):
                self.log_q.put(["debug","PB","key pushed!"])
                if screenOn:
                    # turn screen off
                    self.log_q.put(["debug","PB","screen off"])
                    time.sleep(0.5)
                    subprocess.run("/home/debian/PSS/screenoff.sh")
                    # xset -display :0 -s activate
                    screenOn = False
                else:
                    self.log_q.put(["debug","PB","screen on"])
                    subprocess.run("/home/debian/PSS/screenon.sh")
                    # xset -display :0 -s reset
                    screenOn = True
            else:
                time.sleep(0.1)


def power_button_monitor(log_q):
    log_q.put(["info","PB","Init power button!"])
    pb = power_button(log_q)
    screenOn = True
    while (1):
        flag = pb.read()
        if(flag):
            log_q.put(["debug","PB","key pushed!"])
            if screenOn:
                # turn screen off
                log_q.put(["debug","PB","screen off"])
                time.sleep(0.5)
                subprocess.run("/home/debian/PSS/screenoff.sh")
                # xset -display :0 -s activate
                screenOn = False
            else:
                log_q.put(["debug","PB","screen on"])
                subprocess.run("/home/debian/PSS/screenon.sh")
                # xset -display :0 -s reset
                screenOn = True
        else:
            time.sleep(0.1)
