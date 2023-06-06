#!/usr/bin/env python

""" Sets the given GBT mode for the selected links """

import setPath
import argparse
from CRU import Cru  


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-m", "--mode", required=True, choices=["gbt", "wb"], help="GBT operation mode")
parser.add_argument("-d", "--direction", required=True, choices=["tx", "rx"], help="GBT stream direction")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)

args = parser.parse_args()

# Init gbt
cru = Cru(args.id, args.links, args.verbose)

if args.direction == "tx":
    cru.gbt.txmode(args.mode)
elif args.direction == "rx":
    cru.gbt.rxmode(args.mode)
