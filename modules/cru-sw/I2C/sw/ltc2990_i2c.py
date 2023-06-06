#!/usr/bin/env python

import setThisPath

import sys
import time
from time import sleep
import argparse

from cru_table import *

import LTC2990
from LTC2990 import Ltc2990

# define main
def main() :
    # PCIe card ID
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")

    args = parser.parse_args()

    ltc2990 = Ltc2990(args.id, 2, CRUADD['add_bsp_i2c_tsensor'], 0)
    
    tint = [0, 0, 0, 0]
    vcc = [0, 0, 0, 0]
    t1 = [0, 0, 0, 0]
    t2 = [0, 0, 0, 0]
    t3 = [0, 0, 0, 0]
    t4 = [0, 0, 0, 0]
    v1 = [0, 0, 0, 0]
    v2 = [0, 0, 0, 0]
    v3 = [0, 0, 0, 0]
    v4 = [0, 0, 0, 0]
    vdd = [0, 0, 0, 0]
    vdda = [0, 0, 0, 0]    

    ltc2990.resetI2C()    
    
    # read Tint
    i = 0
    chip_add_ = (0x4c, 0x4e, 0x4f)
    chip_type = ('TEMPERATURE', 'TEMPERATURE', 'TEMPERATURE')
    
    for chip_add in chip_add_:
        ltc2990.i2cUpdateChipAdd(chip_add)
        v = ltc2990.readReg(ltc2990.TINT_MSB_ADD, ltc2990.TINT_LSB_ADD)
        tint[i] = ltc2990.calcTemp(v)
        
        # read Vcc
        v = ltc2990.readReg(ltc2990.VCC_MSB_ADD, ltc2990.VCC_LSB_ADD)
        vcc[i] = ltc2990.calcVcc(v)

        if chip_type[i] == 'TEMPERATURE': 
            ltc2990.resetI2C()
            ltc2990.configureChipTemp()
        elif chip_type[i] == 'VOLTAGESINGLEENDED' :
            ltc2990.configureChipVoltSingleEnded()
        elif chip_type[i] == 'VOLTAGE' : 
            ltc2990.configureChipVoltDif()
        # end IF

        i = i+1
    # end FOR LOOP

    # MAIN LOOP
    for i in range(len(chip_add_)):
        ltc2990.i2cUpdateChipAdd(chip_add_[i])
        if chip_type[i] == 'TEMPERATURE': 
            # read TR1
            v = ltc2990.readReg(ltc2990.V1_MSB_ADD, ltc2990.V1_LSB_ADD)
            t1[i] = ltc2990.calcTemp(v)
            # read TR2
            v = ltc2990.readReg(ltc2990.V2_MSB_ADD, ltc2990.V2_LSB_ADD)
            t2[i] = ltc2990.calcTemp(v)
            # read TR3
            v = ltc2990.readReg(ltc2990.V3_MSB_ADD, ltc2990.V3_LSB_ADD)
            t3[i] = ltc2990.calcTemp(v)
            # read TR4
            v = ltc2990.readReg(ltc2990.V4_MSB_ADD, ltc2990.V4_LSB_ADD)
            t4[i] = ltc2990.calcTemp(v)
        elif chip_type[i] == 'VOLTAGESINGLEENDED' :
            # read V1
            v = ltc2990.readReg(ltc2990.V1_MSB_ADD, ltc2990.V1_LSB_ADD)
            v1[i] = ltc2990.calcVoltage(v)
            # read V2
            v = ltc2990.readReg(ltc2990.V2_MSB_ADD, ltc2990.V2_LSB_ADD)
            v2[i] = ltc2990.calcVoltage(v)
            # read V3
            v = ltc2990.readReg(ltc2990.V3_MSB_ADD, ltc2990.V3_LSB_ADD)
            v3[i] = ltc2990.calcVoltage(v)
            # read V4
            v = ltc2990.readReg(ltc2990.V4_MSB_ADD, ltc2990.V4_LSB_ADD)
            v4[i] = ltc2990.calcVoltage(v)
        elif chip_type[i] == 'VOLTAGE' :
            # read TR1
            v = ltc2990.readReg(ltc2990.V1_MSB_ADD, ltc2990.V1_LSB_ADD)
            print(v)
            vdd[i] = ltc2990.calcDiffVolt(v)
            # read TR1
            v = ltc2990.readReg(ltc2990.V3_MSB_ADD, ltc2990.V3_LSB_ADD)
            print(v)
            vdda[i] = ltc2990.calcDiffVolt(v)

        # end IF
    # end MAIN LOOP
    
    print('')
    print('CHIP TEMPERATURE [', hex(chip_add_[0]), ']')
    print('CHIP INT TEMP [', tint[0], ']')
    print('CHIP VCC      [', vcc[0], ']')
    print('T1 : ', t1[0])
    print('CHIP TEMPERATURE [', hex(chip_add_[1]), ']')
    print('CHIP INT TEMP [', tint[1], ']')
    print('CHIP VCC      [', vcc[1], ']')
    print('T1 : ', t1[1], '\nT3 : ', t3[1])
    print('CHIP TEMPERATURE [', hex(chip_add_[2]), ']')
    print('CHIP INT TEMP [', tint[2], ']')
    print('CHIP VCC      [', vcc[2], ']')
    print('T1 : ', t1[2], '\nT3 : ', t3[2])

if __name__ == '__main__' :
    main()
