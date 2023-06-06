#!/usr/bin/env python

import setPath

import argparse
from time import sleep
from CRU import *
from cru_table import *

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)

parser.add_argument("-s", "--sync", metavar="SYNC", help="80-bit SYNC pattern in hexadecimal")
parser.add_argument("-r", "--reset", metavar="RST", help="80-bit RST pattern in hexadecimal")
parser.add_argument("-e", "--idle", metavar="IDLE", help="80-bit IDLE pattern in hexadecimal")

parser.add_argument("--sync-length", metavar="SYNCLEN", help="length of SYNC pattern, deafult is 1", default="1", type=int)
parser.add_argument("--sync-delay", metavar="DELAY", help="length of SYNC delay, default is 0", default="0", type=int)
parser.add_argument("--reset-length", metavar="RSTLEN", help="length of RST pattern, default is 1", default="1", type=int)

parser.add_argument("--rst-trg-sel", metavar="RSTTRG", help="Select trigger for RESET from TTC_DATA[0-31], default is 30", default="30", type=int)
parser.add_argument("--sync-trg-sel", metavar="SYNCTRG", help="Select trigger for SYNC from TTC_DATA[0-31], default is 29", default="29", type=int)

parser.add_argument("-ss", "--sync-at-start", help="Enable automatically sending sync pattern when runenable goes high", action="store_true", default=False)
parser.add_argument("-t", "--trg-sync", help="Manually trigger SYNC pattern", action="store_true", default=False)
parser.add_argument("-u", "--trg-rst", help="Manually trigger RESET pattern", action="store_true", default=False)


args = parser.parse_args()

# Init cru
cru = Cru(args.id, "all", args.verbose)

# Set TTC mux: select CTP instead of patplayer
cru.ttc.selectDownstreamData("pattern")

if args.idle:
  cru.ttc.setIdlePattern(int(args.idle,0))

if args.sync:
  cru.ttc.setSyncPattern(int(args.sync,0))
     
if args.reset:
  cru.ttc.setResetPattern(int(args.reset,0))

cru.ttc.configSync(syncLength=args.sync_length, syncDelay=args.sync_delay)

cru.ttc.configReset(resetLength=args.reset_length)
    
cru.ttc.selectPatternTrig(syncTrig=args.sync_trg_sel, resetTrig=args.rst_trg_sel)

cru.ttc.enableSyncAtStart(args.sync_at_start)

if args.trg_rst:
  cru.ttc.triggerReset()

if args.trg_sync:
  cru.ttc.triggerSync()
