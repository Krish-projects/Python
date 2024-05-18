#!/usr/bin/python
######################################################################################
#Analyser Remote Debug script
#        This script is used to collect debug information on the remote GW even it has no public IP.
#        It can also support run command line
#V0.1        16/07/2018        By Licai Fang
######################################################################################

import sys, getopt
import iothub_service_client
from iothub_service_client import IoTHubDeviceMethod, IoTHubError
#from iothub_service_client_args import get_iothub_opt_with_module, OptionError

import base64
import time
import sys

# String containing Hostname, SharedAccessKeyName & SharedAccessKey in the format:
# "HostName=<host_name>;SharedAccessKeyName=<SharedAccessKeyName>;SharedAccessKey=<SharedAccessKey>"
CONNECTION_STRING1 = "HostName=wearsense-dev-iot.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=tJX1GpqDbtyEw7RJc6XOcYL90i8j2OgFPLKW5RW2OuE="
#CONNECTION_STRING2 = "HostName=Atamo-PSS.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=QW+TB6UZ/1GpTr+kholAuNQb5dzNeoQQCg8EXBO+FCs="
CONNECTION_STRING2 = "HostName=Atamo-PSS.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=vDswmfoOuNW9Zm0wxJuBTkxH235wpIuqfHhkYDH7BZo="
CONNECTION_STRING = CONNECTION_STRING1

DEVICE_ID = "AnalyserGW3" #PC_GW1" #"0f0000000000000c" # "AnalyserGW1" #"0f0000000000000f"        #"AnalyserGW3"  #""PC_GW1"
MODULE_ID = None
cmd = ''

METHOD_NAME = "DiagnoseGW"
METHOD_PAYLOAD = "{\"cmd\":\"ls\"}"
TIMEOUT = 60
PYTHON_CODE=''

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
    cmd = ["df |grep mmcblk",  "cat /proc/meminfo |grep MemFree" , "ip a |grep ppp0", "tail -n 50 /home/debian/pc/DaviesIoTGW.log", "systemctl status DaviesRun","systemctl status DaviesModem","tail -n 50 /var/log/daemon.log"]
    for cmd1 in cmd:
        debug_str += get_cmd_output(cmd1)

    last_str=""
    for str1 in debug_str:
        last_str+=str1

    #log.debug("DI",last_str)
    return last_str

def do_execmd(cmd):
    debug_str=[]
    debug_str=get_cmd_output(cmd)
    last_str=""
    for str1 in debug_str:
        last_str+=str1

    #log.debug("DI",last_str)
    return last_str[-MAX_SIZE_DIRECT_METHOD:]

import sys
import io
import contextlib

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = io.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old
def do_exec_python(p_code):
    log.warning("PY",p_code)
    with stdoutIO() as s:
        exec(p_code)
    log.warning("PY","exec result||| "+s.getvalue()) 
    return s.getvalue()[-MAX_SIZE_DIRECT_METHOD:]    
# ------------------------------------- firmware version ---------------------
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
            print (line)
            return m.group(1)
    return 'V1.0'

def GW_get_ver_from_str(ver_str):
    """
    V1.1 => 11    V1.0 => 10    V1.2 => 12    V10.1 => 101    V10.2 => 102    V10.10 --> not support
    """
    if(ver_str[0]!="V"):    #invalid, return default 10
        return 10
    else:
        major=''
        minor=''
        major_done=False
        for c in ver_str[1:]:
            if c == ".":
                major_done = True
                continue
            if(not major_done):
                major += c
            else:
                minor += c
        try:
            ret = int(major)*10 + int(minor)
        except:
            log.error("GF","GW_get_ver_from_str faile for %s"%ver_str)
            ret = 10
        return  ret

def GW_get_verstr_from_ver(ver):  #11->V1.1 121->V12.1
    return "V"+str(int(ver/10))+"."+str(ver-10*(ver/10))

