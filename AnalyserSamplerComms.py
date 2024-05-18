import sys 
import time
import datetime

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# print ("AnalyserSamplerComms.py first call startin at : startupTime",datetime.datetime.now())


from Valves_Pump_control import Valves

import deviceStatus as DS 
import Sampler

##### return 0 - False, 1 - True, 2 - error during rotation, 3 - unrecovered error ###########




def samplerRotate(log_q, rotate, valve): 
    """
    Issues slow/fast rotate command to sampler and controls the valves
    """
   
    rotateCmd = rotate
    valveCmd = valve
    
    # cmd_timeOut = time.time()+20
    # log_q.put(["info","AS","cmd_timeOut ="+str(cmd_timeOut)])

    if rotateCmd == "Slow":
        log_q.put(["info","AS","----------Start of Slow Rotate Module--------------"])


        log_q.put(["info","AS","Starting solvent dispense"])
        # if valveCmd ==  "preSolventSquirt" : 
        x=True
        while x:         
            repsonse_SR = Sampler.S_cmd_Slow_rotate()
            log_q.put(["info","AS","Analysersamplercomms, Response for Slow Rotate "+str(repsonse_SR)])
            if (repsonse_SR!=0): ###There is a problem in sampler connection

                return 0

            else:
                time.sleep(2) # wait a while to make sure pad is spinning before solvent squirted
                dispenseSoln = Valves(log_q,True, valveCmd, valveCmd)    
                dispenseSoln.operateValves()
                x=False
            

            
        
        log_q.put(["info","AS","Solvent DISPENSED"])

    else: #fastRotate
        log_q.put(["info","AS","----------Start of Fast Rotate Module--------------"])    
        # if valveCmd == "postSolventSquirt":
        x=True
        while x: 
            if valveCmd == "postSolventSquirt": ##Fast rotate for 9 sec
                repsonse_FR = Sampler.S_cmd_Fast_rotate_Sample()
            elif valveCmd == "calibrate": ##Fast rotate for 12 sec
                repsonse_FR = Sampler.S_cmd_Fast_rotate_Calibrate()
            else: ###Fast rotate for 7 sec for rinsing and other activites
                repsonse_FR = Sampler.S_cmd_Fast_rotate_General()
            log_q.put(["info","AS","Analysersamplercomms, Response for Fast Rotate "+str(repsonse_FR)])   
            if (repsonse_FR==2): ###There is a problem in sampler connection

                return 0
            elif (repsonse_FR==1):
                pass
            
            else:
                time.sleep(2) # wait a while to make sure pad is spinning before solvent squirted    
                if valveCmd == "postSolventSquirt" or valveCmd == "bagChange" or valveCmd == "calibrate" or valveCmd == "rinse":
                    dispenseSoln = Valves(log_q,True, valveCmd, valveCmd)
                    dispenseSoln.operateValves()
                
                x=False
                


    timeOut_rotate = time.time()+90    
        
    cmd_done=False
    while(not cmd_done):
        status = Sampler.S_cmd_Get_status()
        # log_q.put(["info","AS","getting status"])
        # log_q.put(["debug","AS", "Status: " + str(status)])
        # log_q.put(["debug","AS", "Status: status['sample_state'] = %s, status['rotate_state'] = %s, status['status'] = %s"%(str(status['sample_state']), str(status['rotate_state']), str(status['status']))])
        if status['status'] == 'Disconnected':
            cmd_done = True
            log_q.put(["info","AS","Sampler Disconnected after Transient connection"])
            # log_q.put(["debug","AS", "in Status disconnected: status['sample_state'] = %s, status['rotate_state'] = %s, status['status'] = %s"%(str(status['sample_state']), str(status['rotate_state']), str(status['status']))])
            return 0
        if(status['status'] == 'Ready' and status['rotate_state'] != 'A'):
            # rotate has finished
            if status['rotate_state'] == 'F':
                DS.sampler_faultRetry = 0
            cmd_done = True
            if status['fault_code_n'] > 0:
                faultList = status['fault_code']
                log_q.put(["debug","AS", "Status: " + str(status)])
                log_q.put(["debug","AS", "Fault list length: " + str(status['fault_code_n'])])
                log_q.put(["debug","AS", "Fault list: " + str(faultList)])
                # clear Fault List
                Sampler.S_cmd_Clear_faultlist()
                for i in range (0,status['fault_code_n']):
                    
                    #get next Fault code
                    log_q.put(["debug","AS", "In Fault list: " + str(i)])
                    faultCode = chr(faultList[2*i]) + chr(faultList[(2*i)+1])
                    # i=i+1
                    log_q.put(["error","AS","Rotate fault. Got Sampler Fault Code " + faultCode])
                
                if DS.sampler_faultRetry >1:
                    log_q.put(["debug","AS", "sampler_faultRetry: " + str(DS.sampler_faultRetry)])
                    log_q.put(["debug","AS", "Unrecoverable error in the sampler. So instructing the operator to return the sampler"])
                    DS.sampler_faultRetry = 0
                    DS.logout_cause_value  = 0
                    return 3
                else:
                    log_q.put(["debug","AS", "sampler_faultRetry: " + str(DS.sampler_faultRetry)])
                    DS.sampler_faultRetry+=1
        elif (status['rotate_state'] == 'A' or status['rotate_state'] == 'E'):
            if (time.time()>timeOut_rotate):
                Sampler.S_cmd_Reset()
                log_q.put(["debug","AS","--------------Resetting Sampler ----------------------"])

        if (status['rotate_state'] == 'E'):
            log_q.put(["info","AS","Error occured while rotation"])
            log_q.put(["debug","AS", "in Status connected: status['sample_state'] = %s, status['rotate_state'] = %s, status['status'] = %s"%(str(status['sample_state']), str(status['rotate_state']), str(status['status']))])
            cmd_done = True
            return 2

        time.sleep(0.2)

    
    DS.samplerTotalSpinCount+=1    #Updating device status values    
    log_q.put(["info","AS","SAMPLER TOTAL SPIN COUNT  = %d" % DS.samplerTotalSpinCount])         
    log_q.put(["info","AS","----------End of "+rotateCmd+" Rotate Module--------------"])
    return 1


        

