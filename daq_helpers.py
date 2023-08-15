#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
#import visa
import threading
import numpy as np
import os
from mpl_toolkits.axes_grid1 import make_axes_locatable
from queue import Queue
from collections import deque
import queue
from command_interpret import *
from ETROC1_ArrayReg import *
from translate_data import *
import datetime
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari
@date: 2023-03-24
This script is composed of all the helper functions needed for I2C comms, FPGA, etc
'''
#--------------------------------------------------------------------------#
def start_periodic_L1A_WS(cmd_interpret):
    ## 4-digit 16 bit hex, Duration is LSB 12 bits
    ## This tells us how many memory slots to use
    register_11(cmd_interpret, 0x0deb)
    time.sleep(0.01)

    ## 4-digit 16 bit hex, 0xWXYZ
    ## WX (8 bit) -  Error Mask
    ## Y - trigSize[1:0],Period,testTrig
    ## Z - Input command
    register_12(cmd_interpret, 0x0030)          # This is periodic Idle FC
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0deb)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0032)          # This is periodic BC Reset FC
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0000)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0035)          # This is periodic Qinj FC
    cmd_interpret.write_config_reg(10, 0x0001)
    cmd_interpret.write_config_reg(9, 0x0001)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0036)          # This is periodic L1A FC
    cmd_interpret.write_config_reg(10, 0x01f0)
    cmd_interpret.write_config_reg(9, 0x01ff)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    fc_signal_start(cmd_interpret)              # This initializes the memory and starts the FC cycles
    time.sleep(0.01)
    
def start_onetime_L1A_WS(cmd_interpret):
    ## 4-digit 16 bit hex, Duration is LSB 12 bits
    ## This tells us how many memory slots to use
    register_11(cmd_interpret, 0x0deb)
    time.sleep(0.01)

    ## 4-digit 16 bit hex, 0xWXYZ
    ## WX (8 bit) -  Error Mask
    ## Y - trigSize[1:0],Period,testTrig
    ## Z - Input command
    register_12(cmd_interpret, 0x0000)          # This is onetime Idle FC
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0deb)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0002)          # This is onetime BC Reset FC
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0000)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0005)          # This is onetime Qinj FC
    cmd_interpret.write_config_reg(10, 0x0001)
    cmd_interpret.write_config_reg(9, 0x0001)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0006)          # This is onetime L1A FC
    cmd_interpret.write_config_reg(10, 0x01f0)
    cmd_interpret.write_config_reg(9, 0x01ff)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    fc_signal_start(cmd_interpret)              # This initializes the memory and starts the FC cycles
    time.sleep(0.01)

def start_L1A_1MHz(cmd_interpret):
    register_11(cmd_interpret, 0x0de7)
    time.sleep(0.01)

    register_12(cmd_interpret, 0x0030)
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0de7)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)
    
    register_12(cmd_interpret, 0x0032)
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0000)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    for index in range(89):
        register_12(cmd_interpret, 0x0035)
        cmd_interpret.write_config_reg(10, 0x0001 + index*40)
        cmd_interpret.write_config_reg(9, 0x0001 + index*40)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)

        register_12(cmd_interpret, 0x0036)
        cmd_interpret.write_config_reg(10, 0x019 + index*40)
        cmd_interpret.write_config_reg(9, 0x019 + index*40)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)

    fc_signal_start(cmd_interpret)
    time.sleep(0.01)

def configure_memo_FC(cmd_interpret, BCR = False, QInj = False, L1A = False, Initialize = True, Triggerbit=True):
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

    ### Send L1A
    if(L1A):
        register_12(cmd_interpret, 0x0076 if Triggerbit else 0x0036)
        cmd_interpret.write_config_reg(10, 0x01fd)
        cmd_interpret.write_config_reg(9, 0x01fd)
        fc_init_pulse(cmd_interpret)
        time.sleep(0.01)

    fc_signal_start(cmd_interpret)

    time.sleep(0.01)

def stop_L1A_1MHz(cmd_interpret):
    register_12(cmd_interpret, 0x0030)
    cmd_interpret.write_config_reg(10, 0x0000)
    cmd_interpret.write_config_reg(9, 0x0de7)
    fc_init_pulse(cmd_interpret)
    time.sleep(0.01)

    fc_signal_start(cmd_interpret)
    time.sleep(0.01)

    software_clear_fifo(cmd_interpret)
    time.sleep(0.01)

def link_reset(cmd_interpret):
    software_clear_fifo(cmd_interpret) 

def set_trigger_linked(cmd_interpret):
    reads = 0
    clears_error = 0
    clears_fifo = 0
    testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
    print("Register 2 upon checking:", testregister_2)
    data_error = testregister_2[-1]
    df_synced = testregister_2[-2]
    trigger_error = testregister_2[-3]
    trigger_synced = testregister_2[-4]
    linked_flag = (data_error=="0" and df_synced=="1" and trigger_error=="0" and trigger_synced=="1")
    if linked_flag:
        print("Already Linked:",testregister_2)
        return True
    else:
        while linked_flag is False:
            time.sleep(1.01)
            testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
            reads += 1
            print("Read register:",reads)
            print("Register after waiting to link",testregister_2)
            df_synced = testregister_2[-2]
            data_error = testregister_2[-1]
            trigger_synced = testregister_2[-4]
            trigger_error = testregister_2[-3]
            linked_flag = (data_error=="0" and df_synced=="1" and trigger_error=="0" and trigger_synced=="1")
            error_flag = (data_error=="0" and trigger_error=="0")
            print("Linked flag is",linked_flag)
            print("Error flag is",error_flag)
            if linked_flag is False:
                if error_flag is False:
                    software_clear_error(cmd_interpret)
                    clears_error += 1
                    print("Cleared Error:",clears_error)
                    if clears_error == 4:
                        software_clear_fifo(cmd_interpret)
                        clears_fifo += 1
                        print("Cleared FIFO:",clears_fifo)
                else:
                    software_clear_fifo(cmd_interpret)
                    clears_fifo += 1
                    print("Cleared FIFO:",clears_fifo)
    print("Register 2 after trying to link:", testregister_2)
    return True

def set_linked(cmd_interpret):
    reads = 0
    clears = 0
    testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
    print("Register 2 upon checking:", testregister_2)
    data_error = testregister_2[-1]
    df_synced = testregister_2[-2]
    linked_flag = (data_error=="0" and df_synced=="1")
    if linked_flag:
        print("Already Linked:",testregister_2)
        return True
    else:
        while linked_flag is False:
            time.sleep(1.01)
            testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
            reads += 1
            print("Read register:",reads)
            print("Register after waiting to link",testregister_2)
            df_synced = testregister_2[-2]
            data_error = testregister_2[-1]
            linked_flag = (data_error=="0" and df_synced=="1")
            print("Linked flag is",linked_flag)
            if linked_flag is False:
                software_clear_fifo(cmd_interpret)
                clears += 1
                print("Cleared FIFO:",clears)
    print("Register 2 after trying to link:", testregister_2)
    return True

def check_trigger_linked(cmd_interpret):
    testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
    print("Register 2 upon checking:", testregister_2)
    data_error = testregister_2[-1]
    df_synced = testregister_2[-2]
    trigger_error = testregister_2[-3]
    trigger_synced = testregister_2[-4]
    if (data_error=="0" and df_synced=="1" and trigger_error=="0" and trigger_synced=="1"):
        print("All is linked with no errors")
        return True
    return False

def check_linked(cmd_interpret):
    testregister_2 = format(cmd_interpret.read_status_reg(2), '016b')
    print("Register 2 upon checking:", testregister_2)
    data_error = testregister_2[-1]
    df_synced = testregister_2[-2]
    if (data_error=="0" and df_synced=="1"):
        print("All is linked with no errors")
        return True
    return False
    
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
        self.cmd_interpret = cmd_interpret
        self.time_limit = time_limit
        self.overwrite = overwrite
        self.output_directory = output_directory
        self.isQInj = isQInj
        self.DAC_Val = DAC_Val

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
        outfile.write(f'{fpga_state},{en_L1A},{fpga_duration},{fpga_data},{fpga_header},{fpga_triggerbit},{self.DAC_Val}\n')
        outfile.close()
        configure_memo_FC(self.cmd_interpret,Initialize=False,QInj=False,L1A=False)
        print("%s finished!"%self.getName())
#--------------------------------------------------------------------------#

# define a receive data threading class
class Receive_data(threading.Thread):
    def __init__(self, name, queue, cmd_interpret, num_fifo_read, read_thread_handle, write_thread_handle, time_limit, use_IPC = False, stop_DAQ_event = None, IPC_queue = None):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.cmd_interpret = cmd_interpret
        self.num_fifo_read = num_fifo_read
        self.read_thread_handle = read_thread_handle
        self.write_thread_handle = write_thread_handle
        self.time_limit = time_limit
        self.use_IPC = use_IPC
        self.stop_DAQ_event = stop_DAQ_event
        self.IPC_queue = IPC_queue
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
        t = threading.current_thread()              # Local reference of THIS thread object
        t.alive = True                              # Thread is alive by default
        mem_data = []
        total_start_time = time.time()
        print("{} is reading data and pushing to the queue...".format(self.getName()))
        while ((time.time()-total_start_time<=self.time_limit)):
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
                    elif message == 'start L1A 1MHz':
                        start_L1A_1MHz(self.cmd_interpret)
                    elif message == 'start L1A trigger bit':
                        configure_memo_FC(self.cmd_interpret,Initialize=True,QInj=True,L1A=True)
                    elif message == 'start L1A trigger bit data':
                        configure_memo_FC(self.cmd_interpret,Initialize=True) #IDLE FC Only
                    elif message == 'stop L1A':
                        configure_memo_FC(self.cmd_interpret,Initialize=False,Triggerbit=False)
                    elif message == 'stop L1A 1MHz':
                        stop_L1A_1MHz(self.cmd_interpret)
                    elif message == 'stop L1A trigger bit':
                        configure_memo_FC(self.cmd_interpret,Initialize=False)
                    elif message == 'allow threads to exit':
                        self.stop_DAQ_event.set()
                    elif message == 'link reset':
                        link_reset(self.cmd_interpret)
                    ## Special if condition for delay change during the DAQ
                    ## Example: change delay 0x0421
                    ##   becomes: change delay 1057
                    elif ' '.join(message.split(' ')[:2]) == 'change delay':
                        triggerBitDelay(self.cmd_interpret, int(message.split(' ')[2], base=16))
                    else:
                        print(f'Unknown message: {message}')
                except queue.Empty:
                    pass

            if self.daq_on:
                # max allowed by read_memory is 65535
                mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)
                for mem_line in mem_data:
                    self.queue.put(mem_line) 
            if not t.alive:
                print("Read Thread detected alive=False")
                # self.is_alive = False
                break  
            if self.read_thread_handle.is_set():
                print("Read Thread received STOP signal")
                if not self.write_thread_handle.is_set():
                    print("Sending stop signal to Write Thread")
                    self.write_thread_handle.set()
                print("Stopping Read Thread")
                # self.is_alive = False
                break
        print("Read Thread gracefully sending STOP signal to other threads") 
        self.read_thread_handle.set()
        # self.is_alive = False
        print("Sending stop signal to Write Thread")
        self.write_thread_handle.set()
        print("%s finished!"%self.getName())
#--------------------------------------------------------------------------#

# define a write data class
class Write_data(threading.Thread):
    def __init__(self, name, read_queue, translate_queue, num_line, store_dict, binary_only, compressed_binary, skip_binary, read_thread_handle, write_thread_handle, translate_thread_handle, stop_DAQ_event = None):
        threading.Thread.__init__(self, name=name)
        self.read_queue = read_queue
        self.translate_queue = translate_queue
        self.num_line = num_line
        self.store_dict = store_dict
        self.binary_only = binary_only
        self.compressed_binary = compressed_binary
        self.skip_binary = skip_binary
        self.read_thread_handle = read_thread_handle
        self.write_thread_handle = write_thread_handle
        self.translate_thread_handle = translate_thread_handle
        self.stop_DAQ_event = stop_DAQ_event
        # self.is_alive = False

    # def check_alive(self):
    #     return self.is_alive

    def run(self):
        t = threading.current_thread()              # Local reference of THIS thread object
        t.alive = True                              # Thread is alive by default
        # self.is_alive = True
        file_lines = 0
        file_counter = 0
        if (not self.skip_binary):
            outfile = open("./%s/TDC_Data_%d.dat"%(self.store_dict, file_counter), 'w')
            print("{} is reading queue and writing file {}...".format(self.getName(), file_counter))
        else:
            print("{} is reading queue and pushing binary onwards...".format(self.getName()))
        retry_count = 0
        while (True):
            if not t.alive:
                print("Write Thread detected alive=False")
                outfile.close()
                # self.is_alive = False
                break 
            if(file_lines>self.num_line and (not self.skip_binary)):
                outfile.close()
                file_lines=0
                file_counter = file_counter + 1
                outfile = open("./%s/TDC_Data_%d.dat"%(self.store_dict, file_counter), 'w')
                print("{} is reading queue and writing file {}...".format(self.getName(), file_counter))
            elif(file_lines>self.num_line):
                file_lines=0
                file_counter = file_counter + 1
            mem_data = ""
            # Attempt to pop off the read_queue for 30 secs, fail if nothing found
            try:
                mem_data = self.read_queue.get(True, 1)
                retry_count = 0
            except queue.Empty:
                if not self.stop_DAQ_event.is_set():
                    retry_count = 0
                    continue
                if self.write_thread_handle.is_set():
                    print("Write Thread received STOP signal AND ran out of data to write")
                    break
                retry_count += 1
                if retry_count < 30:
                    continue
                print("BREAKING OUT OF WRITE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST FETCH FROM READ_QUEUE!!!")
                # self.read_thread_handle.set()
                # self.is_alive = False
                break
            # Handle the raw (binary) line
            # if int(mem_data) == 0: continue # Waiting for IPC
            # if int(mem_data) == 38912: continue # got a Filler
            # if int(mem_data) == 9961472: continue # got a Filler
            # if int(mem_data) == 2550136832: continue # got a Filler
            binary = format(int(mem_data), '032b')
            if(not self.skip_binary):
                if(self.compressed_binary): outfile.write('%d\n'%int(mem_data))
                else: outfile.write('%s\n'%binary)
            # Increment line counters
            file_lines = file_lines + 1
            # Perform translation related activities if requested
            if(not self.binary_only):
                self.translate_queue.put(binary)
            if self.write_thread_handle.is_set():
                # print("Write Thread received STOP signal")
                if not self.translate_thread_handle.is_set():
                    print("Sending stop signal to Translate Thread")
                    self.translate_thread_handle.set()
                # print("Checking Read Thread from Write Thread")
                # wait for read thread to die...
                # while(self.read_thread_handle.is_set() == False):
                    # time.sleep(1)
                # self.is_alive = False
        print("Write Thread gracefully sending STOP signal to translate thread") 
        self.translate_thread_handle.set()
        self.write_thread_handle.set()
        # self.is_alive = False
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
class Translate_data(threading.Thread):
    def __init__(self, name, translate_queue, cmd_interpret, num_line, timestamp, store_dict, binary_only, board_ID, write_thread_handle, translate_thread_handle, compressed_translation, stop_DAQ_event = None):
        threading.Thread.__init__(self, name=name)
        self.translate_queue = translate_queue
        self.cmd_interpret = cmd_interpret
        self.num_line = num_line
        self.timestamp = timestamp
        self.store_dict = store_dict
        self.binary_only = binary_only
        self.board_ID = board_ID
        self.queue_ch = [deque() for i in range(4)]
        self.link_ch  = ["" for i in range(4)]
        self.write_thread_handle = write_thread_handle
        self.translate_thread_handle = translate_thread_handle
        self.stop_DAQ_event = stop_DAQ_event
        self.hitmap = {i:np.zeros((16,16)) for i in range(4)}
        self.compressed_translation = compressed_translation
        # self.is_alive = False

    # def check_alive(self):
    #     return self.is_alive

    def run(self):
        t = threading.current_thread()
        t.alive = True
        # self.is_alive = True
        total_lines = 0
        file_lines = 0
        file_counter = 0
        if(not self.binary_only): 
            outfile = open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, file_counter), 'w')
            print("{} is reading queue and translating file {}...".format(self.getName(), file_counter))
        else:
            print("{} is reading queue and translating...".format(self.getName()))
        retry_count = 0
        while True:
            if not t.alive:
                print("Translate Thread detected alive=False")
                if(not self.binary_only): outfile.close()
                # self.is_alive = False
                break 
            # if self.translate_thread_handle.is_set():
            #     print("Translate Thread received STOP signal from Write Thread")
            #     if(not self.binary_only): outfile.close()
            #     break
            if((not self.binary_only) and file_lines>self.num_line):
                outfile.close()
                file_lines=0
                file_counter = file_counter + 1
                outfile = open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, file_counter), 'w')
                print("{} is reading queue and translating file {}...".format(self.getName(), file_counter))
            binary = ""
            # Attempt to pop off the translate_queue for 30 secs, fail if nothing found
            try:
                binary = self.translate_queue.get(True, 1)
                retry_count = 0
            except queue.Empty:
                if not self.stop_DAQ_event.is_set:
                    retry_count = 0
                    continue
                if self.translate_thread_handle.is_set():
                    print("Translate Thread received STOP signal AND ran out of data to translate")
                    break
                retry_count += 1
                if retry_count < 30:
                    continue
                print("BREAKING OUT OF TRANSLATE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST FETCH FROM TRANSLATE_QUEUE!!! THIS SENDS STOP SIGNAL TO ALL THREADS!!!")
                # self.read_write_handle.set()
                # self.is_alive = False
                break
            TDC_data, write_flag = etroc_translate_binary(binary, self.timestamp, self.queue_ch, self.link_ch, self.board_ID, self.hitmap, self.compressed_translation)
            if(write_flag==1):
                pass
            elif(write_flag==2):
                TDC_len = len(TDC_data)
                TDC_header_index = -1
                for j,TDC_line in enumerate(TDC_data):
                    if(TDC_line=="HEADER_KEY"):
                        if(TDC_header_index<0):
                            TDC_header_index = j
                        else:
                            print("ERROR! Found more than two headers in data block!!")
                            sys.exit(1)
                        continue
                    if(not self.binary_only): 
                        if(self.compressed_translation):
                            if(TDC_header_index<0):
                                pass
                            else:
                                outfile.write("%s\n"%TDC_line)
                        else:
                            outfile.write("%s\n"%TDC_line)
                    if(TDC_line[9:13]!='DATA'): continue
                if(TDC_len>0):
                    if(not self.binary_only): file_lines  = file_lines  + TDC_len - 1
                    total_lines = total_lines + (TDC_len-1)
        
        print("Translate Thread gracefully ending") 
        self.translate_thread_handle.set()
        # self.is_alive = False
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#

## IIC write slave device
# @param mode[1:0] : '0'is 1 bytes read or wirte, '1' is 2 bytes read or write, '2' is 3 bytes read or write
# @param slave[7:0] : slave device address
# @param wr: 1-bit '0' is write, '1' is read
# @param reg_addr[7:0] : register address
# @param data[7:0] : 8-bit write data
def iic_write(mode, slave_addr, wr, reg_addr, data, cmd_interpret):
    val = mode << 24 | slave_addr << 17 | wr << 16 | reg_addr << 8 | data
    cmd_interpret.write_config_reg(4, 0xffff & val)
    cmd_interpret.write_config_reg(5, 0xffff & (val>>16))
    time.sleep(0.01)
    cmd_interpret.write_pulse_reg(0x0001)                                     # reset ddr3 data fifo
    time.sleep(0.01)

#--------------------------------------------------------------------------#
## IIC read slave device
# @param mode[1:0] : '0'is 1 bytes read or wirte, '1' is 2 bytes read or write, '2' is 3 bytes read or write
# @param slave[6:0]: slave device address
# @param wr: 1-bit '0' is write, '1' is read
# @param reg_addr[7:0] : register address
def iic_read(mode, slave_addr, wr, reg_addr, cmd_interpret):
    val = mode << 24 | slave_addr << 17 |  0 << 16 | reg_addr << 8 | 0x00	  # write device addr and reg addr
    cmd_interpret.write_config_reg(4, 0xffff & val)
    cmd_interpret.write_config_reg(5, 0xffff & (val>>16))
    time.sleep(0.01)
    cmd_interpret.write_pulse_reg(0x0001)				                      # Sent a pulse to IIC module

    val = mode << 24 | slave_addr << 17 | wr << 16 | reg_addr << 8 | 0x00	  # write device addr and read one byte
    cmd_interpret.write_config_reg(4, 0xffff & val)
    cmd_interpret.write_config_reg(5, 0xffff & (val>>16))
    time.sleep(0.01)
    cmd_interpret.write_pulse_reg(0x0001)				                      # Sent a pulse to IIC module
    time.sleep(0.01)									                      # delay 10ns then to read data
    return cmd_interpret.read_status_reg(0) & 0xff
#--------------------------------------------------------------------------#
## Enable FPGA Descrambler
def Enable_FPGA_Descramblber(cmd_interpret, val=0x000b):
    # 0xWXYZ
    # Z is a bit 4 bit binary wxyz
    # z is the enable descrambler
    # y is disable GTX
    # x is polarity
#    w is the memo FC (active high)
    cmd_interpret.write_config_reg(14, val)

#--------------------------------------------------------------------------#
## simple readout fucntion
#@param[in]: write_num: BC0 and L1ACC loop number, 0-65535
def simple_readout(write_num, cmd_interpret):
    cmd_interpret.write_config_reg(15, 0xffff & write_num)                    # write enable
    cmd_interpret.write_pulse_reg(0x0080)                                     # trigger pulser_reg[7]

#--------------------------------------------------------------------------#
## software clear fifo
def software_clear_fifo(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0002)                                     # trigger pulser_reg[1]

#--------------------------------------------------------------------------#
## software clear error
def software_clear_error(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0006)                                     # trigger pulser_reg[5]

#--------------------------------------------------------------------------#
## Register 15
## Enable channel
## 4 bit binary, WXYZ
## W - ch3
## X - ch2
## Y - ch1
## Z - ch0
## Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
def active_channels(cmd_interpret, key = 0x0003): 
    cmd_interpret.write_config_reg(15, key)

#--------------------------------------------------------------------------#
## Register 13
## TimeStamp and Testmode
## Following is binary key, 4 bit binary WXYZ
## 0000: Enable  Testmode & Enable TimeStamp
## 0001: Enable  Testmode & Disable TimeStamp
## 0010: Disable Testmode & Enable TimeStamp
## 0011: Disable Testmode & Disable TimeStamp                  ##BUGGED as of 03-04-2023
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
def counterDuration(cmd_interpret, key = 0x0001): 
    cmd_interpret.write_config_reg(7, key)

#--------------------------------------------------------------------------#
## Fast Command Signal Start
def fc_signal_start(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0004)

#--------------------------------------------------------------------------#
## Fast Command Initialize pulse
## MSB..10000
def fc_init_pulse(cmd_interpret):
    cmd_interpret.write_pulse_reg(0x0010)
