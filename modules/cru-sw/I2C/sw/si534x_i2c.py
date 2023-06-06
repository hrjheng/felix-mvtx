#!/usr/bin/env python

import setThisPath

import sys
import os
import inspect
import argparse

import time
from time import sleep
from cru_table import *
from SI534X import Si534x

                                
        
def main() :

    commands=["reset-pll", "read-pll-config", "config-pll", "config-pll-all", "report-status", "read-reg", "write-reg", "clear-sticky"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
    parser.add_argument("-p", "--pll", choices=["1","2", "3"], help="select PLL, 1: SI5345 #1, 2: SI5345 #2, 3: SI5344")
    parser.add_argument("-c", "--command",  choices=commands, metavar="COM",required=True, help=", ".join(commands))

    parser.add_argument("-x", "--reg-map1", metavar="MAP", help="register map for SI5345 PLL1 created by clock builder pro")
    parser.add_argument("-y", "--reg-map2", metavar="MAP", help="register map for SI5345 PLL2 created by clock builder pro")
    parser.add_argument("-z", "--reg-map3", metavar="MAP", help="register map for SI5344 PLL created by clock builder pro")

    parser.add_argument("-o", "--output", help="output file")
    parser.add_argument("-s", "--show-sticky", action="store_true", help="Report sticky bits as well")
    parser.add_argument("-d", "--data", help="value in hexa")
    parser.add_argument("-e", "--reg-address", metavar="ADDR", help="I2C address in hexa")

    parser.add_argument("--hard-reset", action="store_true", help="Select hard reset. Default is Soft reset")

    parser.set_defaults(show_sticky=False)
    parser.set_defaults(hard_reset=False)

    args = parser.parse_args()

    chip_add = 0x68 # chip address is fixed

    fileDir = os.path.dirname(os.path.realpath(inspect.getfile(Si534x)))
    fileDir = os.path.join(fileDir, 'register_maps')

    if args.command == "config-pll-all":
        if args.reg_map1 == None:
            regmap1 = os.path.join(fileDir, "Si5345-RevD_local_pll1_zdb-Registers.txt")
        else:
            regmap1 = args.reg_map1

        if args.reg_map2 == None:
            regmap2 = os.path.join(fileDir, "Si5345-RevD_local_pll2_zdb-Registers.txt")        
        else:
            regmap2 = args.reg_map2

        if args.reg_map3 == None:
            regmap3 = os.path.join(fileDir, "Si5344-RevD-TFC_40-Registers.txt")        
        else:
            regmap3 = args.reg_map3

        p1 = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5345_1'], chip_add, regmap1, args.output) #todo add output file arg    
        p2 = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5345_2'], chip_add, regmap2, args.output) #todo add output file arg    
        p3 = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5344'], chip_add, regmap3, args.output) #todo add output file arg    

        p1.resetI2C()
        p2.resetI2C()
        p3.resetI2C()

        p1.configurePll()
        p2.configurePll()
        p3.configurePll()

        if args.output:
            p1.closeFile()
            p2.closeFile()
            p3.closeFile()

    else:
        if not args.pll:
            parser.error("When not configuring, --pll flag must be set")

        if args.pll == "1":
            if args.reg_map1 == None:
                regmap1 = os.path.join(fileDir, "Si5345-RevD_local_pll1_zdb-Registers.txt")
            else:
                regmap1 = args.reg_map1
            pll = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5345_1'], chip_add, regmap1, args.output) #todo add output file arg    

        elif args.pll == "2":
            if args.reg_map2 == None:
                regmap2 = os.path.join(fileDir, "Si5345-RevD_local_pll2_zdb-Registers.txt")        
            else:
                regmap2 = args.reg_map2
            pll = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5345_2'], chip_add, regmap2, args.output) #todo add output file arg
                
        else:
            if args.reg_map3 == None:
                regmap3 = os.path.join(fileDir, "Si5344-RevD-TFC_40-Registers.txt")        
            else:
                regmap3 = args.reg_map3
            pll = Si534x(args.id, 2, CRUADD['add_bsp_i2c_si5344'], chip_add, regmap3, args.output) #todo add output file arg

        pll.resetI2C()

        if args.command == "reset-pll":
            pll.resetPll(args.hard_reset)
            pll.reportStatus(True)

        elif args.command == "config-pll":

            pll.configurePll()

        elif args.command == "read-pll-config":
            pll.readPllConfig()

        elif args.command == "report-status":
            pll.reportStatus(args.show_sticky)

        elif args.command == "clear-sticky":
            pll.clearSticky()

        elif args.command == "read-reg":
            pll.writeI2C((0x01), int(args.reg_address,0)>>8)
            print(hex(int(args.reg_address,0)), hex(pll.readI2C(int(args.reg_address,0) & 0xFF)))

        elif args.command == "write-reg":
            pll.writeI2C((0x0001), int(args.reg_address,0)>>8)
            print(hex(int(args.reg_address,0)), hex(pll.readI2C(int(args.reg_address,0))))
            pll.writeI2C(int(args.reg_address,0), int(args.data,0))
            print(hex(int(args.reg_address,0)), hex(pll.readI2C(int(args.reg_address,0))))

        if args.output:
            pll.closeFile()

if __name__ == '__main__' :
    main()
