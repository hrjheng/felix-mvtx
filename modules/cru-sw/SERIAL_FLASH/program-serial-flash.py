#!/usr/bin/env python

""" Script to program the on-board serial flash of the CRU.

 Before running this script, make sure that the MSEL pins are in the correct position.
 The MSEL pins are on the top side of the board, between the SMA connectors.

 SMA1 SMA2  dipswitch  SMA3
  O    O     [1..8]     O

  Switch 6 to 8 (MSEL0-2) must be ON-OFF-ON position (fast serial mode)


  Currently the programming speed is x1.

"""

import math
import os
import sys
import time
import argparse

import setThisPath
from cru_table import *
import ROC


if sys.version_info[0] < 3:
    raise Exception("The script needs Python 3!")


# number of sectors per flash
NO_OF_SEC = 512
# number of pages per sector
PGS_PER_SEC = 256

# base address of slaves
AVL_CSR_BASE_ADDR = CRUADD['add_serial_flash_csr']
AVL_MEM_BASE_ADDR = CRUADD['add_serial_flash_wr_data']
AVL_MEM_WR_RST    = CRUADD['add_serial_flash_wr_rst']

# registers of the IP core
CNTLR_REG          = AVL_CSR_BASE_ADDR +  0*4
BAUD_RATE_REG      = AVL_CSR_BASE_ADDR +  1*4
CS_DELAY_SET_REG   = AVL_CSR_BASE_ADDR +  2*4
OPE_PR_REG         = AVL_CSR_BASE_ADDR +  4*4
RD_INSTR_REG       = AVL_CSR_BASE_ADDR +  5*4
WR_INSTR_REG       = AVL_CSR_BASE_ADDR +  6*4
FLASH_CMD_REG      = AVL_CSR_BASE_ADDR +  7*4
FLASH_CM_CNTLR_REG = AVL_CSR_BASE_ADDR +  8*4
FLASH_CMD_ADDR_REG = AVL_CSR_BASE_ADDR +  9*4
FLASH_WR_DATA0     = AVL_CSR_BASE_ADDR + 10*4
FLASH_RD_DATA0     = AVL_CSR_BASE_ADDR + 12*4

# mask pattern
MASK_WIP = 0x1 #0000_0001
MASK_WR_ERS = 0x81 #1000_0001



def showProgress(count, maxWord):
    """ Show progress bar, total width is 80 """

    percent = count / maxWord 
    ticks = round(percent*69)
    load = "#"*ticks
    bar = "\r"+" {:5.1f}".format(percent*100)+" % ["+load.ljust(69)+"]"
    sys.stdout.write(bar)
    sys.stdout.flush()


def printq(text):
    """ Enable quiet mode """

    if not args.quiet:
        print(text)



parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="PCIe address, e.g. 06:0.0. It can be retrieved by using the o2-roc-list-cards command")
parser.add_argument("-rpd", "--rpd-file", required=True, help="Raw Programming Data file to be loaded into the flash")
parser.add_argument("-p", "--show-progress", help="Show progress bar", action="store_true", default=False)
parser.add_argument("-q", "--quiet", help="Surpress status output", action="store_true", default=False)
args = parser.parse_args()

rpdFile = os.path.abspath(args.rpd_file)

if not os.path.isfile(rpdFile):
    raise OSError("%s file doesn't exist!" % rpdFile)

 
# get ROC for register access
roc = ROC.Roc()
roc.openROC(args.id, 2)


# Initialization routine

#number of total bytes
file_size= os.path.getsize(rpdFile)
#print file_size

#number of total dowrd (32 bit)
dword_total = round(math.ceil(file_size/4))
#print dword_total

#number of sectors to be erased 
no_of_pages = dword_total/64 
no_of_sectors = no_of_pages/256
#print no_of_sectors

# write the CS_DELAY SET reg
roc.rocWr(CS_DELAY_SET_REG, 0x5)

# write the BAUD_RATE_DIV reg
roc.rocWr(BAUD_RATE_REG, 0x10)

#unprotect the memory first ?


start=time.time()

printq("Start configuring flash registers...")
# Write flash registers

# write enable command
roc.rocWr(FLASH_CMD_REG, 0x6)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)  

