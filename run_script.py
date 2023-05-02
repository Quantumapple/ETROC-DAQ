#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import copy
import time
import visa
import struct
import socket
import threading
import datetime
import heartrate
from queue import Queue
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
from optparse import OptionParser

from command_interpret import *
from ETROC1_ArrayReg import *
from daq_helpers import *
from board_details import *
from config_etroc1 import *
#========================================================================================#
freqency = 1000
duration = 1000
'''
@author: Wei Zhang, Murtaza Safdari
@date: 2023-03-24
This script is used for testing ETROC1/2 Array chips. 
The main function of this script is I2C write and read, Ethernet communication, 
instrument control and so on.
'''
# hostname = '192.168.2.7'					# FPGA IP address
port = 1024									# port number
#--------------------------------------------------------------------------#

## main function
def main(options, cmd_interpret):

    num_boards = len(board_type)
    Pixel_board = options.pixel_address
    QSel_board  = options.pixel_charge			                           # Select Injected Charge

    if(options.firmware):
        if(not options.old_data_format):
            print("Setting firmware...")
            print("Active channels: ", active_channels_key)
            active_channels(cmd_interpret, key = active_channels_key)
            print("Timestamp: ", options.timestamp)
            timestamp(cmd_interpret, key = options.timestamp)
        Enable_FPGA_Descramblber(1, cmd_interpret)                     # Enable FPGA Firmware Descramble
        # LED configuration
        testregister = cmd_interpret.read_config_reg(13)
        print(testregister)
        # cmd_interpret.write_config_reg(15, key)
        print('\n')

    
    if(options.i2c):
        DAC_Value_List = []
        for i in range(num_boards):
            DAC_Value_List.append(single_pixel_threshold(board_size[i], options.pixel_address[i], options.pixel_threshold[i]))

    ###################################### Begin Dir making
    if(not options.nodaq):
        userdefinedir = options.output_directory
        userdefinedir_log = "%s_log"%userdefinedir
        ##  Creat a directory named path with date of today
        today = datetime.date.today()
        todaystr = "../" + today.isoformat() + "_Array_Test_Results"
        try:
            os.mkdir(todaystr)
            print("Directory %s was created!"%todaystr)
        except FileExistsError:
            print("Directory %s already exists!"%todaystr)
        userdefine_dir = todaystr + "/%s"%userdefinedir
        # userdefine_dir_log = todaystr + "/%s"%userdefinedir_log
        try:
            os.mkdir(userdefine_dir)
            # os.mkdir(userdefine_dir_log)
        except FileExistsError:
            print("User defined directory %s already created!"%(userdefine_dir))
            # print("User defined directory %s already created!"%(userdefine_dir_log))
            if(options.overwrite != True): 
                print("Overwriting is not enabled, exiting code abruptly...")
                sys.exit(1)
    ###################################### End Dir making
    logtime_stampe = time.strftime('%m-%d_%H-%M-%S',time.localtime(time.time()))
    
    if(options.i2c):
        for B_num in range(num_boards):

            slaveA_addr = slaveA_addr_list[B_num]                                           # I2C slave A address
            slaveB_addr = slaveB_addr_list[B_num]                                           # I2C slave B address

            if(board_type[B_num]==1):
                reg_val = config_etroc1(B_num, options.charge_injection, DAC_Value_List, 
                                        options.pixel_address, options.pixel_charge, cmd_interpret)
            elif(board_type[B_num]==2):
                pass
            elif(board_type[B_num]==3):
                pass

            ## write data to I2C register one by one
            if(options.verbose):
                print("Write data into I2C slave:")
                print(reg_val)
            for i in range(len(reg_val)):
                time.sleep(0.01)
                if i < 32:                                                                  # I2C slave A write
                    iic_write(1, slaveA_addr_list[B_num], 0, i, reg_val[i], cmd_interpret)
                else:                                                                       # I2C slave B write
                    iic_write(1, slaveB_addr_list[B_num], 0, i-32, reg_val[i], cmd_interpret)

            ## read back data from I2C register one by one
            iic_read_val = []
            for j in range(len(reg_val)):
                time.sleep(0.01)
                if j < 32:
                    iic_read_val += [iic_read(0, slaveA_addr_list[B_num], 1, j, cmd_interpret)]            # I2C slave A read
                else:
                    iic_read_val += [iic_read(0, slaveB_addr_list[B_num], 1, j-32, cmd_interpret)]         # I2C slave B read
            if(options.verbose):
                print("I2C read back data:")
                print(iic_read_val)

            # compare I2C write in data with I2C read back data
            if iic_read_val == reg_val:
                print("I2C SUCCESS! Write data matches read data for Board ", B_num)
            else:
                print("I2C ERROR! Write data does not match read data for Board ", B_num)

    time.sleep(1)                                                                       # delay one second
    software_clear_fifo(cmd_interpret)                                                  # clear fifo content

    if(not options.nodaq):
        ## start receive_data, write_data, daq_plotting threading
        store_dict = userdefine_dir
        read_queue = Queue() 
        plot_queue = Queue()
        read_stop_event = threading.Event()     # This is how we stop the read thread
        receive_data = Receive_data('Receive_data', read_queue, cmd_interpret,
        options.num_fifo_read, read_stop_event)
        write_data = Write_data('Write_data', read_queue, plot_queue, cmd_interpret, options.num_file, options.num_line, options.time_limit, options.timestamp, store_dict, options.binary_only, options.make_plots, board_ID, read_stop_event)
        # read_write_data = Read_Write_data('Read_Write_data', plot_queue, cmd_interpret, options.num_file, options.num_line, 
        #                                 options.num_fifo_read, options.timestamp, store_dict, 
        #                                 options.binary_only, options.make_plots, board_ID)
        # start threading
        # read_data.start()
        # write_data.start()
        # read_write_data.start()

        if(options.make_plots):
            daq_plotting = DAQ_Plotting('DAQ_Plotting', plot_queue, options.timestamp, store_dict, options.pixel_address, board_type, board_size, options.plot_queue_time)
            # try:
            #     # Start the thread
            #     daq_plotting.start()
            #     # If the child thread is still running
            #     while daq_plotting.is_alive():
            #         # Try to join the child thread back to parent for 0.5 seconds
            #         daq_plotting.join(0.5)
            # # When ctrl+c is received
            # except KeyboardInterrupt as e:
            #     # Set the alive attribute to false
            #     daq_plotting.alive = False
            #     # Block until child thread is joined back to the parent
            #     daq_plotting.join()
        try:
            # Start the thread
            receive_data.start()
            write_data.start()
            if(options.make_plots): daq_plotting.start()
            # If the child thread is still running
            while receive_data.is_alive():
                # Try to join the child thread back to parent for 0.5 seconds
                receive_data.join(0.5)
            while write_data.is_alive():
                write_data.join(0.5)
            if(options.make_plots):
                while daq_plotting.is_alive():
                    daq_plotting.join(0.5)
        # When ctrl+c is received
        except KeyboardInterrupt as e:
            # Set the alive attribute to false
            receive_data.alive = False
            write_data.alive = False
            if(options.make_plots): daq_plotting.alive = False
            # Block until child thread is joined back to the parent
            receive_data.join()
            write_data.join()
            if(options.make_plots): daq_plotting.join()
        
        
        # wait for thread to finish before proceeding
        # receive_data.join()
        # write_data.join()
        # read_write_data.join()
