#! /usr/bin/env python3
# -*- coding: utf-8 -*-

""" FIXME --- DCO
"""

#import ast

import click
import numpy as np
import sys
        
# XXX --  FIXME -- 
import socket

import pyeudaq
from pyeudaq import EUDAQ_INFO, EUDAQ_ERROR, EUDAQ_DEBUG, EUDAQ_WARN

import queue
import time

# PROVISIONAL!!
import daq_helpers
from command_interpret import command_interpret as fpga_commands
#from etroc_daq import daq_helpers 
#from etroc_daq import command_interpret as fpga_commands


#def create_a_timestamp():
#    return datetime.datetime.now().strftime("%Y%m%d%H%M")


# XXX -- FIXME -- Provisional, this should be taken care by the etroc daq
class ETROCDaq:
    def __init__(self, hostname, port):
        # Create socket TCP IPv4 communication
        # self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._s.connect((hostname, int(port)))

        #### Murtaza's testing ->
        try:
            # initial socket
            self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            print("Failed to create socket!")
            sys.exit()
        try:
            # connect socket
            self._s.connect((hostname, int(port)))
        except socket.error:
            print("failed to connect to ip " + hostname)
            sys.exit()
        #### <- End

        # And create the command interpreter to be sent/received 
        # through this socket
        self._cmd  = fpga_commands(self._s)
        print("cmd_interpret object created and connected")

        # Some data members they are going to be set at some point
        # self._num_fifo_read = 65536
        self._num_fifo_read = 50000         #### Murtaza's testing
        
    def init(self):
        """Probably needed
        """
        pass

    def configure(self):
        """Probably needed...
        """
        pass

    def close(self):
        """XXX -- What should I do here?? 
        """
        self._s.close()
        print("cmd_interpret object deleted")

    def reset(self):
        """Clear software FIFO data and event counters
        """
        # Just try to do this no so often...
        daq_helpers.software_clear_fifo(self._cmd)
        time.sleep(2.1)
        print("Cleared fifo and waited 2 seconds")

    
    # --- XXX -- Convert them into properties using write_config_reg and read_config_reg 
    #     functions

    def firmware_settings(self):
        """XXX -- Los de abajo
        """ 
        pass

    def active_channels(self,channels_bits):
        """Enable channel for the board (chips connected)
        
        Parameters
        ----------
        channels_bit: int 
            A 4 bit binary [0bwxyz], being  w - ch3, x - ch2, y - ch1 and z - ch0
            XXX -- What are those channels? 
            Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
            Register 15, needs firmware option 0xWXYZ,  
                * Z is a bit 4 bit binary wxyz Channel Enable (1=Enable)
                * Y is a bit 4 bit binary wxyz Board Type (1=Etroc2)
        """
        #                                               W     X    Y     Z 
        # Note: Global Trigger Enable is 0x0401 -> 0b[0000][0100][0000][0001]
        daq_helpers.active_channels(self._cmd, channels_bits)
        print(f"active channels set to {format(channels_bits, '016b')}")
        # EQUIVALENT TO self._cmd.write_config_reg(15, channels_bits)

    def timestamp(self,timestamp_bits):
        """Set timeStamp and testmode
        
        Parameters
        -----------
        timestamp_bits: int
            A 4-bit binary 0bWXYZ, where 
                * 0000: Enable  Testmode & Enable TimeStamp
                * 0001: Enable  Testmode & Disable TimeStamp
                * 0010: Disable Testmode & Enable TimeStamp
                * 0011: Disable Testmode & Disable TimeStamp 
            Note that the input needs to be a 4-digit 16 bit hex, 0x000(WXYZ)
        """
        # Need to modify it for the global trigger, in eudaq, always
        # is run in global external triggerL (LSB[2:0] -> needs to be 10
        modified_timestamp_bits = int(f"{timestamp_bits:016b}"[:-2]+'00', base=2)
        daq_helpers.timestamp(self._cmd, timestamp_bits)
        print(f"timestamp to {format(modified_timestamp_bits, '016b')}")

        # EQUIVALENT TO self._cmd.write_config_reg(13, timestamp_bits)

    def trigger_bit_delay(self, selftrigger_delay, trigger_board):
        """Set delay between the self trigger line and ... XXX -- FIXME doc
        XXX -- Could it be? The self-trigger is sent by a chip to the FPGA, the FPGA
        receives the self-trigger signal, then this signal is used to assert the L1A command (in 
        the FPGA) to activate the data stream dump from the chips

        Parameters
        ----------
        trigger_bit_delay: int
            4-digit 16 bit hex where LSB 10 bits are delay, LSB 11th bit is delay enabled 
            Example:  0000||0100||0000||0000 = 0x0400: shift of one clock cycle
        """
        # Build the 16-bits word as string and the as int: 
        # 10 LSB bits are the self trigger delay, 
        # The bit 11 (LSB) is delay enable --> FIXED TO ENABLE (XXX --> THis should change?)
        # The bit 12 (LSB) is ??? --> FIXED TO 1 (XXX --> This should change?)
        # [04b:trigger board | 11 | 010b: selftrigger delay ]  
        # trigger_bit_delay_str = f"{trigger_board:04b}11{selftrigger_delay:010b}"
        string1 = format(trigger_board, '04b')
        string2 = format(selftrigger_delay,'010b')
        trigger_bit_delay_str = f"{string1}11{string2}" #### Murtaza's edit
        daq_helpers.triggerBitDelay(self._cmd, int(trigger_bit_delay_str, base=2))
        print(f"triggerBitDelay to {trigger_bit_delay_str}")
        # EQUIVALENT To self._cmd.write_config_reg(8, int(trigger_bit_delay_str))

    def enable_fpga_descrambler(self, polarity):
        """Enable FPGA descrambler

        XXX --WARNING -- the argument name is misleading because is giving the full 
        registry value, not only the polarity one
        
        Paramaters
        ----------
        polarity: int
            4-digit 16 bit hex word where 0xWXYZ
                * Z a 4 bit binary (0bwxyz)
                    * z : enable descrambler
                    * y : disable GTX
                    * x : polarity
                    * w : enable debug mode flag
                    
                * WXY a 12-bit binary: 
                    * {12'bxxxxxxxxx,add_ethernet_filler,debug_mode,dumping_mode,notGTXPolarity,notGTX,enableAutoSync}
                    XXX --- Not sure field sizes
        """
        daq_helpers.Enable_FPGA_Descramblber(self._cmd, polarity)
        print(f"Enable_FPGA_Descramblber to {format(polarity, '016b')}")
        # EQUIVALENT To self._cmd.write_config_reg(14, polarity)

    # Pulse Register, take care of define the data acquisition state (start and stop
    # Reg[15:0] = 
    # [0bxxxx] -> x,x,x,x
    # [0bxxxx] -> x,stop_DAQ_pulse,start_DAQ_pulse,start_hist_counter,
    # [0bxxxx] -> resumePulse,clear_ws_trig_block_pulse,clrError,initPulse,
    # [0bxxxx] -> errInjPulse,fcStart,fifo_reset,START}
    def start_daq(self):
        """
        """
        # --> some things to be done first
        # check valid data start
        # EQUIVALENT to --?
        daq_helpers.software_clear_error(self._cmd)
        # Start the daq
        daq_helpers.start_DAQ_pulse(self._cmd)
        # EQUIVALENT To self._cmd.write_pulse_reg(0x0200)

        # Now prepare the Fast command memory 
        daq_helpers.configure_memo_FC(
                self._cmd, 
                Initialize=True, 
                QInj=False, 
                L1A=False, 
                BCR=True,
                Triggerbit=True,
                L1ARange=False)
        
        print("START DAQ DONE, registers print?")
    
    def stop_daq(self):
        """
        """
        daq_helpers.stop_DAQ_pulse(self._cmd)
        # EQUIVALENT To self._cmd.write_pulse_reg(0x0400)
        print("STOP DAQ DONE, registers?")
    
    def start_acquisition(self, condition_check):
        """ XXX -- 
        
        Parameters
        ----------
        condition_check: function
        """
        self.start_daq()

    def stop_acquisition(self):
        """Let the data acquisition thread it should stop
        """
        self.stop_daq()

    def acquiring_data(self, condition_check):
        """ XXX -- 

        Parameters
        ----------
        condition_check: function
        """
        print(f"INSIDE acquiring_data: {condition_check()}")
        while condition_check():
            mem_data = self._cmd.read_data_fifo(self._num_fifo_read)
            # --- DEBUG
            if mem_data is []:
                EUDAQ_WARN("No data in buffer! Will try to read again")
                time.sleep(1.01)
                mem_data = self._cmd.read_data_fifo(self._num_fifo_read)
            print(f'INSIDE RECEIVING DATA --- {len(mem_data)} -->? {condition_check()}' )
            for mem_line in mem_data:
                self._data_queue.put(mem_line)
            time.sleep(0.01)

            # Test alive condition ?

        
        # Should it this be done? We are here becasue condition_check() is False


