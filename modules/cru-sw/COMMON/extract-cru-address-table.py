#!/usr/bin/env python

import argparse
from collections import OrderedDict


""" Module used to create a dictionnay of the CRU addresses from the VHDL. 
The pack_cru_core.vhd file is used to obtain the information.

Usage: a pyhton dictionnary file is generated, it should imported with
from cru_table import *
"""

CRUADD=OrderedDict()

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", default="pack_cru_core.vhd", help="VHDL package file name and path")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)

args = parser.parse_args()


def parseStrVal(Str):
        """ Convert VHDL string to integer value.
        """
        val=0
        if "+" in Str: #recursive call
                leftOp=Str[0:Str.find("+")]
                rightOp=Str[Str.find("+")+1:]
                #print leftOp,rightOp
                val=parseStrVal(leftOp) + parseStrVal(rightOp)
        else:
                if "add_" in Str:
                        val=CRUADD[Str];
                else:
                        if "x" in Str: #hex string
                                myStr=Str.replace("_","")
                                myStr=myStr.replace("x","")
                                myStr=myStr.replace("\"","")
                                val=int(myStr,16)
                        else: #decimal string
                                print(Str)
                                val=int(Str)

        return val

def saveDict():
        fileout= open('LIB/cru_table.py', 'w')
        fileout.write('CRUADD={')
        for k in CRUADD.keys():
                fileout.write(('\'{}\':0x{:08X},\n').format(k,CRUADD[k]))
        fileout.write('}')
        

filin = open(args.file, 'r')
for li in filin:
        if ("constant" in li) and ("add_" in li) :
                addLabel=li.split()[1]
                addLabel=addLabel.replace(":","")
                addLabel=addLabel.lower()

                addStrVal=li[li.find(":=")+2:li.find(";")]
                intval=parseStrVal(addStrVal.lower())
                
                CRUADD[addLabel]=intval
                #addStrVal=addStrVal.replace("_","")
                #print (addLabel,addStrVal)
        else:
                continue  # skip line

for k in CRUADD.keys():
        print('{} \t 0x{:08X}').format(k,CRUADD[k])

saveDict()