def Wipe(log_q):  
    """
    Send WIPE command to the sampler and gets the status of the sampler
    """
    log_q.put(["info","AS","----------Start of Wipe Module--------------"])
    Sampler.S_cmd_Wipe()
    log_q.put(["info","AS","Wipe command sent!!!!"])
    cmd_done=False
    while(not cmd_done):
        status = Sampler.S_cmd_Get_status()
        log_q.put(["debug","AS","Got status after Wipe" + str(status)])
        if(status["status"] == 'Ready' ):
            cmd_done = True
            log_q.put(["debug","AS","wipe command complete with status "+status["sample_state"]])
            # log_q.put(["debug","AS","wipe command complete with status "+str(status["sampler_id"])])
            break
        else:
            cmd_done = True
            return False
        time.sleep(0.2)
    return True

    
def Status(log_q):   
    """
    Reads the status of Sampler, returns 0 - False or 1 - True or 2 - sampler not returning back
    """ 
    log_q.put(["info","AS","----------Wait for Sampler to be removed--------------"]) 
    samplerGone = False

    while(not samplerGone):
        status = Sampler.S_cmd_Get_status()
        if (status["status"] == 'Disconnected'):
            log_q.put(["info","AS","----------Sampler DISCONNECTED--------------"]) 
            samplerGone = True

                
            
        elif status['sample_state'] == 'T' or status['sample_state'] == 'E':
            log_q.put(["info","AS","----------Sampler TIMEDOUT BEFORE IT IS removed--------------"]) 

            samplerGone = True
            return 0
        else:
            time.sleep(1)
            
    log_q.put(["info","AS","----------Sampler removed. Wait for Sampler to be returned--------------"])

    timeout = time.time()+40   
    log_q.put(["info","AS","timeout = %d"%timeout])    
    samplerBack = False
    while(not samplerBack):
        status = Sampler.S_cmd_Get_status()
        if (status["status"] == 'Ready'):
            samplerBack = True
            if status['sample_state'] != 'R' and status['fault_code_n'] > 0:
                log_q.put(["info","AS","----------Sampler Error AFTER IT IS removed--------------"]) 

                
                return 0
            else:
            
                pass
        else:
            log_q.put(["info","AS","-------------Sampler is DISCONNECTED. Checking timeout--------------"]) 
            log_q.put(["info","AS","Timeout = %d"%timeout]) 
            log_q.put(["info","AS","time.time() = %d"%(time.time())]) 
            if time.time()>timeout:
                
                samplerNotComingBack = SamplerNotReturned(log_q)
                # QtWidgets.qApp.processEvents()
                if samplerNotComingBack.check():
                    return 2
                else:
                    timeout = time.time()+40        
            time.sleep(1)
    log_q.put(["info","AS","----------Sampler returned--------------"])
    #update results info ready for upload to SMP
    DS.samplerLastSampleStatus = ord(status['sample_state'])
    DS.samplerTriggerTime = status['dis2trigger']
    DS.samplerReconnectTime = status['trigger2dis']
    return 1
    
