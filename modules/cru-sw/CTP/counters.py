#!/usr/bin/env python

import setThisPath

from CRU import *

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-c", "--continuous", help="Read counters every second", action="store_true", default=False)


args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

if args.continuous:
    cru.ttc.loopTrigFromLTUCount()
else:
    print("Heartbeat: {}".format(cru.ttc.getHBTrigFromLTUCount()))
    print("     PHYS: {}".format(cru.ttc.getPHYSTrigFromLTUCount()))
    (sox, eox) = cru.ttc.getSOXEOXTrigFromLTUCount()
    print("      SOx: {}".format(sox))
    print("      EOx: {}".format(eox))
