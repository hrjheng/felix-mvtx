#!/usr/bin/env python

"""Script get information from the SFP+ module 
"""

import setThisPath
import argparse
from SFP import Sfp

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")

args = parser.parse_args()


sfp = Sfp(args.id)

print("       Vendor:\t{:>15}".format(sfp.getVendor()))
print("  Part Number:\t{:>15}".format(sfp.getPartNumber()))
print("Serial Number:\t{:>15}".format(sfp.getSerialNumber()))
print("  Temperature:\t{:>10.3} C".format(sfp.getTemperature()))
print("          Vcc:\t{:>10.2} V".format(sfp.getVcc()))
print("      Tx Bias:\t{:>10.3} mA".format(sfp.getTxBias()))
print("     Tx Power:\t{:>10.2} dBm".format(sfp.getTxPower()))
print("     Rx Power:\t{:>10.2} dBm".format(sfp.getRxPower()))
