#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
#========================================================================================#
'''
@author: Murtaza Safdari, Jongho Lee
@date: 2023-03-30
This script is composed of functions to translate binary data into TDC codes
'''
#----------------------------------------------------------------------------------------#
def etroc1_translate(line, timestamp):
    if(timestamp==1): 
        channel = int(line[0:2], base=2)
        data = line[2:-1]                               ## Ignore final bit (hitflag =1)
    else: 
        channel = int(line[1:3], base=2)
        data = line[3:]
    if (len(data)!=29): print("Tried to unpack ETROC1 data with fewer than required data bits", data, " ", type(data), len(data)) 
    #-------------------------DTYPE CHANNEL TOT TOA CAL----------------------------------#
    TDC_data = "ETROC1 " + "{:d} ".format(channel) + "{:d} ".format(int(data[0:9], base=2)) 
    TDC_data = TDC_data + "{:d} ".format(int(data[9:19], base=2)) + "{:d}".format(int(data[19:], base=2))
    return TDC_data

#----------------------------------------------------------------------------------------#
def etroc2_translate(line, timestamp):
    TDC_data = []
    return TDC_data

#----------------------------------------------------------------------------------------#
def control_translate(line, timestamp):
    if(line[2:4]=='00'):
        time_code = line[4:6]
        data = line[6:]
        if (len(data)!=26): print("Tried to unpack ETROC1 timestamp with fewer than required data bits", data, " ", type(data), len(data)) 
        #------------------Time_TYPE Time_Measurememt (clock cycles)----------------------#
        if(time_code=='00'):   TDC_data = "NORMTRIG "   + "{:d}".format(int(data, base=2))
        elif(time_code=='01'): TDC_data = "RANDTRIG "   + "{:d}".format(int(data, base=2))
        elif(time_code=='10'): TDC_data = "FILLERTIME " + "0"
        elif(time_code=='11'): TDC_data = "MSBTIME "    + "{:d}".format(int(data, base=2))
    else: TDC_data = ""
    return TDC_data

#----------------------------------------------------------------------------------------#
def etroc_translate_binary(line, timestamp):
    data_type = ''
    if(timestamp==1): data_type = 'etroc1'              ## timestamp 0x0001: Disable Testmode & Disable TimeStamp: OLD DATA
    ########################################## CHECK IF TEST ON AND TIME OFF IS OLD DATA
    elif(line[0]=='0'): data_type = 'etroc1'
    elif(line[0]=='1'): 
        if(line[1]=='0'): data_type = 'control'
        elif(line[1]=='1'): data_type = 'etroc2'

    if(data_type == 'etroc1'): TDC_data = etroc1_translate(line, timestamp)
    elif(data_type == 'etroc2'): TDC_data = etroc2_translate(line, timestamp)
    elif(data_type == 'control'): TDC_data = control_translate(line, timestamp)

    return TDC_data