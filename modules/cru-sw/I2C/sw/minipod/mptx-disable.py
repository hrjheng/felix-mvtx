#!/usr/bin/env python

import setThisPath

import sys
import time
import argparse

from cru_table import *
from MINIPOD import *


def main():
    """ disables (1) or enables (0) one ore more channels on given Minipod """
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="card ID")
    parser.add_argument("-c", "--chip-addr", help="I2C address of Minipod chip, e.g. 0x30",default='0x30')
    parser.add_argument("-e", "--enable", help="enable selected channels, default is disable", action="store_true", default=False)
    parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
    
    args = parser.parse_args()

    chip_addr = int(args.chip_addr,16) #0x29 -- 0x31
    channels = args.links

    if args.enable:
        activate = 0
    else:
        activate = 1

    mp = Minipod(args.id, 2, CRUADD['add_bsp_i2c_minipods'], chip_addr)

    if type(mp) is Minipod:
        print("This is a RX chip but the script needs the address of an TX chip!")
        return


    if (channels == "all"):
      links = [i for i in range(12)]
    elif (channels.find("-") > -1):
      r0 = int(channels.split("-")[0])
      r1 = int(channels.split("-")[1])
      if r0 > r1 or r0 < 0 or r1 > 11:
        raise ValueError("Link index out of range, max link index is 11")
      links = [i for i in range(r0, r1+1)]
          
    else:
        links = []
        for i in channels.split(","):
            if int(i) < 0 or int(i) > 11:
                raise ValueError("Link index out of range, max link index is 11")

            links.append(int(i))
    status00 = mp.readI2C(93)
    status11 = mp.readI2C(92)

    for i in links:
        if i < 8:
            mask = pow(2, i)
            status0 = mp.readI2C(93)
            status = (status0 & ~mask) | (activate << i)
            mp.writeI2C(93, status)
        else:
            mask = pow(2, i-8)
            status1 = mp.readI2C(92)
            status = (status1 & ~mask) | (activate << (i-8))

            mp.writeI2C(92, status)
        time.sleep(0.20)

    print(str(format(status11, 'b')), str(format(status00, 'b')))
    status1 = mp.readI2C(92)    
    status0 = mp.readI2C(93)
    print(str(format(status1, 'b')), str(format(status0, 'b')))

if __name__ == "__main__":
    main()
