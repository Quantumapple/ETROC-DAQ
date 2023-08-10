import matplotlib.pyplot as plt
import logging
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
import time
from tqdm import tqdm
from i2c_gui.chips.etroc2_chip import register_decoding
import os, sys
import multiprocessing
import datetime
from pathlib import Path
import pandas as pd
sys.path.insert(1, f'/home/{os.getlogin()}/ETROC2_Test/git/ETROC_DAQ')
import run_script
import importlib
importlib.reload(run_script)

data=0b10111001101000
binary_data = bin(int(data, 0))[2:].zfill(14)

