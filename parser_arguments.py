from optparse import OptionParser

def create_parser():

    def int_list_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, list(map(int, value.split(','))))

    parser = OptionParser()
    #------------------------------------------------------------------------#
    parser.add_option("--hostname", dest="hostname", action="store", type="string", help="FPGA IP Address", default="192.168.2.3")
    parser.add_option("--firmware_key", dest="firmware_key", action="store", type="string", help="FPGA Firmware version (4-bit)", default="0001")
    #------------------------------------------------------------------------#
    parser.add_option("-v", "--verbose",action="store_true", dest="verbose", default=False, help="Print status messages to stdout")
    parser.add_option("-w", "--overwrite",action="store_true", dest="overwrite", default=False, help="Overwrite previously saved files")
    #------------------------------------------------------------------------#
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int", help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-r", "--num_fifo_read", dest="num_fifo_read", action="store", type="int", help="Number of lines read per call of fifo readout", default=50000)
    #------------------------------------------------------------------------#
    parser.add_option("-t", "--time_limit", dest="time_limit", action="store", type="int", help="Number of integer seconds to run this code", default=-1)
    #------------------------------------------------------------------------#
    parser.add_option("--run_name", dest="run_name", type="string", help="Run name under which to store the data, if not set will store the data under a timestamped directory.")
    parser.add_option("-o", "--output_directory", dest="output_directory", action="store", type="string", help="User defined output directory", default="unnamed_output_directory")
    parser.add_option("--ssd",action="store_true", dest="ssd", default=False, help="Save TDC data to ssd path")
    #------------------------------------------------------------------------#
    parser.add_option("--compressed_binary",action="store_true", dest="compressed_binary", default=False, help="Save FPGA binary data (raw output) in int format")
    parser.add_option("--skip_binary",action="store_true", dest="skip_binary", default=False, help="DO NOT save (raw) binary outputs to files")
    parser.add_option("--compressed_translation",action="store_true", dest="compressed_translation", default=False, help="Save only FPGA translated data frames with DATA")
    parser.add_option("--skip_translation",action="store_true", dest="skip_translation", default=False, help="DO NOT Save the translated FPGA data to files")
    parser.add_option("--debug_event_translation",action="store_true", dest="debug_event_translation", default=False, help="DEV dump ETROC raw data in each event")
    parser.add_option("--lock_translation_numwords",action="store_true", dest="lock_translation_numwords", default=False, help="Requires the correct number of 40bit words in the event")
    #------------------------------------------------------------------------#
    parser.add_option("-f", "--firmware",action="store_true", dest="firmware", default=False, help="Set FPGA Config Registers")
    parser.add_option("-s", "--timestamp", type="int",action="store", dest="timestamp", default=0x0000, help="Set FPGA Config Register 13, see daq_helpers for more info")
    parser.add_option("-p", "--polarity", type="int",action="store", dest="polarity", default=0x000f, help="Set FPGA Config Register 14, see daq_helpers for more info")
    parser.add_option("-d", "--trigger_bit_delay", type="int",action="store", dest="trigger_bit_delay", default=0x0400, help="Set FPGA Config Register 8, see daq_helpers for more info")
    parser.add_option("-c", "--counter_duration", type="int",action="store", dest="counter_duration", default=None, help="Set FPGA Config Register 7, see daq_helpers for more info")
    parser.add_option("-a", "--active_channel", type="int",action="store", dest="active_channel", default=0x0001, help="LSB 4 bits - Channel Enable")
    #------------------------------------------------------------------------#
    parser.add_option("--nodaq",action="store_true", dest="nodaq", default=False, help="Switch off DAQ via the FPGA")
    parser.add_option("--useIPC",action="store_true", dest="useIPC", default=False, help="Use Inter Process Communication to control L1A enable/disable")
    #------------------------------------------------------------------------#
    parser.add_option("--reset_all_till_trigger_linked",action="store_true", dest="reset_all_till_trigger_linked", default=False, help="FIFO clear and reset till data frames AND trigger bits are synced and no data error is seen FOR ALL BOARDS")
    parser.add_option("--inpect_links_only",action="store_true", dest="inpect_links_only", default=False, help="Inspect the linked status for all the enabled boards")
    parser.add_option("--check_all_trigger_link_at_end",action="store_true", dest="check_all_trigger_link_at_end", default=False, help="Check ALL ENABLED BOARDS trigger link after getting FPGA and if not linked then take FPGA data again)")
    #------------------------------------------------------------------------#
    parser.add_option("--fpga_data_time_limit", dest="fpga_data_time_limit", action="store", type="int", default=5, help="(DEV ONLY) Set time limit in integer seconds for FPGA Data saving thread")
    parser.add_option("--fpga_data",action="store_true", dest="fpga_data", default=False, help="(DEV ONLY) Save FPGA Register data")
    parser.add_option("--fpga_data_QInj",action="store_true", dest="fpga_data_QInj", default=False, help="(DEV ONLY) Save FPGA Register data and send QInj")
    parser.add_option("--DAC_Val", dest="DAC_Val", action="store", type="int", help="DAC value set for FPGA data taking", default=-1)
    #------------------------------------------------------------------------#
    parser.add_option("--clear_fifo",action="store_true", dest="clear_fifo", default=False, help="Clear FIFO at beginning of script")
    parser.add_option("--clear_error",action="store_true", dest="clear_error", default=False, help="Reset the event counter")
    parser.add_option("--check_valid_data_start",action="store_true", dest="check_valid_data_start", default=False, help="Save data from Event=0 Only, must be used with clear_error")
    parser.add_option("--resume_in_debug_mode",action="store_true", dest="resume_in_debug_mode", default=False, help="Reset and Resume State Machine in Debug Mode")
    #------------------------------------------------------------------------#
    parser.add_option("--start_dev_qinj_fc",action="store_true", dest="start_dev_qinj_fc", default=False, help="Turn on QInj and Ext L1A")
    parser.add_option("--start_dev_qinj_selftrig_fc",action="store_true", dest="start_dev_qinj_selftrig_fc", default=False, help="Turn on QInj Without Ext L1A")
    parser.add_option("--stop_dev_qinj_fc",action="store_true", dest="stop_dev_qinj_fc", default=False, help="Turn off QInj and Ext L1A")
    #------------------------------------------------------------------------#
    parser.add_option("--ws_testing",action="store_true", dest="ws_testing", default=False, help="Perform WS Testing rather than usual DAQ")
    parser.add_option('--ws_chipname',metavar = 'NAME',type = str,help = 'Board label',dest = 'ws_chipname',default="chipname_NA")
    parser.add_option('--ws_ip_address',metavar = 'NAME',type = str,help = 'KC705 FPGA IP address',default="192.168.2.3",dest = 'ws_ip_address')
    parser.add_option('--ws_i2c_port',metavar = 'NAME',type = str,help = 'USB ISS port name',default='/dev/ttyACM1',dest = 'ws_i2c_port')
    parser.add_option("--ws_chip_address", type="int",action="store", dest="ws_chip_address", default=0x0060, help="Chip I2C Address for WS Testing Purposes")
    parser.add_option("--ws_address", type="int",action="store", dest="ws_address", default=0x0040, help="Chip WS I2C Address for WS Testing Purposes")
    # parser.add_argument('--ws_read_mode',metavar='MODE',type = str,choices=["WS", "I2C", "High Level"],default='WS',help='The read mode algorithm to use for reading the WS. Options are: WS - to read with the WS controller; I2C - to read with the I2C controller; High Level - to use the high level functions. Default: WS')
    #------------------------------------------------------------------------#


    return parser
