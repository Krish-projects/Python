import datetime
import os
import sys
import time
from dateutil.relativedelta import relativedelta

from datetime import date, datetime, time 

import Analyser_AzureIoT as IoT   #for all global variables
 
 
###########---------List of parameters for Device status-----########## 
# messageType Text Status
# samplesTotal Int Total samples taken ever
# samplesThisPad Int Number of samples with this pad
# padsTotal Int Total number of pads ever
# solventID String ID of current solvent bag
# solventCount Int Number of samples with this solvent bag
# wasteID String ID of current waste bag
# wasteCount Int Number of samples with this waste bag
# solventTotal Int Total solvent bags used ever
# analyserBatteryLevel Int (0 – 100) Current Analyser battery level
# samplerBatteryLevel Int (0 – 100) Current Sampler battery level
# samplerTotalWipeCount Int
# samplerTotalSpinCount Int
# samplerFaultList List See samplerFaultList
# sofwareVersion Text
# upTime Int Seconds since Analyser startup
# dateTime

global startupTime 
startupTime= datetime.now()        
print ("Device Status.py startin at : startupTime",startupTime)
messageType = 5 #so IoT Hub can differentiate from results  #message type
datetime_current = datetime.now() #dateTime
firmware_ver = 10
connectionStatus = 0
planenumberAndrego = []
engineer = True
process_started = True
CDC_software = ""
downloadWOs = 1 #if true download WOs from SMP at login, else display empty list

crc_str=''
SOFT_WDT_TIMEOUT=60*60 + 10*60        
        
#Analyser details to be updated
analyserBattery = 99 #analyserBatteryLevel
analyserVoltage = 12
analyserBatteryThreshold = 0
analyserCharging = 0 #analyser charging if 1
analyserSamplesTotal = 0 #samplesTotal
analyserPadAge = 0 #samplesThisPad
analyserPadsTotal = 0 #padsTotal
calibrationFactor = 0  ##This factor will be 1 for all other analysers except ET13
calibratedTime = 0
calibrationTimeLimit = 0

analyserLabSampleID = ""
analyserLabSampleCount = 0
enableLabSample = ""

sampleSquirtVolume = 0
postSamplingSolventVolume = 0
sampleRinseSquirtVolume = 0
calibrateVolume = 0
resetSolventBagVolume = 0
referenceThreshold = 0
referenceThreshold_positive = 0
referenceThreshold_negative = 0
confidenceThreshold = 0
padAgeThreshold = 0
rinseCountReqd = 0
sampleVolume = 0
labSampleVolume = 0
lab_RinseCountReqd = 0
WipeRotations = 0
calConstant = 0
ledSettleTime = 99

cause_Of_logout = ["SAMPLER ERROR", "SAMPLER NOT RETURNING BACK", "LED HEATER ERROR" , "UNABLE TO DRAIN COMPLETELY", "INSUFFICIENT SUPPLIES", "CHARGER CONNECTED", "SPECTROMETER NOT FOUND", "CALIBRATION FAILED"]
logout_cause_value = 0

totalSamplingLocations = 0

analyserSolventThreshold = 0 #if solvent remaining is less than this then prompt to change bag
analyserWasteThreshold = 0

analysersolventTotal = 0 #solventTotal    total solvent bags used
analyserSolventID = "" #solventID
analyserSolventRemaining = 0 ####Clean solvent available for sampling
analyserSolventCount = 0

analyserSolventCapacity = 0
analyserWasteCapacity = 0
analyserwasteTotal = 0 #wastesolventTotal    total waste solvent bags used
analyserWasteID = "" #wasteID
analyserWasteRemaining = 0     ####Waste solvent stored after sampling
analyserWasteCount = 0

pumpDispense_per_rev = 0

modemRSSI = 0 # current value of signal strength for display on UI

spectroSerialNumber = ''
spectroEthanolReference = '' # holds ethanol reference filename for this spectrometer


#some Counters
 
samplingCount = 0
totalTimeCount = 0
sampler_faultRetry = 0
samplingStartTime = datetime.now()
totalTime = relativedelta(datetime.now()-samplingStartTime)
        
        

