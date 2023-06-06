#!/usr/bin/env python

import setPath

import os
import inspect
import subprocess
import re

from CRU import *


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

print("Cru-sw hash:")
print(subprocess.check_output(["git", "describe", "--always"]).strip())


def printRegs(regs):
        """ Print register addresses, values, names """
        for name, addr in regs:
                print("{0:#0{1}x}".format(addr,10)+ \
                      "\t{0:#0{1}x}".format(cru.rocRd(addr),10) + \
                      "\t{}".format(name))


def grep(target, exclude=None, offset=None):
        """ search for string in cru_table dictionary, return address sorted list """
        results = {}
        for registerName, address in CRUADD.items():
                if re.search(target, registerName):
                        results[registerName] = address
        if exclude:
                results.pop(exclude, None)
        
        if offset:
                for entry in results:
                        results[entry] += offset

        # result is sorted based on addresses
        results = sorted(results.iteritems(), key=lambda(k,v):(v,k))

        printRegs(results)

        return results



print("\n\nGBT WRAPPERS\n")
for wrap in range(cru.gbt.numOfWrappers):
        baseAddr = [CRUADD["add_gbt_wrapper0"], CRUADD["add_gbt_wrapper1"]][wrap]
        print("GBT WRAPPER #{}".format(wrap))
        globalRegs = grep("add_gbt_wrapper_", exclude="add_gbt_wrapper_bank_offset", offset=baseAddr) 

        for bank in  range(4):
                bankBaseAddr = CRUADD["add_gbt_wrapper_bank_offset"] * (bank + 1)
                for link in range(6):
                        print("  GBT Bank #{}, GBT Link #{}".format(bank, link))
                        linkBaseAddr = bankBaseAddr + CRUADD["add_gbt_bank_link_offset"] * (link + 1)
                        gbtLinkRegs = grep("add_gbt_link_", exclude="add_gbt_link_xcvr_offset", offset=linkBaseAddr)

print("\n\nGBT SC\n")
gbtScaRegs = grep("add_gbt_sca_")
gbtSwtRegs = grep("add_gbt_swt_")
gbtScRegs = grep("add_gbt_sc_")



print("\n\nTTC\n")
grep("add_ttc_data_ctrl")
grep("add_ttc_hbtrig_ltu")
grep("add_ttc_phystrig_ltu")
grep("add_ttc_eox_sox_ltu")

print("  \nONU")
onuCtrlReg = grep("add_ttc_onu_ctrl")

refgenRegs = grep("add_refgen", offset=CRUADD["add_onu_user_refgen"])
refgenCntReg = grep("add_onu_refgen_cnt")

print("  \nFreqmeas")
grep("add_onu_rx") 
grep("add_onu_refout")
grep("add_onu_tx")

print("  \nClkgen")
clkgenRegs = grep("add_ttc_clkgen_", exclude="add_ttc_clk_gen")

print("  \nPatplayer")
patplayerRegs = grep("add_patplayer_")

print("  \nCTPEmu")
ctpEmuRegs = grep("add_ctp_emu_", exclude="add_ctp_emu_core")



print("\n\nDDG\n")
ddgRegs = grep("add_ddg_")



print("\n\nDATAPATH WRAPPER")
for dwrap in range(2):
        baseAddr = [CRUADD["add_base_datapathwrapper0"],CRUADD["add_base_datapathwrapper1"]][dwrap]
        print("  \nDatapath Wrapper #{}".format(dwrap))

        dwrapRegs = grep("add_dwrapper_", offset=baseAddr)

        # datapath links
        for dlink in range(12)+[24]:
                print("  Datapath Wrapper #{}, Link #{}".format(dwrap, dlink))
                dlinkRegs = grep("add_datalink_", offset=baseAddr+CRUADD["add_datalink_offset"]*dlink)

        print("  \nMingler")
        minglerRegs = grep("add_mingler_", exclude="add_mingler_offset", offset=baseAddr)
                
        print("  \nFlowctrl")
        flowRegs = grep("add_flowctrl_", exclude="add_flowctrl_offset", offset=baseAddr)



print("\n\nBSP")
print("  \nInfo")
infoRegs = grep("add_bsp_info_")

print("  \nHousekeeping")
hkeepRegs = grep("add_bsp_hkeeping_")

print("  \nI2C")
i2cRegs = grep("add_bsp_i2c_")
        

