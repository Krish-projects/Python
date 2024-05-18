from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
# from PyQt5.QtGui import QPixmap

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys
import serial
import crc
import time
import Adafruit_BBIO.GPIO as GPIO
import crc8
import zlib

from VirtualKeyboard import *


class SamplerTestGUI(QWidget):

    sig_SamplerTestGUI_closed = pyqtSignal()
    
    def __init__(self, log_q):
        self.samplerSerial=serial.Serial(port = "/dev/ttyO4", baudrate=115200,timeout=2)
        super(SamplerTestGUI,self).__init__()
        GPIO.setup("P9_15", GPIO.IN)
        GPIO.setup("P8_15",GPIO.OUT)
        GPIO.output("P8_15",GPIO.HIGH)
        self.log_q = log_q
        SamplerTestGUI.setGeometry(self,0, 22, 480, 250)
        self.testmodetitle = self.setWindowTitle("Sampler Test Mode")
        
        self.stresscyclevalue = ''
        self.keyboard_1 = VirtualKeyboard(self.stresscyclevalue, False, self.log_q)
        self.keyboard_1.sigInputString.connect(self.stresscycles)         
        
        self.mainfw_virtualkeyboard_value = ''
        self.mainfw_virtualkeyboard = VirtualKeyboard(self.mainfw_virtualkeyboard_value, False, self.log_q)
        self.mainfw_virtualkeyboard.sigInputString.connect(self.mainfw_textbox) 
        
        self.bldcfw_virtualkeyboard_value = ''
        self.bldcfw_virtualkeyboard = VirtualKeyboard(self.bldcfw_virtualkeyboard_value, False, self.log_q)
        self.bldcfw_virtualkeyboard.sigInputString.connect(self.bldcfw_textbox) 
        
        self.statusbutton = QtWidgets.QPushButton("Status", self)
        self.statusbutton.resize(self.statusbutton.sizeHint())
        self.statusbutton.move(10,10)
        self.statusbutton.clicked.connect(self.get_status)
        
        self.clearfaultbutton = QtWidgets.QPushButton("Clear Fault", self)
        self.clearfaultbutton.move(100,10)
        self.clearfaultbutton.resize(self.clearfaultbutton.sizeHint())
        self.clearfaultbutton.clicked.connect(self.clear_faults)
        
        self.wipebutton = QtWidgets.QPushButton("Wipe", self)
        self.wipebutton.resize(self.wipebutton.sizeHint())
        self.wipebutton.move(10,50)
        self.wipebutton.clicked.connect(self.wipe)
        
        self.wipecancelbutton = QtWidgets.QPushButton("Wipe Cancel", self)
        self.wipecancelbutton.resize(self.wipecancelbutton.sizeHint())
        self.wipecancelbutton.move(100,50)
        self.wipecancelbutton.clicked.connect(self.wipe_cancel)        
        
        self.slowrotatebutton = QtWidgets.QPushButton("Slow Rotate", self)
        self.slowrotatebutton.resize(self.slowrotatebutton.sizeHint())
        self.slowrotatebutton.move(10,90)
        self.slowrotatebutton.clicked.connect(self.spray) 

        self.fastrotatebutton = QtWidgets.QPushButton("Fast Rotate", self)
        self.fastrotatebutton.resize(self.fastrotatebutton.sizeHint())
        self.fastrotatebutton.move(150,90)
        self.fastrotatebutton.clicked.connect(self.rinse)                

        self.servoengagebutton = QtWidgets.QPushButton("Servo Engage",self)
        self.servoengagebutton.resize(self.servoengagebutton.sizeHint())
        self.servoengagebutton.move(10,130)
        self.servoengagebutton.clicked.connect(self.servo_engage)
      
        self.servodisengagebutton = QtWidgets.QPushButton("Servo Disengage", self)
        self.servodisengagebutton.resize(self.servodisengagebutton.sizeHint())
        self.servodisengagebutton.move(150,130)
        self.servodisengagebutton.clicked.connect(self.servo_disengage)
        
        self.mainfwupdatebutton = QtWidgets.QPushButton("Firmware Update", self)
        self.mainfwupdatebutton.resize(self.mainfwupdatebutton.sizeHint())
        self.mainfwupdatebutton.move(10,170)
        self.mainfwupdatebutton.clicked.connect(self.main_fw_update)
        
        self.mainfirmwareversion = QtWidgets.QLineEdit(self)
        self.mainfirmwareversion.setGeometry(185,170,35,35) 
        self.mainfirmwareversion.mousePressEvent = self.VKB2
        
        self.bldcupdatebutton = QtWidgets.QPushButton("BLDC Update", self)
        self.bldcupdatebutton.resize(self.bldcupdatebutton.sizeHint())
        self.bldcupdatebutton.move(10,210)
        self.bldcupdatebutton.clicked.connect(self.bldc_fw_update)
        
        self.bldcupdateversion = QtWidgets.QLineEdit(self)
        self.bldcupdateversion.setGeometry(185,210,35,35)
        self.bldcupdateversion.mousePressEvent = self.VKB3
        
        self.resetbutton = QtWidgets.QPushButton("Reset",self)
        self.resetbutton.resize(self.resetbutton.sizeHint())
        self.resetbutton.move(400,170)
        self.resetbutton.clicked.connect(self.reset_sampler)
        
        self.exitbutton = QtWidgets.QPushButton("Close", self)
        self.exitbutton.resize(self.exitbutton.sizeHint())
        self.exitbutton.move(400,210)
        self.exitbutton.clicked.connect(self.exitbutton_clicked)
        
        self.motorstresstestbutton = QtWidgets.QPushButton("Motor Test", self)
        self.motorstresstestbutton.resize(self.motorstresstestbutton.sizeHint())
        self.motorstresstestbutton.move(225,10)
        self.motorstresstestbutton.clicked.connect(self.test_cycle)
        
        self.motorstresscycles = QtWidgets.QLineEdit(self)
        self.motorstresscycles.setGeometry(335,10,30,35) 
        self.motorstresscycles.mousePressEvent = self.VKB1

        self.showfaultsbutton = QtWidgets.QPushButton("Show Faults", self)
        self.showfaultsbutton.resize(self.showfaultsbutton.sizeHint())
        self.showfaultsbutton.move(355,130)
        self.showfaultsbutton.clicked.connect(self.showfaultsbutton_clicked)
        self.showfaultsbutton.setEnabled(False)        
        
