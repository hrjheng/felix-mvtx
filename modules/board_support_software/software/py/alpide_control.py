"""Class to implement the latest capabilities of the alpidecontrol/ctrl block relative to
trigger commands with busy management"""

from enum import IntEnum, unique

from wishbone_module import WishboneModule
from userdefinedexceptions import ChipidMismatchError
from userdefinedexceptions import DataReadbackMismatchError

import alpide_control_monitor
import traceback

@unique
class WsAlpideControlAddress(IntEnum):
    """memory mapping for alpide control module"""
    WRITE_CTRL             =  0
    WRITE_ADDRESS          =  1
    WRITE_DATA             =  2
    PHASE_FORCE            =  3
    READ_STATUS            =  4
    READ_DATA              =  5
    DEAD00                 =  6
    DEAD01                 =  7
    DEAD02                 =  8
    DEAD03                 =  9
    DEAD04                 = 10
    DEAD05                 = 11
    DEAD06                 = 12
    DEAD07                 = 13
    DEAD08                 = 14
    DEAD09                 = 15
    DEAD10                 = 16
    SET_DCTRL_INPUT        = 17
    SET_DCTRL_TX_MASK      = 18
    DEAD11                 = 19
    DEAD12                 = 20
    DEAD13                 = 21
    MANCHESTER_TX_EN       = 22
    DEAD14                 = 23
    DEAD15                 = 24
    DEAD16                 = 25
    DEAD17                 = 26
    DEAD18                 = 27
    DEAD19                 = 28
    DEAD20                 = 29
    DEAD21                 = 30
    DEAD22                 = 31
    DEAD23                 = 32
    AUTO_PHASE_OFFSET      = 33
    SET_DCLK_PARALLEL_0    = 34
    SET_DCLK_PARALLEL_1    = 35
    SET_DCLK_PARALLEL_2    = 36
    SET_DCLK_PARALLEL_3    = 37
    SET_DCLK_PARALLEL_4    = 38
    WAIT_CYCLES            = 39
    MANCHESTER_RX_DETECTED = 40
    DEAD24                 = 41
    DEAD25                 = 42
    DEAD26                 = 43
    DEAD27                 = 44
    DEAD28                 = 45
    DEAD29                 = 46
    DEAD30                 = 47
    DB_FIFO_DATA           = 48
    DB_FIFO_EMPTY          = 49
    DB_FIFO_RDCOUNT        = 50


