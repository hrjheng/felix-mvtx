#!/usr/bin/env python

import setPath

""" Prints ONU status """

import argparse
from CRU import Cru  


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")

args = parser.parse_args()

cru = Cru(args.id, "all", True)

cru.ttc.onuCalibrationStatus()
