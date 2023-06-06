#!/usr/bin/env python

import setPath

import argparse
import subprocess

from CRU import *

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", help="card ID")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)

args = parser.parse_args()

# if not specified look for valid PCIe IDs
if not args.id:
    try:
        ps = subprocess.Popen(('lspci'), stdout=subprocess.PIPE)
        output = subprocess.check_output(('grep', 'Altera'), stdin=ps.stdout)
        ps.wait()
        
    except subprocess.CalledProcessError as e:
        print ("No card found")
        sys.exit(1)

    output = output.split(b"\n")
    pcie_ids = [x.split()[0] if x else None for x in output]

else: # use given PCIe ID
    pcie_ids = [args.id]

for pcie_id in pcie_ids: 
    if pcie_id:
        print ("=========================================================================================")
        print ("PCIe ID {}".format(pcie_id))
        cru = Cru(pcie_id, "all", args.verbose)
        cru.bsp.getFwInfo()
        print ("")

