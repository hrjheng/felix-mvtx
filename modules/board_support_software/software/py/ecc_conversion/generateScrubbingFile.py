"""
Created on Tue Jun  5 15:06:41 2018

@author: Johan Alme

example usage:
if __name__ == '__main__':
    s = Scrub()
    s.generate_scrubbing_file("demo.bit")

"""
import os

class Scrub():
    def __init__(self):
        self.header = ('FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       'FF FF FF FF',
                       '00 00 00 BB',
                       '11 22 00 44',
                       'ff ff ff ff',
                       'ff ff ff ff',
                       'aa 99 55 66',
                       '20 00 00 00',
                       '20 00 00 00',
                       '30 00 80 01',
                       '00 00 00 07',
                       '30 01 80 01',
                       '13 91 90 93',
                       '20 00 00 00',
                       '30 00 c0 01',
                       '00 00 01 00',
                       '30 00 a0 01',
                       '00 00 00 00',
                       '30 00 80 01',
                       '00 00 00 01',
                       '20 00 00 00',
                       '30 00 20 01',
                       '00 00 00 00',
                       '20 00 00 00',
                       '30 00 40 00',
                       '50 46 61 23')

        self.trailer = ('30 00 80 01',
                        '00 00 00 0d',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00',
                        '20 00 00 00')

    def generate_scrubbing_file(self, infilename, fileending="_bs.bit", verbose=True):
        """ Collect the correct piece of a Xilinx Bit-file for generating the blind-scrubbing
        warning: expects a "real" bitfile. will freeze if the file
        does not contain 0xAA followed by 0x30004000 somewhere"""
        i_fn = os.path.realpath(infilename)
        o_fn = str(i_fn[:-4]) + fileending
        if verbose:
            print("Generating blind scrubbing file for " + o_fn)
        with open(i_fn, 'rb') as inFile, open(o_fn, "wb") as outFile:
            numOfWords = 0
            for wrd in self.header:
                numOfWords = int(wrd.replace(" ", "")[2:], 16)
                outFile.write(bytearray.fromhex(wrd))
            byte = inFile.read(1)
            while byte != bytearray.fromhex("AA"):
                byte = inFile.read(1)

            _ = inFile.read(3)  # aligned
            byte4 = inFile.read(4)
            while byte4 != bytearray.fromhex("30004000"):
                byte4 = inFile.read(4)
            _ = inFile.read(4)  # last data bytes in header
            outFile.write(inFile.read(numOfWords * 4))
            for wrd in self.trailer:
                outFile.write(bytearray.fromhex(wrd))
        print("Generated blind scrubbing file " + o_fn)
        return o_fn
