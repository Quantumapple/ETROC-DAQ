#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import visa
import threading
from command_interpret import *
from ETROC1_ArrayReg import *
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is composed of all the helper functions needed for I2C comms, FPGA, etc
'''
#--------------------------------------------------------------------------#
## define a receive data class
class Receive_data(threading.Thread):       # threading class
    def __init__(self, name, queue, num_file, num_line):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
        self.num_line = num_line
    
    def run(self):                          # num_file: set how many data file you want to get
        mem_data = []
        for files in range(self.num_file):
            mem_data = cmd_interpret.read_data_fifo(self.num_line)      # num_line: set how many lines per file you want
            print("{} is producing {} to the queue!".format(self.getName(), files))
            for i in range(self.num_line):
                self.queue.put(mem_data[i])
        print("%s finished!"%self.getName())
#--------------------------------------------------------------------------#
## define a write data class
class Write_data(threading.Thread):         # threading class
    def __init__(self, name, queue, num_file, num_line, store_dict, PhaseAdj, B_nam1, Pixel_Num1, QSel1, DAC_Value1, B_nam2, Pixel_Num2, QSel2, DAC_Value2, B_nam3, Pixel_Num3, QSel3, DAC_Value3):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
        self.num_line = num_line
        self.store_dict = store_dict
        self.phaseadj = PhaseAdj
        self.b_nam1 = B_nam1
        self.pixel_num1 = Pixel_Num1
        self.qsel1 = QSel1
        self.dac_value1 = DAC_Value1
        self.b_nam2 = B_nam2
        self.pixel_num2 = Pixel_Num2
        self.qsel2 = QSel2
        self.dac_value2 = DAC_Value2
        self.b_nam3 = B_nam3
        self.pixel_num3 = Pixel_Num3
        self.qsel3 = QSel3
        self.dac_value3 = DAC_Value3
    
    def run(self):
        for files in range(self.num_file):
            file_name="./%s/TDC_Data_PhaseAdj%d_%sP%d_QSel%d_DAC%d_%sP%d_QSel%d_DAC%d_%sP%d_QSel%d_DAC%d_%d.dat"%(self.store_dict, self.phaseadj, self.b_nam1, self.pixel_num1, self.qsel1, self.dac_value1, self.b_nam2, self.pixel_num2, self.qsel2, self.dac_value2, self.b_nam3, self.pixel_num3, self.qsel3, self.dac_value3, files)
            with open(file_name, 'w') as infile:
                for j in range(self.num_line):
                    val = self.queue.get()
                    infile.write('%d\n'%val)
            print("%s finished!" % self.getName())
            #print("%s\n"%file_name)
            with open(file_name,'r') as infile, open("./%s/TDC_Data_PhaseAdj%d_%sP%d_QSel%d_DAC%d_%sP%d_QSel%d_DAC%d_%sP%d_QSel%d_DAC%d_Split_%d.dat"%(self.store_dict, self.phaseadj, self.b_nam1, self.pixel_num1, self.qsel1, self.dac_value1, self.b_nam2, self.pixel_num2, self.qsel2, self.dac_value2, self.b_nam3, self.pixel_num3, self.qsel3, self.dac_value3, files), 'w') as outfile:
                    for line in infile.readlines():
                        if len(line) <= 2:
                            continue
                        TDC_data = []
                        for j in range(32):
                            TDC_data += [((int(line.split()[0]) >> j) & 0x1)]
                        ID = TDC_data[31] << 1 | TDC_data[30]
                        hitFlag = TDC_data[0]
                        TOT_Code1 = TDC_data[29] << 8 | TDC_data[28] << 7 | TDC_data[27] << 6 | TDC_data[26] << 5 | TDC_data[25] << 4 | TDC_data[24] << 3 | TDC_data[23] << 2 | TDC_data[22] << 1 | TDC_data[21]
                        TOA_Code1 = TDC_data[20] << 9 | TDC_data[19] << 8 | TDC_data[18] << 7 | TDC_data[17] << 6 | TDC_data[16] << 5 | TDC_data[15] << 4 | TDC_data[14] << 3 | TDC_data[13] << 2 | TDC_data[12] << 1 | TDC_data[11]
                        Cal_Code1 = TDC_data[10] << 9 | TDC_data[9] << 8 | TDC_data[8] << 7 | TDC_data[7] << 6 | TDC_data[6] << 5 | TDC_data[5] << 4 | TDC_data[4] << 3 | TDC_data[3] << 2 | TDC_data[2] << 1 | TDC_data[1]
                            # print(TOA_Code1, TOT_Code1, Cal_Code1, hitFlag)
                        if hitFlag!=0:
                            #if ID!=0 or TOA_Code1!=0 or TOT_Code1!=0 or Cal_Code1!=0:
                            if TOA_Code1!=0 or TOT_Code1!=0 or Cal_Code1!=0:
                                if ID!=2:
                                    outfile.write("%2d %3d %3d %3d %d\n"%(ID, TOA_Code1, TOT_Code1, Cal_Code1, hitFlag))
#--------------------------------------------------------------------------#
## IIC write slave device
# @param mode[1:0] : '0'is 1 bytes read or wirte, '1' is 2 bytes read or write, '2' is 3 bytes read or write
# @param slave[7:0] : slave device address
# @param wr: 1-bit '0' is write, '1' is read
# @param reg_addr[7:0] : register address
# @param data[7:0] : 8-bit write data
def iic_write(mode, slave_addr, wr, reg_addr, data):
    val = mode << 24 | slave_addr << 17 | wr << 16 | reg_addr << 8 | data
    cmd_interpret.write_config_reg(4, 0xffff & val)
    cmd_interpret.write_config_reg(5, 0xffff & (val>>16))
    time.sleep(0.01)
    cmd_interpret.write_pulse_reg(0x0001)           # reset ddr3 data fifo
    time.sleep(0.01)

#--------------------------------------------------------------------------#
## IIC read slave device
# @param mode[1:0] : '0'is 1 bytes read or wirte, '1' is 2 bytes read or write, '2' is 3 bytes read or write
# @param slave[6:0]: slave device address
# @param wr: 1-bit '0' is write, '1' is read
# @param reg_addr[7:0] : register address
def iic_read(mode, slave_addr, wr, reg_addr):
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
def Enable_FPGA_Descramblber(val):
    if val==1:
        print("Enable FPGA Descrambler")
    else:
        print("Disable FPGA Descrambler")
    cmd_interpret.write_config_reg(14, 0x0001 & val)       # write enable

#--------------------------------------------------------------------------#
## simple readout fucntion
#@param[in]: write_num: BC0 and L1ACC loop number, 0-65535
def simple_readout(write_num):
    cmd_interpret.write_config_reg(15, 0xffff & write_num)      # write enable
    cmd_interpret.write_pulse_reg(0x0080)                       # trigger pulser_reg[7]

#--------------------------------------------------------------------------#
## software clear fifo
def software_clear_fifo():
    cmd_interpret.write_pulse_reg(0x0002)                       # trigger pulser_reg[1]

#--------------------------------------------------------------------------#
## Enable channel
## 4 bit binary, WXYZ
## W - ch3
## X - ch2
## Y - ch1
## Z - ch0
## Note that the input needs to be a 16 bit rep as hex
def active_channels(key = 0x0003): 
    cmd_interpret.write_config_reg(15, key)

#--------------------------------------------------------------------------#
## TimeStamp and Testmode
## 0x0000: Disable Testmode & Enable TimeStamp
## 0x0001: Disable Testmode & Disable TimeStamp
## 0x0010: Enable Testmode & Enable TimeStamp
## 0x0011: Enable Testmode & Disable TimeStamp
## Note that the input needs to be a 16 bit rep as hex
def timestamp(key=0x0000):
    cmd_interpret.write_config_reg(13, key) 

#--------------------------------------------------------------------------#