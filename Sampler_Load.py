#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import sys
import serial
import crc
import time
import Adafruit_BBIO.GPIO as GPIO
import crc8
import zlib

class Sampler_Update():
    def __init__(self, log_q):
        self.samplerSerial=serial.Serial(port = "/dev/ttyO4", baudrate=115200,timeout=2)
        GPIO.setup("P9_15", GPIO.IN)
        GPIO.setup("P8_15",GPIO.OUT)
        GPIO.output("P8_15",GPIO.HIGH) #set command (not charge) mode
        self.log_q = log_q


    def get_main_fw_version(self):
        fwversion = self.mainfirmwareversion.text()
        # print(fwversion)
        return fwversion

    def read_invalid(self):      
        y = GPIO.input("P9_15")
        return y

    def set_TxE(self,x):
        if x==0:
            GPIO.output("P9_12", GPIO.LOW)
        else:
            GPIO.output("P9_12", GPIO.HIGH)
        return x    
    
    def write_data(self,ser,bits):
        ser.write(bits)
    
    def send_command(self,command):
            print("ready")
            
            self.set_TxE(1)    #Set invalid high (valid signal)
            charge = 50*(b'\x00') 
            eol_char = '\n'.encode('ascii')
            seq_number = chr(32).encode('ascii')
            finalCMD = charge+crc.append_crc(command)+seq_number+eol_char
            # print("finalCMD:%s"%str(finalCMD))
            self.log_q.put(["debug","ST","finalCMD:%s"%str(finalCMD)])
            self.write_data(self.samplerSerial,finalCMD)
            
            time.sleep(0.1)
            self.set_TxE(0)    #Set invalid low (no valid signal)
            response = self.samplerSerial.readline()        #read until EOL (\n) character 
            # print ("Response is:",response)
            self.log_q.put(["debug","ST","Response is:%s"%str(response)])
            timeout = 1     #second
            timeout_start = time.time() #current time
            while ((self.read_invalid() == 1) and (time.time() < timeout_start + timeout)):
                self.log_q.put(["debug","ST","in loop - sampler invalid signal high"])
                # print ("in loop - sampler invalid signal high")
            if (self.read_invalid() == 0):
                self.set_TxE(1)
                self.log_q.put(["debug","ST","in if statement"])
                # print ("in if statement")
            return response
    
    def init_main_bootloader(self, ser):
        self.log_q.put(["error","FW","In init_nain_bootloader"])
        self.set_TxE(1)    #Set invalid high (valid signal)

        charge = 50*(b'\x00')
        
        command = b'\x8C' + 'F'.encode('ascii') +  '00'.encode('ascii')   #Hard coded Rotate command (slow)
        eol_char = '\n'.encode('ascii')
        seq_number = 'z'.encode('ascii')
        self.write_data(ser,charge+crc.append_crc(command)+seq_number+eol_char)
        time.sleep(0.1)
        self.set_TxE(0)    #Set invalid low (no valid signal)

        response = ser.readline()
        x = True
        while (x):
            if (crc.crc_response(response)):
                x = False
            else:
                #time.sleep(0.1)
               self.set_TxE(1)    #Set invalid high (valid signal)
               self.write_data(ser,charge+crc.append_crc(command)+seq_number+eol_char)
               time.sleep(0.1)
               self.set_TxE(0)    #Set invalid low (no valid signal)
               response = ser.readline()

        self.log_q.put(["debug","ST",response])

        
        timeout = 1     #second
        timeout_start = time.time() #current time
        while ((self.read_invalid() == 1) and (time.time() < timeout_start + timeout)):
            ()#print ("in loop - sampler invalid signal high")
        if (self.read_invalid() == 0):
            self.set_TxE(1)
            self.log_q.put(["debug","ST","in if statement"])
            
    def write_image(self, bits):
        self.set_TxE(1)
        self.samplerSerial.write(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8C")
        self.samplerSerial.write(bits)
        time.sleep(0.05)
        self.set_TxE(0)

    def generate_checksum(self, firmwareimage):
        self.imageChecksum = "{:08X}".format(zlib.crc32(firmwareimage)&0xFFFFFFFF)
        
        return self.imageChecksum   
         
    def get_status(self):
        self.log_q.put(["debug","ST","get status"])
        response = self.send_command(b'\x8C' + 'S'.encode('ascii') + '00'.encode('ascii') )          # Hard coded Status Request packet
        self.hideAllParams(False)
        self.parse_status(response)
        return response
            
    def main_fw_update(self, version):
        self.log_q.put(["error","FW","In main_fw_update"])
        chunksize = 1024

        try:
            # print(mainfwVersion.replace(".","_"))
            mainfwVersion = version.replace(".","_")
                        
            f = open("Sampler"+mainfwVersion+".bin", 'rb')
        except FileNotFoundError as fnf_error:
            self.log_q.put(["error","FW","OOPS! "+fnf_error])
            self.write_image('n'.encode('utf-8'))
            return None
        
        self.init_main_bootloader(self.samplerSerial)
        image = f.read()
        f.close()
        
        self.log_q.put(["debug","FW","Firmware size = " + str(len(image))])
        numberoffullblocks = int(len(image)/1024)
        overflow = len(image)%1024
        self.log_q.put(["debug","FW","Number of blocks = " + str(numberoffullblocks) + " overflow = " + str(overflow)])
        imageSize = "{:08X}".format((len(image)))
        self.log_q.put(["debug","FW","ImageSize = " + imageSize])
        imageChecksum = self.generate_checksum(image)
        self.log_q.put(["debug","FW","Checksum = " + imageChecksum])
        
        
        self.write_image(("f" + imageSize + imageChecksum).encode('utf-8'))
        time.sleep(0.002)
        
        output = self.samplerSerial.read_until(b'r', 80)
        if (len(output) == 0):
            self.log_q.put(["debug","FW","no response received"])
            return False
        for i in range(len(output)):
            if (chr(output[i]) == 'r'):
                self.log_q.put(["debug","FW","success"])
                break
            elif( i == len(output)-1):
                self.log_q.put(["debug","FW","fail"])
                self.samplerSerial.close()
                return False 
            
        block = []
        for i in range(chunksize): 
            block.append(0)

        for block_number in range(0,numberoffullblocks):
            self.log_q.put(["debug","FW","write block" + str(block_number)])
            for i in range(0, chunksize):
                block[i] = image[block_number*1024 + i]
            self.write_image(block)
            time.sleep(0.1)
            output = self.samplerSerial.read_until(b'.', 80)
            if (len(output) == 0):
                self.log_q.put(["debug","FW","no response received"])
                return False
            for i in range(len(output)):
                if (chr(output[i]) == '.'):
                    self.log_q.put(["debug","FW","success"])
                    break
                elif( i == len(output)-1):
                    self.log_q.put(["debug","FW","fail"])
                    self.samplerSerial.close()
                    return False 
               
        block_number +=1
        overflowblock = []
        for i in range(overflow): 
            overflowblock.append(0)
        self.log_q.put(["debug","FW","write overflow"])
        for i in range(0, overflow, 1):
            overflowblock[i] = image[block_number*1024 + i]
        self.write_image(overflowblock)
        time.sleep(0.5)
        output = self.samplerSerial.read_until(b',', 80)
        if (len(output) == 0):
            self.log_q.put(["debug","FW","no response received"])
            return False
        for i in range(len(output)):
            if (chr(output[i]) == ','):
                self.log_q.put(["debug","FW","success"])
                break
            elif( i == len(output)-1):
                self.log_q.put(["debug","FW","#fail"])
                self.samplerSerial.close()
                return False 
        
        time.sleep(0.1)
        output = self.samplerSerial.read_until(b'0', 80)
        self.log_q.put(["debug","FW","CRC output: "+str(output)])
        if (len(output) == 0):
            self.log_q.put(["debug","FW","no response received"])
            return False
        for i in range(len(output)):
            if (chr(output[i]) == '0'):
                self.log_q.put(["debug","FW","CRC Success"])
                return True
            elif( i == len(output)-1):
                self.log_q.put(["debug","FW","CRC fail"])
                self.samplerSerial.close()
                return False 