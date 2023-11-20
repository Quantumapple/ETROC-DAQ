#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import threading
import numpy as np
import os, sys
from queue import Queue
from collections import deque
import queue
from command_interpret import *
import translate_data
import daq_helpers
import datetime

from pathlib import Path
sys.path.insert(1, f'../i2c_gui')
import plotly.express as px
import logging
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper
from i2c_gui.chips.etroc2_chip import register_decoding
from i2c_gui.chips.address_space_controller import Address_Space_Controller
from i2c_gui.i2c_connection_helper import I2C_Connection_Helper
from notebooks.notebook_helpers import *
import pandas as pd
from scripts.log_action import log_action_v2
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.pyplot as plt
#========================================================================================#
'''
@author: Murtaza Safdari
@date: 2023-11-19
This script is composed of all the helper functions for ws testing
'''
#--------------------------------------------------------------------------#
def div_ceil(x,y):
    return -(x//(-y))

#--------------------------------------------------------------------------#
# Threading class to only TRANSLATE the binary data and save to disk
class Translate_ws_data(threading.Thread):
    def __init__(self, name, firmware_key, check_valid_data_start, translate_queue, cmd_interpret, num_line, store_dict, skip_translation, board_ID, write_thread_handle, translate_thread_handle, compressed_translation, stop_DAQ_event = None, debug_event_translation = False, lock_translation_numwords = False, ws_chipname, ws_i2c_port, ws_chip_address, ws_address):
        threading.Thread.__init__(self, name=name)
        self.firmware_key            = firmware_key
        self.check_valid_data_start  = check_valid_data_start
        self.translate_queue         = translate_queue
        self.cmd_interpret           = cmd_interpret
        self.num_line                = num_line
        self.store_dict              = store_dict
        self.skip_translation        = skip_translation
        self.board_ID                = board_ID
        self.write_thread_handle     = write_thread_handle
        self.translate_thread_handle = translate_thread_handle
        self.stop_DAQ_event          = stop_DAQ_event
        self.compressed_translation  = compressed_translation
        self.debug_event_translation = debug_event_translation
        self.lock_translation_numwords = lock_translation_numwords
        self.translate_deque         = deque()
        self.valid_data              = False if check_valid_data_start else True
        self.header_pattern          = format(0xc3a3c3a, "028b")
        self.trailer_pattern         = '001011'
        self.channel_header_pattern  = format(0x3c5c, "016b")
        self.file_lines              = 0
        self.file_counter            = 0
        self.retry_count             = 0
        self.in_event                = False
        self.eth_words_in_event      = -1
        self.words_in_event          = -1
        self.current_word            = -1
        self.event_number            = -1
        self.ws_chipname             = ws_chipname
        self.ws_i2c_port             = ws_i2c_port
        self.ws_chip_address         = ws_chip_address
        self.ws_address              = ws_address
        # I2C Device Setup
        i2c_gui.__no_connect__       = False
        i2c_gui.__no_connect_type__  = "echo"
        log_level                    = 30
        logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
        logger                       = logging.getLogger("Script_Logger")
        self.Script_Helper           = i2c_gui.ScriptHelper(logger)
        self.conn                    = i2c_gui.Connection_Controller(self.Script_Helper)
        self.conn.connection_type    = "USB-ISS"
        self.conn.handle: USB_ISS_Helper
        self.conn.handle.port        = self.ws_i2c_port
        self.conn.handle.clk         = 100
        self.conn.connect()
        self.chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=self.conn)
        self.chip.config_i2c_address(self.ws_chip_address)
        self.chip.config_waveform_sampler_i2c_address(self.ws_address)
        logger.setLevel(log_level)
        today = datetime.date.today()
        todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
        base_dir = Path(todaystr)
        base_dir.mkdir(exist_ok=True)
        # Perform Auto-calibration on WS pixel (Row0, Col14)
        # Reset the maps
        baseLine = 0
        noiseWidth = 0
        row_indexer_handle,_,_ = self.chip.get_indexer("row")
        column_indexer_handle,_,_ = self.chip.get_indexer("column")
        row = 0
        col = 14
        column_indexer_handle.set(col)
        row_indexer_handle.set(row)
        # Disable TDC
        self.pixel_decoded_register_write("enable_TDC", "0")
        # Enable THCal clock and buffer, disable bypass
        self.pixel_decoded_register_write("CLKEn_THCal", "1")
        self.pixel_decoded_register_write("BufEn_THCal", "1")
        self.pixel_decoded_register_write("Bypass_THCal", "0")
        self.pixel_decoded_register_write("TH_offset", format(0x07, '06b'))
        # Reset the calibration block (active low)
        self.pixel_decoded_register_write("RSTn_THCal", "0")
        self.pixel_decoded_register_write("RSTn_THCal", "1")
        # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
        self.pixel_decoded_register_write("ScanStart_THCal", "1")
        self.pixel_decoded_register_write("ScanStart_THCal", "0")
        # Check the calibration done correctly
        if(pixel_decoded_register_read("ScanDone", "Status")!="1"): print("!!!ERROR!!! Scan not done!!!")
        baseLine = self.pixel_decoded_register_read("BL", "Status", need_int=True)
        noiseWidth = self.pixel_decoded_register_read("NW", "Status", need_int=True)
        # Disable clock and buffer before charge injection
        self.pixel_decoded_register_write("CLKEn_THCal", "0")
        self.pixel_decoded_register_write("BufEn_THCal", "0")
        # Set Charge Inj Q to 15 fC
        self.pixel_decoded_register_write("QSel", format(0x0e, '05b'))
        ### Print BL and NW from automatic calibration
        print(f"Calibrated (R,C)=(0,14) with BL: {baseLine}, NW: {noiseWidth}")
        ### Disable all pixel readouts before doing anything
        # row_indexer_handle,_,_ = chip.get_indexer("row")
        # column_indexer_handle,_,_ = chip.get_indexer("column")
        # column_indexer_handle.set(0)
        # row_indexer_handle.set(0)
        # broadcast_handle,_,_ = chip.get_indexer("broadcast")
        # broadcast_handle.set(True)
        # pixel_decoded_register_write("disDataReadout", "1")
        # broadcast_handle.set(True)
        # pixel_decoded_register_write("QInjEn", "0")
        # broadcast_handle.set(True)
        # pixel_decoded_register_write("disTrigPath", "1")

    def pixel_decoded_register_write(self, decodedRegisterName, data_to_write):
        bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Pixel Config"][decodedRegisterName]["bits"]
        handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", decodedRegisterName)
        self.chip.read_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        self.chip.write_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)

    def pixel_decoded_register_read(self, decodedRegisterName, key, need_int=False):
        handle = self.chip.get_decoded_indexed_var("ETROC2", f"Pixel {key}", decodedRegisterName)
        self.chip.read_decoded_value("ETROC2", f"Pixel {key}", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def peripheral_decoded_register_write(self, decodedRegisterName, data_to_write):
        bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"][decodedRegisterName]["bits"]
        handle = self.chip.get_decoded_display_var("ETROC2", "Peripheral Config", decodedRegisterName)
        self.chip.read_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        self.chip.write_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)

    def peripheral_decoded_register_read(self, decodedRegisterName, key, need_int=False):
        handle = self.chip.get_decoded_display_var("ETROC2", f"Peripheral {key}", decodedRegisterName)
        self.chip.read_decoded_value("ETROC2", f"Peripheral {key}", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def ws_decoded_register_write(self, decodedRegisterName, data_to_write):
        bit_depth = register_decoding["Waveform Sampler"]["Register Blocks"]["Config"][decodedRegisterName]["bits"]
        handle = self.chip.get_decoded_display_var("Waveform Sampler", "Config", decodedRegisterName)
        self.chip.read_decoded_value("Waveform Sampler", "Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        self.chip.write_decoded_value("Waveform Sampler", "Config", decodedRegisterName)

    def ws_decoded_config_read(self, decodedRegisterName, need_int=False):
        handle = self.chip.get_decoded_display_var("Waveform Sampler", f"Config", decodedRegisterName)
        self.chip.read_decoded_value("Waveform Sampler", f"Config", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def ws_decoded_status_read(self, decodedRegisterName, need_int=False):
        handle = self.chip.get_decoded_display_var("Waveform Sampler", f"Status", decodedRegisterName)
        self.chip.read_decoded_value("Waveform Sampler", f"Status", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def reset_params(self):
        self.translate_deque.clear()
        self.in_event           = False
        self.eth_words_in_event = -1
        self.words_in_event     = -1
        self.current_word       = -1
        self.event_number       = -1

    def run(self):
        t = threading.current_thread()
        t.alive      = True

        self.chip.read_all_address_space("Waveform Sampler") # Read all registers of WS
        rd_addr_handle = self.chip.get_decoded_display_var("Waveform Sampler", "Config", "rd_addr")
        dout_handle = self.chip.get_decoded_display_var("Waveform Sampler", "Status", "dout")
        
        if(not self.skip_translation): 
            outfile  = open("%s/TDC_Data_translated_%d.dat"%(self.store_dict, self.file_counter), 'w')
            print("{} is reading queue and translating file {}...".format(self.getName(), self.file_counter))
        else:
            print("{} is reading queue and translating...".format(self.getName()))
        while True:
            if not t.alive:
                print("Translate Thread detected alive=False")
                if(not self.skip_translation): outfile.close()
                break 
            if((not self.skip_translation) and self.file_lines>self.num_line):
                outfile.close()
                self.file_lines   = 0
                self.file_counter = self.file_counter + 1
                outfile = open("%s/TDC_Data_translated_%d.dat"%(self.store_dict, self.file_counter), 'w')
                print("{} is reading queue and translating file {}...".format(self.getName(), self.file_counter))
            binary = ""
            # Attempt to pop off the translate_queue for 30 secs, fail if nothing found
            try:
                binary = self.translate_queue.get(True, 1)
                self.retry_count = 0
            except queue.Empty:
                if not self.stop_DAQ_event.is_set:
                    self.retry_count = 0
                    continue
                if self.translate_thread_handle.is_set():
                    print("Translate Thread received STOP signal AND ran out of data to translate")
                    break
                self.retry_count += 1
                if self.retry_count < 30:
                    continue
                print("BREAKING OUT OF TRANSLATE LOOP CAUSE I'VE WAITING HERE FOR 30s SINCE LAST FETCH FROM TRANSLATE_QUEUE!!!")
                break
            # Event Header Found
            if(binary[0:28]==self.header_pattern):
                self.reset_params()
                self.in_event = True
                self.translate_deque.append(binary)
                continue
            # Event Header Line Two Found
            elif(self.in_event and (self.words_in_event==-1) and (binary[0:4]==self.firmware_key)):
                self.current_word       = 0
                self.event_number       = int(binary[ 4:20], base=2)
                self.words_in_event     = int(binary[20:30], base=2)
                self.eth_words_in_event = div_ceil(40*self.words_in_event,32)
                # TODO EVENT TYPE?
                self.translate_deque.append(binary)
                # Set valid_data to true once we see fresh data
                if(self.event_number==1): self.valid_data = True
                continue
            # Event Header Line Two NOT Found after the Header
            elif(self.in_event and (self.words_in_event==-1) and (binary[0:4]!=self.firmware_key)):
                self.reset_params()
                continue
            # Trailer NOT Found after the required number of ethernet words was read
            elif(self.in_event and (self.eth_words_in_event==self.current_word) and (binary[0:6]!=self.trailer_pattern) and (not self.debug_event_translation)):
                self.reset_params()
                continue
            # Trailer Found - DO NOT CONTINUE
            elif(self.in_event and (self.eth_words_in_event==self.current_word) and (binary[0:6]==self.trailer_pattern) and (not self.debug_event_translation)):
                self.translate_deque.append(binary)
            # Trailer Found - Debug is true
            elif(self.in_event and (binary[0:6]==self.trailer_pattern) and (self.debug_event_translation)):
                if((self.eth_words_in_event==self.current_word and self.lock_translation_numwords) or (not self.lock_translation_numwords)):
                    self.translate_deque.append(binary)
            # Event Data Word
            elif(self.in_event):
                self.translate_deque.append(binary)
                self.current_word += 1
                continue
            # Ethernet Line not inside Event, Skip it
            else: continue

            # We only come here if we saw a Trailer, but let's put a failsafe regardless
            if((not self.debug_event_translation) and len(self.translate_deque)!=self.eth_words_in_event+3): 
                self.reset_params()
                continue

            # This is where we do the WS I2C stuff
            ### Read from WS memory
            self.ws_decoded_register_write("rd_en_I2C", "1")
            max_steps = 1024  # Size of the data buffer inside the WS
            lastUpdateTime = time.time_ns()
            base_data = []
            coeff = 0.05/5*8.5  # This number comes from the example script in the manual
            time_coeff = 1/2.56  # 2.56 GHz WS frequency
            ws_address_space_controller: Address_Space_Controller = self.chip._address_space["Waveform Sampler"]
            i2c_controller: I2C_Connection_Helper = self.chip._i2c_controller
            addr_regs = [0x00, 0x00]  # regOut1C and regOut1D
            for address in range(max_steps):
                addr_regs[0] = ((address & 0b11) << 6)          # 0x1C
                addr_regs[1] = ((address & 0b1111111100) >> 2)  # 0x1D
                i2c_controller.write_device_memory(ws_address, 0x1C, addr_regs, 8)
                tmp_data = i2c_controller.read_device_memory(ws_address, 0x20, 2, 8)
                data = hex((tmp_data[0] >> 2) + (tmp_data[1] << 6))
                binary_data = bin(int(data, 0))[2:].zfill(14)  # because dout is 14 bits long
                Dout_S1 = int('0b'+binary_data[1:7], 0)
                Dout_S2 = int(binary_data[ 7]) * 24 + \
                            int(binary_data[ 8]) * 16 + \
                            int(binary_data[ 9]) * 10 + \
                            int(binary_data[10]) *  6 + \
                            int(binary_data[11]) *  4 + \
                            int(binary_data[12]) *  2 + \
                            int(binary_data[13])
                base_data.append(
                    {
                        "Data Address": address,
                        "Data": int(data, 0),
                        "Raw Data": bin(int(data, 0))[2:].zfill(14),
                        "pointer": int(binary_data[0]),
                        "Dout_S1": Dout_S1,
                        "Dout_S2": Dout_S2,
                        "Dout": Dout_S1 - coeff * Dout_S2,
                    }
                )
            df = pd.DataFrame(base_data)
            df_length = len(df)
            channels = 8
            df_per_ch : list[pd.DataFrame] = []
            for ch in range(channels):
                df_per_ch += [df.iloc[int(ch * df_length/channels):int((ch + 1) * df_length/channels)].copy()]
                df_per_ch[ch].reset_index(inplace = True, drop = True)
            pointer_idx = df_per_ch[-1]["pointer"].loc[df_per_ch[-1]["pointer"] != 0].index  # TODO: Maybe add a search of the pointer in any channel, not just the last one
            if len(pointer_idx) != 0:  # If pointer found, reorder the data
                pointer_idx = pointer_idx[0]
                new_idx = list(set(range(len(df_per_ch[-1]))).difference(range(pointer_idx+1))) + list(range(pointer_idx+1))
                for ch in range(channels):
                    df_per_ch[ch] = df_per_ch[ch].iloc[new_idx].reset_index(drop = True)  # Fix indexes after reordering
            # interleave the channels
            for ch in range(channels):
                df_per_ch[ch]["Time Index"] = df_per_ch[ch].index * channels + (channels - 1 - ch)  # Flip the order of the channels in the interleave...
                df_per_ch[ch]["Channel"] = ch + 1
            # Actually put it all together in one dataframe and sort the data correctly
            df = pd.concat(df_per_ch)
            df["Time [ns]"] = df["Time Index"] * time_coeff
            df.set_index('Time Index', inplace=True)
            df.sort_index(inplace=True)
            # Disable reading data from WS:
            self.ws_decoded_register_write("rd_en_I2C", "0")

            output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv"
            outfile = base_dir / output
            df.to_csv(outfile)
            df['Aout'] = -(df['Dout']-(31.5-coeff*31.5)*1.2)/32
            output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".png"
            outfile = base_dir / output
            fig, ax = plt.subplots(figsize=(20, 8))
            ax.plot(df['Time [ns]'], df['Dout'])
            ax.set_xlabel('Time [ns]', fontsize=15)
            plt.savefig(outfile)

            fig_aout = px.line(
                df,
                x="Time [ns]",
                y="Aout",
                labels = {
                    "Time [ns]": "Time [ns]",
                    "Aout": "",
                },
                title = "Waveform (Aout) from the board {}".format(self.ws_chipname),
                markers=True
            )
            fig_dout = px.line(
                df,
                x="Time [ns]",
                y="Dout",
                labels = {
                    "Time [ns]": "Time [ns]",
                    "Dout": "",
                },
                title = "Waveform (Dout) from the board {}".format(self.ws_chipname),
                markers=True
            )
            # todaystr = "../ETROC-figures/" + today.isoformat() + "_Array_Test_Results/"
            # base_dir = Path(todaystr)
            # base_dir.mkdir(exist_ok=True)
            fig_aout.write_html(
                base_dir / f'WS_Aout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.html',
                full_html = False,
                include_plotlyjs = 'cdn',
            )
            fig_dout.write_html(
                base_dir / f'WS_Dout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.html',
                full_html = False,
                include_plotlyjs = 'cdn',
            )

            # This is where we translate the TDC data from this data frame
            TDC_data = translate_data.etroc_translate_binary(self.translate_deque, self.valid_data, self.board_ID, self.compressed_translation, self.channel_header_pattern, self.header_pattern, self.trailer_pattern, self.debug_event_translation)
            TDC_len = len(TDC_data)
            if((not self.skip_translation) and (TDC_len>0)): 
                for TDC_line in TDC_data:
                    outfile.write("%s\n"%TDC_line)
                self.file_lines  = self.file_lines  + TDC_len

            # Reset all params before moving onto the next line
            del TDC_data, TDC_len, binary
            self.reset_params()

            # Clear WS Trig Block
            daq_helpers.software_clear_ws_trig_block(self.cmd_interpret)
        
        print("Translate Thread gracefully ending") 
        self.translate_thread_handle.set()
        del t
        if(not self.skip_translation): outfile.close()
        print("%s finished!"%self.getName())