#--------------------------------------------------------------------------#
## if statement
if __name__ == "__main__":

    def int_list_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, list(map(int, value.split(','))))
    parser = OptionParser()
    parser.add_option("--hostname", dest="hostname", action="store", type="string",
                      help="FPGA IP Address", default="192.168.2.7")
    parser.add_option("-n", "--num_file", dest="num_file", action="store", type="int",
                      help="Number of files created by DAQ script", default=1)
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int",
                      help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-r", "--num_fifo_read", dest="num_fifo_read", action="store", type="int",
                      help="Number of lines read per call of fifo readout", default=10000)
    parser.add_option("-t", "--time_limit", dest="time_limit", action="store", type="int",
                      help="Number of seconds to run this code", default=-1)
    parser.add_option("-o", "--output_directory", dest="output_directory", action="store", type="string",
                      help="User defined output directory", default="unnamed_output_directory")
    parser.add_option("-a", "--pixel_address", dest="pixel_address", action="callback", type="string",
                      help="Single pixel address under test for each board", callback=int_list_callback)
    parser.add_option("--pixel_threshold", dest="pixel_threshold", action="callback", type="string",
                      help="Single pixel threshold for pixels under test for each board", callback=int_list_callback)
    parser.add_option("-q", "--pixel_charge", dest="pixel_charge", action="callback", type="string",
                      help="Single pixel charge to be injected (fC) for pixels under test for each board", callback=int_list_callback)
    parser.add_option("-i", "--charge_injection",
                      action="store_true", dest="charge_injection", default=False,
                      help="Flag that enables Qinj")
    parser.add_option("-b", "--binary_only",
                      action="store_true", dest="binary_only", default=False,
                      help="Save only the untranslated FPGA binary data (raw output)")
    parser.add_option("-s", "--timestamp", type="int",
                      action="store", dest="timestamp", default=0x0000,
                      help="Set timestamp binary, see daq_helpers for more info")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Print status messages to stdout")
    parser.add_option("-w", "--overwrite",
                      action="store_true", dest="overwrite", default=False,
                      help="Overwrite previously saved files")
    parser.add_option("-p", "--make_plots",
                      action="store_true", dest="make_plots", default=False,
                      help="Enable plotting of real time hits")
    parser.add_option("--plot_queue_time", dest="plot_queue_time", action="store", type="float",
                      help="Time (s) used to pop lines off the queue for plotting", default=0.1)
    parser.add_option("--old_data_format",
                      action="store_true", dest="old_data_format", default=False,
                      help="(Dev Only) Set if Data is in old format for ETROC1")
    parser.add_option("--i2c",
                      action="store_true", dest="i2c", default=False,
                      help="Config ETROC boards over I2C")
    parser.add_option("--nodaq",
                      action="store_true", dest="nodaq", default=False,
                      help="Switch off DAQ via the FPGA")
    parser.add_option("--firmware",
                      action="store_true", dest="firmware", default=False,
                      help="Configure FPGA firmware settings")
    (options, args) = parser.parse_args()

    if(options.pixel_address == None): options.pixel_address = [5, 5, 5, 5]
    if(options.pixel_threshold == None): options.pixel_threshold = [552, 560, 560, 560]
    if(options.pixel_charge == None): options.pixel_charge = [30, 30, 30, 30]
    if(options.num_fifo_read>65536):                                                # See command_interpret.py read_memory()
        print("Max Number of lines read by fifo capped at 65536, you entered ",options.num_fifo_read,", setting to 65536")
        options.num_fifo_read = 65536

    if(options.verbose):
        print("Verbose Output: ", options.verbose)
        print("\n")
        print("-------------------------------------------")
        print("--------Set of inputs from the USER--------")
        print("FPGA IP Address: ", options.hostname)
        print("Config ETROC boards over I2C: ", options.i2c)
        print("Switch off DAQ via the FPGA?: ", options.nodaq)
        print("Configure FPGA firmware settings?: ", options.firmware)
        print("Number of files created by DAQ script: ", options.num_file)
        print("Number of lines per file created by DAQ script: ", options.num_line)
        print("Number of lines read per call of fifo readout: ", options.num_fifo_read)
        print("Number of seconds to run this code (>0 means effective): ", options.time_limit)
        print("User defined Output Directory: ", options.output_directory)
        print("Single pixel address under test for each board: ", options.pixel_address)
        print("Single pixel threshold for pixels under test for each board: ", options.pixel_threshold)
        print("Single pixel charge to be injected (fC) for pixels under test for each board: ", options.pixel_charge)
        print("Flag that enables Qinj: ", options.charge_injection)
        print("Save only the untranslated FPGA binary data (raw output): ", options.binary_only)
        print("Set timestamp binary, see daq_helpers for more info: ", options.timestamp)
        print("Set timestamp binary, see daq_helpers for more info (explicit hex string): ", "0x{:04x}".format(options.timestamp))
        print("Overwrite previously saved files: ", options.overwrite)
        print("Enable plotting of real time hits: ", options.make_plots)
        print("Time (s) used to pop lines off the queue for plotting: ", options.plot_queue_time)
        print("--------End of inputs from the USER--------")
        print("-------------------------------------------")
        print("\n")
        print("-------------------------------------------")
        print("-------Inputs that have been pre-set-------")
        print("ETROC Board Type: ",   board_type)
        print("ETROC Board Size: ",   board_size)
        print("ETROC Board Name: ",   board_name)
        print("ETROC Chip ID: ",      board_ID)
        print("I2C A Address List: ", slaveA_addr_list)
        print("I2C B Address List: ", slaveB_addr_list)
        print("Load Capacitance of the preamp first stage: ", CLSel_board)
        print("Feedback resistance seleciton: ", RfSel_board)
        print("Bias current selection of the input transistor in the preamp: ", IBSel_board)
        print("Set active channel binary, see daq_helpers for more info: ", active_channels_key)
        print("Set active channel binary, see daq_helpers for more info (explicit hex string): ", "0x{:04x}".format(active_channels_key))
        print("-------------------------------------------")
        print("-------------------------------------------")
        print("\n")

    if(options.binary_only==True and options.make_plots==True):
        print("ERROR! Can't make plots without translating data!")
        sys.exit(1)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	                        # initial socket
    except socket.error:
        print("Failed to create socket!")
        sys.exit()
    try:
        s.connect((options.hostname, port))								                        # connect socket
    except socket.error:
        print("failed to connect to ip " + options.hostname)
    cmd_interpret = command_interpret(s)					                            # Class instance
        
    main(options, cmd_interpret)    # execute main function
    s.close()                       # close socket
