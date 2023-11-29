#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import threading
import numpy as np
import os
from queue import Queue
from collections import deque
import queue
from command_interpret import *
from translate_data import *
import datetime
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-09-13
This script is composed of all the helper functions needed for I2C comms, FPGA, etc
'''
#--------------------------------------------------------------------------#
def div_ceil(x,y):
    return -(x//(-y))

#--------------------------------------------------------------------------#
def set_all_trigger_linked(cmd_interpret, inspect=False):
    print("Resetting/Checking links till ALL boards are linked...")
    register_15 = cmd_interpret.read_config_reg(15)
    string_15   = format(register_15, '016b')
    channel_enable = string_15[-4:]
    linked_flag = False
    while linked_flag == False:
        linked_flag = True
        for i in range(4):
            if(channel_enable[3-i]=="0"): continue
            print("Retrieving channel", i, "...")
            timestamp(cmd_interpret, key = int('000000000000'+format(i, '02b')+'00', base=2))
            time.sleep(0.01)
            if(inspect): time.sleep(4)
            register_2 = format(cmd_interpret.read_status_reg(2), '016b')
            print("Register 2 upon read:", register_2)
            data_error = register_2[-1]
            df_synced = register_2[-2]
            trigger_error = register_2[-3]
            trigger_synced = register_2[-4]
            linked_flag =  linked_flag and (data_error=="0" and df_synced=="1" and trigger_error=="0" and trigger_synced=="1")
        if(linked_flag == False and inspect == False):
            software_clear_fifo(cmd_interpret)
            time.sleep(2.01)
            print("Cleared FIFO...")
        elif(inspect): break
    print("Done!")
    del register_15,string_15,channel_enable,register_2,data_error,df_synced,trigger_error,trigger_synced
    return linked_flag

#--------------------------------------------------------------------------#
def configure_memo_FC(cmd_interpret, BCR = False, QInj = False, L1A = False, Initialize = True, Triggerbit=True, repeatedQInj=False, L1ARange = False):
    if(Initialize):
        register_11(cmd_interpret, 0x0deb)
        time.sleep(0.01)

    # IDLE
    register_12(cmd_interpret, 0x0070 if Triggerbit else 0x0030)
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0deb)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    if(BCR):
        # BCR
        register_12(cmd_interpret, 0x0072 if Triggerbit else 0x0032)
        cmd_interpret.write_config_reg(10, 0x0000)
        cmd_interpret.write_config_reg(9, 0x0000)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)

    # QInj FC
    if(QInj):
        register_12(cmd_interpret, 0x0075 if Triggerbit else 0x0035)
        cmd_interpret.write_config_reg(10, 0x0005)
        cmd_interpret.write_config_reg(9, 0x0005)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)
        if(repeatedQInj):
            register_12(cmd_interpret, 0x0075 if Triggerbit else 0x0035)
            cmd_interpret.write_config_reg(10, 0x0008)
            cmd_interpret.write_config_reg(9, 0x0008)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)
            register_12(cmd_interpret, 0x0075 if Triggerbit else 0x0035)
            cmd_interpret.write_config_reg(10, 0x000c)
            cmd_interpret.write_config_reg(9, 0x000c)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)
            register_12(cmd_interpret, 0x0075 if Triggerbit else 0x0035)
            cmd_interpret.write_config_reg(10, 0x0011)
            cmd_interpret.write_config_reg(9, 0x0011)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)
            register_12(cmd_interpret, 0x0075 if Triggerbit else 0x0035)
            cmd_interpret.write_config_reg(10, 0x0017)
            cmd_interpret.write_config_reg(9, 0x0017)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)

    ### Send L1A
    if(L1A):
        register_12(cmd_interpret, 0x0076 if Triggerbit else 0x0036)
        cmd_interpret.write_config_reg(10, 0x01fd)
        cmd_interpret.write_config_reg(9, 0x01fd)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)

        ### Send L1A Range
        if(L1ARange):
            register_12(cmd_interpret, 0x0076 if Triggerbit else 0x0036)
            cmd_interpret.write_config_reg(10, 0x01fc)
            cmd_interpret.write_config_reg(9, 0x01fc)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)

            register_12(cmd_interpret, 0x0076 if Triggerbit else 0x0036)
            cmd_interpret.write_config_reg(10, 0x01fe)
            cmd_interpret.write_config_reg(9, 0x01fe)
            fc_init_pulse(cmd_interpret)
            time.sleep(0.01)

    fc_signal_start(cmd_interpret)
    time.sleep(0.01)
    print("Done with memoFC configuration")

#--------------------------------------------------------------------------#
def link_reset(cmd_interpret):
    software_clear_fifo(cmd_interpret)
    time.sleep(2.01)

#--------------------------------------------------------------------------#
def get_fpga_data(cmd_interpret, time_limit, overwrite, output_directory, isQInj, DAC_Val):
    fpga_data = Save_FPGA_data('Save_FPGA_data', cmd_interpret, time_limit, overwrite, output_directory, isQInj, DAC_Val)
    try:
        fpga_data.start()
        while fpga_data.is_alive():
            fpga_data.join(0.8)
    except KeyboardInterrupt as e:
        fpga_data.alive = False
        fpga_data.join()

# define a threading class for saving data from FPGA Registers only
class Save_FPGA_data(threading.Thread):
    def __init__(self, name, cmd_interpret, time_limit, overwrite, output_directory, isQInj, DAC_Val):
        threading.Thread.__init__(self, name=name)
        self.cmd_interpret    = cmd_interpret
        self.time_limit       = time_limit
        self.overwrite        = overwrite
        self.output_directory = output_directory
        self.isQInj           = isQInj
        self.DAC_Val          = DAC_Val

    def run(self):
        if(self.isQInj):
            configure_memo_FC(self.cmd_interpret,Initialize=True,QInj=True,L1A=True)
        else:
            configure_memo_FC(self.cmd_interpret,Initialize=True,QInj=False,L1A=False)
        t = threading.current_thread()              # Local reference of THIS thread object
        t.alive = True                              # Thread is alive by default
        print("{} is saving FPGA data directly...".format(self.getName()))
        userdefinedir = self.output_directory
        today = datetime.date.today()
        todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results"
        try:
            os.mkdir(todaystr)
            print("Directory %s was created!"%todaystr)
        except FileExistsError:
            print("Directory %s already exists!"%todaystr)
        userdefine_dir = todaystr + "/%s"%userdefinedir
        outfile = None
        try:
            os.mkdir(userdefine_dir)
        except FileExistsError:
            print("User defined directory %s already created!"%(userdefine_dir))
            if(self.overwrite != True):
                outfile = open("./%s/FPGA_Data.dat"%(userdefine_dir), 'a')
            else:
                if os.path.exists("./%s/FPGA_Data.dat"%(userdefine_dir)):
                    os.system("rm ./%s/FPGA_Data.dat"%(userdefine_dir))
                outfile = open("./%s/FPGA_Data.dat"%(userdefine_dir), 'w')
        if outfile is None:
            print("Outfile not set!")
            sys.exit(1)
        sleep_time = self.time_limit
        if sleep_time < 3:
            sleep_time = 3
        if not t.alive:
            print("Check Link Thread detected alive=False")
        time.sleep(sleep_time)
        read_register   = self.cmd_interpret.read_config_reg(7)
        fpga_duration   = int(format(read_register, '016b')[-6:], base=2)
        read_register   = self.cmd_interpret.read_config_reg(8)
        en_L1A          = format(read_register, '016b')[-11]
        fpga_data       = int(format(self.cmd_interpret.read_status_reg(4), '016b')+format(self.cmd_interpret.read_status_reg(3), '016b'), base=2)
        fpga_header     = int(format(self.cmd_interpret.read_status_reg(6), '016b')+format(self.cmd_interpret.read_status_reg(5), '016b'), base=2)
        fpga_state      = int(format(self.cmd_interpret.read_status_reg(7), '016b'), base=2)
        fpga_triggerbit = int(format(self.cmd_interpret.read_status_reg(9), '016b')+format(self.cmd_interpret.read_status_reg(8), '016b'), base=2)
        while fpga_state < 1: # keep reading until fpga state is not zero to be sure counter started
            read_register   = self.cmd_interpret.read_config_reg(7)
            fpga_duration   = int(format(read_register, '016b')[-6:], base=2)
            read_register   = self.cmd_interpret.read_config_reg(8)
            en_L1A          = format(read_register, '016b')[-11]
            fpga_data       = int(format(self.cmd_interpret.read_status_reg(4), '016b')+format(self.cmd_interpret.read_status_reg(3), '016b'), base=2)
            fpga_header     = int(format(self.cmd_interpret.read_status_reg(6), '016b')+format(self.cmd_interpret.read_status_reg(5), '016b'), base=2)
            fpga_state      = int(format(self.cmd_interpret.read_status_reg(7), '016b'), base=2)
            fpga_triggerbit = int(format(self.cmd_interpret.read_status_reg(9), '016b')+format(self.cmd_interpret.read_status_reg(8), '016b'), base=2)
        outfile.write(f'{fpga_state},{en_L1A},{fpga_duration},{fpga_data},{fpga_header},{fpga_triggerbit},{self.DAC_Val}\n')
        outfile.close()
        configure_memo_FC(self.cmd_interpret,Initialize=False,QInj=False,L1A=False)
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
# Threading class to only READ off the ethernet buffer
class Receive_data(threading.Thread):
    def __init__(self, name, read_queue, cmd_interpret, num_fifo_read, read_thread_handle, write_thread_handle, time_limit, use_IPC = False, stop_DAQ_event = None, IPC_queue = None):
        threading.Thread.__init__(self, name=name)
        self.read_queue          = read_queue
        self.cmd_interpret       = cmd_interpret
        self.num_fifo_read       = num_fifo_read
        self.read_thread_handle  = read_thread_handle
        self.write_thread_handle = write_thread_handle
        self.time_limit          = time_limit
        self.use_IPC             = use_IPC
        self.stop_DAQ_event      = stop_DAQ_event
        self.IPC_queue           = IPC_queue
        if self.use_IPC and self.IPC_queue is None:
            self.use_IPC = False
        if not self.use_IPC:
            self.daq_on = True
            if self.stop_DAQ_event is not None:
                self.stop_DAQ_event.set()
        else:
            self.daq_on = True
            self.stop_DAQ_event.clear()

    def run(self):
        t = threading.current_thread()
        t.alive = True
        mem_data = []
        total_start_time = time.time()
        print("{} is reading data and pushing to the queue...".format(self.getName()))
        while ((time.time()-total_start_time<=self.time_limit)):
            # print("while looped...")
            if self.use_IPC:
                try:
                    message = self.IPC_queue.get(False)
                    print(f'Message: {message}')
                    if message == 'start DAQ':
                        self.daq_on = True
                    elif message == 'stop DAQ':
                        self.daq_on = False
                    elif message == 'start L1A':
                        configure_memo_FC(self.cmd_interpret,Initialize=True,QInj=True,L1A=True,BCR=True,Triggerbit=False)
                    elif message == 'start L1A trigger bit':
                        configure_memo_FC(self.cmd_interpret,Initialize=True,QInj=True,L1A=True)
                    elif message == 'start L1A trigger bit data':
                        configure_memo_FC(self.cmd_interpret,Initialize=True) #IDLE FC Only
                    elif message == 'stop L1A':
                        configure_memo_FC(self.cmd_interpret,Initialize=False,Triggerbit=False)
                    elif message == 'stop L1A trigger bit':
                        configure_memo_FC(self.cmd_interpret,Initialize=False)
                    elif message == 'allow threads to exit':
                        self.stop_DAQ_event.set()
                    elif message == 'link reset':
                        link_reset(self.cmd_interpret)
                    # elif message == 'reset till linked':
                    #     set_trigger_linked(self.cmd_interpret)
                    ## Special if condition for delay change during the DAQ
                    ## Example: change delay 0x0421
                    ##   becomes: change delay 1057
                    elif ' '.join(message.split(' ')[:2]) == 'change delay':
                        triggerBitDelay(self.cmd_interpret, int(message.split(' ')[2], base=16))
                    elif ' '.join(message.split(' ')[:1]) == 'memoFC':
                        words = message.split(' ')[1:]
                        QInj=False
                        L1A=False
                        L1ARange=False
                        BCR=False
                        Triggerbit=False
                        Initialize = False
                        if("QInj" in words): QInj=True
                        if("L1A" in words): L1A=True
                        if("L1ARange" in words):
                            L1A=True
                            L1ARange=True
                        if("BCR" in words): BCR=True
                        if("Triggerbit" in words): Triggerbit=True
                        if("Start" in words): Initialize=True
                        configure_memo_FC(self.cmd_interpret,Initialize=Initialize,QInj=QInj,L1A=L1A,BCR=BCR,Triggerbit=Triggerbit,L1ARange=L1ARange)
                    else:
                        print(f'Unknown message: {message}')
                except queue.Empty:
                    pass
            if self.daq_on:
                # print("In loop and daq_on, attempting to access read_data_fifo")
                mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)
                if mem_data == []:
                    print("No data in buffer! Will try to read again")
                    time.sleep(1.01)
                    mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)

                for mem_line in mem_data:
                    self.read_queue.put(mem_line)
                # print("memdata added to queue:", mem_data)
            # print("In loop, attempting to test alive condition")
            if not t.alive:
                print("Read Thread detected alive=False")
                break
            # print("In loop, attempting to test read_handle condition")
            if self.read_thread_handle.is_set():
                print("Read Thread received STOP signal")
                if not self.write_thread_handle.is_set():
                    print("Sending stop signal to Write Thread")
                    self.write_thread_handle.set()
                print("Stopping Read Thread")
                break
        print("Read Thread gracefully sending STOP signal to other threads")
        self.read_thread_handle.set()
        print("Sending stop signal to Write Thread")
        self.write_thread_handle.set()
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
# Threading class to only WRITE the raw binary data to disk
class Write_data(threading.Thread):
    def __init__(self, name, read_queue, translate_queue, num_line, store_dict, skip_translation, compressed_binary, skip_binary, read_thread_handle, write_thread_handle, translate_thread_handle, stop_DAQ_event = None):
        threading.Thread.__init__(self, name=name)
        self.read_queue              = read_queue
        self.translate_queue         = translate_queue
        self.num_line                = num_line
        self.store_dict              = store_dict
        self.skip_translation        = skip_translation
        self.compressed_binary       = compressed_binary
        self.skip_binary             = skip_binary
        self.read_thread_handle      = read_thread_handle
        self.write_thread_handle     = write_thread_handle
        self.translate_thread_handle = translate_thread_handle
        self.stop_DAQ_event          = stop_DAQ_event
        self.file_lines              = 0
        self.file_counter            = 0
        self.retry_count             = 0

    def run(self):
        t = threading.current_thread()
        t.alive      = True
        prev_status_on_data_stream = ""
        if(not self.skip_binary):
            outfile = open("%s/TDC_Data_%d.dat"%(self.store_dict, self.file_counter), 'w')
            print("{} is reading queue and writing file {}...".format(self.getName(), self.file_counter))
        else:
            print("{} is reading queue and pushing binary onwards...".format(self.getName()))
        while (True):
            if not t.alive:
                print("Write Thread detected alive=False")
                outfile.close()
                break
            if(self.file_lines>self.num_line and (not self.skip_binary)):
                outfile.close()
                self.file_lines   = 0
                self.file_counter = self.file_counter + 1
                outfile = open("%s/TDC_Data_%d.dat"%(self.store_dict, self.file_counter), 'w')
                print("{} is reading queue and writing file {}...".format(self.getName(), self.file_counter))
            mem_data = ""
            # Attempt to pop off the read_queue for 30 secs, fail if nothing found
            try:
                mem_data = self.read_queue.get(True, 1)
                self.retry_count = 0
            except queue.Empty:
                if not self.stop_DAQ_event.is_set():
                    self.retry_count = 0
                    continue
                if self.write_thread_handle.is_set():
                    print("Write Thread received STOP signal AND ran out of data to write")
                    break
                self.retry_count += 1
                if self.retry_count < 30:
                    continue
                print("BREAKING OUT OF WRITE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST FETCH FROM READ_QUEUE!!!")
                break
            binary = format(int(mem_data), '032b')
            # Handle the raw (binary) line
            # if int(mem_data) == 1431655765: continue # Ethernet Filler Line
            if binary[0:16] == '0101010101010101':
                if(prev_status_on_data_stream!=binary[16:]):
                    print(f"(Unique) Status on Data Stream: {binary[16:]}")
                    prev_status_on_data_stream = binary[16:]
                if(not self.skip_translation):
                    self.translate_queue.put("0")
                continue # Ethernet Filler Line
            # if int(mem_data) == 0: continue # Waiting for IPC
            # if int(mem_data) == 38912: continue # got a Filler
            # if int(mem_data) == 9961472: continue # got a Filler
            # if int(mem_data) == 2550136832: continue # got a Filler
            if(not self.skip_binary):
                if(self.compressed_binary): outfile.write('%d\n'%int(mem_data))
                else: outfile.write('%s\n'%binary)
            # Increment line counters
            self.file_lines = self.file_lines + 1
            # Perform translation related activities if requested
            if(not self.skip_translation):
                self.translate_queue.put(binary)
            if self.write_thread_handle.is_set():
                if not self.translate_thread_handle.is_set():
                    print("Sending stop signal to Translate Thread")
                    self.translate_thread_handle.set()
            del binary, mem_data
        print("Write Thread gracefully sending STOP signal to translate thread")
        self.translate_thread_handle.set()
        self.write_thread_handle.set()
        del t
        if(not self.skip_binary): outfile.close()
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
## software clear fifo
## MSB..10, i.e., trigger pulser_reg[1]
def software_clear_fifo(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0002)

#--------------------------------------------------------------------------#
## Reset and Resume state machine after exception in Debug Mode
## MSB..10, i.e., trigger pulser_reg[7]
def resume_in_debug_mode(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0080)

#--------------------------------------------------------------------------#
## software clear error. This should now clear the event counter
## MSB..100000, i.e., trigger pulser_reg[5]
def software_clear_error(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0020)

#--------------------------------------------------------------------------#
## ws clear trigger block.
## i.e., trigger pulser_reg[6]
def software_clear_ws_trig_block(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0040)

#--------------------------------------------------------------------------#
## Fast Command Signal Start
## MSB..100, i.e., trigger pulser_reg[2]
def fc_signal_start(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0004)

#--------------------------------------------------------------------------#
## Fast Command Initialize pulse
## MSB..10000, i.e., trigger pulser_reg[4]
def fc_init_pulse(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0010)

#--------------------------------------------------------------------------#
## Enable FPGA Descrambler
## 0xWXYZ
## Z is a bit 4 bit binary wxyz
## z is the enable descrambler
## y is disable GTX
## x is polarity
## w is the Enable debug mode flag
## {12'bxxxxxxxxx,add_ethernet_filler,debug_mode,dumping_mode,notGTXPolarity,notGTX,enableAutoSync}
def Enable_FPGA_Descramblber(cmd_interpret, val=0x000b):
    cmd_interpret.write_config_reg(14, val)

#--------------------------------------------------------------------------#
## Register 15
## Enable channel
## 4 bit binary, WXYZ
## W - ch3
## X - ch2
## Y - ch1
## Z - ch0
## Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
## Register 15, needs firmware option
# 0xWXYZ
# Z is a bit 4 bit binary wxyz Channel Enable (1=Enable)
# Y is a bit 4 bit binary wxyz Board Type (1=Etroc2)
def active_channels(cmd_interpret, key = 0x0003):
    print(f"writing: {bin(key)} into register 15")
    cmd_interpret.write_config_reg(15, key)

#--------------------------------------------------------------------------#
## Register 13
## TimeStamp and Testmode
## Following is binary key, 4 bit binary WXYZ
## 0000: Enable  Testmode & Enable TimeStamp
## 0001: Enable  Testmode & Disable TimeStamp
## 0010: Disable Testmode & Enable TimeStamp
## 0011: Disable Testmode & Disable TimeStamp  ##BUGGED as of 03-04-2023
## Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
def timestamp(cmd_interpret, key=0x0000):
    cmd_interpret.write_config_reg(13, key)

#--------------------------------------------------------------------------#
## Register 12
## 4-digit 16 bit hex, 0xWXYZ
## WX (8 bit) - Duration
## Y - N/A,N/A,Period,Hold
## Z - Input command
def register_12(cmd_interpret, key = 0x0000):
    cmd_interpret.write_config_reg(12, key)

#--------------------------------------------------------------------------#
## Register 11
## 4-digit 16 bit hex, 0xWXYZ
## WX (8 bit) - N/A
## YZ (8 bit) - Error Mask
def register_11(cmd_interpret, key = 0x0000):
    cmd_interpret.write_config_reg(11, key)

#--------------------------------------------------------------------------#
## Register 8
## 4-digit 16 bit hex
## LSB 10 bits are delay, LSB 11th bit is delay enabled
## 0000||0100||0000||0000 = 0x0400: shift of one clock cycle
def triggerBitDelay(cmd_interpret, key = 0x0400):
    cmd_interpret.write_config_reg(8, key)

#--------------------------------------------------------------------------#
## Register 7
## 4-digit 16 bit hex
## LSB 6 bits  - time (s) for FPGA counters
## Next 4 bits are the channel delay abcd = board: 3,2,1,0.
## This delays the trigger bit of set channels by 1 clock cycle
def counterDuration(cmd_interpret, key = 0x0001):
    cmd_interpret.write_config_reg(7, key)
