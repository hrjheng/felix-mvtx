#!/usr/bin/env python

# 1.0 program to read binary file (32 bit)
# import modules
import struct
import sys
# program
def ReadFile(file_name) :
    f_i = open(file_name,'rb')
    line_number = 0
    line_num = 0
    word_index = 0
    word_hex = [0, 0, 0, 0, 0, 0, 0, 0]
    print_line = 0
    
    while True:
        # read 4 bytes
        rec = f_i.read(4)
        #convert in UNSIGNED INT
        try:
            pos = struct.unpack('I',rec)
        except:
            break
        word = pos[0]
        word_hex[word_index] = hex(word)
        
        if line_number == 7 :
            link_id = int(word_hex[3],0)
            ep_id = link_id >> 28
            packet_c = (link_id >> 8) & 0xff
            link_id = link_id & 0xff
            print('EP ID: ', ep_id, 'Link ID: ', link_id)
        if word_index == 7:
            print("%4d)"%(line_number-7), "%10.10s"% word_hex[7], "%10.10s"% word_hex[6], "%10.10s"% word_hex[5], "%10.10s"% word_hex[4], "%10.10s"% word_hex[3], "%10.10s"% word_hex[2],  "%10.10s"% word_hex[1], "%10.10s"% word_hex[0])
        word_index += 1;
        word_index = word_index % 8
        line_number += 1
        line_number = line_number%2048
    #close the file
    f_i.close()

# define main
def main() :
    ReadFile(sys.argv[1])
if __name__ == '__main__' :
    main()
