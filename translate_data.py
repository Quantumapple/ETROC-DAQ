#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from collections import deque
import numpy as np
import time
import threading
import os
from queue import Queue
import queue
import datetime
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-09-13
This script is composed of functions to translate binary data into TDC codes
'''

def div_ceil(x,y):
    return -(x//(-y))

#--------------------------------------------------------------------------#
# Threading class to only TRANSLATE the binary data and save to disk
class Translate_data(threading.Thread):
    def __init__(self, name, firmware_key, check_valid_data_start, translate_queue, cmd_interpret, num_line, store_dict, skip_translation, board_ID, write_thread_handle, translate_thread_handle, compressed_translation, stop_DAQ_event = None, debug_event_translation = False, lock_translation_numwords = False):
        threading.Thread.__init__(self, name=name)
        self.firmware_key            = firmware_key
        self.check_valid_data_start  = check_valid_data_start
        self.translate_queue         = translate_queue
        self.cmd_interpret           = cmd_interpret
        self.num_line                = num_line
        self.store_dict              = store_dict
        self.skip_translation        = skip_translation
        self.board_ID                = board_ID
        self.write_thread_handle     = write_thread_handle
        self.translate_thread_handle = translate_thread_handle
        self.stop_DAQ_event          = stop_DAQ_event
        self.compressed_translation  = compressed_translation
        self.debug_event_translation = debug_event_translation
        self.lock_translation_numwords = lock_translation_numwords
        self.translate_deque         = deque()
        self.valid_data              = False if check_valid_data_start else True
        self.header_pattern          = format(0xc3a3c3a, "028b")
        self.trailer_pattern         = '001011'
        self.channel_header_pattern  = format(0x3c5c, "016b")
        self.file_lines              = 0
        self.file_counter            = 0
        self.retry_count             = 0
        self.in_event                = False
        self.eth_words_in_event      = -1
        self.words_in_event          = -1
        self.current_word            = -1
        self.event_number            = -1

    def reset_params(self):
        self.translate_deque.clear()
        self.in_event           = False
        self.eth_words_in_event = -1
        self.words_in_event     = -1
        self.current_word       = -1
        self.event_number       = -1

    def run(self):
        t = threading.current_thread()
        t.alive      = True
        
        if(not self.skip_translation): 
            outfile  = open("%s/TDC_Data_translated_%d.nem"%(self.store_dict, self.file_counter), 'w')
            print("{} is reading queue and translating file {}...".format(self.getName(), self.file_counter))
        else:
            print("{} is reading queue and translating...".format(self.getName()))
        while True:
            if not t.alive:
                print("Translate Thread detected alive=False")
                if(not self.skip_translation): outfile.close()
                break 
            if((not self.skip_translation) and self.file_lines>self.num_line):
                outfile.close()
                self.file_lines   = 0
                self.file_counter = self.file_counter + 1
                outfile = open("%s/TDC_Data_translated_%d.nem"%(self.store_dict, self.file_counter), 'w')
                print("{} is reading queue and translating file {}...".format(self.getName(), self.file_counter))
            binary = ""
            # Attempt to pop off the translate_queue for 30 secs, fail if nothing found
            try:
                binary = self.translate_queue.get(True, 1)
                self.retry_count = 0
            except queue.Empty:
                if not self.stop_DAQ_event.is_set:
                    self.retry_count = 0
                    continue
                if self.translate_thread_handle.is_set():
                    print("Translate Thread received STOP signal AND ran out of data to translate")
                    break
                self.retry_count += 1
                if self.retry_count < 30:
                    continue
                print("BREAKING OUT OF TRANSLATE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST FETCH FROM TRANSLATE_QUEUE!!!")
                break
            # Event Header Found
            if(binary[0:28]==self.header_pattern):
                self.reset_params()
                self.in_event = True
                self.translate_deque.append(binary)
                continue
            # Event Header Line Two Found
            elif(self.in_event and (self.words_in_event==-1) and (binary[0:4]==self.firmware_key)):
                self.current_word       = 0
                self.event_number       = int(binary[ 4:20], base=2)
                self.words_in_event     = int(binary[20:30], base=2)
                self.eth_words_in_event = div_ceil(40*self.words_in_event,32)
                # TODO EVENT TYPE?
                self.translate_deque.append(binary)
                # Set valid_data to true once we see fresh data
                if(self.event_number==1): self.valid_data = True
                continue
            # Event Header Line Two NOT Found after the Header
            elif(self.in_event and (self.words_in_event==-1) and (binary[0:4]!=self.firmware_key)):
                self.reset_params()
                continue
            # Trailer NOT Found but we already read more words then we were supposed to
            # elif(self.in_event and (self.eth_words_in_event==-1 or self.eth_words_in_event<self.current_word)):
            #     self.reset_params()
            #     continue
            # Trailer NOT Found after the required number of ethernet words was read
            elif(self.in_event and (self.eth_words_in_event==self.current_word) and (binary[0:6]!=self.trailer_pattern) and (not self.debug_event_translation)):
                self.reset_params()
                continue
            # Trailer Found - DO NOT CONTINUE
            elif(self.in_event and (self.eth_words_in_event==self.current_word) and (binary[0:6]==self.trailer_pattern) and (not self.debug_event_translation)):
                self.translate_deque.append(binary)
            # Trailer Found - Debug is true
            elif(self.in_event and (binary[0:6]==self.trailer_pattern) and (self.debug_event_translation)):
                if((self.eth_words_in_event==self.current_word and self.lock_translation_numwords) or (not self.lock_translation_numwords)):
                    self.translate_deque.append(binary)
            # Event Data Word
            elif(self.in_event):
                self.translate_deque.append(binary)
                self.current_word += 1
                continue
            # Ethernet Line not inside Event, Skip it
            else: continue

            # We only come here if we saw a Trailer, but let's put a failsafe regardless
            if((not self.debug_event_translation) and len(self.translate_deque)!=self.eth_words_in_event+3): 
                self.reset_params()
                continue

            TDC_data = etroc_translate_binary(self.translate_deque, self.valid_data, self.board_ID, self.compressed_translation, self.channel_header_pattern, self.header_pattern, self.trailer_pattern, self.debug_event_translation)
            TDC_len = len(TDC_data)
            if((not self.skip_translation) and (TDC_len>0)): 
                for TDC_line in TDC_data:
                    outfile.write("%s\n"%TDC_line)
                self.file_lines  = self.file_lines  + TDC_len

            # Reset all params before moving onto the next line
            del TDC_data, TDC_len, binary
            self.reset_params()
        
        print("Translate Thread gracefully ending") 
        self.translate_thread_handle.set()
        del t
        if(not self.skip_translation): outfile.close()
        print("%s finished!"%self.getName())

#----------------------------------------------------------------------------------------#
def etroc_translate_binary(translate_deque, valid_data, board_ID, compressed_translation, channel_header_pattern, header_pattern, trailer_pattern, debug=False):
    TDC_data = []
    if(not valid_data): return TDC_data
    header_1 = translate_deque.popleft()
    header_2 = translate_deque.popleft()
    trailer  = translate_deque.pop()
    event_mask = header_1[-4:]
    version    = header_2[0:4]
    event_num  = int(header_2[4:20],  base=2)
    num_words  = int(header_2[20:30], base=2)
    event_type = header_2[30:32]
    hits_count = trailer[6:18]
    crc        = trailer[-8:]
    overflow_count = trailer[18:21]
    hamming_count  = trailer[21:24]
    TDC_data.append(f"EH {version} {event_num} {int(hits_count, base=2)} {num_words}")
    # TODO Bad Data count, Overflow data count, Hamming Error Count
    active_channels = []
    for idx in range(4):
        if(event_mask[3-idx]=="1"): active_channels.append(idx)
    active_channels = deque(active_channels)
    # TODO Handle deletion of variables created in this method
    current_word = 0
    running_word = ""
    etroc_word   = ""
    current_channel = -1
    # pattern_3c5c = '0011110001011100'
    while translate_deque:
        try:
            running_word = running_word + translate_deque.popleft()
        except IndexError:
            print("Empty queue in while loop")
        if(len(running_word)<40): 
            try:
                running_word = running_word + translate_deque.popleft()
            except IndexError:
                print("Empty queue when reading twice in the same loop")
        etroc_word   = running_word[0:40]
        running_word = running_word[40:]
        current_word += 1
        if(debug): 
            TDC_data.append(f"{etroc_word}")
            if(not translate_deque): TDC_data.append(f"{running_word}")
            continue
        # HEADER "H {channel} {L1Counter} {Type} {BCID}"
        if(etroc_word[0:18]==channel_header_pattern+'00'):
            try:
              current_channel=active_channels.popleft()
            except IndexError:
              print("The active_channels deque is empty, more headers found than event mask can allow")
              TDC_data.append(f"THIS IS A BROKEN EVENT SINCE MORE HEADERS THAN MASK FOUND")
            TDC_data.append(f"H {current_channel} {int(etroc_word[18:26], base=2)} {etroc_word[26:28]} {int(etroc_word[28:40], base=2)}")
        # DATA "D {channel} {EA} {ROW} {COL} {TOA} {TOT} {CAL}"
        elif(etroc_word[0]=='1'):
            TDC_data.append(f"D {current_channel} {int(etroc_word[1:3], base=2)} {int(etroc_word[7:11], base=2)} {int(etroc_word[3:7], base=2)} {int(etroc_word[11:21], base=2)} {int(etroc_word[21:30], base=2)} {int(etroc_word[30:40], base=2)}")
        # TRAILER "T {channel} {Status} {Hits} {CRC}"
        elif(etroc_word[0:18]=='0'+board_ID[int(current_channel)]):
            TDC_data.append(f"T {current_channel} {int(etroc_word[18:24], base=2)} {int(etroc_word[24:32], base=2)} {int(etroc_word[32:40], base=2)}")
    # TDC_data.append(f"ET {event_num} {event_type} {overflow_count} {hamming_count} {crc}")
    TDC_data.append(f"ET {event_num}")
    return TDC_data

