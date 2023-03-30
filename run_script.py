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
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is used for testing ETROC1/2 Array chips. The main function of this script is I2C write and read, Ethernet communication, instrument control and so on.
'''
hostname = '192.168.2.3'					#FPGA IP address
port = 1024									#port number
#--------------------------------------------------------------------------#

## main functionl
def main(options):

    active_channels(key = active_channels_key)
    timestamp(key = options.timestamp)

    num_boards = len(board_size)
    DAC_Value_List = []
    for i in range(num_boards):
        DAC_Value_List.append(single_pixel_threshold(board_size[i], options.pixel_address[i], options.pixel_threshold[i]))

    Pixel_board = options.pixel_address
    QSel_board  = options.pixel_charge			# Select Injected Charge
    ###################################### Begin Dir naming
    userdefinedir = "%sP%d_%sP%d_%sP%d_QInj=1M25_Ref_1202_HMC_4095"%(board_name[0], Pixel_board[0], board_name[1], Pixel_board[1], board_name[2], Pixel_board[2])
    userdefinedir_log = "%s_log"%userdefinedir
    ##  Creat a directory named path with date of today
    today = datetime.date.today()
    todaystr = today.isoformat() + "_Array_Test_Results"
    try:
        os.mkdir(todaystr)
        print("Directory %s was created!"%todaystr)
    except FileExistsError:
        print("Directory %s already exists!"%todaystr)
    userdefine_dir = todaystr + "/%s"%userdefinedir
    userdefine_dir_log = todaystr + "/%s"%userdefinedir_log
    try:
        os.mkdir(userdefine_dir)
        os.mkdir(userdefine_dir_log)
    except FileExistsError:
        print("User define directories already created!!!")
    ###################################### End Dir naming
    logtime_stampe = time.strftime('%m-%d_%H-%M-%S',time.localtime(time.time()))
    
    for B_num in range(len(slaveA_addr_list)):
        slaveA_addr = slaveA_addr_list[B_num]       # I2C slave A address
        slaveB_addr = slaveB_addr_list[B_num]       # I2C slave B address

        if(board_type==1):
            reg_val = config_etroc1(B_num, options.charge_injection)
        elif(board_type==2):
            pass
        elif(board_type==3):
            pass

        ## write data to I2C register one by one
        print("Write data into I2C slave:")
        print(reg_val)
        for i in range(len(reg_val)):
            time.sleep(0.01)
            if i < 32:                                                      # I2C slave A write
                iic_write(1, slaveA_addr_list[B_num], 0, i, reg_val[i])
            else:                                                           # I2C slave B write
                iic_write(1, slaveB_addr_list[B_num], 0, i-32, reg_val[i])

        ## read back data from I2C register one by one
        iic_read_val = []
        for j in range(len(reg_val)):
            time.sleep(0.01)
            if j < 32:
                iic_read_val += [iic_read(0, slaveA_addr_list[B_num], 1, j)]            # I2C slave A read
            else:
                iic_read_val += [iic_read(0, slaveB_addr_list[B_num], 1, j-32)]         # I2C slave B read
        print("I2C read back data:")
        print(iic_read_val)


        # compare I2C write in data with I2C read back data
        if iic_read_val == reg_val:
            print("Wrote into data matches with read back data!")
        else:
            print("Wrote into data doesn't matche with read back data!!!!")

    time.sleep(1)                                                       # delay one second
    software_clear_fifo()                                               # clear fifo content

    ## start receive_data and write_data threading
    store_dict = userdefine_dir
    queue = Queue()                                                     # define a queue
    receive_data = Receive_data('Receive_data', queue, options.num_file, options.num_line)        # initial receive_data class
    write_data = Write_data('Write_data', queue, options.num_file, options.num_line, store_dict, PhaseAdj, board_name[0], Pixel_board[0], QSel_board[0], DAC_board[0], board_name[1], Pixel_board[1], QSel_board[1], DAC_board[1], board_name[2], Pixel_board[2], QSel_board[2], DAC_board[2])  # initial write_data class
    
    receive_data.start()                                                # start receive_data threading
    write_data.start()                                                  # start write_data threading

    receive_data.join()                                                 # threading 
    write_data.join()
#--------------------------------------------------------------------------#
## if statement
if __name__ == "__main__":
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	# initial socket
    except socket.error:
        print("Failed to create socket!")
        sys.exit()
    try:
        s.connect((hostname, port))								# connect socket
    except socket.error:
        print("failed to connect to ip " + hostname)
    cmd_interpret = command_interpret(s)					    # Class instance


    parser = OptionParser()                                     # Option Parser for better argument handling
    parser.add_option("-n", "--num_file", dest="num_file", action="store", type="int"
                      help="Number of files created by DAQ script")
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int"
                      help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-pa", "--pixel_address", dest="pixel_address", action="append", type="int"
                      help="Single pixel address under test for each board",
                      default=[5, 5, 5])
    parser.add_option("-pt", "--pixel_threshold", dest="pixel_threshold", action="append", type="int"
                      help="Single pixel threshold for pixels under test for each board",
                      default=[550, 550, 550])
    parser.add_option("-pq", "--pixel_charge", dest="pixel_charge", action="append", type="int"
                      help="Single pixel charge to be injected (fC) for pixels under test for each board",
                      default=[30, 30, 30])
    parser.add_option("-qinj", "--charge_injection",
                      action="store_true", dest="charge_injection", default=False,
                      help="Flag that enables Qinj")
    parser.add_option("-b", "--binary",
                      action="store_true", dest="binary_output", default=False,
                      help="print untranslated FPGA binary data (raw output)")
    parser.add_option("-t", "--timestamp",
                      action="store", dest="timestamp", default=0x0000,
                      help="Set timestamp binary, see daq_helpers for more info") #MAY NEED TO SPECIFY TYPE
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    (options, args) = parser.parse_args()

    main(options)											    # execute main function
    s.close()												    # close socket
