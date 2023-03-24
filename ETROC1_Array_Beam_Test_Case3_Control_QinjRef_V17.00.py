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

    num_boards = len(board_size)

    for i in range(num_boards):
        DAC_Value_List.append(single_pixel_threshold(board_size[i], options.pixel_address[i], options.pixel_threshold[i]))

    Pixel_board= options.pixel_address[i]

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

    logtime_stampe = time.strftime('%m-%d_%H-%M-%S',time.localtime(time.time()))
    for B_num in range(len(slaveA_addr_list)):
        slaveA_addr = slaveA_addr_list[B_num]       # I2C slave A address
        slaveB_addr = slaveB_addr_list[B_num]       # I2C slave B address

        # Charge Injection setting
        Pixel_Num=Pixel_board[B_num]
        QSel = QSel_board[B_num]

        # PreAmp settings
        CLSel = CLSel_board[B_num]                  # default 0
        RfSel = RfSel_board[B_num]
        IBSel = IBSel_board[B_num]

        Board_num = 2                               # Board ID show in tag
        EnScr = 1                                   # Enable Scrambler
        DMRO_revclk = 1                             # Sample clock polarity
        Test_Pattern_Mode_Output = 0                # 0: TDC output data, 1: Counter output data
        TDC_testMode = 0                            # 1: TDC works on test mode, 0: TDC works on normal mode
        TDC_Enable = 1                              # 1: enable TDC 0: disable TDC
        PhaseAdj = 0                              # Phase shifter ranges from 0 to 255
        Total_point = 1                             # Total fetch data = Total_point * 50000
        External_RST = 0                            # 1: reset   0: didn't reset
        Fetch_Data = 1                              # Turn On fetch data
        Data_Format = 1                             # 1: Debug data format (TOA, TOT, Cal, hitflag) 0: Real time data format (30-bit data)
        

        DAC_Value = DAC_Value_List[B_num]
        DAC_board[B_num]=DAC_Value[Pixel_Num]
        print(DAC_Value)
        DAC_Config(DAC_Value)
        reg_val = []

        # charge injection setting
        ETROC1_ArrayReg1.set_QSel(QSel)

        QInj_Enable = [[0x01, 0x00], [0x02, 0x00], [0x04, 0x00], [0x08, 0x00], [0x10, 0x00], [0x20, 0x00], [0x40, 0x00], [0x80, 0x00],\
                        [0x00, 0x01], [0x00, 0x02], [0x00, 0x04], [0x00, 0x08], [0x00, 0x10], [0x00, 0x20], [0x00, 0x40], [0x00, 0x80]]


        ETROC1_ArrayReg1.set_EN_QInj7_0(QInj_Enable[Pixel_Num][0])       # Enable QInj7~0
        ETROC1_ArrayReg1.set_EN_QInj15_8(QInj_Enable[Pixel_Num][1])      # Enable QInj15~8

        #ETROC1_ArrayReg1.set_EN_QInj7_0(0x00)       # Enable QInj7~0
        #ETROC1_ArrayReg1.set_EN_QInj15_8(0x00)      # Enable QInj15~8

        ## PreAmp setting
        ETROC1_ArrayReg1.set_CLSel(CLSel)
        ETROC1_ArrayReg1.set_RfSel(RfSel)
        ETROC1_ArrayReg1.set_IBSel(IBSel)

        ## Discriminator setting
        ETROC1_ArrayReg1.set_HysSel(0xf)

        EN_DiscriOut = [0x11, 0x21, 0x41, 0x81, 0x12, 0x22, 0x42, 0x82, 0x14, 0x24, 0x44, 0x84, 0x18, 0x28, 0x48, 0x88, 0x0f]
        ETROC1_ArrayReg1.set_EN_DiscriOut(EN_DiscriOut[Pixel_Num])


        ## VDAC setting
        VTHOut_Select = [[0xfe, 0xff], [0xfd, 0xff], [0xfb, 0xff], [0xf7, 0xff], [0xef, 0xff], [0xdf, 0xff], [0xbf, 0xff], [0x7f, 0xff],\
                            [0xff, 0xfe], [0xff, 0xfd], [0xff, 0xfb], [0xff, 0xf7], [0xff, 0xef], [0xff, 0xdf], [0xff, 0xbf], [0xff, 0x7f], [0xff, 0xff]]

        ETROC1_ArrayReg1.set_PD_DACDiscri7_0(VTHOut_Select[Pixel_Num][0])
        ETROC1_ArrayReg1.set_PD_DACDiscri15_8(VTHOut_Select[Pixel_Num][1])


        ETROC1_ArrayReg1.set_Dis_VTHInOut7_0(VTHOut_Select[Pixel_Num][0])
        ETROC1_ArrayReg1.set_Dis_VTHInOut15_8(VTHOut_Select[Pixel_Num][1])

        ## Phase Shifter Setting
        ETROC1_ArrayReg1.set_dllEnable(0)           # Enable phase shifter
        ETROC1_ArrayReg1.set_dllCapReset(1)         # should be set to 0
        time.sleep(0.1)
        ETROC1_ArrayReg1.set_dllCapReset(0)         # should be set to 0
        ETROC1_ArrayReg1.set_dllCPCurrent(1)        # default value 1:
        ETROC1_ArrayReg1.set_dllEnable(1)           # Enable phase shifter
        ETROC1_ArrayReg1.set_dllForceDown(0)        # should be set to 0
        ETROC1_ArrayReg1.set_PhaseAdj(PhaseAdj)     # 0-128 to adjust clock phase

        # 320M clock strobe setting
        ETROC1_ArrayReg1.set_RefStrSel(0x03)        # default 0x03: 3.125 ns measuement window

        # clock input and output MUX select
        ETROC1_ArrayReg1.set_TestCLK0(1)            # 0: 40M and 320M clock comes from phase shifter, 1: 40M and 320M clock comes from external pads
        ETROC1_ArrayReg1.set_TestCLK1(0)            # 0: 40M and 320M  go cross clock strobe 1: 40M and 320M bypass
        ETROC1_ArrayReg1.set_CLKOutSel(1)           # 0: 40M clock output, 1: 320M clock or strobe output

        ## DMRO readout Mode
        DMRO_Readout_Select = [[0x01, 0x0], [0x02, 0x0], [0x04, 0x0], [0x08, 0x0], [0x01, 0x1], [0x02, 0x1], [0x04, 0x1], [0x08, 0x1],\
                                [0x01, 0x2], [0x02, 0x2], [0x04, 0x2], [0x08, 0x2], [0x01, 0x3], [0x02, 0x3], [0x04, 0x3], [0x08, 0x3]]
        ETROC1_ArrayReg1.set_OE_DMRO_Row(DMRO_Readout_Select[Pixel_Num][0])       # DMRO readout row select
        ETROC1_ArrayReg1.set_DMRO_Col(DMRO_Readout_Select[Pixel_Num][1])          # DMRO readout column select

        ETROC1_ArrayReg1.set_RO_SEL(0)              # 0: DMRO readout enable  1: Simple readout enable
        ETROC1_ArrayReg1.set_TDC_enableMon(Test_Pattern_Mode_Output)       # 0: Connect to TDC       1: Connect to Test Counter

        ## TDC setting
        ETROC1_ArrayReg1.set_TDC_resetn(1)
        ETROC1_ArrayReg1.set_TDC_testMode(TDC_testMode)
        ETROC1_ArrayReg1.set_TDC_autoReset(0)
        ETROC1_ArrayReg1.set_TDC_enable(TDC_Enable)

        ## DMRO Setting
        ETROC1_ArrayReg1.set_DMRO_ENScr(EnScr)          # Enable DMRO scrambler
        ETROC1_ArrayReg1.set_DMRO_revclk(DMRO_revclk)
        ETROC1_ArrayReg1.set_DMRO_testMode(0)           # DMRO work on test mode
        Enable_FPGA_Descramblber(EnScr)                 # Enable FPGA Firmware Descrambler
        cmd_interpret.write_config_reg(15,0x0003);
        cmd_interpret.write_config_reg(13,0x0000); #noTimestamp
        
        
        ## DMRO CML driver
        ETROC1_ArrayReg1.set_Dataout_AmplSel(7)

        ETROC1_ArrayReg1.set_CLKTO_AmplSel(7)
        ETROC1_ArrayReg1.set_CLKTO_disBIAS(0)

        reg_val = ETROC1_ArrayReg1.get_config_vector()                      # Get Array Pixel Register default data

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
            #winsound.Beep(1000, 500)
        else:
            print("Wrote into data doesn't matche with read back data!!!!")
            #for x in range(3):
            #    winsound.Beep(1000, 500)

        # add log file
        with open("./%s/%s/log_%s.dat"%(todaystr, userdefinedir_log, logtime_stampe),'a+') as logfile:
            logfile.write("%s\n"%time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
            logfile.write("I2C write into data %s:\n"%board_name[B_num])
            for i in range(len(reg_val)):
                if i < 32:                                                      # I2C slave A write
                    logfile.writelines("REGA_%02d %s\n"%(i, hex(reg_val[i])))
                else:                                                           # I2C slave B write
                    logfile.writelines("REGB_%02d %s\n"%(i-32, hex(reg_val[i])))
            if iic_read_val == reg_val:
                logfile.write("Wrote into data matches with read back data!\n")
            else:
                logfile.write("Wrote in data doesn't matche with read back data!!!!\n")
            logfile.write("./%s/%s/log_%s"%(todaystr, userdefinedir_log, logtime_stampe))

    # monitor power supply current
    #Power_current = measure_current(External_RST)
    #print(Power_current)

    time.sleep(1)                                                       # delay one second
    software_clear_fifo()                                               # clear fifo content
    #cmd_interpret.write_config_reg(15,0xff5C)

    ## strat receive_data and wirte_data threading
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
    ETROC1_ArrayReg1 = ETROC1_ArrayReg()                        # New a class

    parser = OptionParser()                                     # Option Parser for better argument handling
    parser.add_option("-n", "--num_file", dest="num_file", action="store", type="int"
                      help="Number of files created by DAQ script")
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int"
                      help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-pa", "--pixel_address", dest="pixel_address", action="append", type="int"
                      help="Single pixel address under test for each board")
    parser.add_option("-pt", "--pixel_threshold", dest="pixel_threshold", action="append", type="int"
                      help="Single pixel threshold for pixels under test for each board")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    (options, args) = parser.parse_args()

    main(options)													    # execute main function
    s.close()												    # close socket
