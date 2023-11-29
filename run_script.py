#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import copy
import time
#import visa
import struct
import socket
import threading
import datetime
#import heartrate
from queue import Queue
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
import parser_arguments
from command_interpret import *
from ETROC1_ArrayReg import *
from daq_helpers import *
from board_details import *
from config_etroc1 import *
#========================================================================================#
freqency = 1000
duration = 1000
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is used for testing ETROC1/2 Array chips. 
The main function of this script is I2C write and read, Ethernet communication, 
instrument control and so on.
'''
# hostname = '192.168.2.7'					# FPGA IP address
port = 1024									# port number
#--------------------------------------------------------------------------#

def main_process(IPC_queue, options, log_file = None):
    if log_file is not None:
        sys.stdout = open(log_file + ".out", "w")
    print('start main process')
    try:
        # initial socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print("Failed to create socket!")
        sys.exit()
    try:
        # connect socket
        s.connect((options.hostname, port))
    except socket.error:
        print("failed to connect to ip " + options.hostname)
        sys.exit()
    cmd_interpret = command_interpret(s)
    main(options, cmd_interpret, IPC_queue)
    s.close()

## main function
def main(options, cmd_interpret, IPC_queue = None):

    if(options.verbose):
        print("Verbose Output: ", options.verbose)
        print("\n")
        print("-------------------------------------------")
        print("--------Set of inputs from the USER--------")
        print("Overwrite previously saved files: ", options.overwrite)
        print("FPGA IP Address: ", options.hostname)
        print("Number of lines per file created by DAQ script: ", options.num_line)
        print("Number of lines read per call of fifo readout: ", options.num_fifo_read)
        print("Number of seconds to run this code (>0 means effective): ", options.time_limit)
        print("User defined Output Directory: ", options.output_directory)
        print("Save only the untranslated FPGA binary data (raw output): ", options.binary_only)
        print("Save FPGA binary data (raw output) in int format: ", options.compressed_binary)
        print("Save only FPGA translated data frames with DATA: ", options.compressed_translation)
        print("DO NOT save binary data (raw output): ", options.skip_binary)
        print("--------End of inputs from the USER--------")
        print("-------------------------------------------")
        print("\n")
        print("-------------------------------------------")
        print("-------Inputs that have been pre-set-------")
        print("ETROC Board Type: ",   board_type)
        print("ETROC Board Size: ",   board_size)
        print("ETROC Board Name: ",   board_name)
        print("ETROC Chip ID: ",      board_ID) 
        print("-------------------------------------------")
        print("-------------------------------------------")
        print("\n")
    
    if(options.firmware):
        print("Setting firmware...")
        active_channels(cmd_interpret, key = options.active_channel)
        timestamp(cmd_interpret, key = options.timestamp)
        triggerBitDelay(cmd_interpret, options.trigger_bit_delay)
        Enable_FPGA_Descramblber(cmd_interpret, options.polarity)
    
    if(options.clear_fifo):
        # time.sleep(0.1)                                 # delay 1000 milliseconds
        # software_clear_fifo(cmd_interpret)              # clear fifo content
        # time.sleep(0.1)                                 # delay 1000 milliseconds
        # software_clear_fifo(cmd_interpret)              # clear fifo content  
        # print("Cleared FIFO") 
        print("Clearing FIFO for ALL boards...")
        register_15 = cmd_interpret.read_config_reg(15)
        string_15   = format(register_15, '016b')
        channel_enable = string_15[-4:]
        for i in range(4):
            if(channel_enable[3-i]=="0"): continue
            print("Acting upon channel", i, "...")
            timestamp(cmd_interpret, key = int('000000000000'+format(i, '02b')+'00', base=2))
            # time.sleep(2.01)
            software_clear_fifo(cmd_interpret)              # clear fifo content
            time.sleep(0.1)                                 # delay 1000 milliseconds
            software_clear_fifo(cmd_interpret)
            time.sleep(2.01)  

    if(options.clear_error):
        time.sleep(0.1)                                 # delay 1000 milliseconds
        software_clear_error(cmd_interpret)             # clear error content
        time.sleep(0.1)                                 # delay 1000 milliseconds
        software_clear_error(cmd_interpret)             # clear error content  
        print("Cleared Error")  

    if(options.counter_duration):
        print("Setting Counter Duration and Channel Delays...")
        counterDuration(cmd_interpret, options.counter_duration)

    # Loop till we create the LED Errors
    # Please ensure LED Pages is set to 011
    if(options.reset_till_linked):
        time.sleep(0.1)
        set_linked(cmd_interpret)

    if(options.reset_till_trigger_linked):
        print("Resetting trigger link at beginning")
        set_trigger_linked(cmd_interpret)
    
    if(options.reset_all_till_trigger_linked):
        print("Resetting trigger link of all boards at beginning")
        set_all_trigger_linked(cmd_interpret)

    if(options.memo_fc_start_onetime_ws):
        start_onetime_L1A_WS(cmd_interpret)
    if(options.memo_fc_start_periodic_ws):
        start_periodic_L1A_WS(cmd_interpret)

    if(options.verbose):
        read_register_7 = cmd_interpret.read_config_reg(7)
        string_7   = format(read_register_7, '016b')
        print("Time (s) for counting stats in FPGA: ", string_7[-6:], int(string_7[-6:], base=2))
        print("Enable Channel Trigger Bit 1 clock delay: ", string_7[-10:-6])
        print('\n')
        read_register_8 = cmd_interpret.read_config_reg(8)
        string_8   = format(read_register_8, '016b')
        print("Written into Reg 8: ", string_8)
        print("Enhance data LED (LED Page 011): ", string_8[-12])
        print("Enable L1A upon Rx trigger bit : ", string_8[-11])
        print("10 bit delay (trigger bit->L1A): ", string_8[-10:], int(string_8[-10:], base=2))
        print('\n')
        read_register_11 = cmd_interpret.read_config_reg(11)
        read_register_12 = cmd_interpret.read_config_reg(12)
        print("Written into Reg 11: ", format(read_register_11, '016b'))
        print("Written into Reg 12: ", format(read_register_12, '016b'))
        print('\n')
        register_13 = cmd_interpret.read_config_reg(13)
        string_13   = format(register_13, '016b')
        print("Written into Reg 13: ", string_13)
        print("Data Rate              : ", string_13[-7:-5])
        print("LED pages              : ", string_13[-5:-2])
        print("Testmode               : ", string_13[-2])
        print("Timestamp (active low) : ", string_13[-1])
        print('\n')
        register_14 = cmd_interpret.read_config_reg(14)
        string_14   = format(register_14, '016b')
        print("Written into Reg 14: ", string_14)
        print("Enable Memo FC mode: ", string_14[-4])
        print("Polarity           : ", string_14[-3])
        print("Disable GTX        : ", string_14[-2])
        print("Enable Descrambler : ", string_14[-1])
        print('\n')
        register_15 = cmd_interpret.read_config_reg(15)
        string_15   = format(register_15, '016b')
        print("Written into Reg 15: ", string_15)
        print("Channel Enable     : ", string_15[-4:])
        print("Board Type         : ", string_15[-8:-4])
        print("Data Source        : ", string_15[-16:-8])
        print('\n')

    if(not options.nodaq):
        userdefinedir = options.output_directory
        today = datetime.date.today()
        if(options.ssd):
            todaystr = "/run/media/daq/T7/" + today.isoformat() + "_Array_Test_Results"
        else:
            todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results"
        try:
            os.mkdir(todaystr)
            print("Directory %s was created!"%todaystr)
        except FileExistsError:
            print("Directory %s already exists!"%todaystr)
        userdefine_dir = todaystr + "/%s"%userdefinedir
        try:
            os.mkdir(userdefine_dir)
        except FileExistsError:
            print("User defined directory %s already created!"%(userdefine_dir))
            if(options.overwrite != True): 
                print("Overwriting is not enabled, exiting code abruptly...")
                sys.exit(1)

    if(options.fpga_data or options.fpga_data_QInj or options.fpga_data_L1A):
        get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.output_directory, options.fpga_data_QInj,
                      options.fpga_data_L1A, options.DAC_Val)
        if(options.check_trigger_link_at_end):
            print("Checking trigger link at end")
            linked_flag = check_trigger_linked(cmd_interpret)
            while linked_flag is False:
                set_trigger_linked(cmd_interpret)
                get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.output_directory, options.fpga_data_QInj, options.fpga_data_L1A, options.DAC_Val)
                linked_flag = check_trigger_linked(cmd_interpret)
        elif(options.check_all_trigger_link_at_end):
            print("Checking trigger link of all boards at end")
            linked_flag = check_all_trigger_linked(cmd_interpret)
            while linked_flag is False:
                set_all_trigger_linked(cmd_interpret)
                get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.output_directory, options.fpga_data_QInj, options.fpga_data_L1A, options.DAC_Val)
                linked_flag = check_all_trigger_linked(cmd_interpret)
        elif(options.check_link_at_end):
            print("Checking data link at end")
            linked_flag = check_linked(cmd_interpret)
            while linked_flag is False:
                set_linked(cmd_interpret)
                get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.output_directory, options.fpga_data_QInj, options.fpga_data_L1A, options.DAC_Val)
                linked_flag = check_linked(cmd_interpret)

    if(not options.nodaq):
        ## start receive_data, write_data
        store_dict = userdefine_dir
        read_queue = Queue()
        translate_queue = Queue() 
        read_thread_handle = threading.Event()    # This is how we stop the read thread
        write_thread_handle = threading.Event()   # This is how we stop the write thread
        translate_thread_handle = threading.Event() # This is how we stop the translate thread (if translate enabled) (set down below...)
        stop_DAQ_event = threading.Event()     # This is how we notify the Read thread that we are done taking data
                                               # Kill order is read, write, translate
        receive_data = Receive_data('Receive_data', read_queue, cmd_interpret, options.num_fifo_read, read_thread_handle, write_thread_handle, options.time_limit, options.useIPC, stop_DAQ_event, IPC_queue)
        write_data = Write_data('Write_data', read_queue, translate_queue, options.num_line, store_dict, options.binary_only, options.compressed_binary, options.skip_binary, read_thread_handle, write_thread_handle, translate_thread_handle, stop_DAQ_event)
        translate_data = Translate_data('Translate_data', translate_queue, cmd_interpret, options.num_line, options.timestamp, store_dict, options.binary_only, board_ID, write_thread_handle, translate_thread_handle, options.compressed_translation, stop_DAQ_event)
        # read_write_data.start()
        try:
            # Start the thread
            receive_data.start()
            write_data.start()
            if(not options.binary_only): translate_data.start()
            # If the child thread is still running
            while receive_data.is_alive():
                # Try to join the child thread back to parent for 0.5 seconds
                receive_data.join(0.5)
            if(not options.binary_only):
                while translate_data.is_alive():
                    translate_data.join(0.5)
            while write_data.is_alive():
                write_data.join(0.5)
        # When ctrl+c is received
        except KeyboardInterrupt as e:
            # Set the alive attribute to false
            receive_data.alive = False
            write_data.alive = False
            if(not options.binary_only): translate_data.alive = False
            # Block until child thread is joined back to the parent
            receive_data.join()
            if(not options.binary_only): translate_data.join()
            write_data.join()
        # wait for thread to finish before proceeding)
        # read_write_data.join()
#--------------------------------------------------------------------------#
## if statement

if __name__ == "__main__":

    parser = parser_arguments.create_parser()
    (options, args) = parser.parse_args()
    if(options.num_fifo_read>65536):   # See command_interpret.py read_memory()
        print("Max Number of lines read by fifo capped at 65536, you entered ",options.num_fifo_read,", setting to 65536")
        options.num_fifo_read = 65536
        
    import platform
    system = platform.system()
    if system == 'Windows' or system == '':
        options.useIPC = False
    
    main_process(None, options)
