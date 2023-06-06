#!/usr/bin/env python

""" Script to control Remote System Upgrade

For the description of the registers see section 1.2.5. in
https://www.intel.com/content/dam/www/programmable/us/en/pdfs/literature/ug/ug_altremote.pdf
(updated for Quartus 18.0)

The additional register #6 (Avalon address 0x18) is for control signals
(refconf, ctl_nupdt (register type), IP core reset)

"""

import setPath

import argparse
from CRU import Cru
from cru_table import *

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("--reload",             help="Trigger firmware reconfiguration from the serial flash", action="store_true", default=False)
parser.add_argument("--register-type",      help="Select register types (control for current settings or update for next reconfiguration)", choices=["control","update"])
parser.add_argument("--watchdog-timeout",   help="12 bit watchdog timeout value")
parser.add_argument("--watchdog-enable",    help="Watchdog enable")
parser.add_argument("--page-select",        help="32 bit offset for start address")
parser.add_argument("--configuration-mode", help="0 for factory page, 1 for application page")
args = parser.parse_args()

cru = Cru(args.id, "all", True)

if args.reload:
    # By default reload factory image. When loading application
    # image,  Intel recommends that you set Configuration Mode to 1. 
    # The content of the control register cannot be read properly 
    # if you fail to do so.
    #
    # cru.rocWr(CRUADD["add_bsp_rsu_conf_mode"], 0x1)

    cru.rocWr(CRUADD["add_bsp_rsu_ctrl"], 0x1)
else:
    if args.watchdog_timeout:
        cru.rocWr(CRUADD["add_bsp_rsu_watchdog_timeout"], 
                  int(args.watchdog_timeout,0))

    if args.watchdog_enable:
        cru.rocWr(CRUADD["add_bsp_rsu_watchdog_enable"], 
                  int(args.watchdog_enable, 0))
        
    if args.page_select:
        cru.rocWr(CRUADD["add_bsp_rsu_pagesel"], 
                  int(args.page_select, 0))

    if args.configuration_mode:
        cru.rocWr(CRUADD["add_bsp_rsu_conf_mode"], 
                  int(args.configuration_mode, 0))

    if args.register_type:
        if args.register_type == "control":
            cru.rocRdMWr(CRUADD["add_bsp_rsu_ctrl"], 4, 1, 0x0)
        else:
            cru.rocRdMWr(CRUADD["add_bsp_rsu_ctrl"], 4, 1, 0x1)

    val = cru.rocRd(CRUADD["add_bsp_rsu_reconf_cond"])
    print("Reconfiguration conditions:\t".rjust(28)+"{}".format(hex(val)))

    val = cru.rocRd(CRUADD["add_bsp_rsu_watchdog_timeout"])
    print("Watchdog timeout:\t".rjust(28)+"{}".format(hex(val)))

    val = cru.rocRd(CRUADD["add_bsp_rsu_watchdog_enable"])
    print("Watchdog enable:\t".rjust(28)+"{}".format(val))

    val = cru.rocRd(CRUADD["add_bsp_rsu_pagesel"])
    print("Page select:\t".rjust(28)+"{}".format(hex(val)))

    val = cru.rocRd(CRUADD["add_bsp_rsu_conf_mode"])
    print("Conf. mode:\t".rjust(28)+"{}".format(val))

    val = cru.rocRd(CRUADD["add_bsp_rsu_ctrl"]) >> 4 & 1
    print("Register type:\t".rjust(28)+"{}".format(val))
