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
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
from optparse import OptionParser

from command_interpret import *
from ETROC1_ArrayReg import *
from daq_helpers import *
from board_details import *
from config_etroc1 import *
from tqdm import tqdm

from usb_iss import UsbIss, defs
from pathlib import Path
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
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	                        # initial socket
    except socket.error:
        print("Failed to create socket!")
        sys.exit()
    try:
        s.connect((options.hostname, port))								                        # connect socket
    except socket.error:
        print("failed to connect to ip " + options.hostname)
        sys.exit()
    cmd_interpret = command_interpret(s)
    main(options, cmd_interpret, IPC_queue)
    s.close()

## main function
def main(options, cmd_interpret, IPC_queue = None):

    num_boards = len(board_type)
    Pixel_board = options.pixel_address
    QSel_board  = options.pixel_charge

    if(options.firmware):
        if(not options.old_data_format):
            print("Setting firmware...")
            print("Active channels: ", active_channels_key)
            active_channels(cmd_interpret, key = active_channels_key)
            print("Timestamp: ", options.timestamp)
            timestamp(cmd_interpret, key = options.timestamp)
        # Enable_FPGA_Descramblber(1, cmd_interpret)
        Enable_FPGA_Descramblber(cmd_interpret, options.polarity)

    # if(options.reset_pulse_register):
    #     print("\n", "Resetting Pulse Register 0x0002")
    #     software_clear_fifo(cmd_interpret)

    if(options.inspect_serial_output):		
        # _ 2b data rate 3b LED configuration 1b testmode 1b timestamp
        testregister = cmd_interpret.read_config_reg(13)
        print('\n')
        print("Written into Reg 13: ", format(testregister, '016b'))
        print('\n')		              
        testregister_2 = cmd_interpret.read_status_reg(2)
        print("Status Reg Addr 2  : ", format(testregister_2, '016b'))
        testregister_3 = cmd_interpret.read_status_reg(3)
        print("Status Reg Addr 3  : ", format(testregister_3, '016b'))
        print("Status Reg Addr 2+3: ", (format(testregister_2, '016b'))+
        (format(testregister_3, '016b')))
        print('\n')

        fixed_32 = 0xabaaafaa
        fixed_16 = int(format(fixed_32,  '032b')[-16:], base=2)
        fixed_8  = int(format(fixed_32,  '032b')[-8:],  base=2)

        quad_8  = ""
        for elem in format(fixed_8,  '08b'): quad_8 = quad_8 + elem + elem + elem + elem
        doub_16 = ""
        for elem in format(fixed_16,  '016b'): doub_16 = doub_16 + elem + elem

        print("Processed Data Checks, look only at relavant bit length")
        print("Fixed Pattern 8    : ", format(fixed_8,  '08b'))
        if(format(fixed_8,  '08b') in format(testregister_2, '016b') and 
        format(fixed_8,  '08b') in format(testregister_3, '016b')):
            print("08 bit pattern found in both Status Reg 2 & 3")
        elif(format(fixed_8,  '08b') in format(testregister_2, '016b') or 
        format(fixed_8,  '08b') in format(testregister_3, '016b')):
            print("08 bit pattern found in ONLY ONE of Status Reg 2 & 3!")
        else: print("08 bit pattern not found in any of the Status Reg 2 or 3!")

        print("Fixed Pattern 16   : ", format(fixed_16, '016b'))
        if(format(fixed_16,  '016b') in format(testregister_2, '016b')*2 and 
        format(fixed_16,  '016b') in format(testregister_3, '016b')*2):
            print("16 bit pattern found in both Status Reg 2 & 3")
        elif(format(fixed_16,  '016b') in format(testregister_2, '016b')*2 or 
        format(fixed_16,  '016b') in format(testregister_3, '016b')*2):
            print("16 bit pattern found in ONLY ONE of Status Reg 2 & 3!")
        else: print("16 bit pattern not found in any of the Status Reg 2 or 3!")

        print("Fixed Pattern 32   : ", format(fixed_32, '032b'))
        if(format(fixed_32,  '032b') in (format(testregister_2, '016b')+format(testregister_3, '016b'))*2):
            print("32 bit pattern found in Status Reg 2 + 3")
        else: print("32 bit pattern not found in Status Reg 2 + 3!")

        print('\n')
        print("Raw Data Checks")
        print("Inflated 8-bit pattern : ", quad_8)
        print("Inflated 16-bit pattern: ", doub_16)
        if(quad_8 in (format(testregister_2, '016b')+format(testregister_3, '016b'))*2):
            print("Quadrupled 8 bit pattern found in Status Reg 2 + 3")
        else: print("Quadrupled 8 bit pattern not found in Status Reg 2 + 3!")
        if(doub_16 in (format(testregister_2, '016b')+format(testregister_3, '016b'))*2):
            print("Doubled 16 bit pattern found in Status Reg 2 + 3")
        else: print("Doubled 16 bit pattern not found in Status Reg 2 + 3!")
        print('\n')

    if(options.do_fc):
        register_11(cmd_interpret, key = register_11_key)
        register_12(cmd_interpret, key = register_12_key)
        fc_signal_start(cmd_interpret)
    if(options.memo_fc):   
        start_L1A(cmd_interpret)

    if(options.memo_fc_start_onetime_ws):
        start_onetime_L1A_WS(cmd_interpret)

    if(options.ws_i2c_initialization):
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        devAddr = 0x60
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00001   ## pixelConfig[15:8]    default:0x26
        data = 0x3e   # Qinjen;  Qinj = 30
        # data = 0x3b    # Qinjen; Qinj = 28
        # data = 0x37  # Qinjen; Qinj = 24
        # data = 0x33   # Qinjen;  Qinj = 20
        # data = 0x26
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])

        devAddr = 0x60
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00000   ## pixelConfig[7:0] default:0x5C (pixelConfig[4:2]:IBSel[2:0] = 0b111)
        # data = 0x5c
        data = 0x1c  # max gain; default power
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])
        #########################TF
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00101   ## pixelConfig[7:0] default:0x5C (pixelConfig[4:2]:IBSel[2:0] = 0b111)
        # data = 0x5c
        data = 0x0c  # max gain; default power
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])

        # reg_addr = 0x0003   ## PeriCfg3
        # data = 0x38
        # iic_write(devAddr, reg_addr, reg_bits, data, cmd_interpret)


        #########################


        slaveA_addr_WS = 0x40
        ### 1F
        reg_add = 0x1f
        data = 0x22 ### clk_gen rst & mem rst
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

        data = 0x0b  ### fc ws_stop; bypass
        # data = 0x2b  ### external WS enable
        # data = 0x8b ### fc ws_stop; vga
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

        ### 0F
        reg_add = 0x0f
        data = 0x00
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])    
        ### 0E
        reg_add = 0x0e
        data = 0x00
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])  
        ### 0D
        reg_add = 0x0d
        data = 0x10  # default ctrl == 10
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

    
    if(options.fc_ws_start):
        WS_onetime_ws_start(cmd_interpret)
    
    if(options.fc_ws_stop):
        WS_onetime_ws_stop(cmd_interpret)

    if(options.ws_onetime_charge_injection):
        WS_start_charge_injection_stop(cmd_interpret)

    # if(options.ws_reconstruction):
    #     WS_start_charge_injection_stop(cmd_interpret)

    if(options.ws_memory_readout):
        # COM_Port = "COM5"
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        def WS_memory_read(file_name):
            slaveA_addr_WS = 0x40

            reg_add = 0x1f
            data = 0x2f  ### bypass mode
            # data = 0xaf  ### vga mode
            # data = 0xf  ### fc ws_stop; bypass
            # data = 0x4f  ### fc 400ns; bypass
            # data = 0x8f ### ws_stop; vga

            iss.i2c.write(slaveA_addr_WS, reg_add, [data])

            reg_rd_add_MSB = 0x1d
            reg_rd_add_LSB = 0x1c
            dout_MSB_add = 0x21
            dout_LSB_add = 0x20
            file1 = open(file_name, "w")
            # for i in tqdm(range(1024)):
            for i in range(1024):
                rd_add_MSB = i // 4
                rd_add_LSB2 = i % 4
                rd_add_LSB = rd_add_LSB2 * 64
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_MSB, rd_add_MSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_MSB, [rd_add_MSB])
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_LSB, rd_add_LSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_LSB, [rd_add_LSB])

                dout_MSB = []
                # dout_MSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_MSB_add, cmd_interpret)
                dout_MSB = iss.i2c.read(slaveA_addr_WS, dout_MSB_add, 1)
                dout_LSB = []
                # dout_LSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_LSB_add, cmd_interpret)
                dout_LSB = iss.i2c.read(slaveA_addr_WS, dout_LSB_add, 1)
                # print(i, bin(rd_add_MSB), bin(rd_add_LSB2), dout_MSB, dout_LSB/4)
                print(i, dout_MSB[0], dout_LSB[0]/4)
                dout_to_file = str(i) + "  " + str(dout_MSB[0]) + "  " + str(dout_LSB[0]) + "\n"
                file1.writelines(dout_to_file)
            file1.close()

            slaveA_addr_WS = 0x40
            reg_add = 0x1f
            data = 0x0b         # set rd_en_I2C off //TF_08_01
            # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret)
            iss.i2c.write(slaveA_addr_WS, reg_add, [data]) 

        WS_memory_read("WS_memory_data_B5_0808_bypass_BX3_BX8_BX13_Q30_linux_fc_1.txt");   
        
        # slaveA_addr_WS = 0x40
        # reg_add = 0x1f
        # data = 0x0b  ### disable read

        # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret)
        # iss.i2c.write(slaveA_addr_WS, reg_add, [data]) 

    if(options.ws_reconstruction):

        # current_directory = os.path.dirname(os.path.abspath(__file__))
        file_name = "WS_memory_data_B5_0808_bypass_BX3_BX8_BX13_Q30_linux_fc_1.txt"
        # file_path = os.path.join(current_directory, file_name)
        #print(os.path.abspath(file_name))

        with open(file_name, 'r') as f:
            b1 = np.loadtxt(f, dtype=int).T

        data_1 = b1[1, :]
        data_2 = b1[2, :]

        data1 = data_1 % 128
        k = None
        for i in range(1024):
            if data_1[i] > 127:
                k = i
                break

        #print(np.where(data_1 > 127)[0])
        end_ind = k - 128 * 7

        data_1st_tem = np.zeros((1024, 8), dtype=int)
        data_2st_tem = np.zeros((1024, 8), dtype=int)

        for i in range(1024):
            data_1_tem = np.binary_repr(data_1[i], width=8)
            l1 = len(data_1_tem)
            data_1st_tem[i] = [int(d) for d in data_1_tem.zfill(8)]
            data_2_tem = np.binary_repr(data_2[i], width=8)
            l1 = len(data_2_tem)
            data_2st_tem[i] = [int(d) for d in data_2_tem.zfill(8)]

        data_1st = data_1st_tem[:, 1:7]
        data_2st = np.hstack((data_1st_tem[:, 7].reshape(-1, 1), data_2st_tem[:, 0:6]))

        gain = 0.04 / 5 * 8.5 *1.25
        Aout_1st = np.zeros(1024)
        Aout_2st = np.zeros(1024)
        for i in range(1024):
            Aout_1st[i] = 32 * data_1st[i, 0] + 16 * data_1st[i, 1] + 8 * data_1st[i, 2] + \
                4 * data_1st[i, 3] + 2 * data_1st[i, 4] + data_1st[i, 5]
            # Aout_1st = int('0b'+data_1_tem[i,1:7],0)

            Aout_2st[i] = 24 * data_2st[i, 0] + 16 * data_2st[i, 1] + 10 * data_2st[i, 2] + \
                6 * data_2st[i, 3] + 4 * data_2st[i, 4] + 2 * data_2st[i, 5] + data_2st[i, 6]

        Aout = Aout_1st - gain * Aout_2st

        Aout_ch = np.zeros((8, 128))
        Aout_ch_align = np.zeros((8, 128))

        for ch in range(1, 9):
            Aout_ch[8 - ch, :] = Aout[(ch - 1) * 128: ch * 128]


        for ch in range(1, 9):
            if end_ind == 128:
                Aout_ch_align[ch - 1, :] = Aout_ch[ch - 1, :]
            else:
                Aout_ch_align[ch - 1, :128 - end_ind] = Aout_ch[ch - 1, end_ind:]
                Aout_ch_align[ch - 1, 129 - end_ind - 1: 128] = Aout_ch[ch - 1, :end_ind]

        # plt.figure()
        # for i in range(8):
        #     plt.subplot(8, 1, i + 1)
        #     plt.plot(Aout_ch_align[i])
        # plt.ylim([0, 2.4])

        Aout_8ch = np.zeros(1024)
        for i in range(1024):
            Aout_8ch[i] = Aout_ch_align[(i - 1) % 8, (i - 1) // 8]

        # for i in range(128):
        #     Aout_8ch[8 * i - 0] = Aout_ch_align[7, i]
        #     Aout_8ch[8 * i - 1] = Aout_ch_align[6, i]
        #     Aout_8ch[8 * i - 2] = Aout_ch_align[5, i]
        #     Aout_8ch[8 * i - 3] = Aout_ch_align[4, i]
        #     Aout_8ch[8 * i - 4] = Aout_ch_align[3, i]
        #     Aout_8ch[8 * i - 5] = Aout_ch_align[2, i]
        #     Aout_8ch[8 * i - 6] = Aout_ch_align[1, i]
        #     Aout_8ch[8 * i - 7] = Aout_ch_align[0, i]

        Aout_8ch_v = -(Aout_8ch - (31.5 - gain * 31.5)) * 1.2 / 32
        N = np.arange(1024)
        t = N * 1 / 2.56

        highest_values = np.sort((Aout_8ch_v))[-2:]
        print("两个pulse的峰值: ", highest_values)

        plt.figure()
        plt.plot(t, Aout_8ch_v, linewidth = 0.5 )
        plt.ylim([-0.3, 0.1])
        # plt.ylim([-1, 0.4])
        plt.xlim([0, 400])
        plt.ylabel("Voltage(V)")
        plt.xlabel("Time(ns)")
        plt.show()

        #print("Mean of Aout_8ch_v ", np.mean(Aout_8ch_v))
        #print("Variance of Aout_8ch_v ", np.var(Aout_8ch_v))
        #print('\n')

        # high_pulse_indices = np.where(Aout_8ch_v > -0.22)[0]
        

    if(options.memo_fc_start_periodic_ws):
        # COM_Port = "COM5"
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        ###################### I2C Initialization
        def WS_I2C_Initial(slaveA_addr_WS):

            devAddr = 0x60
            reg_bits = 16
            reg_addr = 0b100_1110_0000_00001   ## pixelConfig[15:8] 0x01     Qinjen
            # data = 0x3f   # Qinjen;  Qinj = 32
            # data = 0x39   # Qinjen;  Qinj = 26
            # data = 0x37   # Qinjen;  Qinj = 24
            # data = 0x2f   # Qinjen;  Qinj = 16
            data = 0x33   # Qinjen;  Qinj = 20
            # data = 0x1f   # Qinj disable; max Qinj
            # data = 0x26
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)))


            devAddr = 0x60
            reg_bits = 16
            reg_addr = 0b101_1110_0000_00000   ## pixelConfig[7:0] default:0x5C (pixelConfig[4:2]:IBSel[2:0] = 0b111)
            # data = 0x5c
            data = 0x1c  # max gain; default power
            # data = 0x00  # max gain; max power
            # data = 0x40
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)))

            ### 1F
            reg_add = 0x1f
            data = 0x22 ### clk_gen rst & mem rst
            # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret)
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))
          
            # data = 0x2b  ### ext bypass mode
            # data = 0xab  ### ext vga mode
            # data = 0x4b  ### fc 400ns; bypass
            data = 0x0b  ### fc ws_stop; bypass
            # data = 0x8b ### fc ws_stop; vga
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))
            ### 0F
            reg_add = 0x0f
            data = 0x00
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    
            ### 0E
            reg_add = 0x0e
            data = 0x00
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1))) 
            ### 0D
            reg_add = 0x0d
            data = 0x10  # default ctrl == 10
            # data = 0x00  # ctrl for mem effect reduction == 00
            # data = 0x18  # ctrl for mem effect reduction == 11
            # data = 0x30  # short DAC enable
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1))) 

            start_periodic_L1A_WS(cmd_interpret)

        def WS_comp_cali(slaveA_addr_WS):
            ### 0D        <7:5>: EN,RST,SHORT_DAC
            reg_add = 0x0d
            data = 0x30   # short DAC
            # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret) 
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))           

            data = 0x70   # RST
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    

            time.sleep(0.01)

            data = 0x30   # no RST
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    

            time.sleep(0.01)

            data = 0xb0   # EN
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    

            time.sleep(1)

            data = 0x30   # DISABLE
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    

            time.sleep(0.01)

            data = 0x10   # no SHORT
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))    

        ######################### WS memory readout

        def WS_memory_read(slaveA_addr_WS):

            reg_add = 0x1f
            # data = 0x2f  ### bypass mode
            # data = 0xaf  ### vga mode
            data = 0x0f  ### fc ws_stop; bypass
            # data = 0x4f  ### fc 400ns; bypass
            # data = 0x8f ### ws_stop; vga
            iss.i2c.write(slaveA_addr_WS, reg_add, [data])
            print('0x{0:02x}'.format(reg_add), '0x{0:02x}'.format(iss.i2c.read(slaveA_addr_WS, reg_add, byte_count = 1)))  

            reg_rd_add_MSB = 0x1d
            reg_rd_add_LSB = 0x1c
            dout_MSB_add = 0x21
            dout_LSB_add = 0x20
            file1 = open("WS_17_vga_stop_0728_Q20_DP_vdda1p2_nocali_3.txt", "w")
            for i in range(1024):
                rd_add_MSB = i // 4
                rd_add_LSB2 = i % 4
                rd_add_LSB = rd_add_LSB2 * 64
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_MSB, rd_add_MSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_MSB, [rd_add_MSB])
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_LSB, rd_add_LSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_LSB, [rd_add_LSB])

                dout_MSB = []
                # dout_MSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_MSB_add, cmd_interpret)
                dout_MSB = iss.i2c.read(slaveA_addr_WS, dout_MSB_add, byte_count = 1)
                dout_LSB = []
                # dout_LSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_LSB_add, cmd_interpret)
                dout_LSB = iss.i2c.read(slaveA_addr_WS, dout_LSB_add, byte_count = 1)
                # print(i, bin(rd_add_MSB), bin(rd_add_LSB2), dout_MSB, dout_LSB/4)
                print(i, dout_MSB, dout_LSB/4)
                dout_to_file = str(i) + "  " + str(dout_MSB) + "  " + str(dout_LSB) + "\n"
                file1.writelines(dout_to_file)
            file1.close()

        slaveA_addr_WS = 0x40
        WS_I2C_Initial(slaveA_addr_WS)
        # WS_comp_cali(slaveA_addr_WS)
        # WS_memory_read(slaveA_addr_WS)

    if(options.verbose):
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
    
    
    if(options.etroc2_i2c):
        # COM_Port = "COM5"
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        print('etroc2_i2c_configuration...')
        devAddr = 0x60
        reg_addr = 0x0000
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        # iss.i2c.write_ad2(devAddr, register, data)
        print(''.join('0x%2x '%i for i in (iss.i2c.read_ad2(devAddr, register, byte_count = 32))))

        def etroc2_pllCal(devAddr):
            ###--------------------------------------------------------------------------###
            ### calibrate the on-chip PLL
            ###
            reg_addr = 0x000f   ## PeriCfg15
            data = 0x20
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x60
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_dataRate(devAddr):
            ###--------------------------------------------------------------------------###
            ### Adjust the data output rate to 320 Mbps
            ###
            reg_addr = 0x0013   ## PeriCfg19
            data = 0x42
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_softBoot(devAddr):
            ###--------------------------------------------------------------------------###
            #### softBoot the chip
            ###
            reg_addr = 0x0012   ## PeriCfg18
            data = 0x02
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x00
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_settingFC(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x000d   ## PeriCfg13
            data = 0xa0
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x80
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_settingEFuse(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0016   ## PeriCfg22
            data = 0x0f
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            reg_addr = 0x0017   ## PeriCfg23
            data = 0x7f
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            reg_addr = 0x0018   ## PeriCfg24
            data = 0x01
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_fcDataDelay(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0012   ## PeriCfg22
            data = 0x10
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_fcClkDelay(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0012   ## PeriCfg22
            data = 0x08
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_groRst(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x000e   ## PeriCfg22
            data = 0x70
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0xf0
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_pixelEn(devAddr): # col 14, row 0 for WS
            ###--------------------------------------------------------------------------###
            #### pixel enable
            ###        
            reg_addr = 0b100_1110_0000_00001   ## pixelConfig[15:8] 0x01
            data = 0x26
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))


        etroc2_pllCal(devAddr)     ## re-calibrate pll, etroc2_softBoot has the similar function
        etroc2_dataRate(devAddr)   ## change data rate to 320 Mbps, default is 640 Mbps 
        etroc2_settingEFuse(devAddr)

        etroc2_settingFC(devAddr)    ## FC asy alignment
        # etroc2_fcDataDelay(devAddr)
        etroc2_fcClkDelay(devAddr)
        # etroc2_groRst(devAddr)

        # etroc2_pixelEn(devAddr) # col 14, row 0 for WS
    
    
    if(options.i2c):
        print("Inside I2C config")
        DAC_Value_List = []
        for i in range(num_boards):
            DAC_Value_List.append(single_pixel_threshold(board_size[i], options.pixel_address[i], options.pixel_threshold[i]))

    ###################################### Begin Dir making
    if(not options.nodaq):
        userdefinedir = options.output_directory
        userdefinedir_log = "%s_log"%userdefinedir
        ##  Creat a directory named path with date of today
        today = datetime.date.today()
        todaystr = "../../ETROC-Data/" + today.isoformat() + "_Array_Test_Results"
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
        print("Inside I2C setting")
        for B_num in range(num_boards):

            slaveA_addr = slaveA_addr_list[B_num]
            slaveB_addr = slaveB_addr_list[B_num]
            reg_val = []
            if(board_type[B_num]==1):
                reg_val = config_etroc1(B_num, options.charge_injection, DAC_Value_List, options.pixel_address, options.pixel_charge, cmd_interpret)
            elif(board_type[B_num]==2):
                pass
            elif(board_type[B_num]==3):
                pass
            if(options.verbose):
                print("Write data into I2C slave:")
                print(reg_val)
            for i in range(len(reg_val)):
                time.sleep(0.01)
                if i < 32:
                    iic_write(1, slaveA_addr_list[B_num], 0, i, reg_val[i], cmd_interpret)
                else:
                    iic_write(1, slaveB_addr_list[B_num], 0, i-32, reg_val[i], cmd_interpret)
            iic_read_val = []
            for j in range(len(reg_val)):
                time.sleep(0.01)
                if j < 32:
                    iic_read_val += [iic_read(0, slaveA_addr_list[B_num], 1, j, cmd_interpret)]
                else:
                    iic_read_val += [iic_read(0, slaveB_addr_list[B_num], 1, j-32, cmd_interpret)]
            if(options.verbose):
                print("I2C read back data:")
                print(iic_read_val)
            if iic_read_val == reg_val:
                print("I2C SUCCESS! Write data matches read data for Board ", B_num)
            else:
                print("I2C ERROR! Write data does not match read data for Board ", B_num)

    time.sleep(1)                                 # delay one second
    software_clear_fifo(cmd_interpret)            # clear fifo content

    if(not options.nodaq):
        ## start receive_data, write_data, daq_plotting threading
        store_dict = userdefine_dir
        read_queue = Queue()
        translate_queue = Queue() 
        plot_queue = Queue()
        read_stop_event = threading.Event()     # This is how we stop the read thread
        stop_DAQ_event = threading.Event()     # This is how we notify the Write thread that we are done taking data
        receive_data = Receive_data('Receive_data', read_queue, cmd_interpret, options.num_fifo_read, read_stop_event, options.useIPC, stop_DAQ_event, IPC_queue)
        write_data = Write_data('Write_data', read_queue, translate_queue, options.num_file, options.num_line, options.time_limit, store_dict, options.binary_only, options.compressed_binary, options.skip_binary, options.make_plots, read_stop_event, stop_DAQ_event)
        if(options.make_plots or (not options.binary_only)):
            translate_data = Translate_data('Translate_data', translate_queue, plot_queue, cmd_interpret, options.num_file, options.num_line,  options.time_limit, options.timestamp, store_dict, options.binary_only, options.make_plots, board_ID, read_stop_event, options.compressed_translation, stop_DAQ_event)
        if(options.make_plots):
            daq_plotting = DAQ_Plotting('DAQ_Plotting', plot_queue, options.timestamp, store_dict, options.pixel_address, board_type, board_size, options.plot_queue_time, read_stop_event)

        # read_write_data.start()
        try:
            # Start the thread
            receive_data.start()
            write_data.start()
            if(options.make_plots or (not options.binary_only)): translate_data.start()
            if(options.make_plots): daq_plotting.start()
            # If the child thread is still running
            while receive_data.is_alive():
                # Try to join the child thread back to parent for 0.5 seconds
                receive_data.join(0.5)
            if(options.make_plots or (not options.binary_only)):
                while translate_data.is_alive():
                    translate_data.join(0.5)
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
            if(options.make_plots or (not options.binary_only)): translate_data.alive = False
            if(options.make_plots): daq_plotting.alive = False
            # Block until child thread is joined back to the parent
            receive_data.join()
            if(options.make_plots or (not options.binary_only)): translate_data.join()
            write_data.join()
            if(options.make_plots): daq_plotting.join()
        
        # wait for thread to finish before proceeding)
        # read_write_data.join()
#--------------------------------------------------------------------------#
## if statement
        
    if(options.ws_testing):
        ''' 
        i2c initialization
        '''
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        devAddr = 0x60
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00001   ## pixelConfig[15:8]    default:0x26
        data = 0x3e   # Qinjen;  Qinj = 30
        # data = 0x3b    # Qinjen; Qinj = 28
        # data = 0x37  # Qinjen; Qinj = 24
        # data = 0x33   # Qinjen;  Qinj = 20
        # data = 0x26
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])

        devAddr = 0x60
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00000   ## pixelConfig[7:0] default:0x5C (pixelConfig[4:2]:IBSel[2:0] = 0b111)
        # data = 0x5c
        data = 0x1c  # max gain; default power
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])
        #########################TF
        reg_bits = 16
        reg_addr = 0b100_1110_0000_00101   ## pixelConfig[7:0] default:0x5C (pixelConfig[4:2]:IBSel[2:0] = 0b111)
        # data = 0x5c
        data = 0x0c  # max gain; default power
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        iss.i2c.write_ad2(devAddr, register, [data])

        # reg_addr = 0x0003   ## PeriCfg3
        # data = 0x38
        # iic_write(devAddr, reg_addr, reg_bits, data, cmd_interpret)


        #########################


        slaveA_addr_WS = 0x40
        ### 1F
        reg_add = 0x1f
        data = 0x22 ### clk_gen rst & mem rst
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

        data = 0x0b  ### fc ws_stop; bypass
        # data = 0x2b  ### external WS enable
        # data = 0x8b ### fc ws_stop; vga
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

        ### 0F
        reg_add = 0x0f
        data = 0x00
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])    
        ### 0E
        reg_add = 0x0e
        data = 0x00
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])  
        ### 0D
        reg_add = 0x0d
        data = 0x10  # default ctrl == 10
        iss.i2c.write(slaveA_addr_WS, reg_add, [data])

        print("Initialization done")
        time.sleep(1)

        # # COM_Port = "COM5"
        # port = '/dev/ttyACM0'
        # # set usb-iss iic master device
        # iss = UsbIss()
        # iss.open(port)
        # iss.setup_i2c(clock_khz=100)

        print('etroc2_i2c_configuration...')
        devAddr = 0x60
        reg_addr = 0x0000
        register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
        # iss.i2c.write_ad2(devAddr, register, data)
        print(''.join('0x%2x '%i for i in (iss.i2c.read_ad2(devAddr, register, byte_count = 32))))

        def etroc2_pllCal(devAddr):
            ###--------------------------------------------------------------------------###
            ### calibrate the on-chip PLL
            ###
            reg_addr = 0x000f   ## PeriCfg15
            data = 0x20
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x60
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_dataRate(devAddr):
            ###--------------------------------------------------------------------------###
            ### Adjust the data output rate to 320 Mbps
            ###
            reg_addr = 0x0013   ## PeriCfg19
            data = 0x42
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_softBoot(devAddr):
            ###--------------------------------------------------------------------------###
            #### softBoot the chip
            ###
            reg_addr = 0x0012   ## PeriCfg18
            data = 0x02
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x00
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_settingFC(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x000d   ## PeriCfg13
            data = 0xa0
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0x80
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_settingEFuse(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0016   ## PeriCfg22
            data = 0x0f
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            reg_addr = 0x0017   ## PeriCfg23
            data = 0x7f
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            reg_addr = 0x0018   ## PeriCfg24
            data = 0x01
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_fcDataDelay(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0012   ## PeriCfg22
            data = 0x10
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_fcClkDelay(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x0012   ## PeriCfg22
            data = 0x08
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_groRst(devAddr):
            ###--------------------------------------------------------------------------###
            #### setting FC asy alignment
            ###
            reg_addr = 0x000e   ## PeriCfg22
            data = 0x70
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))
            data = 0xf0
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))

        def etroc2_pixelEn(devAddr): # col 14, row 0 for WS
            ###--------------------------------------------------------------------------###
            #### pixel enable
            ###        
            reg_addr = 0b100_1110_0000_00001   ## pixelConfig[15:8] 0x01
            data = 0x26
            register = (reg_addr << 8) & 0xff00 | (reg_addr >> 8) & 0x00ff
            iss.i2c.write_ad2(devAddr, register, [data])
            print('0x{0:04x}'.format(reg_addr), '0x{0:02x}'.format(iss.i2c.read_ad2(devAddr, register, byte_count = 1)[0]))


        etroc2_pllCal(devAddr)     ## re-calibrate pll, etroc2_softBoot has the similar function
        etroc2_dataRate(devAddr)   ## change data rate to 320 Mbps, default is 640 Mbps 
        etroc2_settingEFuse(devAddr)

        etroc2_settingFC(devAddr)    ## FC asy alignment
        # etroc2_fcDataDelay(devAddr)
        # etroc2_fcClkDelay(devAddr)
        # etroc2_groRst(devAddr)

        # etroc2_pixelEn(devAddr) # col 14, row 0 for WS

        time.sleep(1)


        '''
        one time charge injection
        '''
        WS_start_charge_injection_stop(cmd_interpret)
        print("charge injection done")
        time.sleep(0.1)

        '''
        ws_memory_readout
        '''
        # COM_Port = "COM5"
        port = '/dev/ttyACM0'
        # set usb-iss iic master device
        iss = UsbIss()
        iss.open(port)
        iss.setup_i2c(clock_khz=100)

        today = datetime.date.today()
        todaystr = "./WS-Data/" + today.isoformat() + "_Test_Results/"
        base_dir = Path(todaystr)
        base_dir.mkdir(exist_ok=True) 
        outfile = base_dir / ("WS_rawdata_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv")

        def WS_memory_read(file_name):
            slaveA_addr_WS = 0x40

            reg_add = 0x1f
            data = 0x2f  ### bypass mode
            # data = 0xaf  ### vga mode
            # data = 0xf  ### fc ws_stop; bypass
            # data = 0x4f  ### fc 400ns; bypass
            # data = 0x8f ### ws_stop; vga

            iss.i2c.write(slaveA_addr_WS, reg_add, [data])

            reg_rd_add_MSB = 0x1d
            reg_rd_add_LSB = 0x1c
            dout_MSB_add = 0x21
            dout_LSB_add = 0x20
            file1 = open(file_name, "w")
            # for i in tqdm(range(1024)):
            for i in range(1024):
                rd_add_MSB = i // 4
                rd_add_LSB2 = i % 4
                rd_add_LSB = rd_add_LSB2 * 64
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_MSB, rd_add_MSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_MSB, [rd_add_MSB])
                # iic_write_ws(1, slaveA_addr_WS, 0, reg_rd_add_LSB, rd_add_LSB, cmd_interpret)
                iss.i2c.write(slaveA_addr_WS, reg_rd_add_LSB, [rd_add_LSB])

                dout_MSB = []
                # dout_MSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_MSB_add, cmd_interpret)
                dout_MSB = iss.i2c.read(slaveA_addr_WS, dout_MSB_add, 1)
                dout_LSB = []
                # dout_LSB = iic_read_ws(0, slaveA_addr_WS, 1, dout_LSB_add, cmd_interpret)
                dout_LSB = iss.i2c.read(slaveA_addr_WS, dout_LSB_add, 1)
                # print(i, bin(rd_add_MSB), bin(rd_add_LSB2), dout_MSB, dout_LSB/4)
                print(i, dout_MSB[0], dout_LSB[0]/4)
                dout_to_file = str(i) + "  " + str(dout_MSB[0]) + "  " + str(dout_LSB[0]) + "\n"
                file1.writelines(dout_to_file)
            file1.close()

            slaveA_addr_WS = 0x40
            reg_add = 0x1f
            data = 0x0b         # set rd_en_I2C off //TF_08_01
            # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret)
            iss.i2c.write(slaveA_addr_WS, reg_add, [data]) 

        WS_memory_read(outfile);  

        print("memory readout done") 
        time.sleep(1)
        
        # slaveA_addr_WS = 0x40
        # reg_add = 0x1f
        # data = 0x0b  ### disable read

        # iic_write_ws(1, slaveA_addr_WS, 0, reg_add, data, cmd_interpret)
        # iss.i2c.write(slaveA_addr_WS, reg_add, [data]) 

        '''
        ws_reconstruction
        '''
        # file_name = "WS_memory_data_B5_0808_bypass_BX3_BX8_BX13_Q30_linux_fc_1.txt"
        # file_path = os.path.join(current_directory, file_name)
        #print(os.path.abspath(file_name))

        with open(outfile, 'r') as f:
            b1 = np.loadtxt(f, dtype=int).T

        data_1 = b1[1, :]
        data_2 = b1[2, :]

        data1 = data_1 % 128
        k = None
        for i in range(1024):
            if data_1[i] > 127:
                k = i
                break

        #print(np.where(data_1 > 127)[0])
        end_ind = k - 128 * 7

        data_1st_tem = np.zeros((1024, 8), dtype=int)
        data_2st_tem = np.zeros((1024, 8), dtype=int)

        for i in range(1024):
            data_1_tem = np.binary_repr(data_1[i], width=8)
            l1 = len(data_1_tem)
            data_1st_tem[i] = [int(d) for d in data_1_tem.zfill(8)]
            data_2_tem = np.binary_repr(data_2[i], width=8)
            l1 = len(data_2_tem)
            data_2st_tem[i] = [int(d) for d in data_2_tem.zfill(8)]

        data_1st = data_1st_tem[:, 1:7]
        data_2st = np.hstack((data_1st_tem[:, 7].reshape(-1, 1), data_2st_tem[:, 0:6]))

        gain = 0.04 / 5 * 8.5
        Aout_1st = np.zeros(1024)
        Aout_2st = np.zeros(1024)
        for i in range(1024):
            Aout_1st[i] = 32 * data_1st[i, 0] + 16 * data_1st[i, 1] + 8 * data_1st[i, 2] + \
                4 * data_1st[i, 3] + 2 * data_1st[i, 4] + data_1st[i, 5]
            # Aout_1st = int('0b'+data_1_tem[i,1:7],0)

            Aout_2st[i] = 24 * data_2st[i, 0] + 16 * data_2st[i, 1] + 10 * data_2st[i, 2] + \
                6 * data_2st[i, 3] + 4 * data_2st[i, 4] + 2 * data_2st[i, 5] + data_2st[i, 6]

        Aout = Aout_1st - gain * Aout_2st

        Aout_ch = np.zeros((8, 128))
        Aout_ch_align = np.zeros((8, 128))

        for ch in range(1, 9):
            Aout_ch[8 - ch, :] = Aout[(ch - 1) * 128: ch * 128]


        for ch in range(1, 9):
            if end_ind == 128:
                Aout_ch_align[ch - 1, :] = Aout_ch[ch - 1, :]
            else:
                Aout_ch_align[ch - 1, :128 - end_ind] = Aout_ch[ch - 1, end_ind:]
                Aout_ch_align[ch - 1, 129 - end_ind - 1: 128] = Aout_ch[ch - 1, :end_ind]

        # plt.figure()
        # for i in range(8):
        #     plt.subplot(8, 1, i + 1)
        #     plt.plot(Aout_ch_align[i])
        # plt.ylim([0, 2.4])

        Aout_8ch = np.zeros(1024)
        for i in range(1024):
            Aout_8ch[i] = Aout_ch_align[(i - 1) % 8, (i - 1) // 8]

        # for i in range(128):
        #     Aout_8ch[8 * i - 0] = Aout_ch_align[7, i]
        #     Aout_8ch[8 * i - 1] = Aout_ch_align[6, i]
        #     Aout_8ch[8 * i - 2] = Aout_ch_align[5, i]
        #     Aout_8ch[8 * i - 3] = Aout_ch_align[4, i]
        #     Aout_8ch[8 * i - 4] = Aout_ch_align[3, i]
        #     Aout_8ch[8 * i - 5] = Aout_ch_align[2, i]
        #     Aout_8ch[8 * i - 6] = Aout_ch_align[1, i]
        #     Aout_8ch[8 * i - 7] = Aout_ch_align[0, i]

        Aout_8ch_v = -(Aout_8ch - (31.5 - gain * 31.5)) * 1.2 / 32
        N = np.arange(1024)
        t = N * 1 / 2.56

        # highest_values = np.sort((Aout_8ch_v))[-2:]
        # print("两个pulse的峰值: ", highest_values)

        plt.figure()
        plt.plot(t, Aout_8ch_v, linewidth = 0.5 )
        plt.ylim([-0.6, 0.6])
        # plt.ylim([-1, 0.4])
        plt.xlim([0, 400])
        plt.ylabel("Voltage(V)")
        plt.xlabel("Time(ns)")
        plt.show()

def getOptionParser():
    
    def int_list_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, list(map(int, value.split(','))))

    parser = OptionParser()
    parser.add_option("--hostname", dest="hostname", action="store", type="string", help="FPGA IP Address", default="192.168.2.3")
    parser.add_option("-n", "--num_file", dest="num_file", action="store", type="int", help="Number of files created by DAQ script", default=1)
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int", help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-r", "--num_fifo_read", dest="num_fifo_read", action="store", type="int", help="Number of lines read per call of fifo readout", default=50000)
    parser.add_option("-t", "--time_limit", dest="time_limit", action="store", type="int", help="Number of seconds to run this code", default=-1)
    parser.add_option("-o", "--output_directory", dest="output_directory", action="store", type="string", help="User defined output directory", default="unnamed_output_directory")
    parser.add_option("-a", "--pixel_address", dest="pixel_address", action="callback", type="string", help="Single pixel address under test for each board", callback=int_list_callback)
    parser.add_option("--pixel_threshold", dest="pixel_threshold", action="callback", type="string", help="Single pixel threshold for pixels under test for each board", callback=int_list_callback)
    parser.add_option("-q", "--pixel_charge", dest="pixel_charge", action="callback", type="string", help="Single pixel charge to be injected (fC) for pixels under test for each board", callback=int_list_callback)
    parser.add_option("-i", "--charge_injection",action="store_true", dest="charge_injection", default=False, help="Flag that enables Qinj")
    parser.add_option("-b", "--binary_only",action="store_true", dest="binary_only", default=False, help="Save only the untranslated FPGA binary data (raw output)")
    parser.add_option("-c", "--compressed_binary",action="store_true", dest="compressed_binary", default=False, help="Save FPGA binary data (raw output) in int format")
    parser.add_option("--skip_binary",action="store_true", dest="skip_binary", default=False, help="DO NOT save (raw) binary outputsto files")
    parser.add_option("--compressed_translation",action="store_true", dest="compressed_translation", default=False, help="Save only FPGA translated data frames with DATA")
    parser.add_option("-s", "--timestamp", type="int",action="store", dest="timestamp", default=0x000C, help="Set timestamp binary, see daq_helpers for more info")
    parser.add_option("--polarity", type="int",action="store", dest="polarity", default=0x000b, help="Set fc polarity, see daq_helpers for more info")
    parser.add_option("-v", "--verbose",action="store_true", dest="verbose", default=False, help="Print status messages to stdout")
    parser.add_option("-w", "--overwrite",action="store_true", dest="overwrite", default=False, help="Overwrite previously saved files")
    parser.add_option("-p", "--make_plots",action="store_true", dest="make_plots", default=False, help="Enable plotting of real time hits")
    parser.add_option("--plot_queue_time", dest="plot_queue_time", action="store", type="float", help="Time (s) used to pop lines off the queue for plotting", default=0.1)
    parser.add_option("--old_data_format",action="store_true", dest="old_data_format", default=False, help="(Dev Only) Set if Data is in old format for ETROC1")
    parser.add_option("--i2c",action="store_true", dest="i2c", default=False, help="Config ETROC boards over I2C")
    parser.add_option("--nodaq",action="store_true", dest="nodaq", default=False, help="Switch off DAQ via the FPGA")
    parser.add_option("--useIPC",action="store_true", dest="useIPC", default=False, help="Use Inter Process Communication to control L1A enable/disable")
    parser.add_option("--firmware",action="store_true", dest="firmware", default=False, help="Configure FPGA firmware settings")
    parser.add_option("--inspect_serial_output",action="store_true", dest="inspect_serial_output", default=False, help="(DEV ONLY) Decode the register binary values for serial port inspection with test pattern mode data")
    parser.add_option("--do_fc",action="store_true", dest="do_fc", default=False, help="(DEV ONLY) Do Fast Command register setting in frequency train mode")
    parser.add_option("--memo_fc",action="store_true", dest="memo_fc", default=False, help="(DEV ONLY) Do Fast Command with Memory")
    parser.add_option("--memo_fc_start_periodic_ws",action="store_true", dest="memo_fc_start_periodic_ws", default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke start_periodic_L1A_WS() from daq_helpers.py")
    parser.add_option("--memo_fc_start_onetime_ws", action="store_true", dest="memo_fc_start_onetime_ws" , default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke start_onetime_L1A_WS() from daq_helpers.py")
    parser.add_option("--etroc2_i2c",action="store_true", dest="etroc2_i2c", default=False, help="Config ETROC2 part via I2C")
    parser.add_option("--fc_ws_start", action="store_true", dest="fc_ws_start" , default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke WS_onetime_start_WS() from daq_helpers.py")
    parser.add_option("--fc_ws_stop", action="store_true", dest="fc_ws_stop" , default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke WS_onetime_stop_WS() from daq_helpers.py")
    parser.add_option("--ws_onetime_charge_injection", action="store_true", dest="ws_onetime_charge_injection" , default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke WS_start_charge_injection_stop() from daq_helpers.py")
    parser.add_option("--ws_memory_readout", action="store_true", dest="ws_memory_readout" , default=False, help="(WS DEV ONLY) Read the data in WS memory and store them in .txt file for further processing")
    parser.add_option("--ws_i2c_initialization", action="store_true", dest="ws_i2c_initialization" , default=False, help="(WS DEV ONLY) Initialize the I2C in WS and ETROC0")
    parser.add_option("--ws_reconstruction", action="store_true", dest="ws_reconstruction" , default=False, help="(WS DEV ONLY) Reconstruct the waveform")   
    parser.add_option("--ws_testing", action="store_true", dest="ws_testing",default = False, help="(WS DEV ONLY), test the WS and Reconstruction the waveform")
    return parser

if __name__ == "__main__":

    parser = getOptionParser()
    (options, args) = parser.parse_args()

    if(options.pixel_address == None): options.pixel_address = [5, 5, 5, 5]
    if(options.pixel_threshold == None): options.pixel_threshold = [552, 560, 560, 560]
    if(options.pixel_charge == None): options.pixel_charge = [30, 30, 30, 30]
    if(options.num_fifo_read>65536):   # See command_interpret.py read_memory()
        print("Max Number of lines read by fifo capped at 65536, you entered ",options.num_fifo_read,", setting to 65536")
        options.num_fifo_read = 65536
        
    import platform
    system = platform.system()
    if system == 'Windows' or system == '':
        options.useIPC = False

    if(options.verbose):
        print("Verbose Output: ", options.verbose)
        print("\n")
        print("-------------------------------------------")
        print("--------Set of inputs from the USER--------")
        print("Overwrite previously saved files: ", options.overwrite)
        print("FPGA IP Address: ", options.hostname)
        print("Number of files created by DAQ script: ", options.num_file)
        print("Number of lines per file created by DAQ script: ", options.num_line)
        print("Number of lines read per call of fifo readout: ", options.num_fifo_read)
        print("Number of seconds to run this code (>0 means effective): ", options.time_limit)
        print("User defined Output Directory: ", options.output_directory)
        print("(ETROC1) Single pixel address under test for each board: ", options.pixel_address)
        print("(ETROC1) Single pixel threshold for pixels under test for each board: ", options.pixel_threshold)
        print("(ETROC1) Single pixel charge to be injected (fC) for pixels under test for each board: ", options.pixel_charge)
        print("(ETROC1) Flag that enables Qinj: ", options.charge_injection)
        print("Save only the untranslated FPGA binary data (raw output): ", options.binary_only)
        print("Save FPGA binary data (raw output) in int format: ", options.compressed_binary)
        print("Save only FPGA translated data frames with DATA: ", options.compressed_translation)
        print("DO NOT save binary data (raw output): ", options.skip_binary)
        print("Set timestamp binary (Reg 13), see daq_helpers.py -> timestamp() for more info: ", "0x{:04x}".format(options.timestamp))
        print("Set polarity binary (Reg 14), see daq_helpers.py -> Enable_FPGA_Descramblber() for more info: ", "0x{:04x}".format(options.polarity))
        print("Enable plotting of real time hits: ", options.make_plots)
        print("Time (s) used to pop lines off the queue for plotting: ", options.plot_queue_time)
        print("Config (ETROC1) boards over I2C: ", options.i2c)
        print("Switch off DAQ via the FPGA?: ", options.nodaq)
        print("Use IPC to control the L1A: ", options.useIPC)
        print("Configure FPGA firmware settings?: ", options.firmware)
        print("--------End of inputs from the USER--------")
        print("-------------------------------------------")
        print("\n")
        print("-------------------------------------------")
        print("-------Inputs that have been pre-set-------")
        print("ETROC Board Type: ",   board_type)
        print("ETROC Board Size: ",   board_size)
        print("ETROC Board Name: ",   board_name)
        print("ETROC Chip ID: ",      board_ID) 
        print("Set active channel binary (Reg 15), see daq_helpers.py -> active_channels() for more info: ", "0x{:04x}".format(active_channels_key))
        print("-------------------------------------------")
        print("-------------------------------------------")
        print("\n")

    if(options.binary_only==True and options.make_plots==True):
        print("ERROR! Can't make plots without translating data!")
        sys.exit(1)
    
    main_process(None, options)
