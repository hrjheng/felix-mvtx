#!/usr/bin/env python

import setPath
import sys
import time
from time import sleep
import argparse

import ROC
from ROC import Roc

def gotoBusy(roc, debug):
    while True:
        data = roc.rocRd(0xC28, debug)        
        if (data >> 31) == 0x0 : 
            break
        

# define main
def main() :
    line = 0
    # PCIe card ID
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
    parser.add_argument("-c", "--config", default=False, action="store_true", help="xxx")
    parser.add_argument("-g", "--gen_int", default=False, action="store_true", help="xxx")
    parser.add_argument("-w", "--word", type=int, help="xxx", default="1024")
    
    args = parser.parse_args()
    
    debug = None

    roc = Roc()
    roc.openROC(args.id, 0, debug)
    
    if args.config == True:
        roc.rocWr(0x600, 0, debug)
        roc.rocWr(0x400, 3, debug)
    
        roc.rocWr(0xC00, 1, debug)
        if args.gen_int == True:
            roc.rocWr(0x700, 1, debug)
            # start the data gen
            roc.rocWr(0x600, 3, debug)
        else : 
            print ('GBT link')
            # choose the GBT as data source
            roc.rocWr(0x700, 0, debug)
        
    while True:
        data = roc.rocRd(0xC28, debug)
        if (int(data) >> 31) == 0x1 :
            gotoBusy(roc, debug)

        roc.rocWr(0xC04, 1, debug) 
        roc.rocWr(0xC04, 0, debug) 
        gbt0 = roc.rocRd(0xC08, debug)
        gbt1 = roc.rocRd(0xC0C, debug)
        gbt2 = roc.rocRd(0xC10, debug)
        gbt3 = roc.rocRd(0xC14, debug)
        gbt4 = roc.rocRd(0xC18, debug)
        gbt5 = roc.rocRd(0xC1C, debug)
        gbt6 = roc.rocRd(0xC20, debug)
        gbt7 = roc.rocRd(0xC24, debug)
        data = roc.rocRd(0xC28, debug)
        
        print('%X %08X%08X%08X%08X%08X%08X%08X%08X' % (data, gbt7, gbt6, gbt5,gbt4,gbt3,gbt2,gbt1, gbt0 ))
        
        if (int(data) >> 31) == 0x1 :
            gotoBusy(roc, debug)

        line = line + 1
        if line == args.word :
            break

if __name__ == '__main__' :
    main()
