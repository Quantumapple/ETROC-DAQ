#!/usr/bin/env python
# -*- coding: utf-8 -*-
#========================================================================================#
'''
@author: Wei Zhang, Murtaza Safdari, Jongho Lee
@date: 2023-03-24
This script is used to define the I2C addresses of all the relevant boards
Also used to define any relevant details for each corresponding board
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

slaveA_addr_list = [0x03,  0x02,  0x01]
slaveB_addr_list = [0x7f,  0x7e,  0x7d]
#slaveA_addr_list = [0x03,  0x02,  0x01, 0x00]
#slaveB_addr_list = [0x7f,  0x7e,  0x7d, 0x7c]

# Use this to control how many boards are actually attempted for connection
board_type       = [2, 1, 1, 1]            # ETROC version number

active_channels_key = 0x008B
## Register 11
## 4-digit 16 bit hex, Duration
register_11_key = 0x0021
## Register 12
## 4-digit 16 bit hex, 0xWXYZ
## WX (8 bit) -  Error Mask
## Y - trigSize[1:0],Period,testTrig
## Z - Input command
register_12_key = 0x0036


board_size       = [256, 16, 16, 256]

board_name       = ["F28", "F29", "F30", "F47"]
board_ID         = ["10111111100001111","00000000000000000","00000000000000000", "00000000000000000"] 
# 10111111100001111
CLSel_board      = [  0,    0,    0, 0 ]			# Load Capacitance of the preamp first stage, default 0
RfSel_board      = [  2,    2,    2, 2 ]			# Feedback resistance seleciton
IBSel_board      = [  0,    0,    0, 0 ]			# Bias current selection of the input transistor in the preamp

def single_pixel_threshold(size, address, threshold):
	threshold_list = []
	for i in range(size):
		if i==address:
			threshold_list.append(threshold)
		else:
			threshold_list.append(0x000)
	return threshold_list


