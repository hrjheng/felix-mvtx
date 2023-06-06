#!/usr/bin/env python

import setThisPath

import sys
import argparse

from CRU import *

def main() :
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
    parser.add_argument("-fr", "--trg-freq", help="Configure physics trigger frequency. Generate physics trigger every TRG FREQ ticks (28 bit max), larger than 7 to activate", type=int, default="8")
    parser.add_argument("-k", "--hbkeep", help="Sets the number of HBF to keep, before going in drop mode (must be larger than 2). TF starts with keep mode", type=int, default="15000")
    parser.add_argument("-dr", "--hbdrop", help="Sets the number of HBF to drop, before going in keep mode (must be larger than 2). TF starts with keep mode", type=int, default="15000")
    parser.add_argument("-md", "--mode", choices=["continuous","periodic", "manual", "fixed", "hc", "cal"], help="select between periodic, manual physics trigger (SOT/EOT) or continuous trigger (SOC/EOC)", default="periodic")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
    parser.add_argument("-bcmax", "--bcmax", help="Sets BCMAX, deafult is 3560", type=int, default="3560")
    parser.add_argument("-hbmax", "--hbmax", help="Sets HBMAX, defaul is 8", type=int, default="8")
    parser.add_argument("-eox", "--geneox", help="Generat EOX trigger", action="store_true", default=False)
    parser.add_argument("-sinlgetrg", "--singletrigger", help="Generat single PHY trigger", action="store_true", default=False)

    args = parser.parse_args()

    cru = Cru(args.id, "all", args.verbose)

    cru.bsp.getFwInfo() # to check fw info and altera chip id
    
    if args.geneox == True:
        cru.ttc.setEmulatorIdleMode()
    elif args.singletrigger == True:
        cru.ttc.doManualPhysTrig()
    else :
        cru.ttc.resetEmulator(True)
        
        if args.mode == "periodic" :
            # Useless in manual mode
            cru.ttc.setEmulatorPHYSDIV(args.trg_freq)
            cru.ttc.setEmulatorHCDIV(5)
            cru.ttc.setEmulatorCALDIV(5)
            
        if args.mode == "hc" :
            args.mode="periodic"
            cru.ttc.setEmulatorPHYSDIV(5)
            cru.ttc.setEmulatorHCDIV(args.trg_freq)
            cru.ttc.setEmulatorCALDIV(5)
            
        if args.mode == "cal" :
            args.mode="periodic"
            cru.ttc.setEmulatorPHYSDIV(5)
            cru.ttc.setEmulatorHCDIV(5)
            cru.ttc.setEmulatorCALDIV(args.trg_freq)

        if args.mode == "fixed" :
            # Useless in manual mode
            args.mode="periodic"
            
            # Don't send PHYS continuously (no PHYS trigger if the rate < 7)
            # but only at the specified (fixed) BCs
            cru.ttc.setEmulatorPHYSDIV(5) 
            bc=[0x10, 0x14d, 0x29a, 0x3e7, 0x534, 0x681, 0x7ce, 0x91b, 0xa68]
            cru.ttc.setFBCT(bc)

        cru.ttc.setEmulatorTrigMode(args.mode)

        cru.ttc.setEmulatorBCMAX(args.bcmax) # to match the simulation (=Orbit duration=HB duration)
        cru.ttc.setEmulatorHBMAX(args.hbmax) # to match the simulation (=TF duration)
        cru.ttc.setEmulatorPrescaler(args.hbkeep,args.hbdrop)
        #cru.ttc.setEmulatorHCDIV(38) # to generate periodic HC triggers
        #cru.ttc.setEmulatorCALDIV(5) # to generate periodic CAL triggers


        cru.ttc.resetEmulator(False) # start everything, release emulator


if __name__ == '__main__' :
    main()

