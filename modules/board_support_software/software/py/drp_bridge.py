"""DRP bridge implementation"""

from wishbone_module import WishboneModule

class DrpBridge(WishboneModule):
    DRP_ADDRESS = 1
    DRP_DATA    = 2

    def __init__(self,moduleid,board_obj):
        super(DrpBridge, self).__init__(moduleid=moduleid,board_obj=board_obj,name="DrpBridge")

    def write_drp(self,lane, address, data, commitTransaction=True):
        """Write to the drp port. Set Lane via lane setting; defaults to self.lanes[0]"""
        assert address | 0x1FFF == 0x1FFF, "DRP address overflow"
        assert data | 0xFFFF == 0xFFFF, "DRP data overflow"
        address |= (lane<<9)
        self.write(self.DRP_ADDRESS, address, False)
        self.write(self.DRP_DATA, data, commitTransaction)

    def read_drp(self, lane, address, commitTransaction=True):
        """Read from the drp port. Set Lane via lane setting; defaults to self.lanes[0]"""
        assert address | 0x1FFF == 0x1FFF, "DRP address overflow"
        address |= (lane<<9)
        self.write(self.DRP_ADDRESS, address, False)
        return self.read(self.DRP_DATA, commitTransaction=commitTransaction)

    def dump_config(self):
        return ""
