#!/usr/bin/env python

import setPath

from CRU import *


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

cru.bsp.getFwInfo() # to check fw info and altera chip id


cru.report()