class AlpideControl(WishboneModule):
    """Alpide Control wishbone slave"""

    PHASE_DCLK_OFF = 0b11111111
    PHASE_DCLK_DEFAULT = 180

    DB_FIFO_DEPTH = 128

    def __init__(self, moduleid, board_obj, monitor_module):
        super(AlpideControl, self).__init__(moduleid=moduleid, name="ALPIDE CONTROL", board_obj=board_obj)
        self.verbose = False
        self.connector_used = None
        self.phase_dict = {0:   0b11110000,
                           45:  0b11100001,
                           90:  0b11000011,
                           135: 0b10000111,
                           180: 0b00001111,
                           225: 0b00011110,
                           270: 0b00111100,
                           315: 0b01111000}
        self.phase_dict_inv = {v: k for k, v in self.phase_dict.items()}
        self.mask = None

        assert isinstance(monitor_module, alpide_control_monitor.AlpideControlMonitor)
        self._monitor = monitor_module

    def force_phase(self, phase, commitTransaction=True):
        """Forces offset sampling phase for the DCTRL"""
        assert phase | 0x7 == 0x7
        self.write(WsAlpideControlAddress.PHASE_FORCE, 1<<3|phase, commitTransaction)

    def release_phase_force(self, commitTransaction=True):
        """Release the force on offset sampling phase for DCTRL"""
        phase = self.read(WsAlpideControlAddress.PHASE_FORCE, True)&0x7
        self.write(WsAlpideControlAddress.PHASE_FORCE, phase, commitTransaction)

    def get_phase_force(self, commitTransaction=True):
        return self.read(WsAlpideControlAddress.PHASE_FORCE, commitTransaction)>>3 & 0x1

    def get_phase(self, commitTransaction=True):
        """Get offset sampling phase for DCTRL"""
        return self.read(WsAlpideControlAddress.PHASE_FORCE, commitTransaction)&0x7

    def set_auto_phase_offset(self, offset, commitTransaction=True):
        """sets the phase offset for the automatic phase detection"""
        assert offset | 0x7 == 0x7
        self.write(WsAlpideControlAddress.AUTO_PHASE_OFFSET, offset, commitTransaction=commitTransaction)

    def get_auto_phase_offset(self, commitTransaction=True):
        """gets the phase offset for the automatic phase detection"""
        return self.read(WsAlpideControlAddress.AUTO_PHASE_OFFSET, commitTransaction=commitTransaction)

    def write_chip_reg(self, address, data, extended_chipid, commitTransaction=True, readback=None):
        """Write to a specific register on the chip. commitTransaction
        flushes all pending write operations and sends it to the
        board.
        """
        if readback is None:
            readback = False

        self._set_up_dctrl(extended_chipid)

        #YCM disable OB configuration for MVTX project
        assert (extended_chipid == 0xF) or \
            ((self.mask & 0x4) == 0x4 and (extended_chipid < 15)) #or \
           #((self.mask & 0x1) == 0x1 and (extended_chipid & 0x88) == 0x08) or \
           #((self.mask & 0x2) == 0x2 and (extended_chipid & 0x88) == 0x00) or \
           #((self.mask & 0x4) == 0x4 and (extended_chipid & 0x88) == 0x88) or \
           #((self.mask & 0x8) == 0x8 and (extended_chipid & 0x88) == 0x80)

        chipid = extended_chipid & 0x7F

        assert chipid|0x7F == 0x7F
        assert address|0xFFFF == 0xFFFF
        assert data|0xFFFF == 0xFFFF
        self.write(WsAlpideControlAddress.WRITE_ADDRESS, address, commitTransaction=False)
        self.write(WsAlpideControlAddress.WRITE_DATA, data, commitTransaction=False)
        self.write(WsAlpideControlAddress.WRITE_CTRL, 0x9C<<8|chipid, commitTransaction=False)
        self.logger.debug("Write chip register: ChipId: %#2X Addr: %#4X, Data: %04X, commit: %s",
                          chipid, address, data, commitTransaction)
        if readback:
            self.flush()
            self.board.wait(1000, False)
            dataread = self.board.read_chip_reg(address=address, extended_chipid=extended_chipid, commitTransaction=True)
            if address == 0x14: # Special ALPIDE register:
                                # only bits 0 - 8 are writable, 12 is read-only
                                # makes readback fail due to the read-only bit, catching this at the lowest possible level
                dataread = dataread & 0x1FF
            if dataread != data:
                message = "RU {2} data read from {3:#04X} is {1:#04X} while {0:#04X} was expected"
                msg_log = message.format(data, dataread, self.board.get_gbt_channel(), address)
                self.logger.error(msg_log)
                raise DataReadbackMismatchError(message, data, dataread)

        self._reset_dctrl_mask(commitTransaction=False)

        if commitTransaction:
            self.flush()

    def read_chip_reg(self, address, extended_chipid, disable_read=False, commitTransaction=True):
        """Read from a specific chip Register.  commitTransaction flushes all
        pending write operations and sends it to the board.
        """
        if disable_read:
            return 0
        else:
            #self.set_auto_phase_offset(offset=7) # hack used for on surface commissioning in 167 to circumvent phase detection issues with certain FW versions
            self._set_up_dctrl(extended_chipid)
            assert self.connector_used is not None, "Input connector is not set"
            read_done = False
            max_repeat = 1
            repeat = 0

            chipid = extended_chipid & 0x7F
            #YCM disable OB configuration for MVTX project
            assert (self.connector_used == 2 and extended_chipid < 0xF) #or \
                #(self.connector_used in [0,1] and not (extended_chipid & 0x80)) or \
                #(self.connector_used in [2,3] and (extended_chipid & 0x80))
            assert self.mask & (0x1 << self.connector_used) == (0x1 << self.connector_used)
            assert (extended_chipid != 0xF) and ((extended_chipid < 0xF) or ((extended_chipid & 0x7) != 0x7)) # NOT a broadcast chip id

            if ((address & 0x300) >> 8) == 0x1:
                self.logger.info(f"POTENTIAL SPURIOUS TRIGGER: reading address {hex(address)}, chip ID {hex(chipid)}")
                self.logger.info("Traceback:\n"+"".join(traceback.format_stack()))

            while repeat < max_repeat:
                assert chipid|0x7F == 0x7F
                assert address|0xFFFF == 0xFFFF
                self.write(WsAlpideControlAddress.WRITE_ADDRESS, address, commitTransaction=False)
                self.write(WsAlpideControlAddress.WRITE_CTRL, 0x4E<<8|chipid, commitTransaction=False)
                self.read(WsAlpideControlAddress.READ_STATUS, commitTransaction=False)
                self.read(WsAlpideControlAddress.READ_DATA, commitTransaction=False)
                output_stream = self.read_all()
                read_done = True
                status = output_stream[0]
                data = output_stream[1]
                chipid_read = status & 0x7F
                state = status>>7 & 0x3F
                selected_phase = status>>13

                self.logger.debug( ("Read chip register: ChipId: %#2X Addr: %#4X, Data read: %04X, "
                                   "chipid read: %#02X, status: %#02X commit: %s, "
                                    "phase_selected: %d"),
                                   chipid, address, data, chipid_read, state,
                                   commitTransaction, selected_phase)

                if state != 0x3F:
                    gbt_ch = self.board.get_gbt_channel()
                    self.logger.error("RU %d: status read is %#X while 0x3F was expected. status %#04X. data %#04X. "
                                      "Connector %r, Phase %d",
                                      gbt_ch, state, status, data, self.connector_used, selected_phase)
                    self.logger.info("Dumping the debug fifo:")
                    db_fifo_data = self.dump_db_fifo(verbose=False)
                    for data in db_fifo_data:
                        self.logger.error(f"Data 8'b{data:08b}")
                    read_done = False
                if chipid_read != chipid:
                    message = "Chipid read is 0b{0:07b} while 0b{1:07b} was expected on connector {2:1x}"
                    msg_log = message.format(chipid_read, chipid, self.connector_used)
                    self.logger.error(msg_log)
                    self.logger.error("Connector {0}, Phase {1}".format(self.connector_used, selected_phase))
                    self.logger.info("Dumping the debug fifo:")
                    db_fifo_data = self.dump_db_fifo(verbose=False)
                    for data in db_fifo_data:
                        self.logger.error(f"Data 8'b{data:08b}")
                    if repeat == max_repeat-1:
                        raise ChipidMismatchError(message, chipid, chipid_read, self.connector_used)
                    read_done = False
                repeat += 1
                self.logger.debug("dctrl read_chip_reg: repeat = %d, read_done %s", repeat, read_done)
                if read_done:
                    break
            self._reset_dctrl_mask(commitTransaction=False)

            if commitTransaction:
                self.flush()

            return data

    def write_chip_opcode(self, opcode, extended_chipid=0xF, commitTransaction=True):
        """Write a specific opcode to the chip. commitTransaction
        flushes all pending write operations and sends it to the
        board.
        """
        self._set_up_dctrl(extended_chipid, commitTransaction=False)
        self.write(WsAlpideControlAddress.WRITE_CTRL, opcode<<8|0, commitTransaction=commitTransaction)
        self.logger.debug("Write chip opcode: %#02X, commitTransaction: %s",
                          opcode, commitTransaction)
        self._set_up_dctrl(extended_chipid, commitTransaction=commitTransaction)

    def _set_up_dctrl(self, extended_chipid, commitTransaction=True):
        """Preparing the DCTRL interface for a read/write transaction based on the extended_chipid"""

        if extended_chipid == 0xF: # general broadcast
            self._set_dctrl_mask(mask=0x1F, commitTransaction=False)
            # No broadcast read, keep mask untouched
        elif extended_chipid == 0x8000: # HS-L only broadcast
            self._set_dctrl_mask(mask=0x3, commitTransaction=False)
            # No broadcast read, keep mask untouched
        elif extended_chipid == 0x8001: # HS-U only broadcast
            self._set_dctrl_mask(mask=0xC, commitTransaction=False)
            # No broadcast read, keep mask untouched
        elif extended_chipid < 0xF: # IB (for MVTX dctrl_input=2, mask=0x4)
            self._set_dctrl_mask(mask=0x4, commitTransaction=False)
            self._set_input(dctrl_input=2, commitTransaction=False)
        elif not (extended_chipid & 0x80): # HS-L
            if (extended_chipid & 0x8): # Masters A8
                self._set_input(dctrl_input=0, commitTransaction=False)
                self._set_dctrl_mask(mask=0x01, commitTransaction=False)
            else:                       # Masters B0
                self._set_input(dctrl_input=1, commitTransaction=False)
                self._set_dctrl_mask(mask=0x02, commitTransaction=False)
        elif (extended_chipid & 0x80): # HS-U
            if (extended_chipid & 0x8): # Masters A8
                self._set_input(dctrl_input=2, commitTransaction=False)
                self._set_dctrl_mask(mask=0x04, commitTransaction=False)
            else:                       # Masters B0
                self._set_input(dctrl_input=3, commitTransaction=False)
                self._set_dctrl_mask(mask=0x08, commitTransaction=False)
        else:
            self.logger.error(f"Failed to set up DCTRL input and mask for chip 0x{extended_chipid:X}")

        if commitTransaction:
            self.flush()


    def _reset_dctrl_mask(self, commitTransaction=True):
        """ Resets DCTRL mask to default value, all lines active """
        self._set_dctrl_mask(0x1F, commitTransaction=commitTransaction)

    def _set_input(self, dctrl_input=0, force=False, commitTransaction=True):
        """Sets which DCTRL line is used to receive chip replies"""
        assert dctrl_input in range(5)
        if force or dctrl_input != self.connector_used:
            self.logger.debug(f"Set connector to {dctrl_input}, was {self.get_input()}")
            self.write(WsAlpideControlAddress.SET_DCTRL_INPUT, dctrl_input, commitTransaction=commitTransaction)
            self.connector_used = dctrl_input
            assert dctrl_input == self.get_input()
        elif commitTransaction:
            self.flush()

    def set_input(self, dctrl_input=0, force=False, commitTransaction=True):
        self.logger.warning("alpide_control.set_input(...) is deprecated")
        traceback.print_stack()

    def get_input(self):
        """Read on which line the dctrl receives replies """
        return self.read(WsAlpideControlAddress.SET_DCTRL_INPUT)

    def set_dctrl_mask(self, mask, commitTransaction=True):
        self.logger.warning("alpide_control.set_dctrl_mask(...) is deprecated")
        traceback.print_stack()

    def _set_dctrl_mask(self, mask, commitTransaction=True):
        """sets a 1-hot mask for transmission on DCTRL"""
        assert mask | 0x1F == 0x1F
        if self.mask != mask:
            self.mask = mask
            self.write(WsAlpideControlAddress.SET_DCTRL_TX_MASK, mask, commitTransaction=commitTransaction)
            self.logger.debug(f"Setting dctrl mask to 0x{mask:02X}")
        elif commitTransaction:
            self.flush()

    def get_dctrl_mask(self):
        """gets a 1-hot mask for transmission on DCTRL"""
        return self.read(WsAlpideControlAddress.SET_DCTRL_TX_MASK)

    def set_dctrl_mask_for_ib_stave(self, commitTransaction=True):
        """Sets the dctrl_mask to use the ib stave"""
        self.set_dctrl_mask(mask=0x10, commitTransaction=commitTransaction)

    def set_dctrl_mask_for_lower_ob_stave(self, commitTransaction=True):
        """Sets the dctrl_mask to use the lower ob stave"""
        self.set_dctrl_mask(mask=0x3, commitTransaction=commitTransaction)

    def set_dctrl_mask_for_upper_ob_stave(self, commitTransaction=True):
        """Sets the dctrl_mask to use the upper ob stave"""
        self.set_dctrl_mask(mask=0xC, commitTransaction=commitTransaction)

    def enable_all_dctrl_connectors(self, commitTransaction=True):
        """Sets the dctrl_mask to use all the connectors"""
        self.set_dctrl_mask(mask=0x1F, commitTransaction=commitTransaction)

    def disable_all_dctrl_connectors(self, commitTransaction=True):
        """Sets the dctrl_mask to use no connectors"""
        self._set_dctrl_mask(mask=0x0, commitTransaction=commitTransaction)

    def enable_manchester_tx(self, commitTransaction=True):
        """Enables the manchester encoding in transmission"""
        self.write(WsAlpideControlAddress.MANCHESTER_TX_EN, 1, commitTransaction=commitTransaction)

    def disable_manchester_tx(self, commitTransaction=True):
        """Disables the manchester encoding in transmission"""
        self.write(WsAlpideControlAddress.MANCHESTER_TX_EN, 0, commitTransaction=commitTransaction)

    def get_manchester_tx(self):
        """check if the manchester encoding in transmission is enabled"""
        return self.read(WsAlpideControlAddress.MANCHESTER_TX_EN)

    def set_dclk_parallel(self, phase, index, commitTransaction=True):
        """sets the dclk parallel with the given phase [0:45:360-45]"""
        assert index in range(5)
        assert phase in self.phase_dict.keys()
        self.write(WsAlpideControlAddress.SET_DCLK_PARALLEL_0+index, self.phase_dict[phase], commitTransaction=commitTransaction)

    def get_dclk_parallel(self, index, commitTransaction=True):
        """gets the dclk parallel phase [0:45:360-45]"""
        assert index in range(5)
        dclk_parallel = self.read(WsAlpideControlAddress.SET_DCLK_PARALLEL_0+index, commitTransaction=commitTransaction)
        if dclk_parallel in self.phase_dict_inv:
            return self.phase_dict_inv[dclk_parallel]
        elif dclk_parallel == self.PHASE_DCLK_OFF:
            return "OFF"
        else:
            return f"INVALID: {dclk_parallel}"

    def enable_dclk(self, index = [0,1,2,3,4], phase = PHASE_DCLK_DEFAULT, commitTransaction=True):
        """Re-enables DCLK for chips, index is either a list of lane indexes or a single lane index, phase is [0:45:360-45]"""
        assert phase in self.phase_dict.keys()
        self.logger.debug(f"clock phase: {phase}")
        if not isinstance(index, list):
            index = [index]
        for i in index:
            self._enable_dclk(index=i, phase=phase, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def _enable_dclk(self, index, phase, commitTransaction=True):
        """Enables the DCLK for a specific connector"""
        assert index in range(5)
        self.write(WsAlpideControlAddress.SET_DCLK_PARALLEL_0+index, self.phase_dict[phase], commitTransaction=commitTransaction)

    def disable_dclk(self, index=[0,1,2,3,4], commitTransaction=True):
        """Disables DCLK for chips, sets output high, index is either a list of lane indexes or a single lane index"""
        if not isinstance(index, list):
            index = [index]
        for i in index:
            self._disable_dclk(index=i, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def _disable_dclk(self, index, commitTransaction=True):
        """Enables the DCLK for a specific connector"""
        assert index in range(5)
        self.write(WsAlpideControlAddress.SET_DCLK_PARALLEL_0+index, self.PHASE_DCLK_OFF, commitTransaction=commitTransaction)

    def set_wait_cycles(self, value, commitTransaction=True):
        """sets the wait cycles for the automatic phase detection"""
        assert value | 0x1F == 0x1F
        self.write(WsAlpideControlAddress.WAIT_CYCLES, value, commitTransaction=commitTransaction)

    def get_wait_cycles(self, commitTransaction=True):
        """gets the wait cycles for the automatic phase detection"""
        return self.read(WsAlpideControlAddress.WAIT_CYCLES, commitTransaction=commitTransaction)

    def get_manchester_rx_detected(self, commitTransaction=True):
        """Returns 1 if manchester has been detected"""
        return self.read(WsAlpideControlAddress.MANCHESTER_RX_DETECTED, commitTransaction=commitTransaction) & 0x1

    def _get_db_fifo_data(self, commitTransaction=True):
        """Returns a 16 bit data in the FWFT debug FIFO and pops the next word"""
        return self.read(WsAlpideControlAddress.DB_FIFO_DATA, commitTransaction=commitTransaction)

    def _get_db_fifo_empty(self, commitTransaction=True):
        """Returns the empty flag of the FWFT debug FIFO"""
        return self.read(WsAlpideControlAddress.DB_FIFO_EMPTY, commitTransaction=commitTransaction)

    def _get_db_fifo_rdcount(self, commitTransaction=True):
        return self.read(WsAlpideControlAddress.DB_FIFO_RDCOUNT, commitTransaction=commitTransaction) & 0x7F

    def dump_db_fifo(self, stop_at=0, verbose=True):
        """Returns the content of the debug fifo:
        stop_at used only for simulation"""
        if stop_at:
            self.logger.warning("stop_at input is only to be used in simulation!")
        values = self._get_db_fifo_rdcount()
        values = values-stop_at # skip x in sim
        for _ in range(values):
            self._get_db_fifo_data(commitTransaction=False)
        ret = []
        results = self.board.flush_and_read_results(expected_length=values)
        for i in range(len(results)):
            # Data
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == WsAlpideControlAddress.DB_FIFO_DATA, \
                "Requested to read address {0}, but got result for address {1}, iteration {2}".format(WsAlpideControlAddress.DB_FIFO_DATA, (results[i][0] & 0xff), i)
            data_l = (results[i][1]>>0) & 0xFF
            if verbose:
                self.logger.info(f"Data 8'b{data_l:08b}")
            data_h = (results[i][1]>>8) & 0xFF
            if verbose:
                self.logger.info(f"Data 8'b{data_h:08b}")
            ret.append(data_l)
            ret.append(data_h)
        return ret

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsAlpideControlAddress:
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

    def read_counters(self, counters=None, reset_after=False, commitTransaction=True):
        """latches and reads all the counters"""
        return self._monitor.read_counters(counters=counters, reset_after=reset_after, commitTransaction=commitTransaction)

    # Under deprecation

    def get_counters(self, reset_after=False, commitTransaction=True):
        raise DeprecationWarning("Deprecated method: use read_counters instead")
        return self._monitor.read_counters(reset_after=reset_after, commitTransaction=commitTransaction)

    def rst_ctrl_cntrs(self, commitTransaction=True):
        raise NotImplementedError("Obsolete function")

    def busy_force(self, force_value):
        """forces the busy logic to the given value
        Note that the force is not applied to the chip and this force is olny
        relative to the logic steering the trigger generation isnide the
        ctrl/dctrl block"""
        raise NotImplementedError("Functionality removed")

    def busy_force_release(self):
        """releases the force on busy logic"""
        raise NotImplementedError("Functionality removed")

    def get_busy_transceiver_mask(self):
        """gets the actual value of the busy transceiver mask"""
        raise NotImplementedError("Functionality removed")

    def set_busy_transceiver_mask(self, mask):
        """sets the busy transceiver mask"""
        raise NotImplementedError("Functionality removed")

    def get_busy_transceiver_status(self):
        """gets the status of the busy flag for the transceivers"""
        raise NotImplementedError("Functionality removed")

    def on_poweron_chip(self,avdd,dvdd,pvdd,backbias):
        raise DeprecationWarning("Deprecated method")
        self.logger.debug("Power on chip with AVDD=%2.2f, DVDD=%2.2f, PVDD=%s, BB=%s",
                         avdd,dvdd,pvdd,backbias)

    def on_poweroff_chip(self):
        raise DeprecationWarning("Deprecated method")
        self.logger.debug("Power off chip")
