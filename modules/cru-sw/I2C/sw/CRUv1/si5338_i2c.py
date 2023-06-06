#!/usr/bin/env python

import setThisPath

import sys

import time
from time import sleep
import argparse

import SI5338
from SI5338 import Si5338  
                                
def showMenu():
    print ('-------------------')
    print('0) RESET PLL')
    print('1) READ PLL CONFIG')
    print('2) CONFIGURE PLL ')
    print('Else) QUIT')
    print ('-------------------')


        
# define main
def main() :

    commands=["reset-pll", "read-pll-config", "config-pll"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
    parser.add_argument("-c", "--command",  choices=commands, metavar="COM",required=True, help=", ".join(commands))
    parser.add_argument("-a", "--chip-address", choices=["0x70","0x71","0x7a"], metavar="ADDR", help="I2C chip addess, possible values: 0x70 (cru), 0x71 (cru), 0x7a (devkit). Default value is 0x70", default="0x70")

    parser.add_argument("-r", "--reg-map", metavar="MAP", help="register map created by clock builder pro")
    parser.add_argument("-o", "--output", default="/tmp/si5338_i2c.txt", help="output file")

    args = parser.parse_args()

    if args.command == "config-pll" and args.reg_map == None:
        parser.error("No register map specified for configuration")

    chip_add = int(args.chip_address,0)
        

    print('-------------------------------')
    print('Hello I2C Si5338 Python script!')
    print('PCIe ', args.id                 )
    print('BAR  0x00608000'                )
    print('ADD  ', args.chip_address       )
    print('-------------------------------')
    print('')

    si5338 = Si5338(args.id, 2, 0x00030800, chip_add, args.reg_map, args.output)    

    si5338.configRefClk()

    si5338.resetI2C()

    if args.command == "reset-pll":
        si5338.resetPLL()
    elif args.command == "read-pll-config":
        si5338.readPLL()
    elif args.command == "config-pll":
        si5338.disableAllClockOut()
        si5338.pauseLOL()
        
        si5338.configureInput()
        si5338.configurePLL()
        si5338.configureSynth()
        si5338.configureMSN()
        si5338.configureMS0()
        si5338.configureMS1()
        si5338.configureMS2()

        # PHASE allignment
        si5338.configurePhase()
        
        si5338.validateClock()
        si5338.configurePLLLocking()
        si5338.initiatePLLLocking()
        
        si5338.restartLOL()
        si5338.confirmPLLLocked()    
        si5338.copyFCALvalues()
        si5338.setPLLuseFCAL()
        si5338.enableAllOutput()
        
    si5338.closeFile()
    

if __name__ == '__main__' :
    main()
