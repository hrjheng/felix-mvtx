#!/usr/bin/env python

import setThisPath

"""Configuration and control script for the core-ul

The core-ul (https://gitlab.cern.ch/alice-cru/cru-fw-ul/tree/develop/core-ul) emulates 
userlogic output with configurable payload data for testing purposes. This module can be 
used for configuring the output data and throughput, and controlling it (start/stop/resume/reset).
Example configuration data can be found in ul_config_data.txt
Note that by default the core-ul is not compiled into the cru-fw design (which uses the 
dummy_userlogic by default)
"""

from CRU import *


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-wr", "--write", help="32-bit word to be written to RAM")
parser.add_argument("-start", "--start-read", help="Start read", action="store_true", default=False)
parser.add_argument("-stop", "--stop-read", help="Stop read", action="store_true", default=False)
parser.add_argument("-areset", "--assert-reset", help="Assert reset", action="store_true", default=False)
parser.add_argument("-dreset", "--deassert-reset", help="Deassert reset", action="store_true", default=False)
parser.add_argument("-counter", "--show-counter", help="Counter", action="store_true", default=False)
parser.add_argument("-sop", "--show-sop", help="Show number of sent SOP", action="store_true", default=False)
parser.add_argument("-eop", "--show-eop", help="Show number of sent EOP", action="store_true", default=False)
parser.add_argument("-status", "--show-status", help="Show state machine status", action="store_true", default=False)
parser.add_argument("-config", "--config", help="Config file")
parser.add_argument("-idle", "--idle", type=int, help="Number of additional IDLEs (default is 1) between packets", default="1")

args = parser.parse_args()

if args.idle > 0xffff:
    parser.error("Too many IDLEs: --idle should be between 0 and 65535")

cru = Cru(args.id, "all", args.verbose)

# Write data from file
if args.config:
    # Stop reading
    cru.rocRdMWr(CRUADD['add_userlogic'], 0, 1, 0)

    # Reset
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 1)
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 0)

    wordCount = 0
    print("Start writing...")
    addr = CRUADD['add_userlogic'] + 4
    with open(args.config) as configData:
        for val in configData:
            ival = int(val,0)
            cru.rocWr(addr, ival)
            sleep(0.05)
            newVal = cru.rocRd(addr)
            print(hex(addr), hex(ival), hex(newVal))
            wordCount += 1
    print("...done")
    print("Wrote {} words".format(wordCount))

    # Reset
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 1)
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 0)


# Write single word
if args.write:
    cru.rocWr(CRUADD['add_userlogic'] + 4, int(args.write,0))

if args.start_read:
    cru.rocRdMWr(CRUADD['add_userlogic'], 0, 1, 1)

if args.stop_read:
    cru.rocRdMWr(CRUADD['add_userlogic'], 0, 1, 0)

if args.assert_reset:
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 1)

if args.deassert_reset:
    cru.rocRdMWr(CRUADD['add_userlogic'], 4, 1, 0)

if args.idle:
    cru.rocRdMWr(CRUADD['add_userlogic'] + 0x14, 0, 16, args.idle)

if args.show_counter:
    print("Counter: {}".format(cru.rocRd(CRUADD['add_userlogic'] + 0x8)))

if args.show_status:
    states = {
        7: "IDLE",
        6: "RAM_WRITE",
        5: "RAM_WRITE_WAIT",
        4: "RAM_READ",
        3: "RAM_READ_WAIT",
    }
    print("Status: {}".format(states.get(cru.rocRd(CRUADD['add_userlogic'] + 0xC) & 0x7, "OTHER")))

xop = cru.rocRd(CRUADD['add_userlogic'] + 0x10)
if args.show_sop:
    print("Sent SOP: {}".format(xop & 0xffff))

if args.show_eop:
    print("Sent EOP: {}".format(xop >> 16 & 0xffff))
