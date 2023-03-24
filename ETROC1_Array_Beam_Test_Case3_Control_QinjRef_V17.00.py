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
#import winsound
import datetime
import heartrate
from queue import Queue
from command_interpret import *
from ETROC1_ArrayReg import *
import numpy as np
from command_interpret import *
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
#========================================================================================#
freqency = 1000
duration = 1000
'''
@author: Wei Zhang
@date: 2018-02-28
This script is used for testing ETROC1 Array chip. The mianly function of this script is I2C write and read, Ethernet communication, instrument control and so on.
'''
hostname = '192.168.2.3'					#FPGA IP address
port = 1024									#port number
#--------------------------------------------------------------------------#
## define a receive data class
class Receive_data(threading.Thread):       # threading class
    def __init__(self, name, queue, num_file):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
    
    def run(self):                          # num_file: set how many data file you want to get
        mem_data = []
        for files in range(self.num_file):
            mem_data = cmd_interpret.read_data_fifo(50000)
            print("{} is producing {} to the queue!".format(self.getName(), files))
            for i in range(50000):
                self.queue.put(mem_data[i])
        print("%s finished!"%self.getName())
#--------------------------------------------------------------------------#
## define a write data class
class Write_data(threading.Thread):         # threading class
    def __init__(self, name, queue, num_file, store_dict, PhaseAdj, B_nam1, Pixel_Num1, QSel1, DAC_Value1, B_nam2, Pixel_Num2, QSel2, DAC_Value2, B_nam3, Pixel_Num3, QSel3, DAC_Value3):
        threading.Thread.__init__(self, name=name)
        self.queue = queue
        self.num_file = num_file
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
                for j in range(50000):
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
## measure supply current
def measure_current(val):
    Power_Current= {"IO_Current":0, "PA_Current":0, "QInj_Current":0, "Discri_Current":0, "Clk_Current":0, "Dig_Current":0, "3V3_Current":0}
    rm = visa.ResourceManager()
    # print(rm.list_resources())
    inst1 = rm.open_resource('USB0::0x2A8D::0x1102::MY58041593::0::INSTR')      # top power supply
    inst2 = rm.open_resource('USB0::0x2A8D::0x1102::MY58041595::0::INSTR')      # bottom power supply one
    inst3 = rm.open_resource('USB0::0x2A8D::0x1102::MY58041599::0::INSTR')
    Power_Current['IO_Current'] = round(float(inst1.query("MEAS:CURR? CH1"))*1000.0, 3)             # IO power
    Power_Current['PA_Current'] = round(float(inst1.query("MEAS:CURR? CH2"))*1000.0, 3)             # PA power
    Power_Current['QInj_Current'] = round(float(inst1.query("MEAS:CURR? CH3"))*1000.0, 3)           # QInj power
    Power_Current['Discri_Current'] = round(float(inst2.query("MEAS:CURR? CH1"))*1000.0, 3)         # Discri power
    Power_Current['Clk_Current'] = round(float(inst2.query("MEAS:CURR? CH2"))*1000.0, 3)            # Clk power
    Power_Current['Dig_Current'] = round(float(inst2.query("MEAS:CURR? CH3"))*1000.0, 3)            # Dig power
    Power_Current['3V3_Current'] = round(float(inst3.query("MEAS:CURR? CH1"))*1000.0, 3)
    inst1.write("SOURce:VOLTage 1.20,(@1)")
    inst2.write("SOURce:VOLTage 1.20,(@3)")
    # print(Power_Current)
    if val == 1:
        inst3.write("SOURce:VOLTage 0,(@2)")                                      # top channel 1
        inst3.write("SOURce:CURRent 0.002,(@2)")
        inst3.write("OUTPut:STATe ON,(@2)")
        time.sleep(1)
        inst3.write("SOURce:VOLTage 1.2,(@2)")

    return Power_Current
    # print(inst1.query("*IDN?"))
    # print(inst2.query("*IDN?"))
