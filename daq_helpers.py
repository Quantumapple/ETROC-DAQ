#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import visa
import threading
from command_interpret import *
from ETROC1_ArrayReg import *
from translate_data import *
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is composed of all the helper functions needed for I2C comms, FPGA, etc
'''
#--------------------------------------------------------------------------#
## define a receive data class
class Receive_data(threading.Thread):                                   # threading class
    def __init__(self, name, queue, num_file, num_line, cmd_interpret):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
        self.num_line = num_line
        self.cmd_interpret = cmd_interpret
    
    def run(self):                                                      # num_file: set how many data file you want to get
        mem_data = []
        for files in range(self.num_file):
            mem_data = self.cmd_interpret.read_data_fifo(self.num_line)      # num_line: set how many lines per file you want
            print("{} is producing {} to the queue!".format(self.getName(), files))
            for i in range(self.num_line):
                self.queue.put(mem_data[i])  
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
## define a write data class
class Write_data(threading.Thread):                                     # threading class
    def __init__(self, name, queue, num_file, num_line, timestamp, store_dict, binary_only):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
        self.num_line = num_line
        self.timestamp = timestamp
        self.store_dict = store_dict
        self.binary_only = binary_only
    
    def run(self):
        for files in range(self.num_file):
            file_name="./%s/TDC_Data_%d.dat"%(self.store_dict, files)
            with open(file_name, 'w') as infile:
                for j in range(self.num_line):
                    val = self.queue.get()
                    # if int(val) == 0:
                    #     continue
                    binary = format(int(val), '032b')
                    infile.write('%s\n'%binary)
            print("%s finished!" % self.getName())
            if(self.binary_only == False):
                with open(file_name,'r') as infile, open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, files), 'w') as outfile:
                    for line in infile.readlines():
                        TDC_data = etroc_translate_binary(line, timestamp=self.timestamp)
                        outfile.write("%s\n"%TDC_data)

#--------------------------------------------------------------------------#
class Read_Write_data(threading.Thread):
    def __init__(self, name, queue, cmd_interpret, num_file, num_line, num_fifo_read, timestamp, store_dict, binary_only, make_plots):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.cmd_interpret = cmd_interpret
        self.num_file = num_file
        self.num_line = num_line
        self.num_fifo_read = num_fifo_read
        self.timestamp = timestamp
        self.store_dict = store_dict
        self.binary_only = binary_only
        self.make_plots = make_plots

    def run(self):
        mem_data = []
        for files in range(self.num_file):
            file_name="./%s/TDC_Data_%d.dat"%(self.store_dict, files)
            with open(file_name, 'w') as infile, open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, files), 'w') as outfile:
                print("{} is reading data and writing file {} and translation...".format(self.getName(), files))
                i = 0
                while i < self.num_line:
                    mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)   # max allowed by read_memory is 65535
                    # print(len(mem_data)," ", mem_data,"\n")
                    for j in range(len(mem_data)):
                        if int(mem_data[j]) == 0: continue
                        # self.queue.put(mem_data[i])
                        binary = format(int(mem_data[j]), '032b')
                        infile.write('%s\n'%binary)
                        if(self.binary_only == False):
                            TDC_data = etroc_translate_binary(binary, timestamp=self.timestamp)
                            outfile.write("%s\n"%TDC_data)
                            if(self.make_plots): self.queue.put(TDC_data)  
                        i = i+1 
                        # print(i)
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
class DAQ_Plotting(threading.Thread):
    def __init__(self, name, queue, timestamp, store_dict, pixel_address):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.timestamp = timestamp
        self.store_dict = store_dict
        self.pixel_address = pixel_address

    def run(self):
        # mem_data = []
        # val = self.queue.get()
        # Local reference of THIS thread object
        t = threading.current_thread()
        # Thread is alive by default
        t.alive = True
        while(True):
            # If alive is set to false
            if not t.alive:
                print("Plotting Thread detected alive=False")
                # Break out of for loop
                break
            print("Sleeping for 5 seconds...")
            time.sleep(5)
            print("Waited 5 seconds! \n")
        # Thread then stops running
        print("Plotting Thread broke out of loop")


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
def Enable_FPGA_Descramblber(val, cmd_interpret):
    if val==1:
        print("Enable FPGA Descrambler")
    else:
        print("Disable FPGA Descrambler")
    cmd_interpret.write_config_reg(14, 0x0001 & val)                          # write enable

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
## TimeStamp and Testmode
## 0x0000: Disable Testmode & Enable TimeStamp
## 0x0001: Disable Testmode & Disable TimeStamp
## 0x0010: Enable Testmode & Enable TimeStamp
## 0x0011: Enable Testmode & Disable TimeStamp
## Note that the input needs to be a 4-digit 16 bit hex
def timestamp(cmd_interpret, key=0x0000):
    cmd_interpret.write_config_reg(13, key) 

#--------------------------------------------------------------------------#