#!/usr/bin/python
# #############################################################################################################
# gen_release_tgz.py
# Created by: Licai Fang/Andrew Holmes
# Date: 13/07/2018
# Function: This python file will generate the release file PSS_v*.*.tgz, where ** is the version e.g. 1.1
# Revision History:
#   V0.1   13/07/2018: first draft
#   V 0.next   6/6/2019: moified for use in PSS
# Input:
#   This script should be run under /pc directory
# Output:
#   In the readme.txt, 1st line, there is the version string.
#   Then mkidr of Analyser/Release/v*.*
#   cd Analyser/Release; tar czvf Analyser_v*.*.tgz v*.*
#   generate PSS_Analyser_v*.*.tgz.crc.txt
#   
# #############################################################################################################
Release_DIR = './Release/'
Version_File = './readme.txt'

import os.path
import binascii
import re
import tarfile
import zlib
import shutil
import glob
# ------------------------------------- firmware version ---------------------
def fetch_firmware_version(filename):
    """
    V1.1 Change List -> Return V1.1
    V1.2 Change List -> Retrun V1.2
    """
    f = open(filename, "r")
    content = f.read().splitlines()
    for line in content:
        m = re.search("(.+)\sChange list",line)  #+((d)<<8\s+|(d))",line)   #
        if(m):
            print (line)
            return m.group(1)
    return None
def file_crc( fileName):
    prev = 0
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)


import struct
from Crypto.Cipher import AES


def pad16(s):
    t = struct.pack('>I', len(s)) + s
    return t + '0'.encode() * ((16 - len(t) % 16) % 16)


def unpad16(s):
    n = struct.unpack('>I', s[:4])[0]
    return s[4:n + 4]


class Crypt(object):
    def __init__(self, password):
        # password = pad16(password)
        # password = password.encode()
        self.cipher = AES.new(password, AES.MODE_ECB)

    def encrypt(self, s):
        s = pad16(s)
        return self.cipher.encrypt(s)

    def decrypt(self, s):
        t = self.cipher.decrypt(s)
        return unpad16(t)


if __name__ == "__main__":
    """
    Running under software\pc
    """
    p = 'AnalyserFirmware@Atamo01'.encode()
    s = 'my message'.encode()

    c = Crypt(p)
    x = c.encrypt(s)
    y = c.decrypt(x)
    #print [x, y]

    ret_firmware=fetch_firmware_version(Version_File)
    print("Generate Release file for Firmware version: " + ret_firmware)

    v_dir="./release/"+ret_firmware
    #cmd = "mkdir "+v_dir
    #os.system(cmd)
    if not os.path.exists(v_dir):
        os.makedirs(v_dir)
    #cmd = "copy *.py " + v_dir
    #os.system(cmd)
    shutil.copy("./readme.txt", v_dir)
    for f in glob.glob(r'./*.py'):
        shutil.copy(f, v_dir)    
    for f in glob.glob(r'./cfg*'):
        #print(f)
        shutil.copy(f, v_dir)    
    for f in glob.glob(r'./*.service'):
        shutil.copy(f, v_dir)    
    for f in glob.glob(r'./wvdial.*'):
        shutil.copy(f, v_dir)    
    for f in glob.glob(r'./s4*'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./*.sh'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./*.jpg'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./*.json'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./xorg.*'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./params*'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./*.jpeg'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./readme.txt'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./uEnv.txt'):
        shutil.copy(f, v_dir)
    for f in glob.glob(r'./BB-I2C2-RTC-DS3231.dtbo'):
        shutil.copy(f, v_dir)
    shutil.copytree('planeinfo', v_dir + '/planeinfo/')
    shutil.copytree('CSV_files', v_dir + '/CSV_files/')
    shutil.copytree('pyvesc', v_dir + '/pyvesc/')
    shutil.copytree('PyCRC', v_dir+ '/PyCRC/')

    os.chdir("./release")

    tar = tarfile.open(ret_firmware+".tgz", "w:gz")
    tar.add(ret_firmware, arcname=ret_firmware)
    tar.close()    

    f_rd = open(ret_firmware+".tgz", "rb")
    f_wr = open("Analyser_" + ret_firmware +".tgz", "wb")
    content = f_rd.read()
    tgz_c = c.encrypt(content)
    f_wr.write(tgz_c)
    f_rd.close()
    f_wr.close()

    print("Generated Release file " +"Analyser_" + ret_firmware +".tgz")
    tgz_filename="Analyser_" + ret_firmware +".tgz"
    crc=file_crc(tgz_filename)
    print("With crc: "+crc)
    f = open("Analyser_" + ret_firmware +".tgz_crc_"+crc+".txt", "w")
    f.write(crc+"\n")
    f.close()

    f_rd = open(tgz_filename, "rb")
    f_wr = open("check_Analyser_" + ret_firmware +".tgz", "wb")
    content = f_rd.read()
    tgz_c = c.decrypt(content)
    f_wr.write(tgz_c)
    f_rd.close()
    f_wr.close()

