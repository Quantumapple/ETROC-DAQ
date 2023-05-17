#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from collections import deque
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-03-30
This script is composed of functions to translate binary data into TDC codes
'''
#----------------------------------------------------------------------------------------#
def etroc1_translate(line, timestamp):
    if(timestamp==1 or timestamp==3): 
        channel = int(line[0:2], base=2)
        data = line[2:-1]                               ## Ignore final bit (hitflag =1)
    else: 
        channel = int(line[1:3], base=2)
        data = line[3:]
    if (len(data)!=29): print("Tried to unpack ETROC1 data with fewer than required data bits", data, " ", type(data), len(data)) 
    #-------------------------DTYPE CHANNEL TOT TOA CAL----------------------------------#
    TDC_data = "ETROC1 " + "{:d} ".format(channel) + "{:d} ".format(int(data[0:9], base=2)) 
    TDC_data = TDC_data + "{:d} ".format(int(data[9:19], base=2)) + "{:d}".format(int(data[19:], base=2))
    return TDC_data, 1

#----------------------------------------------------------------------------------------#
def etroc2_translate(line, timestamp, queues, links, board_ID):
    TDC_data = []
    pattern_3c5c = '0011110001011100'
    trail_found = False
    channel = int(line[2:4], base=2)
    # Discard first 4 bits which are 11+channel
    data = line[4:]
    if (len(data)!=28): print("Tried to unpack ETROC2 data with fewer than required data bits / line", data, " ", type(data), len(data))
    # append new line to the right of deque if deque is empty, or is linked and previously translated
    # If the link is not established and deque was empty, check if you're adding a line with the fixed pattern in it and if so only keep relevant part of the stream
    # Function returns empty list
    if (len(queues[channel])==0): 
        if(len(links[channel])>0):
            queues[channel].append(data)
        else:
            if(pattern_3c5c in data):
                links[channel] = "START"
                staring_index = data.find(pattern_3c5c)
                queues[channel].append(data[staring_index:])
            else: queues[channel].append(data)
        return TDC_data, 2
    if(len(links[channel])>0):
        if(queues[channel][-1][0]!='0' and queues[channel][-1][0]!='1'): 
            queues[channel].append(data)
            return TDC_data, 2
    # else unpack last element to complete lines
    last_element = queues[channel].pop()
    # If not linked yet, check for fixed pattern in the old + new data
    if(len(links[channel])==0):
        new_line = last_element + data
        # If not found, discard old element and return empty list
        if(not pattern_3c5c in new_line):
            queues[channel].append(data)
            return TDC_data, 2
        # If found, prepare last_element and data with 40 bit words + residual if possible, proceed to attempt translation
        else:
            links[channel] = "START"
            staring_index = new_line.find(pattern_3c5c)
            new_line = new_line[staring_index:]
            nl_res_len = 40 - len(new_line)
            last_element = new_line[0:40]
            if(nl_res_len>=0): data = ""
            else: data = new_line[nl_res_len:]
    # If linked already, prepare last_element and data with 40 bit words + residual if possible, proceed to attempt translation
    else:
        # ETROC2 word length is 40 bits
        residual_len = 40 - len(last_element)
        # Note overspills are handled correctly in Python 3.6.8
        last_element = last_element + data[0:residual_len]
        data = data[residual_len:]
    if(len(last_element)>40): 
        print("ERROR! MORE THAN 40 BITS BEING TREATED AS A WORD!")
        sys.exit(1)
    # If last_element is less than 40 bits, push back and hope for new data
    elif(len(last_element)< 40): queues[channel].append(last_element)
    # If it is 40 bits, we can translate!
    elif(len(last_element)==40):
        #-------Translate 40bit ETROC word--------#
        last_line = "ETROC2 " + "{:d} ".format(channel)
        if(last_element[0:18]==pattern_3c5c+'00'):
            # Translating frame header
            # We add a unique element here to track how many data lines there are in this block
            queues[channel].append("HEADER_KEY")
            last_line = last_line + "HEADER "
            last_line = last_line + "L1COUNTER " + last_element[18:26] + " "
            last_line = last_line + "TYPE " + last_element[26:28] + " "
            last_line = last_line + "BCID " + last_element[28:40]
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "HEADER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                queues[channel].clear()
                links[channel]==""
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at HEADER")
                sys.exit(1)
        elif(last_element[0:18]=='0'+board_ID[channel]):
            # Translating frame trailer
            trail_found = True
            last_line = last_line + "TRAILER "
            last_line = last_line + "CHIPID " + last_element[1:18] + " "
            last_line = last_line + "STATUS " + last_element[18:24] + " "
            last_line = last_line + "HITS " + last_element[24:32] + " "
            last_line = last_line + "CRC " + last_element[32:40]
            # Expected
            if(links[channel]=="HEADER" or links[channel]=="DATA"): links[channel] = "TRAILER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="TRAILER" or links[channel]=="FILLER" or links[channel]=="START"):
                queues[channel].clear()
                links[channel]==""
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at TRAILER")
                sys.exit(1)
        elif(last_element[0:18]==pattern_3c5c+'10'):
            # Translating frame filler
            last_line = last_line + "FRAMEFILLER "
            last_line = last_line + "L1COUNTER " + last_element[18:26] + " "
            last_line = last_line + "EBS " + last_element[26:28] + " "
            last_line = last_line + "BCID " + last_element[28:40]
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "FILLER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                queues[channel].clear()
                links[channel]==""
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at FRAME FILLER")
                sys.exit(1)
        elif(last_element[0:18]==pattern_3c5c+'11'):
            # Translating firmware filler
            last_line = last_line + "FIRMWAREFILLER "
            last_line = last_line + "MISSINGCOUNT " + last_element[18:40]
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "FILLER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                queues[channel].clear()
                links[channel]==""
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at FIRMWARE FILLER")
                sys.exit(1)
        elif(last_element[0]=='1'):
            # Translating data
            last_line = last_line + "DATA "
            last_line = last_line + "EA " + last_element[1:3] + " "
            last_line = last_line + "COL " + "{:d} ".format(int(last_element[3:7], base=2))
            last_line = last_line + "ROW " + "{:d} ".format(int(last_element[7:11], base=2))
            last_line = last_line + "TOA " + "{:d} ".format(int(last_element[11:21], base=2))
            last_line = last_line + "TOT " + "{:d} ".format(int(last_element[21:30], base=2))
            last_line = last_line + "CAL " + "{:d} ".format(int(last_element[30:40], base=2))
            last_line = last_line + last_element[11:11+4] + " " + last_element[15:15+4] + " "
            last_line = last_line + last_element[19:19+12] + " " + last_element[31:40]
            # Expected
            if(links[channel]=="HEADER" or links[channel]=="DATA"): links[channel] = "DATA"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="TRAILER" or links[channel]=="FILLER" or links[channel]=="START"):
                queues[channel].clear()
                links[channel]==""
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at DATA")
                sys.exit(1)
        # When the 40 bit word is none of the above, clear queue, reset link, exit function
        else:
            queues[channel].clear()
            links[channel]==""
            return TDC_data, 2
        #-----------------------------------------#
        queues[channel].append(last_line)
        # If we found a trailing line, we can dump the deque into our main queue
        if(trail_found):
            TDC_data = list(queues[channel])
            queues[channel].clear()
            links[channel]==""
        if(len(data)>0): queues[channel].append(data)

    return TDC_data, 2

#----------------------------------------------------------------------------------------#
def control_translate(line, timestamp):
    if(line[2:4]=='00'):
        time_code = line[4:6]
        data = line[6:]
        if (len(data)!=26): print("Tried to unpack ETROC1 timestamp with fewer than required data bits", data, " ", type(data), len(data)) 
        #------------------Time_TYPE Time_Measurememt (clock cycles)----------------------#
        #--NORMTRIG is 26 bit counter, MSBTIME is also 26 bit counter cathes NORMTRIG overflows--#
        # --25ns per counter cycle, and 25*32 ns per NORMTRIG increment in Qing operations --#
        if(time_code=='00'):   TDC_data = "NORMTRIG "   + "{:d}".format(int(data, base=2))
        elif(time_code=='01'): TDC_data = "RANDTRIG "   + "{:d}".format(int(data, base=2))
        elif(time_code=='10'): TDC_data = "FILLERTIME " + "0"
        elif(time_code=='11'): TDC_data = "MSBTIME "    + "{:d}".format(int(data, base=2))
    elif(line[2:6]=='0110'): TDC_data = "FILLER"
    else: TDC_data = ""
    return TDC_data, 1

#----------------------------------------------------------------------------------------#
def etroc_translate_binary(line, timestamp, queues, links, board_ID):
    data_type = ''
    if(timestamp==1): data_type = 'etroc1'              ## timestamp 0x0001: Disable Testmode & Disable TimeStamp: OLD DATA
    ########################################## CHECK IF TEST ON AND TIME OFF IS OLD DATA
    elif(line[0]=='0'): data_type = 'etroc1'
    elif(line[0]=='1'): 
        if(line[1]=='0'): data_type = 'control'
        elif(line[1]=='1'): data_type = 'etroc2'

    if(data_type == 'etroc1'): TDC_data = etroc1_translate(line, timestamp)
    elif(data_type == 'etroc2'): TDC_data = etroc2_translate(line, timestamp, queues, links, board_ID)
    elif(data_type == 'control'): TDC_data = control_translate(line, timestamp)

    return TDC_data