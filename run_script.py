#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import copy
import time
import struct
import socket
import threading
import datetime
import queue
import parser_arguments
import command_interpret
import daq_helpers
import translate_data
import ws_testing
import platform
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-03-24
This script is used for testing ETROC2 Array chips.
The main function of this driver script is to facilitate I2C write and read, Ethernet communication,
instrument control and so on, handling the New Event Model (Sept 2023)
'''
port = 1024
# 17F0F  =   10111111100001111
board_ID = ["10111111100001111","10111111100001111","10111111100001111", "10111111100001111"]

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
    cmd_interpret = command_interpret.command_interpret(s)
    main(options, cmd_interpret, IPC_queue)
    s.close()

#--------------------------------------------------------------------------#
## main function
def main(options, cmd_interpret, IPC_queue = None):
    if(options.firmware):
        print("Setting firmware...")
        daq_helpers.active_channels(cmd_interpret, key = options.active_channel)
        daq_helpers.timestamp(cmd_interpret, key = options.timestamp)
        daq_helpers.triggerBitDelay(cmd_interpret, options.trigger_bit_delay)
        daq_helpers.Enable_FPGA_Descramblber(cmd_interpret, options.polarity)

    if(options.counter_duration):
        print("Setting Counter Duration and Channel Delays...")
        daq_helpers.counterDuration(cmd_interpret, options.counter_duration)

    if(options.verbose):
        read_register_7 = cmd_interpret.read_config_reg(7)
        string_7   = format(read_register_7, '016b')
        print("Written into Reg 7: ", string_7)
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
        read_register_13 = cmd_interpret.read_config_reg(13)
        string_13   = format(read_register_13, '016b')
        print("Written into Reg 13: ", string_13)
        print("Data Rate              : ", string_13[-7:-5])
        print("LED pages              : ", string_13[-5:-2])
        print("Testmode               : ", string_13[-2])
        print("Timestamp (active low) : ", string_13[-1])
        print("DEV Status Page        : ", string_13[-2:])
        print('\n')
        read_register_14 = cmd_interpret.read_config_reg(14)
        string_14   = format(read_register_14, '016b')
        print("Written into Reg 14: ", string_14)
        print("Add Ethernet Filler: ", string_14[-6])
        print("Enable Debug mode  : ", string_14[-5])
        print("Enable Dumping mode: ", string_14[-4])
        print("Polarity           : ", string_14[-3])
        print("Disable GTX        : ", string_14[-2])
        print("Enable AutoSync    : ", string_14[-1])
        print('\n')
        read_register_15 = cmd_interpret.read_config_reg(15)
        string_15   = format(read_register_15, '016b')
        print("Written into Reg 15  : ", string_15)
        print("Channel Enable       : ", string_15[-4:])
        print("WS Trig Stop Delay   : ", string_15[-7:-4])
        print("Enable WS Trigger    : ", string_15[-8:-7])
        print("Triple Trigger       : ", string_15[-9:-8])
        print("Trigger OR Logic     : ", string_15[-10:-9])
        print("Enable Global Trigger: ", string_15[-11:-10])
        print("Global Trigger Delay : ", string_15[-16:-11])
        print('\n')
        # if(string_13[-2:]!='00'):
        #     def unpack_state_history(dumped_data):
        #         print("State! ->")
        #         print("chip_data_buffer_din         :", dumped_data[-40:])
        #         print("state (state machine)        :", dumped_data[-43:-40])
        #         print("chip_data_ready              :", dumped_data[-44:-43])
        #         print("sortMask                     :", dumped_data[-48:-44])
        #         print("readToken                    :", dumped_data[-50:-48])
        #         print("chip_data_buffer_empty       :", dumped_data[-51:-50])
        #         print("chip_data_buffer_full        :", dumped_data[-52:-51])
        #         print("chip_data_buffer_wren        :", dumped_data[-53:-52])
        #         print("isHeader[readToken]          :", dumped_data[-54:-53])
        #         print("emptyETROC2FIFOCh[readToken] :", dumped_data[-55:-54])
        #         print("rdenETROC2FIFOCh[readToken]  :", dumped_data[-56:-55])
        #     print("Data from Status Registers for debugging, printed from latest state to oldest state:")
        #     for status_page in ["01","10","11"]:
        #         modified_timestamp = format(options.timestamp, '016b')
        #         modified_timestamp = modified_timestamp[:-2] + status_page
        #         daq_helpers.timestamp(cmd_interpret, key = int(modified_timestamp, base=2))
        #         time.sleep(1.1)
        #         print("Waited for 1 sec")
        #         print(fr"Status Page {status_page} Set, data as follows ->")
        #         temp_reg = ""
        #         temp_reg = format(cmd_interpret.read_status_reg(0), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(1), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(2), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(3), '016b')[-8:] + temp_reg
        #         unpack_state_history(temp_reg)
        #         temp_reg = ""
        #         temp_reg = format(cmd_interpret.read_status_reg(3), '016b')[-16:-8] + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(4), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(5), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(6), '016b') + temp_reg
        #         unpack_state_history(temp_reg)
        #         temp_reg = ""
        #         temp_reg = format(cmd_interpret.read_status_reg(7), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(8), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(9), '016b') + temp_reg
        #         temp_reg = format(cmd_interpret.read_status_reg(10), '016b')[-8:] + temp_reg
        #         unpack_state_history(temp_reg)
        #         if(status_page=="10"):
        #             print("Special registers start ->")
        #             print("Buffer almost full : ", format(cmd_interpret.read_status_reg(10), '016b')[-10:-9])
        #             print("Hold L1A           : ", format(cmd_interpret.read_status_reg(10), '016b')[-9 :-8])
        #             print("Special registers end")
        #     del temp_reg, modified_timestamp
        del read_register_7,read_register_8,read_register_11,read_register_12,read_register_13,read_register_14,read_register_15
        del string_7,string_8,string_13,string_14,string_15

    if(options.clear_fifo):
        print("Clearing FIFO...")
        daq_helpers.software_clear_fifo(cmd_interpret)
        time.sleep(2.1)
        print("Waited for 2 secs")

    if(options.clear_error or options.check_valid_data_start):
        print("Clearing Event Counter...")
        daq_helpers.software_clear_error(cmd_interpret)
        time.sleep(0.1)

    if(options.resume_in_debug_mode):
        print("Resetting and Resuming State Machine in Debug Mode..")
        daq_helpers.resume_in_debug_mode(cmd_interpret)
        time.sleep(2.1)
        print("Waited for 2 secs")

    if(options.reset_all_till_trigger_linked):
        print("Resetting/Checking link of all boards...")
        daq_helpers.set_all_trigger_linked(cmd_interpret, options.inpect_links_only)

    if(options.start_dev_qinj_fc):
        print("Starting QInj + Ext L1A train...")
        daq_helpers.configure_memo_FC(cmd_interpret,Initialize=True,QInj=True,L1A=True,BCR=True,Triggerbit=True)
    if(options.start_dev_qinj_selftrig_fc):
        print("Starting QInj Without Ext L1A train...")
        daq_helpers.configure_memo_FC(cmd_interpret,Initialize=True,QInj=True,L1A=False,BCR=True,Triggerbit=True,repeatedQInj=False)
    if(options.stop_dev_qinj_fc):
        print("Stopping QInj + Ext L1A train...")
        daq_helpers.configure_memo_FC(cmd_interpret,Initialize=False,QInj=False,L1A=False,BCR=False,Triggerbit=True)

    # if(options.ws_testing):
    #     daq_helpers.software_clear_ws_trig_block(cmd_interpret)

    if(not options.nodaq):
        userdefinedir = options.output_directory
        today = datetime.date.today()
        final_dir_str = today.isoformat() + "_Array_Test_Results"
        if options.run_name is not None:
            final_dir_str = options.run_name
        if(options.ssd):
            todaystr = "/run/media/daq/T7/" + final_dir_str
        else:
            todaystr = "../ETROC-Data/" + final_dir_str
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

    if(options.fpga_data or options.fpga_data_QInj):
        daq_helpers.get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.run_name, options.output_directory, options.fpga_data_QInj, options.DAC_Val)
        if(options.check_all_trigger_link_at_end):
            print("Checking trigger link of all boards at end")
            linked_flag = daq_helpers.set_all_trigger_linked(cmd_interpret, True)
            while linked_flag is False:
                daq_helpers.set_all_trigger_linked(cmd_interpret)
                daq_helpers.get_fpga_data(cmd_interpret, options.fpga_data_time_limit, options.overwrite, options.run_name, options.output_directory, options.fpga_data_QInj, options.DAC_Val)
                linked_flag = daq_helpers.set_all_trigger_linked(cmd_interpret, True)

    if(not options.nodaq):
        store_dict = userdefine_dir
        read_queue = queue.Queue()
        translate_queue = queue.Queue()
        read_thread_handle = threading.Event()      # This is how we stop the read thread
        write_thread_handle = threading.Event()     # This is how we stop the write thread
        translate_thread_handle = threading.Event() # This is how we stop the translate thread (if translate enabled) (set down below...)
        stop_DAQ_event = threading.Event()          # This is how we notify the Read thread that we are done taking data
                                                    # Kill order is read, write, translate
        receive_data = daq_helpers.Receive_data('Receive_data', read_queue, cmd_interpret, options.num_fifo_read, read_thread_handle, write_thread_handle, options.time_limit, options.useIPC, stop_DAQ_event, IPC_queue)
        write_data = daq_helpers.Write_data('Write_data', read_queue, translate_queue, options.num_line, store_dict, options.skip_translation, options.compressed_binary, options.skip_binary, read_thread_handle, write_thread_handle, translate_thread_handle, stop_DAQ_event)
        if(not options.ws_testing):
            translate_data_thread = translate_data.Translate_data('Translate_data', options.firmware_key, options.check_valid_data_start, translate_queue, cmd_interpret, options.num_line, store_dict, options.skip_translation, board_ID, write_thread_handle, translate_thread_handle, options.compressed_translation, stop_DAQ_event, options.debug_event_translation, options.lock_translation_numwords)
        else:
            ws_chip = ws_testing.return_initialized_ws_chip(options.ws_i2c_port, options.ws_chip_address, options.ws_address)
            translate_data_thread = ws_testing.Translate_ws_data('Translate_ws_data', options.firmware_key, options.check_valid_data_start, translate_queue, cmd_interpret, options.num_line, store_dict, options.skip_translation, board_ID, write_thread_handle, translate_thread_handle, options.compressed_translation, stop_DAQ_event, options.debug_event_translation, options.lock_translation_numwords, ws_chip, options.ws_chipname, options.ws_i2c_port, options.ws_chip_address, options.ws_address)
        try:
            # Start the thread
            receive_data.start()
            write_data.start()
            if(not options.skip_translation): translate_data_thread.start()
            # If the child thread is still running
            while receive_data.is_alive():
                # Try to join the child thread back to parent for 0.5 seconds
                receive_data.join(0.5)
            if(not options.skip_translation):
                while translate_data_thread.is_alive():
                    translate_data_thread.join(0.5)
            while write_data.is_alive():
                write_data.join(0.5)
        # When ctrl+c is received
        except KeyboardInterrupt as e:
            # Set the alive attribute to false
            receive_data.alive = False
            write_data.alive = False
            if(not options.skip_translation): translate_data_thread.alive = False
            # Block until child thread is joined back to the parent
            receive_data.join()
            if(not options.skip_translation): translate_data_thread.join()
            write_data.join()
        # wait for thread to finish before proceeding)

#--------------------------------------------------------------------------#
if __name__ == "__main__":

    parser = parser_arguments.create_parser()
    (options, args) = parser.parse_args()

    # See command_interpret.py read_memory()
    if(options.num_fifo_read>65536):
        print("Max Number of lines read by fifo capped at 65536, you entered ",options.num_fifo_read,", setting to 65536")
        options.num_fifo_read = 65536

    if(options.time_limit<=0):
        print("DAQ Runtime <= 0, setting no DAQ mode...")
        options.nodaq = True

    if(options.verbose):
        for option, value in vars(options).items(): print('%s = %s' % (option, value))

    system = platform.system()
    if system == 'Windows' or system == '':
        options.useIPC = False

    main_process(None, options)