def checkStatus(log_q):
    """
    Checks the status of Sampler
    """
    status = Sampler.S_cmd_Get_status()
    # check status from last poll
    if status['sample_state'] == 'R':
        #analyse fault codes
        if status['fault_code_n'] > 0:
            faultList = status['fault_code']
            log_q.put(["debug","AS", "Status: " + str(status)])
            # log_q.put(["debug","AS", "Fault list length: " + str(status['fault_code_n'])])
            log_q.put(["debug","AS", "Fault list: " + str(faultList)])
            # clear Fault List
            Sampler.S_cmd_Clear_faultlist()
            for i in range (0,status['fault_code_n']):
                #get next Fault code
                log_q.put(["debug","AS", "In Fault list: " + str(i)])
                faultCode = chr(faultList[i+0]) + chr(faultList[i+1])
                log_q.put(["error","AS","Check Status, Got Sampler Fault Code " + faultCode])
                
        log_q.put(["info","AS",'Response "WIPE OK" received after taking the sample']) 

        
        DS.analyserSamplesTotal+=1    #Updating device status values
        DS.analyserPadAge+=1    #Updating device status values  
        DS.samplerFaultList+=1    #Updating device status values 
        DS.samplerTotalWipeCount+=1    #Updating device status values
        DS.samplerTotalSpinCount+=1    #Updating device status values         
        
        
        log_q.put(["info","AS","ANALYSER TOTAL SAMPLES  = %d" % DS.analyserSamplesTotal])   
        log_q.put(["info","AS","ANALYSER PAD AGE  = %d" % DS.analyserPadAge]) 
        log_q.put(["info","AS","SAMPLER LAST SAMPLE STATUS  = %s" % str(DS.samplerLastSampleStatus)])   
        log_q.put(["info","AS","SAMPLER TRIGGER TIME  = %d" % DS.samplerTriggerTime])
        log_q.put(["info","AS","SAMPLER RECONNECT TIME  = %d" % DS.samplerReconnectTime])   
        log_q.put(["info","AS","SAMPLER FAULT LIST  = %d" % DS.samplerFaultList])
        log_q.put(["info","AS","SAMPLER TOTAL WIPE COUNT  = %d" % DS.samplerTotalWipeCount])   
        log_q.put(["info","AS","SAMPLER TOTAL SPIN COUNT  = %d" % DS.samplerTotalSpinCount])
    
        return 0
    elif status['sample_state'] == 'C':
        #Sampler removed and returned but no trigger
        #return rewet and retry
        log_q.put(["error","AS","Sampler removed but trigger not pressed to take sample retrying operation"])
        Sampler.S_cmd_Clear_faultlist()
        return 1
    elif status['sample_state'] == 'T' or status['sample_state'] == 'E':
        #analyse fault codes
        if status['fault_code_n'] > 0:
            faultList = status['fault_code']
            log_q.put(["debug","AS", "Status: " + str(status)])
            # log_q.put(["debug","AS", "Fault list length: " + str(status['fault_code_n'])])
            log_q.put(["debug","AS", "Fault list: " + str(faultList)])
            # clear Fault List
            Sampler.S_cmd_Clear_faultlist()
            for i in range (0,status['fault_code_n']):
                #get next Fault code
                log_q.put(["debug","AS", "In Fault list: " + str(i)])
                faultCode = chr(faultList[i+0]) + chr(faultList[i+1])
                log_q.put(["error","AS","Got Sampler Fault Code " + faultCode])
        # return rewet and retry
        return 2



class SamplerNotReturned(QWidget):
    def __init__(self, log_q):
        self.log_q = log_q
        super (SamplerNotReturned, self).__init__()
        SamplerNotReturned.setGeometry(self, 0, 22, 480, 250)
    def check(self):
        confirm = QMessageBox.question(self, 'Message',
                    "Sampler not in place for a long time. Do you want to replace it and continue?")
        QtWidgets.qApp.processEvents() 
        if confirm == QtWidgets.QMessageBox.Yes:
            QtWidgets.qApp.processEvents() 
            self.log_q.put(["error","AS","Sampler will be returned"])
            # print("Sampler will be returned")
            return False
        else:
            self.log_q.put(["error","AS","Sampler will not be returned"])
            return True      


           



        
 
    
    