# volatile configuration register
roc.rocWr(FLASH_CMD_REG, 0x1081)
roc.rocWr(FLASH_WR_DATA0, 0xab)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
#print "CONFIGURED VCR"

# write enable command
roc.rocWr(FLASH_CMD_REG, 0x6)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)  

# enhanced volatile configuration register
roc.rocWr(FLASH_CMD_REG, 0x1061)
roc.rocWr(FLASH_WR_DATA0, 0xef)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
#print "CONFIGURED EVCR"

# 4 byte address enable
roc.rocWr(FLASH_CMD_REG, 0xb7)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
#print "ACTIVATED 4 BYTE MODE"

# write enable command
roc.rocWr(FLASH_CMD_REG, 0x6)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)  

# non volatile configuration egister
roc.rocWr(FLASH_CMD_REG, 0x20b1)
roc.rocWr(FLASH_WR_DATA0, 0xafee)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 

# checking WIP bit to check write in progress
roc.rocWr(FLASH_CMD_REG, 0x1805)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
while roc.rocRd(FLASH_RD_DATA0)and MASK_WIP == MASK_WIP:
    roc.rocWr(FLASH_CMD_REG, 0x1805)
    roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
    #print hex(roc.rocRd(FLASH_RD_DATA0))   

#print "CONFIGURED NVCR"

printq("Configuring flash registers done.")


# Reset flash writer UL's address counter to zero
roc.rocWr(AVL_MEM_WR_RST, 0x1)
time.sleep(0.1)
roc.rocWr(AVL_MEM_WR_RST, 0x0)


#Erase routine
printq("Start erasing die...")

# The image is smaller than the memory, so it's enough to 
# erase 2 dies out of 4

#DIE 0

# write enable command
roc.rocWr(FLASH_CMD_REG, 0x6)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
        
# erase die
roc.rocWr(FLASH_CMD_REG, 0x4C4)
roc.rocWr(FLASH_CMD_ADDR_REG, 0x0)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    


# checking WIP bit to check write in progress
roc.rocWr(FLASH_CMD_REG, 0x1805)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
while roc.rocRd(FLASH_RD_DATA0)and MASK_WIP == MASK_WIP:
    roc.rocWr(FLASH_CMD_REG, 0x1805)
    roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 

# checking WR/ERASE bit to check the state ready/busy
roc.rocWr(FLASH_CMD_REG, 0x1870)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
while roc.rocRd(FLASH_RD_DATA0) and MASK_WR_ERS != MASK_WR_ERS:
    roc.rocWr(FLASH_CMD_REG, 0x1870)
    roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)

#DIE 1

# write enable command
roc.rocWr(FLASH_CMD_REG, 0x6)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
        
# erase die
roc.rocWr(FLASH_CMD_REG, 0x4C4)
roc.rocWr(FLASH_CMD_ADDR_REG, 0x2000000)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    


# checking WIP bit to check write in progress
roc.rocWr(FLASH_CMD_REG, 0x1805)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
while roc.rocRd(FLASH_RD_DATA0)and MASK_WIP == MASK_WIP:
    roc.rocWr(FLASH_CMD_REG, 0x1805)
    roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 

# checking WR/ERASE bit to check the state ready/busy
roc.rocWr(FLASH_CMD_REG, 0x1870)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
while roc.rocRd(FLASH_RD_DATA0) and MASK_WR_ERS != MASK_WR_ERS:
    roc.rocWr(FLASH_CMD_REG, 0x1870)
    roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)

end=time.time()
erase_time =int(end-start)
printq("Erasing time: {:d} mins {:d} seconds".format(erase_time//60, erase_time%60))
printq("Erasing die done.")



#read status after erasing
###################################
# read status register
roc.rocWr(FLASH_CMD_REG, 0x1805)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)
#print "RDSR"    
#print hex(roc.rocRd(FLASH_RD_DATA0))
        
# read flag status register
roc.rocWr(FLASH_CMD_REG, 0x1870)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
#print "RDFLSR"   
#print hex (roc.rocRd(FLASH_RD_DATA0))

# read non volatile configuration register
roc.rocWr(FLASH_CMD_REG, 0x28b5)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)
#print "RDNVCR"    
#print hex(roc.rocRd(FLASH_RD_DATA0))

