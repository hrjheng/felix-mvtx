"""file implementing the control for the ws_i2_gbt wishbone slave"""

from enum import IntEnum
from xml.dom import minidom

import time
import os
import logging

from wishbone_module import WishboneModule

import i2c_gbtx_monitor


class WsI2cGbtxAddress(IntEnum):
    """memory mapping for the ws_i2gbtx got from ?"""
    ADDRESS_GBTX0 = 0
    ADDRESS_GBTX1 = 1
    ADDRESS_GBTX2 = 2
    DATA          = 3
    RESET         = 4
    SNIFF_I2C     = 5
    DB_FIFO_DATA  = 6
    DB_FIFO_EMPTY = 7
    DB_FIFO_RDCNT = 8

class XckuI2cBadStatusError(Exception):
    """basic class to define an XCKU I2C read error exception"""
    def __init__(self, completed_byte_count, arbitration_lost_count, noack_error_count):
        self.message = (f"I2C transaction failed - Completed_byte_count: {completed_byte_count},"
                        f"Arbitration_lost_count: {arbitration_lost_count}, Noack_error_count: {noack_error_count}")
        super().__init__(self.message)

class WsI2cGbtx(WishboneModule):
    """Wishbone module controlling the XCKU I2C master on the I2C bus shared between the XCKU (master), SCA (master) and the three GBTx chips (slaves)"""

    def __init__(self, moduleid, board_obj, monitor_module):
        """init"""
        super(WsI2cGbtx, self).__init__(moduleid=moduleid, name="Wishbone i2gbtx", board_obj=board_obj)
        assert isinstance(monitor_module, i2c_gbtx_monitor.WsI2cGbtxMonitor)
        self._monitor = monitor_module

    def set_address(self, address, gbtx_index=0, commitTransaction=True):
        """Sets the address for the next I2C transaction in GBTx gbtx """
        assert address | 0xFFFF == 0xFFFF
        self.write(WsI2cGbtxAddress.ADDRESS_GBTX0 + gbtx_index, address, commitTransaction=commitTransaction)

    def get_address(self, gbtx_index=0, commitTransaction=True):
        """Gets the address for the next I2C transaction"""
        return self.read(WsI2cGbtxAddress.ADDRESS_GBTX0 + gbtx_index, commitTransaction=commitTransaction)

    def reset_i2c_bus(self, commitTransaction=True):
        """Resets the I2C bus, toggles the SCL 9 cycles followed by STOP condition to resolve stuck slave"""
        self.write(WsI2cGbtxAddress.RESET, 0x0, commitTransaction=commitTransaction)

    def sniff_i2c(self, commitTransaction=True):
        """Gets the current value of the I2C pads"""
        val = self.read(WsI2cGbtxAddress.SNIFF_I2C, commitTransaction=commitTransaction)
        return {"sda": val >> 1, "scl": val & 0x1}

    def _get_db_fifo_data(self, commitTransaction=True):
        """Returns a 16 bit data in the FWFT debug FIFO and pops the next word"""
        return self.read(WsI2cGbtxAddress.DB_FIFO_DATA, commitTransaction=commitTransaction)

    def _get_db_fifo_empty(self, commitTransaction=True):
        """Returns the empty flag of the FWFT debug FIFO"""
        return self.read(WsI2cGbtxAddress.DB_FIFO_EMPTY, commitTransaction=commitTransaction)

    def _get_db_fifo_rdcount(self, commitTransaction=True):
        return self.read(WsI2cGbtxAddress.DB_FIFO_RDCNT, commitTransaction=commitTransaction)

    def dump_db_fifo(self, stop_at=0, verbose=True):
        """Returns the content of the debug fifo:
        stop_at used only for simulation"""
        if stop_at:
            self.logger.warning("stop_at input is only to be used in simulation!")
        values = self._get_db_fifo_rdcount()
        values = values-stop_at # skip x in sim
        results = []
        for _ in range(values):
            results.append(self._get_db_fifo_data())
        ret = []
        for i in range(len(results)):
            # Data
            scl = results[i] & 0xFF
            if verbose:
                self.logger.info(f"SCL 8'b{scl:08b}")
            sda = (results[i]>>8) & 0xFF
            if verbose:
                self.logger.info(f"Data 8'b{sda:08b}")
            ret.append((sda, scl))
        return ret

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsI2cGbtxAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str

    # Monitor
    def reset_counters(self, commitTransaction=True):
        """resets all the counters"""
        self._monitor.reset_all_counters(commitTransaction=commitTransaction)

    def read_counters(self, reset_after=False, commitTransaction=True):
        """latches and reads all the counters"""
        return self._monitor.read_counters(reset_after=reset_after, commitTransaction=commitTransaction)

    # I2C helper functions

    def _write_data(self, data, commitTransaction=True):
        """Writes the data to the corresponding GBTx register set in the last set_address
        operation (if no write/read happened in between)

        NOTE: this operation increases the address by 1!"""
        self.write(WsI2cGbtxAddress.DATA, data, commitTransaction=commitTransaction)

    def _write_data_and_check(self, data):
        """Writes the data to the corresponding GBTx register set in the last set_address
        operation (if no write/read happened in between)

        NOTE: this operation increases the address by 1!"""
        self.reset_counters()
        self.write(WsI2cGbtxAddress.DATA, data)
        self._check_i2c_transcation()

    def _check_i2c_transcation(self):
        counters = self._monitor.read_counters(reset_after=True)
        error = False
        if counters['completed_byte_count'] < 4:
            self.logger.warning("completed_byte_count less than 4!")
            error = True
        if counters['arbitration_lost_error_count'] > 0:
            self.logger.warning("arbitration_lost_error_count is higher than 0!")
            error = True
        if counters['noack_error_count'] > 0:
            self.logger.warning("noack_error_count is higher than 0!")
            error = True
        if error:
            raise XckuI2cBadStatusError(counters['completed_byte_count'],
                                        counters['arbitration_lost_error_count'],
                                        counters['noack_error_count'])


    def _read_data(self, commitTransaction=True):
        """Read the data from the corresponding GBTx register set in the last set_address
        operation (if no write/read happened in between)

        NOTE: this operation increases the address by 1!"""
        return self.read(WsI2cGbtxAddress.DATA, commitTransaction=commitTransaction)

    def _read_data_and_check(self):
        """Read the data from the corresponding GBTx register set in the last set_address
        operation (if no write/read happened in between)

        NOTE: this operation increases the address by 1!"""
        self.reset_counters()
        val = self.read(WsI2cGbtxAddress.DATA)
        self._check_i2c_transcation()
        return val

    def _check_data(self, expected_data=0x0):
        """Reads and checks the data from the corresponding GBTx register set in the last set_address
        operation (if no write/read happened in between)

        NOTE: this operation increases the address by 1!"""
        data = self._read_data(commitTransaction=True)
        if data != expected_data:
            self.logger.warning(f"Data was not as expected {data} != {expected_data}")
            return False
        return True

    # GBTx I2C functions

    def read_gbtx_register(self, register, gbtx_index=0, check=True, commitTransaction=True):
        """Reads the data to the corresponding GBTx register"""
        self.set_address(address=register, gbtx_index=gbtx_index, commitTransaction=False)
        if check:
            return self._read_data_and_check()
        else:
            return self._read_data(commitTransaction=commitTransaction)

    def write_gbtx_register(self, register, value, gbtx_index=0, check=True, commitTransaction=True):
        """Writes the data to the corresponding GBTx register"""
        self.set_address(address=register, gbtx_index=gbtx_index, commitTransaction=False)
        if check:
            self._write_data_and_check(data=value)
        else:
            self._write_data(data=value, commitTransaction=commitTransaction)


    def check_gbtx_register(self, register, expected_data, gbtx_index=0):
        """Reads and checks the data from the corresponding GBTx register"""
        data = self.read_gbtx_register(register, gbtx_index)
        if data != expected_data:
            self.logger.warning(f"Register {register} was {data:02x} != expected {expected_data:02x}")
            return False
        return True

    def dump_gbtx_config(self, gbtx_index):
        """Dump the modules state and configuration as a string"""
        assert gbtx_index in range(3)
        GBTx_REG_MAX = 435
        SINGLE_I2C_TRANSACTION_TIME = 72000 # in WB_CLK clock cycles
        waittime = GBTx_REG_MAX*SINGLE_I2C_TRANSACTION_TIME
        config_str = "--- GBTx {0} ASIC ---\n".format(gbtx_index)
        config_str += "  - :\n"
        self.set_address(address=0, gbtx_index=gbtx_index, commitTransaction=False)
        for address in range(GBTx_REG_MAX):
            self._read_data(commitTransaction=False)
        self.flush()
        time.sleep(waittime*6.25e-9)
        results = self.read_all()
        for address in range(GBTx_REG_MAX):
            value = results[address]
            config_str += "    - {0} : {1:#06X}\n".format(address, value)
        return config_str

    def gbtx_config(self, registers, gbtx_index=0, check=True):
        """Write GBTx xml configuration data in file "filename" to GBTx "gbtx" """
        assert gbtx_index in range(3)

        for reg in registers:
            self.write_gbtx_register(register=reg[0], value=reg[1], gbtx_index=gbtx_index, check=check)

    def check_gbtx_config(self, registers, gbtx_index=0):
        assert gbtx_index in range(3)

        num_errors = 0
        for reg in registers:
            try:
                if not self.check_gbtx_register(register=reg[0], expected_data=reg[1], gbtx_index=gbtx_index):
                    num_errors += 1
            except Exception as e:
                self.logger.error(f"Reading of register {reg[0]} failed - could not check")
                num_errors += 1
        if num_errors > 0:
            return False
        return True

    # Recover bus

    def is_bus_stuck(self):
        bus_sniff = self.sniff_i2c()
        if not bus_sniff['sda'] or not bus_sniff['scl']:
            return True
        return False

    def recover_stuck_bus(self):
        if self.is_bus_stuck():
            self.logger.info("Bus is stuck - attempting recovery...")
            for _ in range(10):
                self.reset_i2c_bus()
                if not self.is_bus_stuck():
                    self.logger.info("Bus is recovered by I2C reset!")
                    return True
            self.logger.info("I2C reset not sufficient, attempting force write of GBTx1&2!")
            for _ in range(10):
                self.write_gbtx_register(0, 0, 1, False)
                self.write_gbtx_register(0, 0, 2, False)
                if not self.is_bus_stuck():
                    self.logger.info("Bus is recovered by force write!")
                    return True
            self.logger.error("Bus recovery failed - powercycle required!")
            return False
        else:
            self.logger.info("Bus is not stuck - no recovery needed")
