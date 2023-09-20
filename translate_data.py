#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from collections import deque
import numpy as np
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-09-13
This script is composed of functions to translate binary data into TDC codes
'''
#----------------------------------------------------------------------------------------#
def etroc_translate_binary(translate_deque, valid_data, board_ID, compressed_translation, header_pattern, trailer_pattern):
    TDC_data = []
    if(not valid_data): return TDC_data

    header_1 = translate_deque.popleft()
    header_2 = translate_deque.popleft()
    trailer  = translate_deque.pop()

    event_mask = header_1[-4:]
    version    = header_2[0:4]
    event_num  = int(header_2[4:20],  base=2)
    num_words  = int(header_2[20:30], base=2)
    event_type = header_2[-2:]
    hits_count = trailer[6:18]
    crc        = trailer[-8:]
    # TODO Bad Data count, Overflow data count, Hamming Error Count

    # TODO Add to TDC_data Header stuff

    # TODO Default channel to the first active channel

    current_word = 0
    running_word = ""
    etroc_word   = ""
    while current_word<num_words:
        running_word += translate_deque.popleft()
        if(len(running_word)<40): running_word += translate_deque.popleft()
        etroc_word   = running_word[0:40]
        running_word = running_word[40:]

        # TODO advance channel when new header found

        # Decode binary and add to to TDC_data

        current_word += 1


    trail_found = False
    filler_found = False
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
            # last_line = last_line + "BCID " + last_element[28:40]
            last_line = last_line + "BCID " + f"{int(last_element[28:40], base=2)}"
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "HEADER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                # print("QD at HEADER, because found after",links[channel])
                # print(list(queues[channel]))
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at HEADER")
                sys.exit(1)
        elif(last_element[0:18]=='0'+board_ID[channel]):
            # Translating frame trailer
            trail_found = True
            last_line = last_line + "TRAILER "
            last_line = last_line + "CHIPID " + f"{hex(int(last_element[1:18], base=2))}" + " "
            last_line = last_line + "STATUS " + last_element[18:24] + " "
            last_line = last_line + "HITS " + f"{int(last_element[24:32], base=2)}" + " "
            last_line = last_line + "CRC " + last_element[32:40]
            # Expected
            if(links[channel]=="HEADER" or links[channel]=="DATA"): links[channel] = "TRAILER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="TRAILER" or links[channel]=="FILLER" or links[channel]=="START"):
                # print("QD at Trailer, because found after",links[channel])
                # print(list(queues[channel]))
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at TRAILER")
                sys.exit(1)
        elif(last_element[0:18]==pattern_3c5c+'10'):
            # Translating frame filler
            filler_found = True
            last_line = last_line + "FRAMEFILLER "
            last_line = last_line + "L1COUNTER " + last_element[18:26] + " "
            last_line = last_line + "EBS " + last_element[26:28] + " "
            last_line = last_line + "BCID " + f"{int(last_element[28:40], base=2)}"
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "FILLER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                # print("QD at FF, because found after",links[channel])
                # print(list(queues[channel]))
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at FRAME FILLER")
                sys.exit(1)
        elif(last_element[0:18]==pattern_3c5c+'11'):
            # Translating firmware filler
            filler_found = True
            last_line = last_line + "FIRMWAREFILLER "
            last_line = last_line + "MISSINGCOUNT " + f"{int(last_element[18:40], base=2)}"
            # Expected
            if(links[channel]=="START" or links[channel]=="FILLER" or links[channel]=="TRAILER"): links[channel] = "FILLER"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="DATA" or links[channel]=="HEADER"):
                # print("QD at F, because found after",links[channel])
                # print(list(queues[channel]))
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
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
            # last_line = last_line + last_element[11:11+4] + " " + last_element[15:15+4] + " "
            # last_line = last_line + last_element[19:19+12] + " " + last_element[31:40]
            # Expected
            if(links[channel]=="HEADER" or links[channel]=="DATA"): links[channel] = "DATA"
            # Error in frame, clear queue, reset link, exit function
            elif(links[channel]=="TRAILER" or links[channel]=="FILLER" or links[channel]=="START"):
                # print("QD at Data, because found after",links[channel])
                # print(list(queues[channel]))
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
                return TDC_data, 2
            # Unexpected invalid link state
            else: 
                print("ERROR! LINKS[CH] in invalid state at DATA")
                sys.exit(1)
            # Check for the hitmap's integrity, clear if >1 hit from the same pixel
            if(hitmap[channel][int(last_element[7:11], base=2),int(last_element[3:7], base=2)]>0):
                print("Dumped at hitmap")
                queues[channel].clear()
                links[channel]==""
                hitmap[channel] = np.zeros((16,16))
                return TDC_data, 2
            else: hitmap[channel][int(last_element[7:11], base=2),int(last_element[3:7], base=2)] += 1

        # When the 40 bit word is none of the above, clear queue, reset link, exit function
        else:
            # print("QD at INVALID 40 Word")
            queues[channel].clear()
            links[channel]==""
            hitmap[channel] = np.zeros((16,16))
            return TDC_data, 2
        #-----------------------------------------#
        queues[channel].append(last_line)
        # If we found a filler line, we can dump the deque into our main queue
        if(filler_found):
            if(not compressed_translation): TDC_data = list(queues[channel])
            queues[channel].clear()
            links[channel]==""
            hitmap[channel] = np.zeros((16,16))
            if(len(data)>0): queues[channel].append(data)
            return TDC_data, 3
        # If we found a trailing line, we can dump the deque into our main queue
        if(trail_found):
            if(not compressed_translation or np.any(hitmap[channel]>0)): TDC_data = list(queues[channel])
            queues[channel].clear()
            links[channel]==""
            hitmap[channel] = np.zeros((16,16))
        if(len(data)>0): queues[channel].append(data)

    return TDC_data, 2

