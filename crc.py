# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 11:29:38 2018

@author: Ben
"""
import crc8

def append_crc(packet_send):
    
    hash = crc8.crc8()
    hash.update(packet_send)
    m = hash.hexdigest()#.encode('ascii')
    if ord(m[0]) > 96:                          #this step is necessary because the crc8 module outputs the ascii characters in lower case
        m0 = chr(ord(m[0]) - 32)                #convert to upper case
    else:
        m0 = m[0]                               #else just copy the value
    if ord(m[1]) > 96:
        m1 = chr(ord(m[1]) - 32)
    else:
        m1 = m[1]
    m = m0 + m1
    packet_send = packet_send + m.encode('ascii')       #concat crc onto end of command
    #print ("packet_send=",packet_send)
    return packet_send

def crc_response(packet_receive):
    start=999

    for index in range (0,len(packet_receive)-1):       
        if packet_receive[index] == 0x8c:    
            start=index        
            lhigh=packet_receive[start+2]-48            #requires data length ascii hex characters to be in upper case Sampler side
            if lhigh>9:
                lhigh-=7
            print(str(lhigh))
            llow=packet_receive[start+3]-48
            if llow>9:
                llow-=7
            print(str(llow))
            length=16*lhigh+llow
            print ("length=",length)
      
            break
    if start<999:
        packet=packet_receive[start:start+length+4]
        try:
            packetcrc=packet_receive[start+length+4:start+length+6].decode("utf-8")

            
        except Exception:
            packetcrc=0
            print("Bad crc")
            
        hash=crc8.crc8()
        hash.update(packet)
        calccrc=hash.hexdigest().upper()  
        if calccrc == packetcrc:
            print("Good crc")
            # print("packet crc =",packetcrc,"calcrc=",calccrc)
            return 1
        else:
            print("Bad crc")
            return 0
    else:
        # print("Didn't find packet start")
        return 0