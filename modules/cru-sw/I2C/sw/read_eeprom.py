#!/usr/bin/env python

"""Script to print the content of the serial EEPROM

Example output
{"cn": "TEAM31", "io": "48/48", "pn": "p40_tv20pr004" , "dt": "2018-03-19"}

Fields:
 - "cn": contractor name
 - "io": minipod configuration (RX/TX)
 - "pn": serial number of the board
 - "dt": date of production

"""

import setThisPath
import argparse
from EEPROM import Eeprom

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")

args = parser.parse_args()


eeprom = Eeprom(args.id)

print(eeprom.readContent())
