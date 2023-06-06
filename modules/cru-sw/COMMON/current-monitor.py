#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

# LTC2418
#  channel 0 : A10_VCC
#  channel 1 : A10_1V8_ALL
#  channel 2 : A10_VCCR_GXB
#  channel 3 : A10_VCCT_GXB
#  channel 4 : A10_VCCPT_GXB
#  channel 5 : A10_1V8
#  channel 6 : 3V3
#  channel 7 : 2V5

# LTC2498
#  channel 1 : 12V
#  channel 2 : 12v ATX
#  channel 3 : external

import setPath
import argparse

from ROCEXT import *
from cru_table import *
from CRU import *

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
args = parser.parse_args()

cru = Cru(args.id, args.links, args.verbose)

print( 'getChipID : ' + str(cru.bsp.getChipID()))

param_R   = [0.001,0.003,0.003,0.003,0.003,0.003,0.003,0.003,0.01,0.01,1]
param_div = [1,1,1,1,1,1,1,1,1/6,1/6,1]
param_bit = 5 / ((2**24) - 1)

# create & initialise current array
global I_array
I_array, m=[],1
while m != 12 :
  I_array.append(0)
  m = m + 1

# read current value
for i in range(11):
#  I_array[i] = ( cru.rocRd(0x00010020 + (4 * i)) * param_bit ) /( param_R[i] * param_div[i])
  I_array[i] = ( cru.rocRd(CRUADD['add_a10_meas_vcc'] + (4 * i)) * param_bit ) /( param_R[i] * param_div[i])
  
# print current value  
print ("Current measure :")
#for i in range(11):
#  print(" valeur : ", i, I_array[i])
# ADC LTC2418
print("Current VCCIN   (0V9)  ={0:9.3f} A" .format(I_array[0]))
print("Current VCCR    (1V02) ={0:9.3f} A" .format(I_array[2]))
print("Current VCCT    (1V02) ={0:9.3f} A" .format(I_array[3]))
print("Current VCCPT   (1V8)  ={0:9.3f} A" .format(I_array[4]))
print("Current 1V8 ALL (1V8)  ={0:9.3f} A" .format(I_array[1]))
print("Current 1V8            ={0:9.3f} A" .format(I_array[5]))
print("Current 2V5            ={0:9.3f} A" .format(I_array[7]))
print("Current 3V3            ={0:9.3f} A" .format(I_array[6]))
# ADC LTC2498
print("Current 12V            ={0:9.3f} A" .format(I_array[8]))
print("Current 12V ATX        ={0:9.3f} A" .format(I_array[9]))
print("Current EXT            ={0:9.3f} A" .format(I_array[10]))

