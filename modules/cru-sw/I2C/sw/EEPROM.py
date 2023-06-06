"""Class to access the serial EEPROM

The EEPROM is connected to the FPGA via I2C, the chip address is 0x50.
The content has a dictionary format enclosed in brackets.

Example ID:
{"cn": "TEAM31", "io": "48/48", "pn": "p40_tv20pr004" , "dt": "2018-03-19"}

Fields:
 - "cn": contractor name
 - "io": minipod configuration (RX/TX)
 - "pn": serial number of the board
 - "dt": date of production

"""

from time import sleep
from I2C import I2c
from cru_table import *

class Eeprom(I2c):
    def __init__(self, pcie_id):
        """Init I2C for accessing EEPROM flash"""

        self.i2cInit(pcie_id, 2, CRUADD['add_bsp_i2c_eeprom'], 0x50)
        self.max_chars = 1000//8 # EEPROM size is 1KB

    def readContent(self):
        """Reads content of the EEPROM, returns it as a string"""

        self.resetI2C()
        content = ""
        for i in range(self.max_chars):
            res = self.readI2C(i)
            content = content + chr(res)
            if res == ord("}"):
                break

        # Necessary when several read in sequence 
        # are done to prevent loss!
        sleep(0.01)

        # Protection against \xff\xff..
        if len(content) > 0 and content[0] == "\xff":
            content = "?"*len(content)
        
        return content
