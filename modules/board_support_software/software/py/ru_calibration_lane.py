"""file implementing the control for the calibration_lane wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule

@unique
class CalibrationLaneAddress(IntEnum):
    """memory mapping for the calibration_lane got from calibration_lane_wishbone_pkg.vhd"""
    USER_FIELD_0 = 0
    USER_FIELD_1 = 1
    USER_FIELD_2 = 2
    RESET        = 3


class CalibrationLane(WishboneModule):
    """wishbone slave used to configure the calibration lane"""

    def __init__(self, moduleid, board_obj):
        super(CalibrationLane, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                              name="calibration lane")
        self.addr_list = CalibrationLaneAddress

    def set_user_field(self, user_field, commitTransaction=True):
        """Sets the user field and resets the counter for this field"""
        assert user_field | 0xFFFF_FFFF_FFFF == 0xFFFF_FFFF_FFFF
        self.write(self.addr_list.USER_FIELD_2, (user_field >> 32) & 0xFFFF, commitTransaction=False)
        self.write(self.addr_list.USER_FIELD_1, (user_field >> 16) & 0xFFFF, commitTransaction=False)
        self.write(self.addr_list.USER_FIELD_0, (user_field >> 0)  & 0xFFFF, commitTransaction=commitTransaction)

    def get_user_field(self, commitTransaction=True):
        """Gets user field"""
        self._request_user_field()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=3)
            return self._format_user_field(results)

    def _request_user_field(self):
        """WB read request"""
        for address in [self.addr_list.USER_FIELD_2, self.addr_list.USER_FIELD_1, self.addr_list.USER_FIELD_0]:
            self.read(address, commitTransaction=False)

    def _format_user_field(self, results):
        assert len(results) == 3
        ret = 0
        for i, address in enumerate([self.addr_list.USER_FIELD_2, self.addr_list.USER_FIELD_1, self.addr_list.USER_FIELD_0]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def reset(self):
        """Resets the lane, disabling it"""
        self.write(self.addr_list.RESET,0)

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in self.addr_list:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
