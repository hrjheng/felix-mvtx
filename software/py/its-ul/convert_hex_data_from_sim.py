#!/usr/bin/env python3
"""Convert file of lines of hex data (from UVM simulation) to binary format"""

import argparse

def convert(input, output):
    f = open(input, "r")
    data = f.readlines()
    data = [line[:-1] for line in data]

    with open(output, "wb") as f:
        for line in data:
            word = bytes.fromhex(line)
            word = bytearray(word)
            for i in range(0, len(word), 2):
                word[i], word[len(word)-1-i] = word[len(word)-1-i], word[i]
            f.write(word)
                
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", required=False, help="Path to file to convert", default="/dev/stdin")
    parser.add_argument("-o", "--outputfile", required=False, help="Path to file to write", default="output.bin")
    
    args = parser.parse_args()
    input = args.inputfile
    output = args.outputfile
    
    convert(input, output)