################################################################################################
        self.voltage =  QtWidgets.QLabel(self)
        # self.voltage.setText("00.00V")
        self.voltage.move(395,5)        

        self.soc =  QtWidgets.QLabel(self)
        # self.soc.setText("50%")
        self.soc.move(395,25)
        
        self.current =  QtWidgets.QLabel(self)
        # self.current.setText("0mA")
        self.current.move(395,45)
        
        self.speed =  QtWidgets.QLabel(self)
        # self.speed.setText("0 RPM")
        self.speed.move(395,65)
        
        self.mainfwversion =  QtWidgets.QLabel(self)
        # self.mainfwversion.setText("v1.0")
        self.mainfwversion.move(250,170)
        
        self.bootloaderfwversion =  QtWidgets.QLabel(self)
        # self.bootloaderfwversion.setText("BL:v1")
        self.bootloaderfwversion.move(300,170)
        
        self.bldcfwversion =  QtWidgets.QLabel(self)
        # self.bldcfwversion.setText("v1")
        self.bldcfwversion.move(250,210)
        
        self.numberoffaults =  QtWidgets.QLabel(self)
        # self.numberoffaults.setText("0")
        self.numberoffaults.move(395,105)
        
        self.deviceid =  QtWidgets.QLabel(self)
#        self.deviceid.setText("00A")
        self.deviceid.move(395,85)
        
        self.log_q.put(["debug","ST","Sampler test mode page open"])
        self.show()
 
    def VKB1(self, event):
        
        if self.keyboard_1.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter stress cycles'])
            self.keyboard_1.show()
        else:
            self.keyboard_1.hide()
            
    def VKB2(self, event):
        
        if self.mainfw_virtualkeyboard.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter main firmware version'])
            self.mainfw_virtualkeyboard.show()
        else:
            self.mainfw_virtualkeyboard.hide()
            
    def VKB3(self, event):
        
        if self.bldcfw_virtualkeyboard.isHidden():
            self.log_q.put(["debug","LD", 'Virtual Keyboard enabled to enter bldc version'])
            self.bldcfw_virtualkeyboard.show()
        else:
            self.bldcfw_virtualkeyboard.hide()
            
    def showfaultsbutton_clicked(self):
        faults = QtWidgets.QMessageBox()
        faults.setIcon(QtWidgets.QMessageBox.Information)
        faults.setText("Click show details to view all faults")
        faults.setWindowTitle("Faults")
        faults.setDetailedText(self.faultcodes)
        faults.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        faults.setGeometry(300,237,0,0)
        faults.exec_()      
           
    def stresscycles(self, data):
        self.data = data
        self.log_q.put(["info","LD", 'Stress Cycles: '+self.data]) 
        self.motorstresscycles.setText(self.data)    
        
    def mainfw_textbox(self, data):
        self.data = data
        self.log_q.put(["info","LD", 'Main FW: '+self.data]) 
        self.mainfirmwareversion.setText(self.data)
        
    def bldcfw_textbox(self, data):
        self.data = data
        self.log_q.put(["info","LD", 'BLDC FW: '+self.data]) 
        self.bldcupdateversion.setText(self.data)
 
    def exitbutton_clicked(self):
        self.log_q.put(["debug","LD", 'Exitting sampler test page'])
        self.samplerSerial.close()
        self.close()
        self.sig_SamplerTestGUI_closed.emit()        
        
    def get_main_fw_version(self):
        fwversion = self.mainfirmwareversion.text()
        self.log_q.put(["debug","ST",fwversion])
        return fwversion
    
    def get_bldc_fw_version(self):
        fwversion = self.bldcupdateversion.text()
        self.log_q.put(["debug","ST",fwversion])
        return fwversion
    
    def get_motor_cycles(self):

        if self.motorstresscycles.text():
            numberofcycles = int(self.motorstresscycles.text())
            self.log_q.put(["debug","ST","numberofcycles = %d"%numberofcycles])
        else:
            QtWidgets.QMessageBox.warning(self, "No data" ,"No data supplied")
            return None
        
        return numberofcycles
    
    def update(self):
        self.voltage.adjustSize()
        self.soc.adjustSize()        
        self.current.adjustSize()       
        self.speed.adjustSize()      
        self.mainfwversion.adjustSize()       
        self.bootloaderfwversion.adjustSize()      
        self.bldcfwversion.adjustSize()
        self.numberoffaults.adjustSize()        
    
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
            self.log_q.put(["debug","ST","ready"])         
            self.set_TxE(1)    #Set invalid high (valid signal)
            charge = 50*(b'\x00') 
            eol_char = '\n'.encode('ascii')
            seq_number = chr(32).encode('ascii')
            finalCMD = charge+crc.append_crc(command)+seq_number+eol_char
            self.log_q.put(["debug","ST","finalCMD:%s"%str(finalCMD)])
            self.write_data(self.samplerSerial,finalCMD)
            
            time.sleep(0.1)
            self.set_TxE(0)    #Set invalid low (no valid signal)
            response = self.samplerSerial.readline()        #read until EOL (\n) character 

            self.log_q.put(["debug","ST","Response is:%s"%str(response)])
            timeout = 1     #second
            timeout_start = time.time() #current time
            while ((self.read_invalid() == 1) and (time.time() < timeout_start + timeout)):
                self.log_q.put(["debug","ST","in loop - sampler invalid signal high"])
            if (self.read_invalid() == 0):
                self.set_TxE(1)
                self.log_q.put(["debug","ST","in if statement"])
            return response
    
    def get_status(self):
        self.log_q.put(["debug","ST","get status"])
        response = self.send_command(b'\x8C' + 'S'.encode('ascii') + '00'.encode('ascii') )          # Hard coded Status Request packet
        self.hideAllParams(False)
        self.parse_status(response)
        return response
            
    def parse_status(self, packet_receive):
        start=999
        for index in range (0,len(packet_receive)):
            if packet_receive[index] == 0x8c:    
                start=index        
                lhigh=packet_receive[start+2]-48  #requires data length ascii hex characters to be in upper case Sampler side
                if lhigh>9:
                    lhigh-=7
                llow=packet_receive[start+3]-48
                if llow>9:
                    llow-=7
                length=16*lhigh+llow
                self.log_q.put(["debug","ST","length="+str(length)])
                break
        if start<999:
            packet=packet_receive[start:start+length+4]
            packetcrc=packet_receive[start+length+4:start+length+6].decode("utf-8")
            hash=crc8.crc8()
            hash.update(packet)
            calccrc=hash.hexdigest().upper()
      
            if calccrc == packetcrc:
                self.log_q.put(["debug","ST","good crc"])

                number_of_faults = int(packet_receive[start+69:start+71].decode("utf-8"),16)
                packetcrc=packet_receive[start+length+4:start+length+6].decode("utf-8")

                self.voltage.setText(packet_receive[start+46:start+50].decode("utf-8")+"V")
                self.soc.setText(packet_receive[start+43:start+46].decode("utf-8") + "%")
                self.mainfwversion.setText("v" + packet_receive[start+36:start+39].decode("utf-8"))
                self.current.setText(packet_receive[start+71+number_of_faults*2:start+75+number_of_faults*2].decode("utf-8")+"mA")
                self.speed.setText(packet_receive[start+39:start+43].decode("utf-8") + "RPM")
                self.bootloaderfwversion.setText("BL:v" + packet_receive[start+76+number_of_faults*2:start+78+number_of_faults*2].decode("utf-8"))
                self.bldcfwversion.setText("v" + packet_receive[start+75+number_of_faults*2:start+76+number_of_faults*2].decode("utf-8"))            
                self.numberoffaults.setText(packet_receive[start+69:start+71].decode("utf-8"))
                self.deviceid.setText(packet_receive[start+33:start+36].decode("utf-8"))
                
                self.update()
                
            else:
                self.log_q.put(["debug","ST","bad crc"])
        else:
            self.log_q.put(["debug","ST","Didn't find packet start"])
            
    def hideAllParams(self, flag):
        if flag:
            self.log_q.put(["debug","ST","Hiding all parameters!!!"])
            self.voltage.hide()
            self.soc.hide()
            self.mainfwversion.hide()
            self.current.hide()
            self.speed.hide()
            self.bootloaderfwversion.hide()
            self.bldcfwversion.hide()
            self.numberoffaults.hide()
        else:
            self.log_q.put(["debug","ST","Showing all parameters!!!"])
 
            self.voltage.show()
            self.soc.show()
            self.mainfwversion.show()
            self.current.show()
            self.speed.show()
            self.bootloaderfwversion.show()
            self.bldcfwversion.show()
            self.numberoffaults.show()        
    
    def spray(self):
        self.hideAllParams(True)
        self.log_q.put(["debug","ST","START spray"])
        self.send_command(b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '0120'.encode('ascii') + '06'.encode('ascii'))
        
    def rinse(self):
        self.hideAllParams(True)
        self.log_q.put(["debug","ST","START rinse"])
        self.send_command(b'\x8C' + 'R'.encode('ascii') + '04'.encode('ascii') + '6000'.encode('ascii') + '05'.encode('ascii'))
        
    def wipe(self):
        self.hideAllParams(True)
        self.log_q.put(["debug","ST","START wipe"])
        self.send_command(b'\x8C' +'W'.encode('ascii') +'07'.encode('ascii') +'0120'.encode('ascii') +'01'.encode('ascii')+'5'.encode('ascii') )
        
    def wipe_cancel(self):
        self.hideAllParams(True)    
        self.log_q.put(["debug","ST","CANCEL wipe"])
        self.send_command(b'\x8C' +'X'.encode('ascii') +'00'.encode('ascii') )
        
    def clear_faults(self):
        self.hideAllParams(True)    
        self.log_q.put(["debug","ST","clear fault"])
        self.send_command(b'\x8C' + 'C'.encode('ascii') + '00'.encode('ascii') )
        
    def servo_engage(self):
        self.hideAllParams(True)
        self.log_q.put(["debug","ST","servo engaged"])
        self.send_command(b'\x8C' + 'E'.encode('ascii') +  '00'.encode('ascii') )
        
    def servo_disengage(self):
        self.hideAllParams(True)    
        self.log_q.put(["debug","ST","servo disengaged"])
        self.send_command(b'\x8C' + 'D'.encode('ascii') +  '00'.encode('ascii') )
        
    def fw_update(self):
        self.log_q.put(["debug","ST","Didn't find packet start"])
        self.send_command(b'\x8C' + 'F'.encode('ascii') +  '00'.encode('ascii') )
    
    def reset_sampler(self):
        self.log_q.put(["debug","ST","firmware update init"])
        self.send_command(b'\x8C' + 'T'.encode('ascii') +  '00'.encode('ascii') )
    
    def check_rotate_state(self):
        while 1:     
            time.sleep(0.5)
            response = self.get_status()
            if (response != b''):    
                if (chr(response[50+68]) == 'F'):
                    return 1
                elif (chr(response[50+68]) == 'E'):
                    return 1
            
    def check_wipe_state(self):
        while 1:
            time.sleep(0.5)
            response = self.get_status()
            if (response != b''):
                if ((chr(response[50+67]) != 'C')):
                    return 1
                
    def test_cycle(self):
        start_time = time.time()
        cycles = self.get_motor_cycles()
        if (isinstance(cycles, int)):
            for i in range (0,cycles): #1
        #        get_status()
                self.spray()
                self.check_rotate_state()
                self.rinse()
                self.check_rotate_state()
                # self.wipe()
                # self.check_wipe_state()
           
            self.log_q.put(["debug","ST","TEST COMPLETE, TIME = ",time.time() - start_time])         
        
    def init_main_bootloader(self, ser):
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
    
        self.log_q.put(["debug","ST","response = "+str(response)])
    
        
        timeout = 1     #second
        timeout_start = time.time() #current time
        while ((self.read_invalid() == 1) and (time.time() < timeout_start + timeout)):
            ()#print ("in loop - sampler invalid signal high")
        if (self.read_invalid() == 0):
            self.set_TxE(1)
            self.log_q.put(["debug","ST","in if statement"])
            
    def write_image(self, bits):
        self.set_TxE(1)
        self.samplerSerial.write(50*(b'\x00')+b"\x8C")
        self.samplerSerial.write(bits)
        time.sleep(0.05)
        self.set_TxE(0)
    
    def generate_checksum(self, firmwareimage):
        self.imageChecksum = "{:08X}".format(zlib.crc32(firmwareimage)&0xFFFFFFFF)
        
        return self.imageChecksum   
         
    def main_fw_update(self):
        
        chunksize = 1024

        try:
            mainfwVersion = self.get_main_fw_version()
            self.log_q.put(["debug","ST",mainfwVersion.replace(".","_")])
            mainfwVersion = mainfwVersion.replace(".","_")
                        
            f = open("Sampler"+mainfwVersion+".bin", 'rb')
        except FileNotFoundError as fnf_error:

            self.log_q.put(["debug","ST",fnf_error])
            warning1 = QtWidgets.QMessageBox()
            warning1.setIcon(QtWidgets.QMessageBox.Warning)
            warning1.setText("Sampler Firmware Binary Not Found!")
            warning1.setWindowTitle("Firmware Update Warning")
            warning1.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
            warning1.setGeometry(300,300,0,0)
            warning1.exec_()
            return None
        
        self.init_main_bootloader(self.samplerSerial)
        image = f.read()
        f.close()
        
        self.log_q.put(["debug","ST","Firmware size = " + str(len(image))])
        numberoffullblocks = int(len(image)/1024)
        overflow = len(image)%1024
        self.log_q.put(["debug","ST","Number of blocks = " + str(numberoffullblocks) + " overflow = " + str(overflow)])
        imageSize = "{:08X}".format((len(image)))
        self.log_q.put(["debug","ST","ImageSize = " + imageSize])
        imageChecksum = self.generate_checksum(image)
        self.log_q.put(["debug","ST","Checksum = " + imageChecksum])
        
        
        self.write_image(("f" + imageSize + imageChecksum).encode('utf-8'))
        time.sleep(0.002)
        output = self.samplerSerial.read()
        if (output == b"r"):
            self.log_q.put(["debug","ST","Ready for firmware"])
        else:   
            self.log_q.put(["debug","ST","not ready"])
            self.samplerSerial.close()
            sys.exit()
        
        block = []
        for i in range(chunksize): 
            block.append(0)

        for block_number in range(0,numberoffullblocks):
            self.log_q.put(["debug","ST","write block" + str(block_number)])
            for i in range(0, chunksize):
                block[i] = image[block_number*1024 + i]
            self.write_image(block)
            time.sleep(0.1)
            if(self.samplerSerial.read()==b"."):
                self.log_q.put(["debug","ST","success"])
            else:
                self.log_q.put(["debug","ST","fail"])
                self.samplerSerial.close()
                sys.exit()
               
        block_number +=1
        overflowblock = []
        for i in range(overflow): 
            overflowblock.append(0)
        self.log_q.put(["debug","ST","write overflow"])
        for i in range(0, overflow, 1):
            overflowblock[i] = image[block_number*1024 + i]
        self.write_image(overflowblock)
        time.sleep(0.5)
        if(self.samplerSerial.read()==b","):
            self.log_q.put(["debug","ST","success"])
        else:
            self.log_q.put(["debug","ST","#fail"])
            self.samplerSerial.close()
            sys.exit()
        
        time.sleep(0.1)
        if(self.samplerSerial.read()==b"0"):
            self.log_q.put(["debug","ST","CRC Success"])
        else:
            self.log_q.put(["debug","ST","CRC fail"])

    def init_bldc_bootloader(self,ser):
        self.set_TxE(ser,1)    #Set invalid high (valid signal)
        charge = 50*(b'\x00')
        command = b'\x8C' + 'B'.encode('ascii') +  '00'.encode('ascii')
        eol_char = '\n'.encode('ascii')
        seq_number = 'z'.encode('ascii')
        self.write_data(ser,charge+crc.append_crc(command)+seq_number+eol_char)
        time.sleep(0.1)
        self.set_TxE(ser,0)    #Set invalid low (no valid signal)

        response = ser.readline()
        x = True
        while (x):
            if (crc.crc_response(response)):
                x = False
            else:
                #time.sleep(0.1)
                self.set_TxE(ser,1)    #Set invalid high (valid signal)
                self.write_data(ser,charge+crc.append_crc(command)+seq_number+eol_char)
                time.sleep(0.1)
                self.set_TxE(ser,0)    #Set invalid low (no valid signal)
                response = ser.readline()
        self.log_q.put(["debug","ST",response])     
        timeout = 1     #second
        
        timeout_start = time.time() #current time
        while ((self.read_invalid(ser) == 1) and (time.time() < timeout_start + timeout)):
            ()#print ("in loop - sampler invalid signal high")
        if (self.read_invalid(ser) == 0):
            self.set_TxE(ser,1)
            self.log_q.put(["debug","ST","in if statement"])
            
    def bldc_fw_update(self):
        
        chunksize = 256

        try:
            bldcfwVersion =  self.get_bldc_fw_version()          
            f = open("bldc-"+bldcfwVersion+".bin", 'rb')
            
        except FileNotFoundError as fnf_error:
            self.log_q.put(["debug","ST",fnf_error])
            warning1 = QtWidgets.QMessageBox()
            warning1.setIcon(QtWidgets.QMessageBox.Warning)
            warning1.setText("BLDC Firmware Binary Not Found!")
            warning1.setWindowTitle("Firmware Update Warning")
            warning1.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
            warning1.setGeometry(300,300,0,0)
            warning1.exec_()
            return None
    
        self.init_bldc_bootloader(self.samplerSerial)
        image = f.read()
        f.close()
        
        self.log_q.put(["debug","ST","Firmware size = " + str(len(image))])
        numberoffullblocks = int(len(image)/256)
        overflow = len(image)%256
        self.log_q.put(["debug","ST","Number of blocks = " + str(numberoffullblocks) + " overflow = " + str(overflow)])
        imageSize = "{:08X}".format((len(image)))
        self.log_q.put(["debug","ST","ImageSize = " + imageSize])
        imageChecksum = self.generate_checksum(image)
        self.log_q.put(["debug","ST","Checksum = " + imageChecksum])

        self.write_image(("f" + imageSize + imageChecksum).encode('utf-8'))
        time.sleep(0.002)
        output = self.samplerSerial.read()
        if (output == b"r"):
            self.log_q.put(["debug","ST","Ready for firmware"])
        else:   
            self.log_q.put(["debug","ST","not ready"])
            self.samplerSerial.close()
            sys.exit()
        
        block = []
        for i in range(chunksize): 
            block.append(0)
        
        for block_number in range(0,numberoffullblocks):
            self.log_q.put(["debug","ST","write block" + str(block_number)])
            for i in range(0, chunksize):
                block[i] = image[block_number*256 + i]
            self.write_image(block)
            time.sleep(0.1)
            if(self.samplerSerial.read()==b"."):
                self.log_q.put(["debug","ST","success"])
            else:
                self.log_q.put(["debug","ST","fail"])
                self.samplerSerial.close()
                sys.exit()
               
        block_number +=1
        overflowblock = []
        for i in range(overflow): 
            overflowblock.append(0)
        self.log_q.put(["debug","ST","write overflow"])
        for i in range(0, overflow, 1):
            overflowblock[i] = image[block_number*256 + i]
        self.write_image(overflowblock)
        time.sleep(0.5)
        if(self.samplerSerial.read()==b","):
            self.log_q.put(["debug","ST","success"])
        else:
            self.log_q.put(["debug","ST","#fail"])
            self.samplerSerial.close()
            sys.exit()
        
        time.sleep(0.1)
        if(self.samplerSerial.read()==b"0"):
            self.log_q.put(["debug","ST","CRC Success"])
        else:
            self.log_q.put(["debug","ST","CRC fail"])
            
# if __name__ == '__main__':

    # GPIO.setup("P9_12", GPIO.OUT)
    # app = QApplication(sys.argv)
    # styleSheet = """
    # QScrollBar:vertical{width:30px}
    # QScrollBar:horizontal{height:30px}
    # QMesssageBox{background-color:#333333}
    # QCheckBox:indicator{width:40px}
    # QCheckBox:indicator{height: 40px}
    # """   
    # app.setFont(QtGui.QFont('Ariel', 16))
    # app.setStyleSheet(styleSheet)    
    # win = SamplerTestGUI()
    # win.show()
    # sys.exit(app.exec_())