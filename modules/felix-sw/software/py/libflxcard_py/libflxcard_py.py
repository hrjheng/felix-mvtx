"""Dummy class to run without the FLP"""

class flxcard():

    def __init__(self):
        pass

    def card_open(self, card_nr, lock_mask):
        pass

    def register_write(self, reg, data):
        pass

    def register_read(self, reg):
        return 0
