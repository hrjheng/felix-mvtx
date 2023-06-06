#!/usr/bin/env python

import setThisPath

import sys

import time
from time import sleep
import argparse

import I2C
from I2C import I2c

# define main
def main() :

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
    parser.add_argument("-b", "--base-address", required=True, help="I2C base address")

    args = parser.parse_args()

    base_add_int = int(args.base_address,0)

    i2c = I2c(args.id, 2, base_add_int, 0)   
    ret = i2c.scanI2C()

    print('On I2C chain [', args.base_address, '] found ', ret, ' chip/s')
    print('--')

if __name__ == '__main__' :
    main()
