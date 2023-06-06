#!/usr/bin/env python

import setPath

import argparse
from CRU import *


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-r", "--reset-sticky", help="Reset sticky status error bits", action="store_true", default=False)

args = parser.parse_args()

# Init cru
cru = Cru(args.id, args.links, args.verbose)

cru.ttc.getClockFreq()
cru.gbt.getRefFrequencies()

if args.reset_sticky:
    cru.gbt.RstError()

cru.gbt.checkLinkLockStatus()
cru.gbt.isGBTWrapper()
cru.gbt.getGBTWrapperType()
