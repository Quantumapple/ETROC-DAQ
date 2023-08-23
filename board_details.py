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

# Use this to control how many boards are actually attempted for connection
# ETROC version number
board_type       = [2, 2, 2, 2]

board_size       = [256, 256, 256, 256]
board_name       = ["F28", "F29", "F30", "F47"]
# 17F0F =  10111111100001111
board_ID         = ["10111111100001111","10111111100001111","10111111100001111", "10111111100001111"]