"""Abstraction of a wishbone accessed module.

Provides Read/Write functionality to a module with given module_id on
construction time.

"""

from enum import IntEnum, unique

import logging

from communication import AddressMismatchError


@unique
class WriteReadBit(IntEnum):
    READ  = 0
    WRITE = 1


class WishboneModule(object):
    """ Abstract wishbone module providing basic communication functions """

    def __init__(self, moduleid, name, board_obj):
        self.moduleid = moduleid
        self.board = board_obj
        self.comm = self.board.comm
        self.name = name
        self.logger = logging.getLogger("Module Id {0}: {1}".format(moduleid, name))

    def write(self, addr, data, commitTransaction=True):
        """Write to a specific address of the module. Optionally commit transaction"""
        self.logger.debug("Writing reg \t0x{0:02X}{1:02X}, value \t0x{2:04X}".format(self.moduleid, addr, data))
        self.board.write(self.moduleid, addr, data, commitTransaction)
        
    def read(self, addr, commitTransaction=True):
        """Read from a specific address from the module. Optionally commit transaction"""
        reg, val = self.board.read(self.moduleid, addr, commitTransaction)
        if commitTransaction:
            # read_results returns [(addr0,data0),(addr1,data1),...,(addrN,dataN)]
            complete_read_address = reg & 0x7FFF
            complete_address = (self.moduleid<<8)|addr
            rderr_flag = (reg >> 15) & 1
            if complete_address != complete_read_address:
                message = ("The address read is different than the one requested! complete_address {0:04X},"
                           "complete_read_address {1:04X}, rderr_flag {2}")
                raise AddressMismatchError(
                    message, complete_address, complete_read_address, rderr_flag)
            data = val
            self.logger.debug("Reading reg\t0x{0:02X}{1:02X}, value 0x{2:04X}".format(self.moduleid, addr, data))
            return data
        else:
            return None

    def flush(self):
        """Flush all pending transactions."""
        self.board.flush()

    def firmware_wait(self, wait_value, commitTransaction=True):
        """Execute a wait of wait_value*6.25 ns"""
        self.board.wait(wait_value, commitTransaction=commitTransaction)

    def read_all(self):
        """Read all results after a flush()"""
        ret = self.board.flush_and_read_results()
        data = []
        for item in ret:
            data.append(item[1])
        return data

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        return "Not implemented yet\n"

    def generate_fred_sequences(self):
        """Generates the sequences for fred"""
        self.logger.info(f"Module {self.name}")
        self.generate_write_fred_sequence()
        self.generate_read_fred_sequence()

    def generate_write_fred_sequence(self):
        """Generates a sequence for writing to the wishbone slave
        e.g. for module 4
        84[ADDR][DATA >> 8][DATA&0xFF]"""
        self._generate_fred_sequence(write=True)

    def generate_read_fred_sequence(self):
        """Generates a sequence for writing to the wishbone slave
        e.g. for module 4
        04[ADDR]00000000"""
        self._generate_fred_sequence(write=False)

    def _generate_fred_sequence(self, write=True):
        """Generates a sequence for writing to the wishbone slave
        e.g. for module 4 write
        84[ADDR][DATA >> 8][DATA&0xFF]"""
        address = self.moduleid & 0x7F
        string = ""
        if write:
            address |= WriteReadBit.WRITE.value << 7
            string += "Write\t"
            data_string = "[DATA >> 8][DATA&0xFF]"
        else:
            string += "Read\t"
            data_string = "00000000"
        string += f"{address:02X}[ADDR]"
        string += data_string
        self.logger.info(string)
