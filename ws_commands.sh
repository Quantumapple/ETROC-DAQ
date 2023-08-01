#!/bin/bash

## Step 1.
## Initialize the i2c in WS and ETROC2 for WS testing:
## It configures the WS I2C to set the WS in bypass mode and use the
## ws_start/ws_stop FC command for power-on/off control. It also configure the
## ETROC2 i2c to enable the charge injection and set QSel to 31 (32fC).
python run_script.py -s 0x000C -v -w --hostname "192.168.2.3" -t 120 -l 100000 -o test --firmware --ws_i2c_initialization --nodaq


## Step 2.
## Check whether the FC command is setup correctly
## It sends out a onetime ws_start signal to enable the WS. 
## The current of VDDWSA should be ~75mA and the current of VDDWSD should be ~15mA after running the above command.
python run_script.py -s 0x000C -v -w --hostname 192.168.2.3 -t 120 -l 100000 -o test --firmware --fc_ws_start --nodaq

## Test the ws_stop FC command
## The current of VDDWSA should be ~20mA and the current of VDDWSD should be ~3mA after running the above command
python run_script.py -s 0x000C -v -w --hostname 192.168.2.3 -t 120 -l 100000 -o test --firmware --fc_ws_stop --nodaq

## If the current doesn’t change with ws_start/stop, use options ‘etroc2_i2c’ to reset (set data rate and do the alignment) the FC link
python run_script.py -s 0x000C -v -w --hostname 192.168.2.3 -t 120 -l 100000 -o test --firmware --nodaq --etroc2_i2c


## Step 3.
## WS test with charge injection
## It configures the FC to send out a onetime ws_start signal at 1BX, onetime charge
## injection at 3BX and 8BX, onetime ws_stop signal at 20BX (these FC command
## locations can be adjusted by modifying the FC command addresses specified in
## ‘WS_start_charge_injection_stop’ in the ‘daq_helpers.py’).
python run_script.py -s 0x000C -v -w --hostname 192.168.2.3 -t 120 -l 100000 -o test --firmware --ws_onetime_charge_injection --nodaq


## Step 4.
## Read the data in WS memory and store the output data in .txt file for further processing
## It reads out all data stored in the WS memory and saves them into a .txt file with specified file name.
python run_script.py -s 0x000C -v -w --hostname 192.168.2.3 -t 120 -l 100000 -o test --firmware --ws_memory_readout --nodaq