# volatile configuration register
roc.rocWr(FLASH_CMD_REG, 0x1885)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
#print "RDVCR"   
#print hex(roc.rocRd(FLASH_RD_DATA0))

# enhanced volatile configuiration register
roc.rocWr(FLASH_CMD_REG, 0x1865)
roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)  
#print "RDEVCR"  
#print hex(roc.rocRd(FLASH_RD_DATA0))



#START OF WRITE ROUTINE
printq("Start writing flash...")

# continuous write
  
#standard write process (x1) 
roc.rocWr(OPE_PR_REG,0x0)
roc.rocWr(CNTLR_REG,0x101)
roc.rocWr(WR_INSTR_REG, 0x0502) 

doRead = True
dword_count = 0
i = 0

#open the file pointer for readinf the file
with open(rpdFile, "rb") as f:
    while doRead: 
        # Conversion: read 4 bytes, and convert them
        # to 32 bit in the following way:
        # 
        # Example:
        #
        # Input:
        # reading order is 0x03, 0x0a, 0x20, 0x04
        # (in hexdump it's printed as 0a:03:04:20)
        # 
        #
        # Process: 
        # 03:0a:20:04 -> c0:50:04:20 -> 0x20:04:50:c0 
        #
        #
        # Output:
        # 0x20:04:50:c0 
        # 
        # Value to be written to flash:
        # 0x200450c0 

        value = 0

        # Get 4 bytes to assemble the 32 bit value
        for j in range(4):
            # read content 1 byte at a time
            byte = f.read(1)

            # break if EOF
            if byte == b"":
                doRead = False
                break

            reversed_byte = 0

            # Process each byte in nibbles (two 4-bit nibbles)
            # byte.hex() is a string, one char corresponds to a nibble
            for i, nibble_char in enumerate(byte.hex()):
                nibble = int(nibble_char, 16)
                reversed_nibble = 0

                # reverse the nibble's bits
                for k in range(4):
                    reversed_nibble = (reversed_nibble << 1) | (nibble & 1)
                    nibble = nibble >> 1

                # Save the two nibbles in reversed order
                reversed_byte = reversed_byte | reversed_nibble << i*4

            # Save the 4 new bytes in reversed order
            value = value | reversed_byte << j*8

            # Value is ready to be written with rocwr()

        if doRead:
            #writing data to memory and checking status

            # write enable command
            roc.rocWr(FLASH_CMD_REG, 0x6)
            roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 

            # write data
            roc.rocWr(AVL_MEM_BASE_ADDR, value)

            #delay of 10 us
            #time.sleep(.00001)

            # checking WIP bit to check write in progress
            roc.rocWr(FLASH_CMD_REG, 0x1805)
            roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
            while roc.rocRd(FLASH_RD_DATA0)and MASK_WIP == MASK_WIP:
                roc.rocWr(FLASH_CMD_REG, 0x1805)
                roc.rocWr(FLASH_CM_CNTLR_REG, 0x1) 
                #print hex(roc.rocRd(FLASH_RD_DATA0))

            # checking WR/ERASE bit to check the state ready/busy
            roc.rocWr(FLASH_CMD_REG, 0x1870)
            roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)    
            while roc.rocRd(FLASH_RD_DATA0) and MASK_WR_ERS != MASK_WR_ERS:
                roc.rocWr(FLASH_CMD_REG, 0x1870)
                roc.rocWr(FLASH_CM_CNTLR_REG, 0x1)
                #print hex(roc.rocRd(FLASH_RD_DATA0))

            
            #counting the number of dword
            dword_count = dword_count + 1
            if args.show_progress and not args.quiet:
                showProgress(dword_count, dword_total)

printq("\n{}/{} words written to flash".format(dword_count, dword_total))
printq("Writing flash done.")


#CLOSING ROUTINE
#protect the memory ?
#try to erase to check the protection ?

end=time.time()

total_time = int(end-start)
printq("Total elapsed time: {:d} mins {:d} seconds.\n".format(total_time//60, total_time%60))
