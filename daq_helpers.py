#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import visa
import threading
import numpy as np
import matplotlib
# matplotlib.use('WebAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.axes_grid1 import make_axes_locatable
from queue import Queue
from collections import deque
import queue
from command_interpret import *
from ETROC1_ArrayReg import *
from translate_data import *
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari
@date: 2023-03-24
This script is composed of all the helper functions needed for I2C comms, FPGA, etc
'''
#--------------------------------------------------------------------------#
# define a receive data class
class Receive_data(threading.Thread):                                   # threading class
    def __init__(self, name, queue, cmd_interpret, num_file, num_line, num_fifo_read):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.cmd_interpret = cmd_interpret
        self.num_file = num_file
        self.num_line = num_line
        self.num_fifo_read = num_fifo_read
    
    def run(self):
        mem_data = []
        for files in range(self.num_file):
            mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)      # max allowed by read_memory is 65535
            print("{} is reading data and pushing to the queue...".format(self.getName()))
            for mem_line in mem_data:
                self.queue.put(mem_line)  
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
# define a write data class
class Write_data(threading.Thread):
    def __init__(self, name, queue, cmd_interpret, num_file, num_line, num_fifo_read, timestamp, store_dict, binary_only, make_plots, board_ID):
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
        self.board_ID = board_ID
        self.queue_ch = [deque() for i in range(4)]                # Inelegant solution making a deque for each channel

    def run(self):
        mem_data = []
        for files in range(self.num_file):
            file_name="./%s/TDC_Data_%d.dat"%(self.store_dict, files)
            with open(file_name, 'w') as infile, open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, files), 'w') as outfile:
                print("{} is reading data and writing file {} and translation...".format(self.getName(), files))
                i = 0
                start_time = time.time()
                while i < self.num_line:
                    mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)   # max allowed by read_memory is 65535
                    for j in range(len(mem_data)):
                        if int(mem_data[j]) == 0: continue
                        binary = format(int(mem_data[j]), '032b')
                        infile.write('%s\n'%binary)
                        if(self.binary_only == False):
                            TDC_data, write_flag = etroc_translate_binary(binary, self.timestamp, self.queue_ch, self.board_ID)
                            if(write_flag==1):
                                outfile.write("%s\n"%TDC_data)
                                i = i+1
                                if(TDC_data[0:6]=='ETROC1'):
                                    if(self.make_plots): self.queue.put(TDC_data)
                            elif(write_flag==2):
                                TDC_len = len(TDC_data)
                                TDC_header_index = -1
                                for j,TDC_line in enumerate(TDC_data):
                                    if(TDC_line=="HEADER_KEY"):
                                        if(TDC_header_index<0):
                                            TDC_header_index = j
                                        else:
                                            print("ERROR! Found more than two headers in data block!!")
                                        continue
                                    outfile.write("%s\n"%TDC_line)
                                    if(TDC_line[9:13]!='DATA'): continue
                                    if(self.make_plots): self.queue.put(TDC_line)
                                i = i+(TDC_len-TDC_header_index)
                            else:
                                pass
                        
                        start_time = time.time()
                        # print(i)
                    if(time.time()-start_time > 30):
                        print("BREAKING OUT OF WRITE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST WRITE!!!")
                        break
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
class Read_Write_data(threading.Thread):
    def __init__(self, name, queue, cmd_interpret, num_file, num_line, num_fifo_read, timestamp, store_dict, binary_only, make_plots, board_ID):
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
        self.board_ID = board_ID
        self.queue_ch = [deque() for i in range(4)]                # Inelegant solution making a deque for each channel

    def run(self):
        mem_data = []
        for files in range(self.num_file):
            file_name="./%s/TDC_Data_%d.dat"%(self.store_dict, files)
            with open(file_name, 'w') as infile, open("./%s/TDC_Data_translated_%d.dat"%(self.store_dict, files), 'w') as outfile:
                print("{} is reading data and writing file {} and translation...".format(self.getName(), files))
                i = 0
                start_time = time.time()
                while i < self.num_line:
                    mem_data = self.cmd_interpret.read_data_fifo(self.num_fifo_read)   # max allowed by read_memory is 65535
                    for j in range(len(mem_data)):
                        if int(mem_data[j]) == 0: continue
                        binary = format(int(mem_data[j]), '032b')
                        infile.write('%s\n'%binary)
                        if(self.binary_only == False):
                            TDC_data, write_flag = etroc_translate_binary(binary, self.timestamp, self.queue_ch, self.board_ID)
                            if(write_flag==1):
                                outfile.write("%s\n"%TDC_data)
                                i = i+1
                                if(TDC_data[0:6]=='ETROC1'):
                                    if(self.make_plots): self.queue.put(TDC_data)
                            elif(write_flag==2):
                                TDC_len = len(TDC_data)
                                TDC_header_index = -1
                                for j,TDC_line in enumerate(TDC_data):
                                    if(TDC_line=="HEADER_KEY"):
                                        if(TDC_header_index<0):
                                            TDC_header_index = j
                                        else:
                                            print("ERROR! Found more than two headers in data block!!")
                                        continue
                                    outfile.write("%s\n"%TDC_line)
                                    if(TDC_line[9:13]!='DATA'): continue
                                    if(self.make_plots): self.queue.put(TDC_line)
                                i = i+(TDC_len-TDC_header_index)
                            else:
                                pass
                        
                        start_time = time.time()
                        # print(i)
                    if(time.time()-start_time > 30):
                        print("BREAKING OUT OF WRITE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST WRITE!!!")
                        break
        print("%s finished!"%self.getName())

#--------------------------------------------------------------------------#
class DAQ_Plotting(threading.Thread):
    def __init__(self, name, queue, timestamp, store_dict, pixel_address, board_type, board_size, plot_queue_time):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.timestamp = timestamp
        self.store_dict = store_dict
        self.pixel_address = pixel_address
        self.board_type = board_type
        self.board_size = board_size
        self.plot_queue_time = plot_queue_time

    def run(self):
        t = threading.current_thread()                          # Local reference of THIS thread object
        t.alive = True                                          # Thread is alive by default

        ch0 = np.zeros((int(np.sqrt(self.board_size[0])),int(np.sqrt(self.board_size[0])))) 
        ch1 = np.zeros((int(np.sqrt(self.board_size[1])),int(np.sqrt(self.board_size[1])))) 
        ch2 = np.zeros((int(np.sqrt(self.board_size[2])),int(np.sqrt(self.board_size[2])))) 
        ch3 = np.zeros((int(np.sqrt(self.board_size[3])),int(np.sqrt(self.board_size[3])))) 

        plt.ion()
        # fig, ((ax0, ax1), (ax2, ax3)) = plt.subplots(2,2, dpi=75)
        fig = plt.figure(dpi=75, figsize=(8,8))
        gs = fig.add_gridspec(8,8)
        ax0 = fig.add_subplot(gs[0:int(np.sqrt(self.board_size[0]))//4, 0:int(np.sqrt(self.board_size[0]))//4])
        ax1 = fig.add_subplot(gs[4:4+int(np.sqrt(self.board_size[1]))//4, 0:int(np.sqrt(self.board_size[1]))//4])
        ax2 = fig.add_subplot(gs[0:int(np.sqrt(self.board_size[2]))//4, 4:4+int(np.sqrt(self.board_size[2]))//4])
        ax3 = fig.add_subplot(gs[4:4+int(np.sqrt(self.board_size[3]))//4, 4:4+int(np.sqrt(self.board_size[3]))//4])

        if(len(self.board_type)>0):
            ax0.set_title('Channel 0: ETROC {:d}'.format(self.board_type[0]))       
        if(len(self.board_type)>1):
            ax1.set_title('Channel 1: ETROC {:d}'.format(self.board_type[1]))
        if(len(self.board_type)>2):
            ax2.set_title('Channel 2: ETROC {:d}'.format(self.board_type[2]))
        if(len(self.board_type)>3):
            ax3.set_title('Channel 3: ETROC {:d}'.format(self.board_type[2]))
        
        img0 = ax0.imshow(ch0, interpolation='none')
        ax0.set_aspect('equal')
        img1 = ax1.imshow(ch1, interpolation='none')
        ax1.set_aspect('equal')
        img2 = ax2.imshow(ch2, interpolation='none')
        ax2.set_aspect('equal')
        img3 = ax3.imshow(ch3, interpolation='none')
        ax3.set_aspect('equal')

        ax0.get_xaxis().set_visible(False)
        ax0.get_yaxis().set_visible(False)
        # ax0.set_frame_on(False)
        ax1.get_xaxis().set_visible(False)
        ax1.get_yaxis().set_visible(False)
        # ax1.set_frame_on(False)
        ax2.get_xaxis().set_visible(False)
        ax2.get_yaxis().set_visible(False)
        # ax2.set_frame_on(False)
        ax3.get_xaxis().set_visible(False)
        ax3.get_yaxis().set_visible(False)
        # ax3.set_frame_on(False)

        divider = make_axes_locatable(ax0)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(img0, cax=cax, orientation='vertical')
        divider = make_axes_locatable(ax1)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(img1, cax=cax, orientation='vertical')
        divider = make_axes_locatable(ax2)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(img2, cax=cax, orientation='vertical')
        divider = make_axes_locatable(ax3)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        fig.colorbar(img3, cax=cax, orientation='vertical')

        # plt.tight_layout()
        # plt.draw()
        # def init():etroc_translate_binary
        #     line.set_data([], [])
        #     return line,
        # def animate(i):
        #     x = np.linspace(0, 4, 1000)
        #     y = np.sin(2 * np.pi * (x - 0.01 * i))
        #     line.set_data(x, y)
        #     return line,

        # anim = FuncAnimation(fig, animate, init_func=init,
        #                                frames=200, interval=20, blit=False)

        # anim.save('sine_wave.gif', writer='imagemagick')

        while(True):                                            # If alive is set to false

            ch0 = np.zeros((int(np.sqrt(self.board_size[0])),int(np.sqrt(self.board_size[0])))) 
            ch1 = np.zeros((int(np.sqrt(self.board_size[1])),int(np.sqrt(self.board_size[1])))) 
            ch2 = np.zeros((int(np.sqrt(self.board_size[2])),int(np.sqrt(self.board_size[2])))) 
            ch3 = np.zeros((int(np.sqrt(self.board_size[3])),int(np.sqrt(self.board_size[3])))) 
            img0.set_data(ch0)
            img0.autoscale()
            img1.set_data(ch1)
            img1.autoscale()
            img2.set_data(ch2)
            img2.autoscale()
            img3.set_data(ch3)
            img3.autoscale()

            if not t.alive:
                print("Plotting Thread detected alive=False")
                break                                           # Break out of for loop

            start_time = time.time()
            delta_time = 0
            mem_data = []
            while(delta_time < self.plot_queue_time):
                try:
                    task = self.queue.get(False)                # Empty exception is thrown right away
                    mem_data.append(task)
                except queue.Empty:                             # Handle empty queue here
                    pass
                # else:                                         # Handle task here and call q.task_done()
                delta_time = time.time() - start_time

            # NEED TO DOUBLE CHECK PIXEL LAYOUT
            for line in mem_data:
                words = line.split()
                if(words[0]=="ETROC1"):
                    if(words[1]=="0"):   ch0[self.pixel_address[0]%int(np.sqrt(self.board_size[0])),self.pixel_address[0]//int(np.sqrt(self.board_size[0]))] += 1
                    elif(words[1]=="1"): ch1[self.pixel_address[1]%int(np.sqrt(self.board_size[1])),self.pixel_address[1]//int(np.sqrt(self.board_size[1]))] += 1
                    elif(words[1]=="2"): ch2[self.pixel_address[2]%int(np.sqrt(self.board_size[2])),self.pixel_address[2]//int(np.sqrt(self.board_size[2]))] += 1
                    elif(words[1]=="3"): ch3[self.pixel_address[3]%int(np.sqrt(self.board_size[3])),self.pixel_address[3]//int(np.sqrt(self.board_size[3]))] += 1
                elif(words[0]=="ETROC2"):
                    if(words[2]!="DATA"): continue
                    if(words[1]=="0"):   ch0[int(words[8]),int(words[6])] += 1
                    elif(words[1]=="1"): ch1[int(words[8]),int(words[6])] += 1
                    elif(words[1]=="2"): ch2[int(words[8]),int(words[6])] += 1
                    elif(words[1]=="3"): ch3[int(words[8]),int(words[6])] += 1
                elif(words[0]=="ETROC3"): continue
                else: continue
                

            img0.set_data(ch0)
            img0.autoscale()
            img1.set_data(ch1)
            img1.autoscale()
            img2.set_data(ch2)
            img2.autoscale()
            img3.set_data(ch3)
            img3.autoscale()
            # ax0.relim()
            # ax0.autoscale_view()
            # ax1.relim()
            # ax1.autoscale_view()
            # ax2.relim()
            # ax2.autoscale_view()
            # ax3.relim()
            # ax3.autoscale_view()
            # plt.tight_layout()
            fig.canvas.draw_idle()
            plt.pause(0.01)
            print("This pass of the Plotting function loop parsed {:d} lines of output".format(len(mem_data)))

        plt.ioff()
        plt.show()

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
## Following is binary key, 4 bit binary WXYZ
## 0000: Enable  Testmode & Enable TimeStamp
## 0001: Enable  Testmode & Disable TimeStamp
## 0010: Disable Testmode & Enable TimeStamp
## 0011: Disable Testmode & Disable TimeStamp                  ##BUGGED as of 03-04-2023
## Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
def timestamp(cmd_interpret, key=0x0000):
    cmd_interpret.write_config_reg(13, key) 

#--------------------------------------------------------------------------#