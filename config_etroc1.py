from ETROC1_ArrayReg import * 

def config_etroc():
    
    Board_num = 2                               # Board ID show in tag
    EnScr = 1                                   # Enable Scrambler
    DMRO_revclk = 1                             # Sample clock polarity
    Test_Pattern_Mode_Output = 0                # 0: TDC output data, 1: Counter output data
    TDC_testMode = 0                            # 1: TDC works on test mode, 0: TDC works on normal mode
    TDC_Enable = 1                              # 1: enable TDC 0: disable TDC
    PhaseAdj = 0                                # Phase shifter ranges from 0 to 255
    Total_point = 1                             # Total fetch data = Total_point * 50000
    External_RST = 0                            # 1: reset   0: didn't reset
    Fetch_Data = 1                              # Turn On fetch data
    Data_Format = 1                             # 1: Debug data format (TOA, TOT, Cal, hitflag) 0: Real time data format (30-bit data)

    DAC_Value = DAC_Value_List[B_num]
    DAC_board[B_num]=DAC_Value[Pixel_Num]
    print(DAC_Value)
    DAC_Config(DAC_Value)
    reg_val = []                                # list for register config

    # Charge Injection setting
    Pixel_Num=Pixel_board[B_num]
    QSel = QSel_board[B_num]
    
    ETROC1_ArrayReg.set_QSel(QSel)
    QInj_Enable = [[0x01, 0x00], [0x02, 0x00], [0x04, 0x00], [0x08, 0x00], [0x10, 0x00], [0x20, 0x00], [0x40, 0x00], [0x80, 0x00],\
                [0x00, 0x01], [0x00, 0x02], [0x00, 0x04], [0x00, 0x08], [0x00, 0x10], [0x00, 0x20], [0x00, 0x40], [0x00, 0x80]]
    
    ETROC1_ArrayReg.set_EN_QInj7_0(QInj_Enable[Pixel_Num][0])       # Enable QInj7~0
    ETROC1_ArrayReg.set_EN_QInj15_8(QInj_Enable[Pixel_Num][1])      # Enable QInj15~
    #ETROC1_ArrayReg.set_EN_QInj7_0(0x00)       # Enable QInj7~0
    #ETROC1_ArrayReg.set_EN_QInj15_8(0x00)      # Enable QInj15~
    
    ## PreAmp setting
    CLSel = CLSel_board[B_num]                  # default 0
    RfSel = RfSel_board[B_num]
    IBSel = IBSel_board[B_num]

    ETROC1_ArrayReg.set_CLSel(CLSel)
    ETROC1_ArrayReg.set_RfSel(RfSel)
    ETROC1_ArrayReg.set_IBSel(IBSel)

    
    ## Discriminator setting
    ETROC1_ArrayReg.set_HysSel(0xf)
    EN_DiscriOut = [0x11, 0x21, 0x41, 0x81, 0x12, 0x22, 0x42, 0x82, 0x14, 0x24, 0x44, 0x84, 0x18, 0x28, 0x48, 0x88, 0x0f]
    ETROC1_ArrayReg.set_EN_DiscriOut(EN_DiscriOut[Pixel_Num])

    ## VDAC setting
    VTHOut_Select = [[0xfe, 0xff], [0xfd, 0xff], [0xfb, 0xff], [0xf7, 0xff], [0xef, 0xff], [0xdf, 0xff], [0xbf, 0xff], [0x7f, 0xff],\
                    [0xff, 0xfe], [0xff, 0xfd], [0xff, 0xfb], [0xff, 0xf7], [0xff, 0xef], [0xff, 0xdf], [0xff, 0xbf], [0xff, 0x7f], [0xff, 0xff]]
    ETROC1_ArrayReg.set_PD_DACDiscri7_0(VTHOut_Select[Pixel_Num][0])
    ETROC1_ArrayReg.set_PD_DACDiscri15_8(VTHOut_Select[Pixel_Num][1])
    ETROC1_ArrayReg.set_Dis_VTHInOut7_0(VTHOut_Select[Pixel_Num][0])
    ETROC1_ArrayReg.set_Dis_VTHInOut15_8(VTHOut_Select[Pixel_Num][1])

    ## Phase Shifter Setting
    ETROC1_ArrayReg.set_dllEnable(0)           # Enable phase shifter
    ETROC1_ArrayReg.set_dllCapReset(1)         # should be set to 0
    time.sleep(0.1)
    ETROC1_ArrayReg.set_dllCapReset(0)         # should be set to 0
    ETROC1_ArrayReg.set_dllCPCurrent(1)        # default value 1:
    ETROC1_ArrayReg.set_dllEnable(1)           # Enable phase shifter
    ETROC1_ArrayReg.set_dllForceDown(0)        # should be set to 0
    ETROC1_ArrayReg.set_PhaseAdj(PhaseAdj)     # 0-128 to adjust clock phas

    # 320M clock strobe setting
    ETROC1_ArrayReg.set_RefStrSel(0x03)        # default 0x03: 3.125 ns measuement windo

    # clock input and output MUX select
    ETROC1_ArrayReg.set_TestCLK0(1)            # 0: 40M and 320M clock comes from phase shifter, 1: 40M and 320M clock comes from external pads
    ETROC1_ArrayReg.set_TestCLK1(0)            # 0: 40M and 320M  go cross clock strobe 1: 40M and 320M bypass
    ETROC1_ArrayReg.set_CLKOutSel(1)           # 0: 40M clock output, 1: 320M clock or strobe outpu

    ## DMRO readout Mode
    DMRO_Readout_Select = [[0x01, 0x0], [0x02, 0x0], [0x04, 0x0], [0x08, 0x0], [0x01, 0x1], [0x02, 0x1], [0x04, 0x1], [0x08, 0x1],\
                        [0x01, 0x2], [0x02, 0x2], [0x04, 0x2], [0x08, 0x2], [0x01, 0x3], [0x02, 0x3], [0x04, 0x3], [0x08, 0x3]]
    ETROC1_ArrayReg.set_OE_DMRO_Row(DMRO_Readout_Select[Pixel_Num][0])       # DMRO readout row select
    ETROC1_ArrayReg.set_DMRO_Col(DMRO_Readout_Select[Pixel_Num][1])          # DMRO readout column selec
    ETROC1_ArrayReg.set_RO_SEL(0)              # 0: DMRO readout enable  1: Simple readout enable
    ETROC1_ArrayReg.set_TDC_enableMon(Test_Pattern_Mode_Output)       # 0: Connect to TDC       1: Connect to Test Counte

    ## TDC setting
    ETROC1_ArrayReg.set_TDC_resetn(1)
    ETROC1_ArrayReg.set_TDC_testMode(TDC_testMode)
    ETROC1_ArrayReg.set_TDC_autoReset(0)
    ETROC1_ArrayReg.set_TDC_enable(TDC_Enable

    ## DMRO Setting
    ETROC1_ArrayReg.set_DMRO_ENScr(EnScr)          # Enable DMRO scrambler
    ETROC1_ArrayReg.set_DMRO_revclk(DMRO_revclk)
    ETROC1_ArrayReg.set_DMRO_testMode(0)           # DMRO work on test mode
    Enable_FPGA_Descramblber(EnScr)                 # Enable FPGA Firmware Descramble

    ## DMRO CML driver
    ETROC1_ArrayReg.set_Dataout_AmplSel(7)
    ETROC1_ArrayReg.set_CLKTO_AmplSel(7)
    ETROC1_ArrayReg.set_CLKTO_disBIAS(0)
    reg_val = ETROC1_ArrayReg.get_config_vector()                      # Get Array Pixel Register default data

    ## Enable channel
    ## 0x0001: ch0
    ## 0x0002: ch1
    ## 0x0004: ch2
    ## 0x0008: ch3
    cmd_interpret.write_config_reg(15,0x0003);

    ## TimeStamp and Testmode
    ## 0x0000: Disable Testmode & Enable TimeStamp
    ## 0x0001: Disable Testmode & Disable TimeStamp
    ## 0x0010: Enable Testmode & Enable TimeStamp
    ## 0x0011: Enable Testmode & Disable TimeStamp
    cmd_interpret.write_config_reg(13,0x0000); 