def exception_handler(method):
    def inner(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            EUDAQ_ERROR(str(e))
            raise e
    return inner

class ETROCProducer(pyeudaq.Producer):
    def __init__(self, name, runctrl, board_id, simulation):
        pyeudaq.Producer.__init__(self, name, runctrl)
        self.is_running = False
        self._name = f"{name}_{board_id}"

    def check_running_condition(self):
        """Helper function 
        """
        return self.is_running
        
    @exception_handler
    def DoInitialise(self):
        initconf = self.GetInitConfiguration()
        # Initialization for the boards and chips
        hostname = initconf.Get('hostname', default = '192.168.2.3')
        port = initconf.Get('port', default='1024')
        print(f"Doinitialize, hostname {hostname}, port {port}")
        # XXX -- Any other extra info needed from the configuration file
        
        # Daq initialization
        # self._daq = ETROCDaq(hostname, port)
        # self._daq.reset()
        
    @exception_handler
    def DoConfigure(self):
        """ XXX -- 
        """ 
        # Initialize events, .. and dthings
        
        # Settings for the DAQ: see Define DAQ Settings:  
        #  https://github.com/CMS-ETROC/i2c_gui/blob/main/testbeam_nbs/beam_DAQ.ipynb

        # --- 
        # conf = self.GetConfiguration()
        # # ACtive channels -- XXX Explanation
        # active_channels = conf.Get('active_channels', default='0x0401')        
        # print(f"ANTES active channels {active_channels}")
        # self._daq.active_channels(int(active_channels,base=16))
        
        # timestamp = conf.Get('timestamp', default="0x0000")
        # self._daq.timestamp(int(timestamp,base=16))
            
        # # ---> What is the trigger board? Is the one choose to act as trigger in a pack 
        # #      of several boards? Looks like
        # trigger_board = conf.Get('trigger_board', default="0b0001")
        # selftrigger_delay = conf.Get('selftrigger_delay', default="484")
        # self._daq.trigger_bit_delay(selftrigger_delay=int(selftrigger_delay), trigger_board=int(trigger_board,base=2))

        # polarity = conf.Get("polarity", default="0x0027")
        # self._daq.enable_fpga_descrambler(int(polarity, base=16))
        
        # EUDAQ_INFO(f'ETROC --- FIXME extra info ---  was configured')

        # If data should be written dwon to other place than within eudaq
        # use get_fpga_data 
        
    @exception_handler
    def DoStartRun(self):
        #Temporary try
        self._daq = ETROCDaq('192.168.2.3', '1024')
        self._daq.reset()
        #
        # ACtive channels -- XXX Explanation
        active_channels ='0x0401'        
        print(f"ANTES active channels {active_channels}")
        self._daq.active_channels(int(active_channels,base=16))
        
        timestamp = "0x0000"
        self._daq.timestamp(int(timestamp,base=16))
            
        # ---> What is the trigger board? Is the one choose to act as trigger in a pack 
        #      of several boards? Looks like
        trigger_board ="0b0001"
        selftrigger_delay = "484"
        self._daq.trigger_bit_delay(selftrigger_delay=int(selftrigger_delay), trigger_board=int(trigger_board,base=2))

        polarity = "0x0027"
        self._daq.enable_fpga_descrambler(int(polarity, base=16))
        
        EUDAQ_INFO(f'ETROC --- FIXME extra info ---  was configured')
        #Finish temporary try


        self._daq.start_acquisition(self.check_running_condition)
        self.is_running = 1
        
    @exception_handler
    def DoStopRun(self):
        self.is_running = 0
        print("ENTERING ---DOStop")
        self._daq.stop_acquisition()
        print("ENTERING ---after stop")
        # Not running anymore
        

        # and Wait for all data to be processed.
        print("ENTERING --- data should be still being sent")
        # --> FALLA self._daq._data_queue.join()
        print("ENTERING --- after join")

    @exception_handler
    def DoReset(self):
        if hasattr(self, '_daq'):
            self._daq.close()
            delattr(self, '_daq')
        self.is_running = 0
        
    @exception_handler
    def RunLoop(self):
        EUDAQ_INFO("ETROC Starting loop")
        
        n_trigger = 0

        print("Antes del while")
        while self.is_running:
            # Creation of the etroc event type and sub-type
            event = pyeudaq.Event("RawEvent","ETROC")
            event.SetTriggerN(n_trigger)
            # BORE info
            if n_trigger == 0:
                event.SetBORE()
                event.SetTag("producer_name", str(self._name))
            # Access to the stored data
            mem_data = self._daq._cmd.read_data_fifo(self._daq._num_fifo_read)
            if mem_data is []:
                EUDAQ_WARN("No data in buffer! Will try to read again")
                time.sleep(1.01)
                mem_data = self._cmd.read_data_fifo(self._daq._num_fifo_read)
            # --- XXX -- Do I need to serialize data?? If yes: bytes() or struct? or io?
            
            # --- XXX -- Need a identificator for the ROC Use the channel as Block Id
            for element in mem_data:
                if int(element) == 0: continue # Waiting for IPC
                if int(element) == 38912: continue # got a Filler
                if int(element) == 9961472: continue # got a Filler
                if int(element) == 2550136832: continue # got a Filler
                if int(element) == 1431699200: continue
                if int(element) == 1431698688: continue
                binary_mem_data = format(int(element), '032b')
                # if binary_mem_data == '01010101010101011111111100000000': continue

                event.AddBlock(0, binary_mem_data)
                # print(binary_mem_data)
                
            # input(f"{mem_data} -----------")

            # Decode of the data for debugging?

            # Convert into event
            self.SendEvent(event)
            n_trigger += 1

            time.sleep(1e-6) 
        
        print("END OF runLoop")
        # Should be given ??? I dhtin the DoStop is doing it ... right?
        #self._daq.data_queue.join()
        

@click.command()
@click.option('-n','--name', default='etroc_producer',
              help='Name for the producer (default "etroc_producer")')
@click.option('-r','--runctrl',default='tcp://localhost:44000', 
              help='Address of the run control, for example (and default) "tcp://localhost:44000"')
@click.option('-b','--board-id', default = 0)
@click.option('-s','--dry-run',is_flag=True, default=False, 
              help='Don\'t connect to anything, use a simulation to produce events')
def main(name, runctrl, board_id, dry_run):
    producer = ETROCProducer(name,runctrl,board_id, dry_run)
    # XXX -- logger
    EUDAQ_INFO(f" [ETROCProducer]: Connecting to runcontrol in {runctrl} ...")
    producer.Connect()
    time.sleep(2)
    EUDAQ_INFO(' [ETROCProducer]: Connected')
    while(producer.IsConnected()):
        time.sleep(1)
        
if __name__ == "__main__":
    main()
