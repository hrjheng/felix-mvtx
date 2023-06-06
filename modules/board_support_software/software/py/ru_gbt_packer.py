"""Implements the control for the gbt_packer_wishbone wishbone slave"""

from enum import IntEnum, unique

from wishbone_module import WishboneModule

@unique
class GbtPackerAddress(IntEnum):
    """Memory mapping for the gbt_packer_wishbone"""
    TIMEOUT_TO_START      = 0
    TIMEOUT_START_STOP    = 1
    TIMEOUT_IN_IDLE       = 2
    RESET                 = 3
    GBTX_FIFO_EMPTY       = 4
    LANE_FIFO_EMPTY       = 5
    PROTOCOL_CONFIG       = 6
    SKIP_ITS_PAYLOAD      = 7
    DATA_EXCLUSIVE_PACKET = 8


class GbtPacker(WishboneModule):
    """GBT packer wishbone module"""

    def __init__(self, moduleid, board_obj, monitor0, monitor1, monitor2):
        super(GbtPacker, self).__init__(moduleid=moduleid,board_obj=board_obj,name="GBT Packer")
        self.addr_list = GbtPackerAddress
        self._monitor0 = monitor0
        self._monitor1 = monitor1
        self._monitor2 = monitor2
        self._monitor1.set_as_slave_monitor()
        self._monitor2.set_as_slave_monitor()

    def set_timeout_to_start(self, data, commitTransaction=True):
        """Set the timeout from receiving a trigger to the first received start from a lane"""
        assert data | 0xFFFF == 0xFFFF
        self.write(GbtPackerAddress.TIMEOUT_TO_START, data, commitTransaction)

    def set_timeout_start_stop(self, data, commitTransaction=True):
        """Set the timeout from receiving a start from any lane until the last stop is received"""
        assert data | 0xFFFF == 0xFFFF
        self.write(GbtPackerAddress.TIMEOUT_START_STOP, data, commitTransaction)

    def set_timeout_in_idle(self, data, commitTransaction=True):
        """Set the timeout when all lanes are not presenting data, after a start"""
        assert data | 0xFFFF == 0xFFFF
        self.write(GbtPackerAddress.TIMEOUT_IN_IDLE, data, commitTransaction)

    def get_timeout_to_start(self, commitTransaction=True):
        """Get the timeout from receiving a trigger to the first received start from a lane"""
        return self.read(GbtPackerAddress.TIMEOUT_TO_START, commitTransaction)

    def get_timeout_start_stop(self, commitTransaction=True):
        """Get the timeout from receiving a start from any lane until the last stop is received"""
        return self.read(GbtPackerAddress.TIMEOUT_START_STOP, commitTransaction)

    def get_timeout_in_idle(self, commitTransaction=True):
        """Get the timeout when all lanes are not presenting data, after a start"""
        return self.read(GbtPackerAddress.TIMEOUT_IN_IDLE, commitTransaction)

    def set_reset(self, value, commitTransaction=True):
        """Set the reset register of the GBT packer. When set, keeps the packer in disabled/reset mode and empties the trigger fifo"""
        assert value | 0x1 == 0x1
        self.write(GbtPackerAddress.RESET, value, commitTransaction)

    def reset(self, commitTransaction=True):
        """Toggle reset of GBT packer and flush trigger fifos"""
        for value in [1, 0]:
            self.write(GbtPackerAddress.RESET, value, commitTransaction)

    def is_gbtx_fifo_empty(self, fifo_id=0):
        """Return True if the specified GBTx output FIFO is empty"""
        assert fifo_id in range(3), f"FIFO identifier must be within range 0-2"
        val = (self.read(GbtPackerAddress.GBTX_FIFO_EMPTY) >> fifo_id) & 0x1
        return val == 0x1

    def are_gbtx_fifos_empty(self):
        """Return True if all GBTx output FIFOs are empty"""
        val = self.read(GbtPackerAddress.GBTX_FIFO_EMPTY) & 0x7
        return val == 0x7

    def are_lane_fifos_empty(self):
        """Return True if all lane FIFOs are empty"""
        val = self.read(GbtPackerAddress.LANE_FIFO_EMPTY) & 0x1
        return val == 0x1

    def write_protocol_config(self, value, commitTransaction=True):
        """Write the protocol configuration register of the GBT packer"""
        assert value | 0x3 == 0x3
        self.write(GbtPackerAddress.PROTOCOL_CONFIG, value, commitTransaction)

    def set_ddw_and_ihw_on_trigger_only(self, commitTransaction=True):
        """When set, transmit DDW and IHW only if there are triggers in the HBF"""
        self.write_protocol_config(0x3, commitTransaction)

    def clear_protocol_config(self, commitTransaction=True):
        """When cleared, always transmit DDW and IHW"""
        self.write_protocol_config(0x0, commitTransaction)

    def write_skip_its_payload(self, value, commitTransaction=True):
        """Write the skip ITS payload register of the GBT packer"""
        assert value | 0x1 == 0x1
        self.write(GbtPackerAddress.SKIP_ITS_PAYLOAD, value, commitTransaction)

    def set_skip_its_payload(self, commitTransaction=True):
        """Set the skip ITS payload register of the GBT packer"""
        self.write_skip_its_payload(0x1, commitTransaction)

    def clear_skip_its_payload(self, commitTransaction=True):
        """Set the skip ITS payload register of the GBT packer"""
        self.write_skip_its_payload(0x0, commitTransaction)

    def write_data_exclusive_packet(self, value, commitTransaction=True):
        """Set the data exclusive packet register of the GBT packer"""
        assert value | 0x1 == 0x1
        self.write(GbtPackerAddress.DATA_EXCLUSIVE_PACKET, value, commitTransaction)

    def set_data_exclusive_packet(self, commitTransaction=True):
        """Set the data exclusive packet register of the GBT packer"""
        self.write_data_exclusive_packet(0x1, commitTransaction)

    def clear_data_exclusive_packet(self, commitTransaction=True):
        """Clear the data exclusive packet register of the GBT packer"""
        self.write_data_exclusive_packet(0x0, commitTransaction)

    # Monitor

    def reset_counter(self, register, commitTransaction=True):
        """Resets counter specified in 'register'"""
        self._monitor0.reset_counter(register=register, commitTransaction=commitTransaction)
        self._monitor1.reset_counter(register=register, commitTransaction=commitTransaction)
        self._monitor2.reset_counter(register=register, commitTransaction=commitTransaction)

    def reset_all_counters(self, commitTransaction=True):
        """Reset all counters (master=>slave)"""
        self._monitor0.reset_all_counters(commitTransaction)

    def latch_counters(self, commitTransaction=False):
        """Latches values into counters (master=>slave)"""
        self._monitor0.latch_all_counters(commitTransaction)

    def read_counters(self, counters=None, reset_after=False, commitTransaction=True):
        """Read all counters in a counter monitor"""
        ret = []
        ret.append(self._monitor0.read_counters(counters=counters, latch_first=True, reset_after=reset_after, commitTransaction=commitTransaction))
        ret.append(self._monitor1.read_counters(counters=counters, latch_first=False, reset_after=False, commitTransaction=commitTransaction))
        ret.append(self._monitor2.read_counters(counters=counters, latch_first=False, reset_after=False, commitTransaction=commitTransaction))
        return ret

    def read_counter(self, counter=None, reset_after=False, commitTransaction=True):
        """Reads a single counter, returns only the value"""
        ret = []
        ret.append(self._monitor0.read_counter(counter=counter, latch_first=True, reset_after=reset_after, commitTransaction=commitTransaction))
        ret.append(self._monitor1.read_counter(counter=counter, latch_first=False, reset_after=False, commitTransaction=commitTransaction))
        ret.append(self._monitor2.read_counter(counter=counter, latch_first=False, reset_after=False, commitTransaction=commitTransaction))
        return ret

    def read_all_counters(self):
        """Read all counters of monitor"""
        return self.read_counters()

    def get_nums(self, cnt_pre, cnt_post):
        nums = dict()
        nums['TRIGGER_READ'] = cnt_post['TRIGGER_READ'] - cnt_pre['TRIGGER_READ']
        nums['SOP_SENT'] = cnt_post['SOP_SENT'] - cnt_pre['SOP_SENT']
        nums['EOP_SENT'] = cnt_post['EOP_SENT'] - cnt_pre['EOP_SENT']
        nums['PACKET_DONE'] = cnt_post['PACKET_DONE'] - cnt_pre['PACKET_DONE']
        nums['PACKET_EMPTY'] = cnt_post['PACKET_EMPTY'] - cnt_pre['PACKET_EMPTY']
        return nums

    def get_rates(self, nums, th_nums):
        if th_nums['TF'] == 0:
            self.logger.error("Found no timeframes")
            exit()
        elif th_nums['HBA'] == 0:
            self.logger.error("Found no HBA")
            exit()

        rates = dict()
        rates['TRIGGER_READ'] = round(nums['TRIGGER_READ'] / th_nums['TF'], 1)
        rates['SOP_SENT'] = round(nums['SOP_SENT'] / th_nums['HBA'], 1)
        rates['EOP_SENT'] = round(nums['EOP_SENT'] / th_nums['HBA'], 1)
        rates['PACKET_DONE'] = round(nums['PACKET_DONE'] / th_nums['HBA'], 1)
        rates['PACKET_EMPTY'] = round(nums['PACKET_EMPTY'] / th_nums['HBA'], 1)
        return rates

    def format_rates(self, rates):
        log = \
            f"TRIGGER_READ/TF: {rates['TRIGGER_READ']} - " + \
            f"SOP/HBA: {rates['SOP_SENT']} - " + \
            f"EOP/HBA: {rates['EOP_SENT']} - " + \
            f"PACKET_DONE/HBA: {rates['PACKET_DONE']} - " + \
            f"PACKET_EMPTY/HBA: {rates['PACKET_EMPTY']}"
        return log

    # Dump module

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in GbtPackerAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
