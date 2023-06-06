#!/usr/bin/env python

"""Script to access, configure and control the Detector Data Generator (DDG)

The core firmware's DDG module can generate continuous or packetized data stream
"""

import setThisPath

import argparse
from time import sleep
from CRU import *
from cru_table import *

# Parse arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument(
    "-v", "--verbose", 
    help="increase output verbosity", 
    action="store_true", 
    default=False
)

parser.add_argument(
    "-r", "--reset", 
    help="asserts then de-asserts the reset signal", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-c", "--configure", 
    help="Configure ddg mode (continuous or packet)", 
    choices=["continuous", "packet"],
    default="continuous"
)

# Continuous stream options
parser.add_argument(
    "-tpc", "--tpc-emu", 
    help="enable TPC data format in continuous mode", 
    action="store_true", 
    default=False
)

# GBT packet stream options
parser.add_argument(
    "-t", "--trigger",        
    help="select between internal or TTC trigger, default value is ttc", 
    choices=["internal", "ttc"], 
    default="ttc"
)
parser.add_argument(
    "-ts", "--trigger-select", 
    help="32-bit mask for selecting which TTCPON bit triggers the packets\n(by default hb, orbit, sox, eox are excluded)", 
    default="0xFFFFF87C"
)
parser.add_argument(
    "-z", "--rnd-size",
    help="Packet sizes are random if specified", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-pllimit", "--payload-limit",
    help="Max size of payload in GBT words. Min 0, max 511. Default is 508", 
    type=int,
    default="508"
)
parser.add_argument(
    "-rndrange", "--rnd-range", 
    help="Min 1, max PAYLOAD_LIMIT, AND must be a power of 2. Default is 512.\nResulting payload size range in gbt words:\n[PAYLOAD_LIMIT - RND_RANGE + 1, PAYLOAD_LIMIT]", 
    type=int,
    default="512"
)
parser.add_argument(
    "-w", "--rnd-idle-btw",   
    help="Random number of IDLEs between packets", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-il", "--idle-length",    
    help="number of IDLEs between packets (if not random)", 
    default="4",  
    type=int
)
parser.add_argument(
    "-n", "--rnd-idle-in",    
    help="Random IDLE words in payload", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-p", "--pause",          
    help="Pause ddg", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-u", "--resume",         
    help="Resume ddg", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-s", "--sent",          
    help="Print number of sent packets (32-bit counter)", 
    action="store_true", 
    default=False
)
parser.add_argument(
    "-missed", "--missed-triggers",          
    help="Print number of missed triggers (32-bit counter)", 
    action="store_true", 
    default=False
)


args = parser.parse_args()

if not args.configure and (args.rnd_size or args.rnd_idle_btw or args.rnd_idle_in or args.idle_length or args.tpc_emu):
    parser.error("--configure/-c flag required when changing parameters")

if args.idle_length < 0 or args.idle_length > 1023:
    parser.error("Illegal --idle-length value! Must be between 0 and 1023 (inclusive)")

if args.payload_limit < 1 or args.payload_limit > 511:
    parser.error("Illegal --payload-limit value! Must be between 1 and 511 (inclusive)")

isPowerofTwo = True
if sum([(args.rnd_range >> x) & 0x1 for x in range(9)]) > 1:
    isPowerofTwo = False

if args.rnd_size and (args.rnd_range < 0 or args.rnd_range > args.payload_limit or (not isPowerofTwo)):
    parser.error("Illegal --rnd-range value! Must be between 0 and --payload-limit (inclusive) AND must be power of 2. Currently PAYLOAD_LIMIT is {}, RND_RANGE is {}".format(args.payload_limit, args.rnd_range))


# Init cru
cru = Cru(args.id, "all", args.verbose)

if args.configure == "continuous":
    cru.ddg.useTpcEmu(args.tpc_emu)
    cru.ddg.configStream(args.configure)
else:
    cru.ddg.configPackets(rndSize      = args.rnd_size, 
                          payloadLimit = args.payload_limit, 
                          rndRange     = args.rnd_range, 
                          rndIdleBtw   = args.rnd_idle_btw, 
                          rndIdleIn    = args.rnd_idle_in, 
                          trigger      = args.trigger, 
                          idleLength   = args.idle_length)
    if args.trigger == "ttc":
        cru.ddg.selectTriggerBit(int(args.trigger_select,0))


if args.reset:
    cru.ddg.reset()

if args.pause:
    cru.ddg.pause()
elif args.resume:
    cru.ddg.resume()

if args.sent:
    print(cru.ddg.sentPackets())

if args.missed_triggers:
    print(cru.ddg.missedTriggers())
