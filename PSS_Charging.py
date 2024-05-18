#### PSS Charging ########

"""
Title: PSS_Charging.py

This package contains the definition of two object classes:

analyser_charge: which monitors the battery status of the analyser and reports it to the GUI through a queue. When a plug pack is attached is also controls the charger.
The analyser charge object will be constantly running.

sampler_charge: the code for this object will only run when the plug pack is attached to the analyser. removing the plug pack will cause the loop to break.

"""

###############  Python Modules  ##########################

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_GPIO.I2C as I2C
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.UART as UART 
import time
import serial                   
import crc
import threading
import deviceStatus as DS

##############   Pin Setup     ############################

GPIO.setup("P8_14",GPIO.OUT) # Analyser Charge Disable (When High turns the charger off)
GPIO.setup("P8_15",GPIO.OUT) # Sampler Charge Enable
GPIO.setup("P9_12",GPIO.OUT) # TxE
# GPIO.setup("P9_15",GPIO.IN) # Invalidz Signal
#GPIO.setup("GPIO1_26",GPIO.IN) # ALCCz
analyser=serial.Serial(port = "/dev/ttyO4", baudrate=115200,timeout=5)
ADC.setup()
                
#######Reverse bit order function ############################

def rev_bytes_16(value):
    x=bin(value)
    x=x[2:]
    l=len(x)
    d=16-l
    x=d*"0"+x
    x=x[8:16]+x[0:8]
    
    reverse= int (x,2)
    
    return reverse
    
                
                
##############   Analyser Battery Management ################

