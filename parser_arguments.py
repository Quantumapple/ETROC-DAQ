from optparse import OptionParser

def create_parser():
    
    def int_list_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, list(map(int, value.split(','))))

    parser = OptionParser()
    parser.add_option("--hostname", dest="hostname", action="store", type="string", help="FPGA IP Address", default="192.168.2.3")
    parser.add_option("-l", "--num_line", dest="num_line", action="store", type="int", help="Number of lines per file created by DAQ script", default=50000)
    parser.add_option("-r", "--num_fifo_read", dest="num_fifo_read", action="store", type="int", help="Number of lines read per call of fifo readout", default=50000)
    parser.add_option("-t", "--time_limit", dest="time_limit", action="store", type="int", help="Number of integer seconds to run this code", default=-1)
    parser.add_option("-o", "--output_directory", dest="output_directory", action="store", type="string", help="User defined output directory", default="unnamed_output_directory")
    parser.add_option("--ssd",action="store_true", dest="ssd", default=False, help="Save TDC data to ssd path")
    parser.add_option("--binary_only",action="store_true", dest="binary_only", default=False, help="Save only the untranslated FPGA binary data (raw output)")
    parser.add_option("--compressed_binary",action="store_true", dest="compressed_binary", default=False, help="Save FPGA binary data (raw output) in int format")
    parser.add_option("--skip_binary",action="store_true", dest="skip_binary", default=False, help="DO NOT save (raw) binary outputsto files")
    parser.add_option("--compressed_translation",action="store_true", dest="compressed_translation", default=False, help="Save only FPGA translated data frames with DATA")
    parser.add_option("-s", "--timestamp", type="int",action="store", dest="timestamp", default=0x0000, help="Set timestamp binary, see daq_helpers for more info")
    parser.add_option("-p", "--polarity", type="int",action="store", dest="polarity", default=0x000f, help="Set fc polarity, see daq_helpers for more info")
    parser.add_option("-d", "--trigger_bit_delay", type="int",action="store", dest="trigger_bit_delay", default=0x0400, help="Set trigger bit delay, see daq_helpers for more info")
    parser.add_option("-c", "--counter_duration", type="int",action="store", dest="counter_duration", default=None, help="LSB 6 bits - Time (s) for FPGA data counting")
    parser.add_option("-a", "--active_channel", type="int",action="store", dest="active_channel", default=0x0011, help="LSB 4 bits - Channel Enable")
    parser.add_option("--DAC_Val", dest="DAC_Val", action="store", type="int", help="DAC value set for FPGA data taking", default=-1)
    parser.add_option("-v", "--verbose",action="store_true", dest="verbose", default=False, help="Print status messages to stdout")
    parser.add_option("-w", "--overwrite",action="store_true", dest="overwrite", default=False, help="Overwrite previously saved files")
    parser.add_option("--nodaq",action="store_true", dest="nodaq", default=False, help="Switch off DAQ via the FPGA")
    parser.add_option("--useIPC",action="store_true", dest="useIPC", default=False, help="Use Inter Process Communication to control L1A enable/disable")
    parser.add_option("-f", "--firmware",action="store_true", dest="firmware", default=False, help="Configure FPGA firmware settings")
    parser.add_option("--reset_till_linked",action="store_true", dest="reset_till_linked", default=False, help="FIFO clear and reset till data frames are synced and no data error is seen (Please ensure LED Pages is set to 011)")
    parser.add_option("--reset_till_trigger_linked",action="store_true", dest="reset_till_trigger_linked", default=False, help="FIFO clear and reset till data frames AND trigger bits are synced and no data error is seen (Please ensure LED Pages is set to 011)")
    parser.add_option("--reset_all_till_trigger_linked",action="store_true", dest="reset_all_till_trigger_linked", default=False, help="FIFO clear and reset ALL ENABLED BOARDS till data frames AND trigger bits are synced and no data error is seen")
    parser.add_option("--check_link_at_end",action="store_true", dest="check_link_at_end", default=False, help="Check data link after getting FPGA and if not linked then take FPGA data again)")
    parser.add_option("--check_trigger_link_at_end",action="store_true", dest="check_trigger_link_at_end", default=False, help="Check trigger link after getting FPGA and if not linked then take FPGA data again)")
    parser.add_option("--check_all_trigger_link_at_end",action="store_true", dest="check_all_trigger_link_at_end", default=False, help="Check ALL ENABLED BOARDS trigger link after getting FPGA and if not linked then take FPGA data again)")
    parser.add_option("--fpga_data_time_limit", dest="fpga_data_time_limit", action="store", type="int", default=5, help="(DEV ONLY) Set time limit in integer seconds for FPGA Data saving thread")
    parser.add_option("--fpga_data",action="store_true", dest="fpga_data", default=False, help="(DEV ONLY) Save FPGA Register data")
    parser.add_option("--fpga_data_QInj",action="store_true", dest="fpga_data_QInj", default=False, help="(DEV ONLY) Save FPGA Register data and send QInj and L1A")
    parser.add_option("--fpga_data_L1A",action="store_true", dest="fpga_data_L1A", default=False, help="(DEV ONLY) Save FPGA Register data and send L1A")
    parser.add_option("--clear_fifo",action="store_true", dest="clear_fifo", default=False, help="Clear FIFO at beginning of script")
    parser.add_option("--clear_error",action="store_true", dest="clear_error", default=False, help="Clear error at beginning of script")
    parser.add_option("--memo_fc_start_periodic_ws",action="store_true", dest="memo_fc_start_periodic_ws", default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke start_periodic_L1A_WS() from daq_helpers.py")
    parser.add_option("--memo_fc_start_onetime_ws", action="store_true", dest="memo_fc_start_onetime_ws" , default=False, help="(WS DEV ONLY) Do Fast Command with Memory, invoke start_onetime_L1A_WS() from daq_helpers.py")
    

    return parser