#--------------------------------------------------------------------------#
## DAC output configuration, 0x000: 0.6V  ox200: 0.8V  0x2ff: 1V
#@para[in] num : 0-15 value: Digital input value
def DAC_Config(DAC_Value):
    DAC_160bit = []
    for i in range(len(DAC_Value)):
        for j in range(10):
            DAC_160bit += [(DAC_Value[i] >> j) & 0x001]
    DAC_8bit = [[] for x in range(20)]
    for k in range(len(DAC_8bit)):
        DAC_Single = 0
        for l in range(8):
            DAC_Single += (DAC_160bit[k*8+l] & 0x1) << l
        DAC_8bit[k] = DAC_Single
    ETROC1_ArrayReg1.set_VTHIn7_0(DAC_8bit[0])
    ETROC1_ArrayReg1.set_VTHIn15_8(DAC_8bit[1])
    ETROC1_ArrayReg1.set_VTHIn23_16(DAC_8bit[2])
    ETROC1_ArrayReg1.set_VTHIn31_24(DAC_8bit[3])
    ETROC1_ArrayReg1.set_VTHIn39_32(DAC_8bit[4])
    ETROC1_ArrayReg1.set_VTHIn47_40(DAC_8bit[5])
    ETROC1_ArrayReg1.set_VTHIn55_48(DAC_8bit[6])
    ETROC1_ArrayReg1.set_VTHIn63_56(DAC_8bit[7])
    ETROC1_ArrayReg1.set_VTHIn71_64(DAC_8bit[8])
    ETROC1_ArrayReg1.set_VTHIn79_72(DAC_8bit[9])
    ETROC1_ArrayReg1.set_VTHIn87_80(DAC_8bit[10])
    ETROC1_ArrayReg1.set_VTHIn95_88(DAC_8bit[11])
    ETROC1_ArrayReg1.set_VTHIn103_96(DAC_8bit[12])
    ETROC1_ArrayReg1.set_VTHIn111_104(DAC_8bit[13])
    ETROC1_ArrayReg1.set_VTHIn119_112(DAC_8bit[14])
    ETROC1_ArrayReg1.set_VTHIn127_120(DAC_8bit[15])
    ETROC1_ArrayReg1.set_VTHIn135_128(DAC_8bit[16])
    ETROC1_ArrayReg1.set_VTHIn143_136(DAC_8bit[17])
    ETROC1_ArrayReg1.set_VTHIn151_144(DAC_8bit[18])
    ETROC1_ArrayReg1.set_VTHIn159_152(DAC_8bit[19])
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
## main functionl
def main():
    slaveA_addr_list = [0x03, 0x02, 0x01]       # I2C address for Board F28, F29, F30
    slaveB_addr_list = [0x7f, 0x7e, 0x7d]

    #Pixel 0: 484 for B1: 0x02/0x7d, 480 for D: 0x01/0x7e, 468 for F29: 0x03/0x7f
    #Pixel 4: 440 for B1: 0x02/0x7d, 440 for D: 0x01/0x7e, 444 for F29: 0x03/0x7f

    F28_DAC_P0 = 0x000  
    F28_DAC_P1 = 0x000  
    F28_DAC_P2 = 0x000   
    F28_DAC_P3 = 0x000
    F28_DAC_P4 = 0x000   
    F28_DAC_P5 = 552 #11fC 2023/02/28
    F28_DAC_P6 = 0x000  
    F28_DAC_P7 = 0x000
    F28_DAC_P8 = 0x000
    F28_DAC_P9 = 0x000
    F28_DAC_P10 = 0x000  
    F28_DAC_P11 = 0x000
    F28_DAC_P12 = 0x000
    F28_DAC_P13 = 0x000
    F28_DAC_P14 = 0x000
    F28_DAC_P15 = 0x000
    F28_DAC_Value = [F28_DAC_P0, F28_DAC_P1, F28_DAC_P2, F28_DAC_P3, F28_DAC_P4, F28_DAC_P5, F28_DAC_P6, F28_DAC_P7, F28_DAC_P8,\
                    F28_DAC_P9, F28_DAC_P10, F28_DAC_P11, F28_DAC_P12, F28_DAC_P13, F28_DAC_P14, F28_DAC_P15]

    F29_DAC_P0 = 0x000
    F29_DAC_P1 = 0x000
    F29_DAC_P2 = 0x000
    F29_DAC_P3 = 0x000
    F29_DAC_P4 = 0x000
    F29_DAC_P5 = 560 # 10fC 2023/03/03
    F29_DAC_P6 = 0x000
    F29_DAC_P7 = 0x000
    F29_DAC_P8 = 0x000
    F29_DAC_P9 = 0x000
    F29_DAC_P10 = 0x000
    F29_DAC_P11 = 0x000
    F29_DAC_P12 = 0x000
    F29_DAC_P13 = 0x000
    F29_DAC_P14 = 0x000
    F29_DAC_P15 = 0x000
    F29_DAC_Value = [F29_DAC_P0, F29_DAC_P1, F29_DAC_P2, F29_DAC_P3, F29_DAC_P4, F29_DAC_P5, F29_DAC_P6, F29_DAC_P7, F29_DAC_P8,\
                     F29_DAC_P9, F29_DAC_P10, F29_DAC_P11, F29_DAC_P12, F29_DAC_P13, F29_DAC_P14, F29_DAC_P15]

    F30_DAC_P0 = 0x000   
    F30_DAC_P1 = 0x000
    F30_DAC_P2 = 0x000
    F30_DAC_P3 = 0x000
    F30_DAC_P4 = 0x000
    F30_DAC_P5 = 560 # 10fC 2023/03/03
    F30_DAC_P6 = 0x000
    F30_DAC_P7 = 0x000
    F30_DAC_P8 = 0x000
    F30_DAC_P9 = 0x000 
    F30_DAC_P10 = 0x000
    F30_DAC_P11 = 0x000
    F30_DAC_P12 = 0x000
    F30_DAC_P13 = 0x000
    F30_DAC_P14 = 0x000
    F30_DAC_P15 = 0x000
    F30_DAC_Value = [F30_DAC_P0, F30_DAC_P1, F30_DAC_P2, F30_DAC_P3, F30_DAC_P4, F30_DAC_P5, F30_DAC_P6, F30_DAC_P7, F30_DAC_P8,\
                    F30_DAC_P9, F30_DAC_P10, F30_DAC_P11, F30_DAC_P12, F30_DAC_P13, F30_DAC_P14, F30_DAC_P15]

    DAC_Value_List = [F28_DAC_Value, F29_DAC_Value, F30_DAC_Value]

    #Pixel_Num = 0                              # range from 0-15
    BoardName  = ["F28", "F29" ,"F30"]
    Pixel_board= [  5,    5,    5 ]             # range from 0-15
    CLSel_board= [  0,    0,    0 ]
    RfSel_board= [  2,    2,    2 ]
    IBSel_board= [  0,    0,    0 ]
    QSel_board = [ 30,   30,   30 ]
    DAC_board  = [  0,    0,    0 ]

    userdefinedir = "%sP%d_%sP%d_%sP%d_QInj=1M25_Ref_1202_HMC_4095"%(BoardName[0], Pixel_board[0], BoardName[1], Pixel_board[1], BoardName[2], Pixel_board[2])
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
            logfile.write("I2C write into data %s:\n"%BoardName[B_num])
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
    num_file = int(sys.argv[1])                                         # total files will be read back
    store_dict = userdefine_dir
    queue = Queue()                                                     # define a queue
    receive_data = Receive_data('Receive_data', queue, num_file)        # initial receive_data class
    write_data = Write_data('Write_data', queue, num_file, store_dict, PhaseAdj, BoardName[0], Pixel_board[0], QSel_board[0], DAC_board[0], BoardName[1], Pixel_board[1], QSel_board[1], DAC_board[1], BoardName[2], Pixel_board[2], QSel_board[2], DAC_board[2])  # initial write_data class
    
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
    main()													    # execute main function
    s.close()												    # close socket
