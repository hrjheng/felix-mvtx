#!/usr/bin/env python

import setThisPath

import argparse
import MINIPOD as mp

from cru_table import *

# parameters: BAR address, chanel, base addr, chip addr


# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-c", "--chip-addr", help="I2C address of Minipod chip, e.g. 0x30")

args = parser.parse_args()

# Uuse user input or scan all addresses
chip_found = []
if args.chip_addr:
    chip_found = [int(args.chip_addr, 0)]
    
else: # scan through all addresses for minipod chips
    scan = mp.I2c(args.id, 2, CRUADD['add_bsp_i2c_minipods'], 0x0)
    for addr in range(scan.start_chip_add, scan.end_chip_add+1):
        scan.resetI2C()
        val_32 = (addr << 16) | 0x0
        scan.rocWr(scan.i2c_cfg, int(val_32))
        
        scan.rocWr(scan.i2c_cmd, 0x4)
        scan.rocWr(scan.i2c_cmd, 0x0)
        
        scan.waitI2Cready()
        
        val = scan.rocRd(scan.i2c_dat)
        val = scan.uns(val)
        if val >> 31 == 0x1:
            chip_found.append(addr)

print("Addr\tType\tTemperature [C]")
print("---------------------------------")            

for chip in chip_found:
    try:
        # Init Minipod object
        minipod = mp.Minipod(args.id, 2, CRUADD['add_bsp_i2c_minipods'], chip)

        if type(minipod) == mp.MinipodTx:
            mptype = "TX"
        else:
            mptype = "RX"

        # get internal temperature
        temp = minipod.doubleRead(28, lambda x,y: minipod.twos_comp(x, 8) + y * 0.00390625, \
                                   to_log_file=False, printResultIn='degC')[2]
        
        print(hex(chip), "\t", mptype, "\t", "%.2f" % round(temp,2))

    except ValueError:
        # chip is neither TX nor RX
        print("Unknown chip at address", hex(chip))
        continue


        