CMD_RUN_FILE_NAME="__cmd_run.txt"
def iothub_method_sample_run():
    global METHOD_PAYLOAD,METHOD_NAME,cmd
    try:
        if cmd!="":
            if cmd =='exit':
                print("User Exit")
                return
            if cmd =='quit':
                print("User Exit")
                return
            if cmd[1]==':' :
                METHOD_NAME = "ExeCmdLongRun"
                METHOD_PAYLOAD = "{\"cmd\":\"" +cmd + "\"}"
                print(METHOD_PAYLOAD)
            # elif cmd =='EnableWifiAP':
                # METHOD_NAME = "ExeCmd"
                # cmd="cp bb-wl18xx /etc/default; reboot"
                # METHOD_PAYLOAD = "{\"cmd\":\"" +cmd + "\"}"
                # print(METHOD_PAYLOAD)
            elif cmd =='EnablePublicIP':
                METHOD_NAME = "ExeCmd"
                cmd="cp wvdial.conf.extranet /etc/wvdial.conf; reboot"
                METHOD_PAYLOAD = "{\"cmd\":\"" +cmd + "\"}"
                print(METHOD_PAYLOAD)
            else:
                METHOD_NAME = "ExeCmd"
                METHOD_PAYLOAD = "{\"cmd\":\"" +cmd + "\"}"
                print(METHOD_PAYLOAD)
                pass
            pass
        else:
            METHOD_NAME = "DiagnoseGW"
            METHOD_PAYLOAD = "{\"cmd\":\"ls\"}"
            
        if(PYTHON_CODE!=''):        #run python code on remote machine
            METHOD_NAME = "ExePython"
            cmd = base64.b64encode(PYTHON_CODE)
            METHOD_PAYLOAD = "{\"cmd\":\"" +cmd + "\"}"
            print("ExePython " + PYTHON_CODE)
            
                
        iothub_device_method = IoTHubDeviceMethod(CONNECTION_STRING)
        if (MODULE_ID is None):
            response = iothub_device_method.invoke(DEVICE_ID, METHOD_NAME, METHOD_PAYLOAD, TIMEOUT)
        else:
            response = iothub_device_method.invoke(DEVICE_ID, MODULE_ID, METHOD_NAME, METHOD_PAYLOAD, TIMEOUT)
        print("Got a response")
        rcv_str = "{0}".format(response.payload)
        try:
            print("b64decode")
            #print(base64.b64decode(rcv_str[14:-3]))
            #print("decode2")
            print(base64.b64decode(rcv_str[14:-3]).decode('UTF-8'))
            #print("string")
            #print(rcv_str[14:-3])
            #print("straight decode")
            #print(rcv_str[14:-3].decode('base64'))
        except Exception as ex:
            print("Result print failed")
            print(str(ex))
            pass



    except IoTHubError as iothub_error:
        print ( "" )
        print ( "Unexpected error {0}".format(iothub_error) )
        return
    except KeyboardInterrupt:
        print ( "" )
        print ( "IoTHubDeviceMethod sample stopped" )
        exit(0)


def usage():
    print ( "Usage: Analyser_remote_debug.py -d <device_id> -c <cmd> -i <IotHubNumber> -e <p_code>")
    print ( "    deviceid :<Existing device ID to call a method on>, e.g. Analyser2, PC_GW1 " )
    print ( "    cmd      :cmd to remote debug" )
    print ( "         exit:exit this script")
    print ( "         quit:exit this script")
#    print ( "         EnableWifiAP: enable wifi AP of this GW, GW will reboot, script error")
    print ( "         r:xxxx  : Run long run program on GW")
    print ( "         k:      : kill long run program on GW")    
    print ( "         f:      : fetch long run program output on GW")
    print ( "         other shell cmd: ")
    print ( "    p_code   :python code for remote debugging" )
    print ( "    IotHubNumber : 0-> wearsense-dev-iot.azure-devices.net (default)" )
    print ( "                 : 1-> wearsense-iot-test.azure-devices.net " )
    print ( " Example:  ./Analyser_remote_debug.py -d Analyser2 -c \"cat gw_cfg_file.csv\" ")
    print ( "           ./Analyser_remote_debug.py -d Analyser2 -c \"cd V1.5; ls\" ")
    print ( "           ./Analyser_remote_debug.py -d Analyser2 -c \"r: tail -f AnalyserIoTGW.log\" ")
    print ( "           ./Analyser_remote_debug.py -d Analyser2 -c \"f:\" ")

if __name__ == '__main__':

    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:c:i:e:h", ["help"]) # -d Device -c: command
    except getopt.GetoptError as err:
        # print help information and exit:
        print (str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    print(sys.version)
    for o, a in opts:
        if o in ("-d"):
            DEVICE_ID = a
            print("DEVICE_ID is: " + a)
        elif o in ("-c"):
            cmd = a
            print("cmd is : " + a)
        elif o in ("-i"):
            if a=='1' :
                CONNECTION_STRING = CONNECTION_STRING2
            print("CONNECTION_STRING is : " +  CONNECTION_STRING)
        elif o in ("-e"):
            PYTHON_CODE = a
            print("Python code is" +  PYTHON_CODE)
            
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"
    print("Analyser Debug session starting....")
    iothub_method_sample_run()
    print("Analyser Debug session exit!")
