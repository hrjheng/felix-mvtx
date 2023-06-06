#!/usr/bin/env python

import setPath

from CRU import *


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

# Monitor packet statistics per link

halfNumAllLinks = len(cru.gbt.getLinkList())//2
links=cru.gbt.getLinkIndices()
for l in links:
    # One half of the links are in wrapper0 (e.g. 12 out of 24), 
    # the other half is in wrapper1
    dwrap = l // halfNumAllLinks

    # link indexing starts from 0 in both wrappers
    link = l % halfNumAllLinks

    cru.dwrapper.getGbtDatapathLinkCounters(dwrap, link)


print("UL links:")
cru.dwrapper.getGbtDatapathLinkCounters(0, 15)
cru.dwrapper.getGbtDatapathLinkCounters(1, 15)


print("-----------------------------------------------------------------------------")


# Monitor statistics per wrapper: dropped packets and total packet throughput
for wid, waddr in enumerate(cru.dwrapper.wrapperAddList):
    droppedPkt = cru.rocRd(waddr + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_drop_pkts'])
    totPerSec = cru.rocRd(waddr + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_tot_per_sec'])
    print("Wrapper {}:  dropped packets: ".format(wid) + "{}".format(droppedPkt).rjust(10)+", \ttotal packets/sec: " + "{}".format(totPerSec).rjust(10))
    