class analyser_charge(threading.Thread):
    """
    This object is used to monitor the condition of the analyser's battery and control it's battery charger.

    This objects run() method will be running in a thread constantly as long as the analyser is running

    """
 
    def __init__(self,analyser_charge_q, log_q, hard_high_ACR= 65000,hard_low_ACR=2000,hard_high_v=16.8,hard_low_v=13.2,hard_high_charge_cur=1.5,hard_high_discharge_cur=2,hard_high_temp=100, hard_low_temp=-10,soft_low_soc=95,soft_high_soc=95,soft_high_v=16.5,soft_low_v=16.0,soft_low_charge_i=0.1,charge_en=1, poll_rate=5, log_rate=10): # Still need to set these parameters
        # Initialise Variables
        threading.Thread.__init__(self)
        self.charge_q = analyser_charge_q
        self.log_q = log_q
        self.poll_rate = poll_rate
        self.log_rate = log_rate
        self.hard_high_ACR=hard_high_ACR
        self.hard_low_ACR=hard_low_ACR
        self.hard_high_v=hard_high_v
        self.hard_low_v=hard_low_v
        self.hard_high_charge_cur=hard_high_charge_cur
        self.hard_high_discharge_cur=hard_high_discharge_cur
        self.hard_high_temp=hard_high_temp
        self.hard_low_temp=hard_low_temp
        
        self.soft_low_soc=soft_low_soc
        self.soft_high_soc=soft_high_soc
        self.soft_high_v=soft_high_v
        self.soft_low_v=soft_low_v
        self.soft_low_charge_i=soft_low_charge_i
        
        self.charge_en=charge_en
        self.charger=0
        self.battery_voltage=0
        self.alccz=1
        self.log_q.put(["debug","AC","In AC Init"])
        
        # Start I2C Comms Object
        try:
            self.i2c_device=I2C.get_i2c_device(address=0x64,busnum=0)   
        
            # Setup gas Gauge Hardware Thresholds to Values for ALCCz alarms
            self.i2c_device.write16(register=0x04,value=rev_bytes_16(hard_high_ACR))
            self.i2c_device.write16(register=0x06,value=rev_bytes_16(hard_low_ACR))
            self.i2c_device.write16(register=0x0A,value=rev_bytes_16(int((hard_high_v/23.6)*65535)))
            self.i2c_device.write16(register=0x0C,value=rev_bytes_16(int((hard_low_v/23.6)*65535)))
            self.i2c_device.write16(register=0x10,value=rev_bytes_16(int(((32767/6)*hard_high_charge_cur)+32767)))
            self.i2c_device.write16(register=0x12,value=rev_bytes_16(int(((-32767/6)*hard_high_discharge_cur)+32767)))
            #self.i2c_device.write8(register=0x16,value=hard_high_temp+273)
            #self.i2c_device.write8(register=0x17,value=hard_low_temp+273)
            
            # Setup ADC scan mode
            self.i2c_device.write8(register=0x01,value=0b10100100) # Sets the ADC to run every 10s and update the relevant registers. The last 100 bits set the presacaler value to 256
        except Exception as e:
            self.log_q.put(["error","AC","Exception in AC Init: "+str(e)])
        # self.run()

    def get_SOC(self):
        ACR=self.readDevice(0x02)
        self.send_log(["debug","AC","ACR: " + str(ACR)])
        SOC=((ACR-16384)/32768)*100
        # self.log_q.put(["debug","AC","Calc SOC: " + str(SOC)])
        if SOC>100:
            SOC=100
            if ACR>49652:            # If ACR gets to high above the 100% value re-write to 100%
                self.set_full_charge()
                self.log_q.put(["debug","AC","Set ACR to 100 value"])
        elif SOC<0 and ACR<15884:
            SOC=0
            self.writeDevice(0x02, rev_bytes_16(16384))
            self.log_q.put(["debug","AC","Set ACR to 0 value"])
        
        # Checks for illogical SOC values and corrects them if necessary
        
        elif SOC<20:
            if self.battery_voltage>14.0:
                self.estimate_SOC()
                
        elif 20<=SOC<=80:
            if (self.battery_voltage<14.0) or (self.battery_voltage>16.0):
                self.estimate_SOC()
                
        elif SOC>80:
            if self.battery_voltage<16.0:
                self.estimate_SOC()
        
        SOC=int(SOC)
        return SOC

    def estimate_SOC(self):
        self.log_q.put(["debug","AC","Error Detected. Estimating SOC based on Battery Voltage"])
        
        battery_voltage=self.get_battery_voltage()
    
        if battery_voltage>16.0:
            self.writeDevice(0x02, rev_bytes_16(int(49152-(0*32768))))
            self.log_q.put(["debug","AC","Estimate SOC set to 100%"])
        elif 15.6<battery_voltage<16.0:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.1*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 90%"])
        elif 15.4<battery_voltage<15.6:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.2*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 80%"])
        elif 15.2<battery_voltage<15.4:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.3*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 70%"])
        elif 15.0<battery_voltage<15.2:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.4*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 60%"])
        elif 15.0<battery_voltage<15.2:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.5*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 50%"])        
        elif 14.8<battery_voltage<15.0:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.6*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 40%"])
        elif 14.6<battery_voltage<14.8:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.7*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 30%"])                   
        elif 14.4<battery_voltage<14.6:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.8*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 20%"])
        elif 13.6<battery_voltage<14.4:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.9*32768))))
                self.log_q.put(["debug","AC","Estimate SOC set to 10%"])
        elif 12.4<battery_voltage<13.6:
                self.writeDevice(0x02, rev_bytes_16(int(49152-(0.95*32768))))
                self.log_q.put(["debug","AC","New Battery. SOC set to 5%"])
        elif battery_voltage<12.4:
                self.writeDevice(0x02,rev_bytes_16(int(49152-(1.0*32768))))
                self.log_q.put(["debug","AC","New Battery. SOC set to 0%"])        

    def readDevice(self, regValue):
        try:
            result = self.i2c_device.readU16(register=regValue,little_endian=False)
            return result
        except Exception as e:
            self.log_q.put(["error","AC","Exception reading charger: "+str(e)])
            
    def writeDevice(self, regValue, writeValue):
        try:
            self.i2c_device.write16(regValue, writeValue)
        except Exception as e:
            self.log_q.put(["error","AC","Exception writing to charger: "+str(e)])
            

    def get_battery_voltage(self):
        reg_value=self.readDevice(0x08)
        self.battery_voltage=round((reg_value/65535)*23.6,2)
        return self.battery_voltage

    
    def check_charger(self):
        value=ADC.read("P9_33")
        if value>0.2:
            self.send_log(["debug","AC","Valid Plug Pack Attached"])
            return 1
        else:
            self.send_log(["debug","AC","Invalid Charge Signal"])
            return 0
        
    
    def charger_switch(self,on_off):
        if on_off==1:
            self.charge_en=1
            GPIO.output("P8_14",GPIO.LOW)
            self.log_q.put(["debug","AC","Charger Enabled"])
        if on_off==0:
            self.charge_en=0
            GPIO.output("P8_14",GPIO.HIGH)
            self.log_q.put(["debug","AC","Charger Disbabled"])
   
    
    def check_alcc(self):
        value= GPIO.input("GPIO1_26")
        self.alccz=value
        if value==0:
            self.check_alarms()
        
    def read_current(self):
        reg_value=self.readDevice(0x0E)
        battery_current=6*((reg_value-32767)/32767)
        return battery_current
        
    def set_full_charge(self):
        self.writeDevice(0x02, rev_bytes_16(49152))
        
    def send_log(self,log_params):
        if self.log_time == 0:
            self.log_q.put(log_params)
    def run(self):    
        
        self.log_time = 0
        self.charger=self.check_charger()
        
        self.charger_switch(on_off=1)
    
        stop=0
        while stop!=1:
            # Periodically print battery voltage and SOC of the battery pack
            # Then eventuallty one will hit a threshold where it wants to charge again
                    # We want to make SOC voltage and charger connection accessible from the main application so that it can be shown in the GUI
                    
            battery_voltage=self.get_battery_voltage()
            SOC=self.get_SOC()
            charge_current=self.read_current()
            self.charger=self.check_charger()
            
            self.send_log(["debug","AC","SOC: %s" %SOC])
            self.send_log(["debug","AC","Battery Voltage: %s" %battery_voltage])
            # if self.charger==0 and self.charge_en==1:
                # self.log_q.put(["debug","AC","Warning charge needed but no charger is attached"])
            
            if self.charge_en==0:
                self.send_log(["debug","AC","Not Charging"])
                if SOC<self.soft_low_soc:
                    self.log_q.put(["debug","AC","Low charge. Enabling charger"])
                    self.charger_switch(1)
                
                elif battery_voltage<self.soft_low_v:
                    self.log_q.put(["debug","AC","Low battery voltage. Enabling charger"])
                    self.charger_switch(1)
                
            if self.charger==1 and self.charge_en==1:
                self.send_log(["debug","AC","Charging"])
                # if SOC>self.soft_high_soc:
                    # self.log_q.put(["debug","AC","High charge. Disabling charger"])
                    # self.set_full_charge()
                    # self.charger_switch(0)
                if battery_voltage>self.soft_high_v and charge_current<self.soft_low_charge_i:
                    self.log_q.put(["debug","AC","Fully Charged. Disabling charger"])
                    self.set_full_charge()
                    self.charger_switch(0)
            self.charge_q.put([SOC,battery_voltage,self.charger])
            if self.log_time == self.log_rate:
                self.log_time = 0
            else:
                self.log_time += 1
            time.sleep(self.poll_rate)
            #self.check_alcc()

