#!/usr/bin/env python

import setThisPath

"""
Script for reading RX Minipod input optical power values
for all 12 links and putting it to standard output.

command line arguments: PCIe ID, BAR channel, base address (in hex), 
                        chip address (in hex)

If no command line arguments given default values are used

"""
import argparse

from cru_table import * 
from MINIPOD import *


def printPower(allPower, rxChips):
       
    # Print(to std output
    print('\n RX input optical powers\n')

    if not allPower:
        print("No RX chip found!")
    else:
        for addr in rxChips:
            print("\t"+hex(addr)+"\t\t",end='')

        print("")
        for j in range(len(allPower)):
            print('Link   Power [uW]\t',end='')

        print("")

        for j in range(len(allPower)):
            print('------------------\t',end='')
            
        print("")
     
        # Values are reversed (link11 -> link0) print(them in correct order
        for i in range(12):
            for j in range(len(allPower)):
                print('%s : %s\t\t' % (str(i).rjust(4), allPower[j][11-i].rjust(6)),end='')
            print("")

def main():

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="card ID")
    parser.add_argument("-c", "--chip-addr", help="I2C address of Minipod chip, e.g. 0x30")

    args = parser.parse_args()


    # Used to hardcode chip addresses
    #chip_found = [0x28, 0x29, 0x30, 0x31]

    # Now either use user input or scan all addresses
    chip_found = []
    if args.chip_addr:
        chip_found = [int(args.chip_addr, 0)]

    else: # scan through all addresses for minipod chips
        scan = I2c(args.id, 2, CRUADD['add_bsp_i2c_minipods'], 0x0)
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


    allPower = []
    rxChips = []
    for chip in chip_found:
        try:
            # Init Minipod object
            mp = Minipod(args.id, 2, CRUADD['add_bsp_i2c_minipods'], chip)

            # skip if chip is TX
            if type(mp) is MinipodTx:
                continue

        except ValueError:
            # chip is neither TX nor RX
            continue

        rxChips.append(chip)

        # Get input optical powers (see minipodrxaux.py)
        powers = []
        for reg_add in range(64, 88, 2):
            (reg1, reg2, result) = mp.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.1)
            powers.append(str(result))
        allPower.append(powers)
        
    printPower(allPower, rxChips)

if __name__ == '__main__' : 
    main()
