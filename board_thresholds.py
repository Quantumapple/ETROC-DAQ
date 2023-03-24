#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is used to specify discrimiator thresholds for all the boards MANUALLY
'''
#--------------------------------------------------------------------------#

'''
A address is set using jumper pins on the ETROC1 board
There are 7 bits with 2 addressable, default value is 00000_A1_A2
Any inserted jumpers will flip the bit. Avoid address 00

''' 
'''
B address is set using jumper pins on the ETROC1 board
There are 7 bits with 2 addressable, default value is 11111_B1_B2
Any inserted jumpers will flip the bit

''' 

slaveA_addr_list = [0x03, 0x02, 0x01]
slaveB_addr_list = [0x7f, 0x7e, 0x7d]

board_side = [4, 4, 4]

pixel = {():, ():, ():}

for side in board_side:
    for i in range(side):
        for j in range(side):
            list.append()

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