#!/usr/bin/env python

import setThisPath

from MINIPOD import *

# parameters: BAR address, chanel, base addr, chip addr

mp = Minipod("18:00.0", 2, 0x00030600, 0x31)
mp.minipodReport()
mp.changeChip(0x30)
mp.minipodReport()
mp.changeChip(0x28) 
mp.minipodReport()
mp.changeChip(0x29) 
mp.minipodReport() 
