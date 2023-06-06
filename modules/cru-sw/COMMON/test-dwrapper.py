#!/usr/bin/env python

import setPath

from CRU import *

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
#parser.add_argument("-c", "--clock", choices=["local", "ttc"], help="select between local or TTC (external) clock, default value is local", default="local")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)


args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

print("Note: standalone must have been executed first...\n")
 
cru.dwrapper.stopBigFIFO(True)
cru.dwrapper.getBigFifoLvl(True)
cru.dwrapper.getStatistics(True)
cru.dwrapper.setDatapathLink(wrap=0,link=2,stop=0,source=1,resetGBTrec=0,resetRawrec=0,forceEOP=1,replaceFlag=0,replaceHBID=0,resetCDC=0,cdcControl=1)
cru.dwrapper.setRawRecorder(wrap=0,link=2,CUTBYHBID=0,CUTBYLEN=1,maxlen=0x1EA,stop=0)
