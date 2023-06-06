#!/usr/bin/env python

import setPath

from CRU import *

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")

parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)

parser.add_argument("-m", "--mask", help="LED blinking mask (hexadecimal)", default='0xF')

args = parser.parse_args()

cru = Cru(args.id, args.links, args.verbose)

cru.bsp.ledBlinkLoop(int(args.mask,0))
