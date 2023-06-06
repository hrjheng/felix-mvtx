#!/usr/bin/env python

# 1.0 program to read binary file (32 bit)
# import modules
import struct
import sys
# program
def ReadFile(file_name) :
    f_i = open(file_name,'rb')
    
    line_number = 0

    num_ev = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    while True:
        # read 4 bytes
        rec = f_i.read(4)
        #convert in UNSIGNED INT
        try:
            pos = struct.unpack('I',rec)
        except:
            break

        word = pos[0]
        word_hex = hex(word)

        if line_number < 4 :
            if line_number == 3:
                gbt_link = word  & 0xff
                if gbt_link > 31:
                        gbt_link = 0
                num_ev[gbt_link] += 1
                print("%10.10s <== RDH WORD 0 (word %d) LINK ID %d EV %d"% (word_hex, line_number%4, gbt_link, num_ev[gbt_link]))
            elif line_number == 2:
                size = (word >> 16) & 0xffff
                offset = word & 0xffff
                print("%10.10s <== RDH WORD 0 (word %d) SIZE %d OFFSET %d"% (word_hex, line_number%4, size, offset))
            else : 
                print("%10.10s <== RDH WORD 0 (word %d)"% (word_hex, line_number%4))
        elif line_number < 8 : 
            print("%10.10s <== RDH WORD 1 (word %d)"% (word_hex, line_number%4))
        elif line_number < 12 : 
            print("%10.10s <== RDH WORD 2 (word %d)"% (word_hex, line_number%4))
        elif line_number < 16 : 
            print("%10.10s <== RDH WORD 3 (word %d)"% (word_hex, line_number%4))
        else : 
            print("%10.10s "% word_hex)

        line_number += 1
        line_number = line_number%2048
    #close the file
    f_i.close()
# define main
def main() :
    ReadFile(sys.argv[1])
if __name__ == '__main__' :
    main()
