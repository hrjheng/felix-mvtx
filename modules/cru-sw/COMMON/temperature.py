#!/usr/bin/env python

import setPath

import sys
from CRU import *
from MINIPOD import *
from LTC2990 import *

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
args = parser.parse_args()

cru = Cru(args.id, "all", args.verbose)

# FPGA temperature
fpgaRawTemp = cru.rocRd(CRUADD['add_bsp_hkeeping_tempctrl']) & 0x3ff
fpgaTemp    = fpgaRawTemp * 693.0 / 1024 - 265    # Convert to degC


# Minipod temperature
sys.stdout.write("Scanning Minipods...")
sys.stdout.flush()
minipodAddresses = Minipod.getMinipodAddresses(args.id)

minipodTemp = []

for mpAddr in minipodAddresses:
    try:
        # Init Minipod object
        mp = Minipod(args.id, 2, CRUADD['add_bsp_i2c_minipods'], mpAddr)
        
        minipodTemp.append((mpAddr, mp.getTemperature()))

    except ValueError:
        # chip is neither TX nor RX
        continue
sys.stdout.write("done\n")


# LTC2990 temperature
sys.stdout.write("Scanning LTC2990 sensors...")
sys.stdout.flush()
ltc2990 = Ltc2990(args.id, 2, CRUADD['add_bsp_i2c_tsensor'], 0)
chip_adds = [0x4c, 0x4e, 0x4f]

tint = []
remoteTemp0 = []
remoteTemp1 = []

for chip_add in chip_adds:
    ltc2990.i2cUpdateChipAdd(chip_add)
    v = ltc2990.readReg(ltc2990.TINT_MSB_ADD, ltc2990.TINT_LSB_ADD)
    tint.append(ltc2990.calcTemp(v))
    
    ltc2990.resetI2C()
    ltc2990.configureChipTemp()

for chip_add in chip_adds:
    ltc2990.i2cUpdateChipAdd(chip_add)
    # read TR1
    v = ltc2990.readReg(ltc2990.V1_MSB_ADD, ltc2990.V1_LSB_ADD)
    remoteTemp0.append(ltc2990.calcTemp(v))

    # read TR3
    v = ltc2990.readReg(ltc2990.V3_MSB_ADD, ltc2990.V3_LSB_ADD)
    remoteTemp1.append(ltc2990.calcTemp(v))
sys.stdout.write("done\n\n")

# Print everything
print("FPGA internal: {:.2f} C".rjust(18).format(fpgaTemp))
print("")

print("Minipods")
for mp in minipodTemp:
    print("  chip {}: {:.2f} C".format(hex(mp[0]), mp[1]))

print("")

print("LTC2990 sensors")
for i, chip in enumerate(chip_adds):
    print("  chip {}:".format(hex(chip)))
    print("    internal: {:.2f} C".format(tint[i]))
    print("     remote0: {:.2f} C".format(remoteTemp0[i]))
    print("     remote1: {:.2f} C".format(remoteTemp1[i]))
    print("")
