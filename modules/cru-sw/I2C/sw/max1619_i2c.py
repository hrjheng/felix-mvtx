#!/usr/bin/env python

import setThisPath

import sys

import time
from time import sleep

import argparse

import MAX1619 
from MAX1619 import Max1619


# define main
def main() :
    # INIT

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")

    args = parser.parse_args()

    print('-------------------------------')
    print('Hello I2C MAX1619 Python script!')
    print('PCIe ', args.id)
    print('BAR  0x00600000')
    print('-------------------------------')
    print('')

    max1619 = Max1619(args.id, 2, 0x00600000, 0x18)
    
    max1619.resetI2C()
    
    # Read manufacturer ID
    # It should be always 0x4d
    ret = max1619.readMFGID()
    if ret != 0x4d:
        max1619.errorMsg('ERROR manufacturer ID must be 0x4d, read = ', ret)
    else : 
        print('MFGID ', hex(ret))
        
    # Read device ID
    # It should be always 0x4
    ret = max1619.readDEVID()
    if ret != 0x4:
        max1619.errorMsg('Error DEVICE ID must be 0x4, read = ', hex(ret))
    else:
        print('DEVID ', hex(ret))

    print('')
    # CHECK temperature
    print('-----------')
    print('TEMPERATURE')
    print('-----------')
    ret = max1619.readLocalTemperature()
    print('MAX1619      :', ret, ' C')
    ret = max1619.readRemoteTemperature()
    print('FPGA(remote) :', ret, ' C')
    #ret = readFPGAtemp(ch)
    #print 'FPGA         :', ret, ' C'
    
if __name__ == '__main__' :
    main()