#Sampler details to be updated 
sampleTime = 0       
samplerBattery = 0 #samplerBatteryLevel
samplerBatteryThreshold = 50
samplerCharging = 0 #sampler charging if 1
samplerTotalWipeCount = 0 #samplerTotalWipeCount
samplerTotalSpinCount = 0 #samplerTotalSpinCount
samplerLastSampleStatus = 0
samplerTriggerTime = 0
samplerReconnectTime = 0
samplerFaultList = 0 #samplerFaultList
statusPacket_lengthIdentifier = 66
statusPacket_rotateIdentifier = 67


# Result variables
result = 0
confidence = 0
error = 0
absorbance = 0




# Some global values
log_q = 0
ourSiteIataCode = 'XXX'
ourTimezone = ''
Site = ''
SiteKey = ''
userID = ''
analyserID = ""
samplerID = b''
deviceName = ""
integrationTime = ""
brightness255 = ""
brightness275 = ""
brightness285 = ""
brightness295 = ""
rst = ""
RowStart = 0
RowEnd = 0
targetTemp = 0
actual_rev = 0
locationsList = []
LEDs	= ()
factory_val_WL = []
factory_val_intensity = []


homeDirectory = '/home/debian/PSS/'
refFilesDirectory = homeDirectory + 'CSV_files/'
homeRwDirectory = '/var/PSS/'
localRefFilesDirectory = homeRwDirectory + 'CSV_files/'
resultsDirectory = homeRwDirectory + 'Results/'
regoDirectory = homeDirectory+'planeinfo/'

# solvent and waste bag capacity values

# print ("Device Status.py ending at : endTime",datetime.now() )

def format_sleep_status():
    sleepStatus = {}
    sleepStatus['samplerTotalWipeCount'] = samplerTotalWipeCount
    sleepStatus['samplerTotalSpinCount'] = samplerTotalSpinCount
    sleepStatus['analyserSamplesTotal'] = analyserSamplesTotal
    sleepStatus['analyserPadAge'] = analyserPadAge
    sleepStatus['analysersolventTotal'] = analysersolventTotal
    sleepStatus['analyserPadsTotal'] = analyserPadsTotal
    sleepStatus['analyserSolventRemaining'] = analyserSolventRemaining
    sleepStatus['analyserWasteRemaining'] = analyserWasteRemaining
    sleepStatus['analyserwasteTotal'] = analyserwasteTotal
    sleepStatus['analyserLabSampleCount'] = analyserLabSampleCount
    sleepStatus['analyserBattery'] = analyserBattery
    sleepStatus['analyserSolventID'] = analyserSolventID
    return sleepStatus

    
    
def format_dev_status():
    upTime=datetime.now()-startupTime #upTime
    print("UpTime = ", upTime,"hr:min:sec")
    # global G_AN_STATUS
    s_format = "{\"messageType\": %s, \"analyserID\": \"%s\", \"samplerID\":\"%s\",\"analyserBattery\": %d,\"samplerBattery\": %d\
    ,\"samplerTotalWipeCount\": %d,\"samplerTotalSpinCount\": %d, \"samplerLastSampleStatus\" : %d,\"UpTime\": %s\
    ,\"samplerTriggerTime\": %d, \"samplerReconnectTime\": %d, \"samplerFaultList\": %d, \"analyserSamplesTotal\": %d, \"analyserPadAge\": %d\
    , \"analyserPadsTotal\": %d, \"analyserSolventID\":\"%s\", \"analyserWasteID\":\"%s\", \"analyserSolventCount\": %d\
    , \"analyserWasteCount\": %d , \"firmwareVersion\": \"%s\, \"datetime\": \"%s\,  \"analysersolventTotal\": \"%s\,  \"analyserwasteTotal\": \"%s\
	, \"analyserLabSampleID\": %s, \"analyserLabSampleCount\": %d}"

    message = s_format%(str(messageType), analyserID, samplerID,analyserBattery,samplerBattery
    , samplerTotalWipeCount, samplerTotalSpinCount, samplerLastSampleStatus, upTime
    , samplerTriggerTime, samplerReconnectTime, samplerFaultList, analyserSamplesTotal,analyserPadAge
    , analyserPadsTotal, analyserSolventID, analyserWasteID, analyserSolventCount
    , analyserWasteCount, firmware_ver, datetime_current, analysersolventTotal, analyserwasteTotal
	, analyserLabSampleID, analyserLabSampleCount)
    return message
