#!/usr/bin/env python

import setPath

from GBT import *
from CRU import *

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-c", "--clock", choices=["local", "ttc"], help="select between local or ttc (external) clock, default value is local", default="local")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-p", "--pon-upstream", help="use PON upstream", action="store_true", default=False)
parser.add_argument("-phasescan", "--manual-phase-scan", help="Scan the phase of PON TX fPLL in software (will disable automatic scan)", action="store_true", default=False)
parser.add_argument("-t", "--ttc-downstream", choices=["ctp", "pattern", "midtrg"], help="TTC downstream data: ctp, pattern or midtrg, default is ctp", default="ctp")
parser.add_argument("-g", "--gbt-mode", choices=["gbt", "wb"], help="GBT mode: gbt, wb", default="gbt")
parser.add_argument("-o", "--onu-address", type=int, help="ONU address")
parser.add_argument("-m", "--mode", help="datapath mode", choices=["packet", "continuous"], default="packet")
parser.add_argument("-lb", "--internal-loopback", help="Enable GBT internal loopback", action="store_true", default=False)
parser.add_argument("-x", "--gbt-mux", choices=["ttc", "ddg", "swt"], help="Set gbt mux: ttc, ddg or swt", default="ttc")
parser.add_argument("-ar", "--allow-reject", help="Enables HBF rejection", action="store_true", default=False)
parser.add_argument("-ul", "--user-logic", help="Enable user logic links in datapath wrapper", action="store_true", default=False)
parser.add_argument("-ulonly", "--user-logic-only", help="Enable ONLY user logic links in datapath wrapper", action="store_true", default=False)
parser.add_argument("-dyn", "--dyn-offset", help="Enable dynamic offset instead of fixed (0x2000)", action="store_true", default=False)

args = parser.parse_args()

# PON upstream can't be used with local clock
if args.clock != "ttc" and args.pon_upstream:
    parser.error("For PON upstream (-p|--pon-upstream) ttc clock must be selected!")

# Always set both upstream and onu address flags
if (args.pon_upstream and args.onu_address == None) or (not args.pon_upstream and args.onu_address != None):
    parser.error("Always set ONU address (-o|--onu-address N) together with PON upstream (-p|--pon-upstream)!")

cru = Cru(args.id, args.links, args.verbose)


#################################
## Some version info
#################################
cru.bsp.getFwInfo()
cru.bsp.hwCompatibleFw(args.id)

#################################
## General board calibration
#################################

print ("Starting TTC PON calibration")

cru.ttc.selectGlobal240(args.clock)

if args.clock == "ttc":
    cru.ttc.calibTTC()

    if args.pon_upstream:
        cru.ttc.configPonTx(args.onu_address, args.manual_phase_scan)

# select TTC downstream output
cru.ttc.selectDownstreamData(args.ttc_downstream)

# Select GBT TX input
cru.setGbtTxMux(args.gbt_mux)

# run GBT calibrations
print ("Starting GBT calibration")
cru.gbt.fpllref(2)
cru.gbt.fpllcal()
cru.gbt.cdrref(2)
cru.gbt.txcal()
cru.gbt.rxcal()


# setup GBT TX
cru.gbt.internalDataGenerator(0)
cru.gbt.txmode("gbt")

cru.gbt.rxmode(args.gbt_mode)

if args.internal_loopback:
    # enable GBT internal loopback
    cru.gbt.loopback(1) 
else:
    cru.gbt.loopback(0)

# setup datapath wrapper
# disable run
cru.bsp.disableRun()

# disable DWRAPPER datagenerator (in case of restart)
cru.dwrapper.datagenerator_resetpulse()
cru.dwrapper.use_datagenerator_source(False)
cru.dwrapper.datagenerator_enable(False)

#disable all links in both datapath wrapper
cru.dwrapper.linkEnableMask(0, 0)
cru.dwrapper.linkEnableMask(1, 0)

# disable rejection by default
cru.dwrapper.setFlowControl(wrap=0,allowReject=0)
cru.dwrapper.setFlowControl(wrap=1,allowReject=0)

# set TRIG windowsize
cru.dwrapper.setTrigWindowSize(wrap=0,size=1000)
cru.dwrapper.setTrigWindowSize(wrap=1,size=1000)

if args.mode == "packet":
    # packet mode
    isGBTpkt = 1
else:
    # continuous mode
    isGBTpkt = 0



# Configure regular links in datapath
if not args.user_logic_only:
    halfNumAllLinks = len(cru.gbt.getLinkList())//2
    
    #enable selected links
    links=cru.gbt.getLinkIndices()
    for l in links:
        # One half of the links are in wrapper0 (e.g. 12 out of 24), 
        # the other half is in wrapper1
        dwrap = l // halfNumAllLinks
    
        # link indexing starts from 0 in both wrappers
        link = l % halfNumAllLinks
    
        cru.dwrapper.linkEnableBit(dwrap, link)        
        cru.dwrapper.setGbtDatapathLink(wrap=dwrap,link=link, is_GBT_pkt=isGBTpkt,RAWMAXLEN=0x1FC)

        # if a link is used, set allowReject for the corresponding wrapper
        cru.dwrapper.setFlowControl(wrap=dwrap,allowReject=int(args.allow_reject))


# Configure user logic links in datapath
if args.user_logic or args.user_logic_only:
    cru.dwrapper.linkEnableBit(0, 15)
    cru.dwrapper.linkEnableBit(1, 15)
    
    cru.dwrapper.setGbtDatapathLink(wrap=0,link=15, is_GBT_pkt=isGBTpkt,RAWMAXLEN=0x1FC)
    cru.dwrapper.setGbtDatapathLink(wrap=1,link=15, is_GBT_pkt=isGBTpkt,RAWMAXLEN=0x1FC)

# Use or not dynamic offset (not by default)
if args.dyn_offset:
    cru.dwrapper.useDynamicOffset(wrapper=0,en=True)
    cru.dwrapper.useDynamicOffset(wrapper=1,en=True)
    print ("Dynamic memory offset")
else:
    cru.dwrapper.useDynamicOffset(wrapper=0,en=False)
    cru.dwrapper.useDynamicOffset(wrapper=1,en=False)
