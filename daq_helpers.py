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

