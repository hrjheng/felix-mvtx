#!/usr/bin/env python

import setPath
import argparse
from cru_table import *

from CRU import Cru

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-m", "--mux", choices=["ttc", "ddg", "swt"], help="Set gbt mux: ttc, ddg or swt", default="ttc")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-s", "--shortcut", help="Loopback every TX link's input directly to the RX links' output skipping the GBT, enabling the GBT to operate independently", action="store_true", default=False)

args = parser.parse_args()

# Init gbt
cru = Cru(args.id, args.links, args.verbose)
        
cru.setGbtTxMux(args.mux)

cru.gbt.useDDGshortcut(args.shortcut)
