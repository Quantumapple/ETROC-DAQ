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
def return_initialized_ws_chip(ws_i2c_port, ws_chip_address, ws_address):
    # I2C Device Setup
    i2c_gui.__no_connect__       = False
    i2c_gui.__no_connect_type__  = "echo"
    log_level                    = 30
    logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
    logger                       = logging.getLogger("Script_Logger")
    Script_Helper           = i2c_gui.ScriptHelper(logger)
    conn                    = i2c_gui.Connection_Controller(Script_Helper)
    conn.connection_type    = "USB-ISS"
    conn.handle: USB_ISS_Helper
    conn.handle.port        = ws_i2c_port
    conn.handle.clk         = 100
    conn.connect()
    chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=conn)
    chip.config_i2c_address(ws_chip_address)
    chip.config_waveform_sampler_i2c_address(ws_address)
    logger.setLevel(log_level)
    chip.read_all_address_space("Waveform Sampler") # Read all registers of WS
    return chip

#--------------------------------------------------------------------------#
# Threading class to only TRANSLATE the binary data and save to disk
class Translate_ws_data(threading.Thread):
    def __init__(self, name, verbose, firmware_key, check_valid_data_start, translate_queue, cmd_interpret, num_line, store_dict, skip_translation, board_ID, write_thread_handle, translate_thread_handle, compressed_translation, stop_DAQ_event = None, debug_event_translation = False, lock_translation_numwords = False, ws_chip=None, ws_chipname=None, ws_i2c_port=None, ws_chip_address=None, ws_address=None):
        threading.Thread.__init__(self, name=name)
        self.verbose                 = verbose
        self.firmware_key            = firmware_key
        self.check_valid_data_start  = check_valid_data_start
        self.translate_queue         = translate_queue
        self.cmd_interpret           = cmd_interpret
        self.num_line                = num_line
        self.store_dict              = store_dict
        self.base_dir                = store_dict
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
        self.chip                    = ws_chip
        # self.run()
        # self.start_ws_sampling()

        # today = datetime.date.today()
        # todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
        # self.base_dir = Path(todaystr)
        # self.base_dir.mkdir(exist_ok=True)
        # Perform Auto-calibration on WS pixel (Row0, Col14)
        # Reset the maps
        # baseLine = 0
        # noiseWidth = 0
        # row_indexer_handle,_,_ = self.chip.get_indexer("row")
        # column_indexer_handle,_,_ = self.chip.get_indexer("column")
        # row = 0
        # col = 14
        # column_indexer_handle.set(col)
        # row_indexer_handle.set(row)
        # # Disable TDC
        # self.pixel_decoded_register_write("enable_TDC", "0")
        # # Enable THCal clock and buffer, disable bypass
        # self.pixel_decoded_register_write("CLKEn_THCal", "1")
        # self.pixel_decoded_register_write("BufEn_THCal", "1")
        # self.pixel_decoded_register_write("Bypass_THCal", "0")
        # self.pixel_decoded_register_write("TH_offset", format(0x07, '06b'))
        # # Reset the calibration block (active low)
        # self.pixel_decoded_register_write("RSTn_THCal", "0")
        # self.pixel_decoded_register_write("RSTn_THCal", "1")
        # # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
        # self.pixel_decoded_register_write("ScanStart_THCal", "1")
        # self.pixel_decoded_register_write("ScanStart_THCal", "0")
        # # Check the calibration done correctly
        # if(self.pixel_decoded_register_read("ScanDone", "Status")!="1"): print("!!!ERROR!!! Scan not done!!!")
        # baseLine = self.pixel_decoded_register_read("BL", "Status", need_int=True)
        # noiseWidth = self.pixel_decoded_register_read("NW", "Status", need_int=True)
        # # Disable clock and buffer before charge injection
        # self.pixel_decoded_register_write("CLKEn_THCal", "0")
        # self.pixel_decoded_register_write("BufEn_THCal", "0")
        # # Set Charge Inj Q to 15 fC
        # self.pixel_decoded_register_write("QSel", format(0x0e, '05b'))
        # ### Print BL and NW from automatic calibration
        # print(f"Calibrated (R,C)=(0,14) with BL: {baseLine}, NW: {noiseWidth}")
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

    # def ws_decoded_register_write(self, decodedRegisterName, data_to_write):
    #     bit_depth = register_decoding["Waveform Sampler"]["Register Blocks"]["Config"][decodedRegisterName]["bits"]
    #     print("Got bit depth")
    #     handle = self.chip.get_decoded_display_var("Waveform Sampler", "Config", decodedRegisterName)
    #     print("GOt handle")
    #     self.chip.read_decoded_value("Waveform Sampler", "Config", decodedRegisterName)
    #     print("Read decoded value")
    #     if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
    #     data_hex_modified = hex(int(data_to_write, base=2))
    #     if(bit_depth>1): handle.set(data_hex_modified)
    #     elif(bit_depth==1): handle.set(data_to_write)
    #     else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
    #     print("handle set")
    #     self.chip.write_decoded_value("Waveform Sampler", "Config", decodedRegisterName)
    #     print("wrote decoded value")

    # def ws_decoded_config_read(self, decodedRegisterName, need_int=False):
    #     handle = self.chip.get_decoded_display_var("Waveform Sampler", f"Config", decodedRegisterName)
    #     self.chip.read_decoded_value("Waveform Sampler", f"Config", decodedRegisterName)
    #     if(need_int): return int(handle.get(), base=16)
    #     else: return handle.get()

    # def ws_decoded_status_read(self, decodedRegisterName, need_int=False):
    #     handle = self.chip.get_decoded_display_var("Waveform Sampler", f"Status", decodedRegisterName)
    #     self.chip.read_decoded_value("Waveform Sampler", f"Status", decodedRegisterName)
    #     if(need_int): return int(handle.get(), base=16)
    #     else: return handle.get()

    def start_ws_sampling(self):
        i2c_controller: I2C_Connection_Helper = self.chip._i2c_controller
        reg_all = i2c_controller.read_device_memory(self.ws_address, 0x0D, 17, 8)
        reg_all[-1] = 0x22
        i2c_controller.write_device_memory(self.ws_address, 0x1F, [reg_all[-1]], 8)
        reg_all[-1] = 0x0b
        i2c_controller.write_device_memory(self.ws_address, 0x1F, [reg_all[-1]], 8)
        # reg_all[-1] = reg_all[-1] & 0b11111110                 # 0: mem_rstn, reset memory
        # i2c_controller.write_device_memory(self.ws_address, 0x1F, [reg_all[-1]], 8)
        # reg_all[-1] = reg_all[-1] | 0b00000001                 # 0: mem_rstn, reset memory
        # i2c_controller.write_device_memory(self.ws_address, 0x1F, [reg_all[-1]], 8)
        # reg_all[-1] = reg_all[-1] & 0b11110111               # 0: clk_gen_rstn, reset clock generation
        # reg_all[-1] = reg_all[-1] & 0b01111111               # sel1, 0: Bypass mode, 1: VGA mode
        reg_all[2] = 0x00                                      # DDT 0F, Time Skew Calibration set to 0
        reg_all[1] = 0x00                                      # DDT 0E, Time Skew Calibration set to 0
        i2c_controller.write_device_memory(self.ws_address, 0x0E, [reg_all[1],reg_all[2]], 8)
        reg_all[0] = (reg_all[0] & 0b11110111) | 0b00010000    # 0D CTRL default = 0x10 for regOut0D
        # reg_all[0] = (reg_all[0] & 0b11101111) | 0b00001000    # 0D CTRL default = 0x01 for regOut0D
        # reg_all[0] = reg_all[0] | 0b00011000                   # 0D CTRL default = 0x11 for regOut0D
        # reg_all[0] = reg_all[0] & 0b11100111                   # 0D CTRL default = 0x00 for regOut0D
        reg_all[0] = reg_all[0] & 0b00011111                   # 0D comp_cali Comparator calibration should be off
        i2c_controller.write_device_memory(self.ws_address, 0x0D, reg_all, 8)
        print("Chip WS Config Done!")

    def reset_params(self):
        self.translate_deque.clear()
        self.in_event           = False
        self.eth_words_in_event = -1
        self.words_in_event     = -1
        self.current_word       = -1
        self.event_number       = -1

    def single_run(self):
        t = threading.current_thread()
        t.alive      = True

        # This is where we do the WS I2C stuff
        print("Entering WS I2C Reading...")
        i2c_controller: I2C_Connection_Helper = self.chip._i2c_controller

        ### Read from WS memory
        reg1F = i2c_controller.read_device_memory(self.ws_address, 0x1F, 1, 8)
        reg1F[0] = reg1F[0] | 0b00000100
        i2c_controller.write_device_memory(self.ws_address, 0x1F, reg1F, 8)
        #self.ws_decoded_register_write("rd_en_I2C", "1")
        print("rd_en_I2C set to 1")

        max_steps = 1024  # Size of the data buffer inside the WS
        lastUpdateTime = time.time_ns()
        base_data = []
        coeff = 0.05/5*8.5  # This number comes from the example script in the manual
        time_coeff = 1/2.56  # 2.56 GHz WS frequency
        addr_regs = [0x00, 0x00]  # regOut1C and regOut1D
        for address in range(max_steps):
            addr_regs[0] = ((address & 0b11) << 6)          # 0x1C
            addr_regs[1] = ((address & 0b1111111100) >> 2)  # 0x1D
            i2c_controller.write_device_memory(self.ws_address, 0x1C, addr_regs, 8)
            tmp_data = i2c_controller.read_device_memory(self.ws_address, 0x20, 2, 8)
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
        print("Done with Address Loop")
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
        reg1F = i2c_controller.read_device_memory(self.ws_address, 0x1F, 1, 8)
        reg1F[0] = reg1F[0] & 0b11111011
        i2c_controller.write_device_memory(self.ws_address, 0x1F, reg1F, 8)
        # Restart the WS Sampler
        self.start_ws_sampling()
        print("rd_en_i2c set to 0 AND restarted WS")
        output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + f"_{plot_counter}.csv"
        outfilename = self.base_dir +f"/{output}"
        df.to_csv(outfilename)
        df['Aout'] = -(df['Dout']-(31.5-coeff*31.5)*1.2)/32
        output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + f"_{plot_counter}.png"
        outfilename = self.base_dir +f"/{output}"
        # fig, ax = plt.subplots(figsize=(20, 8))
        # ax.plot(df['Time [ns]'], df['Dout'])
        # ax.set_xlabel('Time [ns]', fontsize=15)
        # plt.savefig(outfilename)
        # plt.close()

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
            self.base_dir + f'/WS_Aout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_{plot_counter}.html',
            full_html = False,
            include_plotlyjs = 'cdn',
        )
        fig_dout.write_html(
            self.base_dir + f'/WS_Dout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_{plot_counter}.html',
            full_html = False,
            include_plotlyjs = 'cdn',
        )

        # Clear WS Trig Block
        daq_helpers.software_clear_ws_trig_block(self.cmd_interpret)
        print("Done with WS I2C Reading and Released L1A Block")
        plot_counter += 1
        print("WS Thread gracefully ending")
        self.translate_thread_handle.set()
        del t
        print("%s finished!"%self.getName())

    def run(self):
        t = threading.current_thread()
        t.alive      = True
        plot_counter = 0
        while True:
            if not t.alive:
                print("Translate Thread detected alive=False")
                break

            # This is where we do the WS I2C stuff
            print("Entering WS I2C Reading...")
            i2c_controller: I2C_Connection_Helper = self.chip._i2c_controller

            ### Read from WS memory
            reg1F = i2c_controller.read_device_memory(self.ws_address, 0x1F, 1, 8)
            reg1F[0] = reg1F[0] | 0b00000100
            i2c_controller.write_device_memory(self.ws_address, 0x1F, reg1F, 8)
            #self.ws_decoded_register_write("rd_en_I2C", "1")
            print("rd_en_I2C set to 1")

            max_steps = 1024  # Size of the data buffer inside the WS
            lastUpdateTime = time.time_ns()
            base_data = []
            coeff = 0.05/5*8.5  # This number comes from the example script in the manual
            time_coeff = 1/2.56  # 2.56 GHz WS frequency
            addr_regs = [0x00, 0x00]  # regOut1C and regOut1D
            for address in range(max_steps):
                addr_regs[0] = ((address & 0b11) << 6)          # 0x1C
                addr_regs[1] = ((address & 0b1111111100) >> 2)  # 0x1D
                i2c_controller.write_device_memory(self.ws_address, 0x1C, addr_regs, 8)
                tmp_data = i2c_controller.read_device_memory(self.ws_address, 0x20, 2, 8)
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
            print("Done with Address Loop")
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
            reg1F = i2c_controller.read_device_memory(self.ws_address, 0x1F, 1, 8)
            reg1F[0] = reg1F[0] & 0b11111011
            i2c_controller.write_device_memory(self.ws_address, 0x1F, reg1F, 8)
            # Restart the WS Sampler
            self.start_ws_sampling()
            print("rd_en_i2c set to 0 AND restarted WS")
            output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + f"_{plot_counter}.csv"
            outfilename = self.base_dir +f"/{output}"
            df.to_csv(outfilename)
            df['Aout'] = -(df['Dout']-(31.5-coeff*31.5)*1.2)/32
            output = f"rawdataWS_{self.ws_chipname}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + f"_{plot_counter}.png"
            outfilename = self.base_dir +f"/{output}"
            # fig, ax = plt.subplots(figsize=(20, 8))
            # ax.plot(df['Time [ns]'], df['Dout'])
            # ax.set_xlabel('Time [ns]', fontsize=15)
            # plt.savefig(outfilename)
            # plt.close()

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
                self.base_dir + f'/WS_Aout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_{plot_counter}.html',
                full_html = False,
                include_plotlyjs = 'cdn',
            )
            fig_dout.write_html(
                self.base_dir + f'/WS_Dout_{self.ws_chipname}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_{plot_counter}.html',
                full_html = False,
                include_plotlyjs = 'cdn',
            )

            # Clear WS Trig Block
            daq_helpers.software_clear_ws_trig_block(self.cmd_interpret)
            print("Done with WS I2C Reading and Released L1A Block")
            plot_counter += 1
            if self.translate_thread_handle.is_set():
                # print("Translate Thread received STOP signal AND ran out of data to translate")
                break
        
        print("Translate Thread gracefully ending") 
        self.translate_thread_handle.set()
        del t
        print("%s finished!"%self.getName())
