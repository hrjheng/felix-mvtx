#!/usr/bin/env python

import setPath

""" Sets the given GBT mode for the selected links """

import argparse
from CRU import Cru  


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")

args = parser.parse_args()

# Init gbt
cru = Cru(args.id, "all", True)

cru.bsp.resetClockTree()
