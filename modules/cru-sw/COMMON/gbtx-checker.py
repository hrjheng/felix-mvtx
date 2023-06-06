#!/usr/bin/env python

import setPath

from CRU import *

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-c", "--counter-type", choices=["8bit", "30bit"], help="select counter type: 8bit, 30bit. Default value is 30bit", default="30bit")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-s", "--stat", choices=["cnt", "fec", "all"], help="Select what error counters to print: cnt, fec or all. Default value is all", default="all")
parser.add_argument("-mode", "--mode", choices=["gbt", "wb"], help="Select GBT Mode: gbt, wb (if the option is not used, current GBT modes are kept)")
parser.add_argument("-rst", "--reset-counters", help="Reset error counters", action="store_true", default=False)
parser.add_argument("-p", "--pattern", choices=["counter", "static"], help="Select pattern type", default="counter")

parser.add_argument("-g", "--mask-hi", help="Mask high: [95:64] in hexadecimal", default="0xFFFFFFFF")
parser.add_argument("-m", "--mask-mid", help="Mask mid: [63:32] in hexadecimal", default="0xFFFFFFFF")
parser.add_argument("-w", "--mask-low", help="Mask los: [31:0] in hexadecimal", default="0xFFFFFFFF")

args = parser.parse_args()

cru = Cru(args.id, args.links, args.verbose)

if args.mode:
    cru.gbt.rxmode(args.mode)

cru.gbt.patternmode(args.pattern)

# mask could be constructed more smartely? 0xFF for each link on pass instead a mask of 12 links?
cru.gbt.rxpatternmask(0xFFFFFFFF & int(args.mask_hi, 0),0xFFFFFFFF & int(args.mask_mid, 0),0xFFFFFFFF & int(args.mask_low, 0))

if args.reset_counters:
    cru.gbt.cntrst()

# Monitor
cru.gbt.stat(infiniteLoop=True, stat=args.stat)

