#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ETROC1_ArrayReg import * 
from command_interpret import *
from board_details import *
from daq_helpers import *
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is composed of helper functions specific to ETROC1
'''
#--------------------------------------------------------------------------#
## DAC output configuration, 0x000: 0.6V  ox200: 0.8V  0x2ff: 1V
#@para[in] num : 0-15 value: Digital input value
def ETROC1_DAC_Config(DAC_Value, ETROC1_ArrayReg1):
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
def config_etroc1(B_num, charge_injection, DAC_Value_List, Pixel_board, QSel_board, cmd_interpret):

    ETROC1_ArrayReg1 = ETROC1_ArrayReg()   
    
    EnScr = 1                                   # Enable Scrambler
    DMRO_revclk = 1                             # Sample clock polarity
    Test_Pattern_Mode_Output = 0                # 0: TDC output data, 1: Counter output data
    TDC_testMode = 0                            # 1: TDC works on test mode, 0: TDC works on normal mode
    TDC_Enable = 1                              # 1: enable TDC 0: disable TDC
    PhaseAdj = 0                                # Phase shifter ranges from 0 to 255

    DAC_Value = DAC_Value_List[B_num]
    ETROC1_DAC_Config(DAC_Value, ETROC1_ArrayReg1)
    reg_val = []                                # list for register config

    # Charge Injection setting
    Pixel_Num=Pixel_board[B_num]
    QSel = QSel_board[B_num]
    
    ETROC1_ArrayReg1.set_QSel(QSel)
    QInj_Enable = [[0x01, 0x00], [0x02, 0x00], [0x04, 0x00], [0x08, 0x00], [0x10, 0x00], [0x20, 0x00], [0x40, 0x00], [0x80, 0x00],\
                [0x00, 0x01], [0x00, 0x02], [0x00, 0x04], [0x00, 0x08], [0x00, 0x10], [0x00, 0x20], [0x00, 0x40], [0x00, 0x80]]
    if(charge_injection):
        ETROC1_ArrayReg1.set_EN_QInj7_0(QInj_Enable[Pixel_Num][0])       # Enable QInj7~0
        ETROC1_ArrayReg1.set_EN_QInj15_8(QInj_Enable[Pixel_Num][1])      # Enable QInj15~8
    else:
        ETROC1_ArrayReg1.set_EN_QInj7_0(0x00)                            # Disable QInj7~0
        ETROC1_ArrayReg1.set_EN_QInj15_8(0x00)                           # Disable QInj15~8
    
    ## PreAmp setting
    CLSel = CLSel_board[B_num]                  
    RfSel = RfSel_board[B_num]
    IBSel = IBSel_board[B_num]

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
    ######## DOUBLE CHECK NEEDED
    ETROC1_ArrayReg1.set_dllEnable(0)           # Enable phase shifter
    ETROC1_ArrayReg1.set_dllCapReset(1)         # should be set to 0
    time.sleep(0.1)
    ETROC1_ArrayReg1.set_dllCapReset(0)         # should be set to 0
    ETROC1_ArrayReg1.set_dllCPCurrent(1)        # default value 1:
    ETROC1_ArrayReg1.set_dllEnable(1)           # Enable phase shifter
    ETROC1_ArrayReg1.set_dllForceDown(0)        # should be set to 0
    ETROC1_ArrayReg1.set_PhaseAdj(PhaseAdj)     # 0-128 to adjust clock phase
    ######## DOUBLE CHECK NEEDED

    # 320M clock strobe setting
    ETROC1_ArrayReg1.set_RefStrSel(0x03)        # default 0x03: 3.125 ns measuement windo

    # clock input and output MUX select
    ######## DOUBLE CHECK NEEDED
    ETROC1_ArrayReg1.set_TestCLK0(1)            # 0: 40M and 320M clock comes from phase shifter, 1: 40M and 320M clock comes from external pads
    ETROC1_ArrayReg1.set_TestCLK1(0)            # 0: 40M and 320M  go cross clock strobe 1: 40M and 320M bypass
    ETROC1_ArrayReg1.set_CLKOutSel(1)           # 0: 40M clock output, 1: 320M clock or strobe output
    ######## DOUBLE CHECK NEEDED

    ## DMRO readout Mode
    DMRO_Readout_Select = [[0x01, 0x0], [0x02, 0x0], [0x04, 0x0], [0x08, 0x0], [0x01, 0x1], [0x02, 0x1], [0x04, 0x1], [0x08, 0x1],\
                        [0x01, 0x2], [0x02, 0x2], [0x04, 0x2], [0x08, 0x2], [0x01, 0x3], [0x02, 0x3], [0x04, 0x3], [0x08, 0x3]]
    ETROC1_ArrayReg1.set_OE_DMRO_Row(DMRO_Readout_Select[Pixel_Num][0])       # DMRO readout row select
    ETROC1_ArrayReg1.set_DMRO_Col(DMRO_Readout_Select[Pixel_Num][1])          # DMRO readout column selec
    ETROC1_ArrayReg1.set_RO_SEL(0)                                            # 0: DMRO readout enable  1: Simple readout enable
    ETROC1_ArrayReg1.set_TDC_enableMon(Test_Pattern_Mode_Output)              # 0: Connect to TDC       1: Connect to Test Counter

    ## TDC setting
    ETROC1_ArrayReg1.set_TDC_resetn(1)
    ETROC1_ArrayReg1.set_TDC_testMode(TDC_testMode)
    ETROC1_ArrayReg1.set_TDC_autoReset(0)
    ETROC1_ArrayReg1.set_TDC_enable(TDC_Enable)

    ## DMRO Setting
    ETROC1_ArrayReg1.set_DMRO_ENScr(EnScr)                              # Enable DMRO scrambler
    ETROC1_ArrayReg1.set_DMRO_revclk(DMRO_revclk)
    ETROC1_ArrayReg1.set_DMRO_testMode(0)                               # DMRO work on test mode

    ############################## DOES THIS NEED TO HAPPEN EVERYTIME ###################################
    # Enable_FPGA_Descramblber(EnScr, cmd_interpret)                      # Enable FPGA Firmware Descramble

    ## DMRO CML driver
    ETROC1_ArrayReg1.set_Dataout_AmplSel(7)
    ETROC1_ArrayReg1.set_CLKTO_AmplSel(7)
    ETROC1_ArrayReg1.set_CLKTO_disBIAS(0)
    reg_val = ETROC1_ArrayReg1.get_config_vector()                      # Get Array Pixel Register default data

    return reg_val