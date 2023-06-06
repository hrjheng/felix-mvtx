#!/usr/bin/env python

import setPath

""" Prints phase scanning status """

import argparse
from cru_table import *
from CRU import Cru 

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")

args = parser.parse_args()

cru = Cru(args.id, "all", True)

val = cru.rocRd(CRUADD['add_ttc_clkgen_phasestat'])
valstate = val & 0x3
if valstate == 0:
    state = "IDLE"
elif valstate == 1:
    state = "SHIFT"
elif valstate == 2:
    state = "WAITSTATUS"
else:
    state = "CHECKSTATUS"
print("   State: {}".format(state))
print("    Scan: {}".format(val >> 2 & 1))
print("Seen bad: {}".format(val >> 3 & 1))
print("Phg. cnt: {}".format(val >> 4 & 0x3f))
print("  rstint: {}".format(val >> 10 & 1))
print("phg flag: {}".format(val >> 12 & 1))
print("rxl flag: {}".format(val >> 13 & 1))
print("pll flag: {}".format(val >> 14 & 1))
print("step cnt: {}".format(val >> 16 & 0xffff))
