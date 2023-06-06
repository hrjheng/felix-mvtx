"""Dummy class to run without the FLP"""

class BarChannel():

    def __init__(self, pcie_id, bar_ch):
        pass
    def register_write(self, reg, data):
        pass
    def register_read(self, reg):
        return 0
