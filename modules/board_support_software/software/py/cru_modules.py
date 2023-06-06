""" UserLogic Modules
"""

import time
from enum import IntEnum, unique

import logging

import cru_table
from git_hash_lut import get_its_ul_version

offset_userlogic = cru_table.CRUADD['add_userlogic']

@unique
class user_logic(IntEnum):
    ul_version_core = offset_userlogic + 0x0000_0000
    user_logic = offset_userlogic + 0x00001_000
    dw0_l0  = offset_userlogic + 0x00002_000
    dw0_l1  = offset_userlogic + 0x00003_000
    dw0_l2  = offset_userlogic + 0x00004_000
    dw0_l3  = offset_userlogic + 0x00005_000
    dw0_l4  = offset_userlogic + 0x00006_000
    dw0_l5  = offset_userlogic + 0x00007_000
    dw0_l6  = offset_userlogic + 0x00008_000
    dw0_l7  = offset_userlogic + 0x00009_000
    dw0_l8  = offset_userlogic + 0x0000A_000
    dw0_l9  = offset_userlogic + 0x0000B_000
    dw0_l10 = offset_userlogic + 0x0000C_000
    dw0_l11 = offset_userlogic + 0x0000D_000
    dw1_l0  = offset_userlogic + 0x0000E_000
    dw1_l1  = offset_userlogic + 0x0000F_000
    dw1_l2  = offset_userlogic + 0x00010_000
    dw1_l3  = offset_userlogic + 0x00011_000
    dw1_l4  = offset_userlogic + 0x00012_000
    dw1_l5  = offset_userlogic + 0x00013_000
    dw1_l6  = offset_userlogic + 0x00014_000
    dw1_l7  = offset_userlogic + 0x00015_000
    dw1_l8  = offset_userlogic + 0x00016_000
    dw1_l9  = offset_userlogic + 0x00017_000
    dw1_l10 = offset_userlogic + 0x00018_000
    dw1_l11 = offset_userlogic + 0x00019_000
    ep_dw0 = offset_userlogic + 0x00020_000
    ep_dw1 = offset_userlogic + 0x00021_000
    ul_common = offset_userlogic + 0x000fd_000
    ul_version = offset_userlogic + 0x000fe_000

def get_link_address(dw, link):
    sum = dw*256 + link*16
    if sum == 0x000: return user_logic.dw0_l0
    if sum == 0x010: return user_logic.dw0_l1
    if sum == 0x020: return user_logic.dw0_l2
    if sum == 0x030: return user_logic.dw0_l3
    if sum == 0x040: return user_logic.dw0_l4
    if sum == 0x050: return user_logic.dw0_l5
    if sum == 0x060: return user_logic.dw0_l6
    if sum == 0x070: return user_logic.dw0_l7
    if sum == 0x080: return user_logic.dw0_l8
    if sum == 0x090: return user_logic.dw0_l9
    if sum == 0x0A0: return user_logic.dw0_l10
    if sum == 0x0B0: return user_logic.dw0_l11
    if sum == 0x100: return user_logic.dw1_l0
    if sum == 0x110: return user_logic.dw1_l1
    if sum == 0x120: return user_logic.dw1_l2
    if sum == 0x130: return user_logic.dw1_l3
    if sum == 0x140: return user_logic.dw1_l4
    if sum == 0x150: return user_logic.dw1_l5
    if sum == 0x160: return user_logic.dw1_l6
    if sum == 0x170: return user_logic.dw1_l7
    if sum == 0x180: return user_logic.dw1_l8
    if sum == 0x190: return user_logic.dw1_l9
    if sum == 0x1A0: return user_logic.dw1_l10
    if sum == 0x1B0: return user_logic.dw1_l11

def get_ep_address(dw):
    if dw == 0x0: return user_logic.ep_dw0
    if dw == 0x1: return user_logic.ep_dw1

@unique
class user_logic_link(IntEnum):
    lnk_busy                                      = 0x000

    lnk_gbt_pkt_dec_num_link_err_phy              = 0x004
    lnk_gbt_pkt_dec_num_link_err_data             = 0x008
    lnk_gbt_pkt_dec_num_pkt_processed             = 0x00C
    lnk_gbt_pkt_dec_num_pkt_err_protocol          = 0x010
    lnk_gbt_pkt_dec_num_pkt_err_corrupt_sop       = 0x014
    lnk_gbt_pkt_dec_num_pkt_err_corrupt_eop       = 0x018
    lnk_gbt_pkt_dec_num_pkt_err_corrupt_rdh       = 0x01C
    lnk_gbt_pkt_dec_num_pkt_err_len_mismatch      = 0x020
    lnk_gbt_pkt_dec_num_pkt_err_checksum_mismatch = 0x024
    lnk_gbt_pkt_dec_num_pkt_err_unexpected_index  = 0x028
    lnk_gbt_pkt_dec_num_pkt_err_link_err_phy      = 0x02C
    lnk_gbt_pkt_dec_num_pkt_err_link_err_data     = 0x030
    lnk_gbt_pkt_dec_num_pkt_err_oversized         = 0x034

    lnk_pkt_assembler_fifo_status                 = 0x100
    lnk_pkt_assembler_num_pkt_processed           = 0x104

@unique
class user_logic_ep(IntEnum):
    arbiter_num_pkt_processed = 0x0

class CruModule():
    """Common communication class for CRU modules"""

    def __init__(self, comm, name):
        self.comm = comm
        self.name = name
        self.logger = logging.getLogger(f"{name}")

    def write(self, addr, data):
        # self.logger.info(f"Writing reg {hex(addr)}, value \t0x{hex(data)}")
        self.comm.roc_write(addr, data)

    def read(self, addr):
        # self.logger.info(f"Read reg {hex(addr)}")
        data = self.comm.roc_read(addr)
        # self.logger.info(f"Read reg {hex(addr)}, got {hex(data)}")
        return data


@unique
class user_logic_version_core(IntEnum):
    dirty_and_idcode = user_logic.ul_version_core + 0x0000_0000
    gitshorthash = user_logic.ul_version_core + 0x0000_0004
    builddate = user_logic.ul_version_core + 0x0000_0008
    buildtime = user_logic.ul_version_core + 0x0000_000C

@unique
class ul_idcode(IntEnum):
    ITS = 0xA001
    MCH = 0xA002
    MID = 0xA003
    TOF = 0xA004
    TPC = 0xA005
    TRD = 0xA006

class UserLogicVersionCore(CruModule):

    def __init__(self, comm) -> None:
        super().__init__(comm, "UserLogicVersionCore")

    def get_dirty_and_idcode(self):
        return self.read(user_logic_version_core.dirty_and_idcode)

    def get_dirty(self):
        val = self.get_dirty_and_idcode()
        return bool(val >> 31)

    def get_idcode(self):
        idcode = (self.get_dirty_and_idcode()) & 0xffff
        if idcode in ul_idcode._value2member_map_:
            return ul_idcode(idcode).name
        else:
            return f"{hex(idcode)} (NOT DEFINED)"

    def get_gitshorthash(self):
        return self.read(user_logic_version_core.gitshorthash)

    def get_builddate(self):
        return self.read(user_logic_version_core.builddate)

    def get_buildtime(self):
        return self.read(user_logic_version_core.buildtime)

    def print(self):
        hash = self.get_gitshorthash()
        s = f"User Logic Version\t\t{hex(hash)}\t{get_its_ul_version(hash)} \t Dirty: {self.get_dirty()}"
        s += f"\n\t\t\t\t\t\t\t\t\t"
        s += f"IDCode: {self.get_idcode()} \t Build date: {hex(self.get_builddate())} \t Build time: {hex(self.get_buildtime())}"
        self.logger.info(s)

class UserLogicVersion(CruModule):

    def __init__(self, comm) -> None:
        super().__init__(comm, "UserLogicVersion")

    def read_val(self, offset):
        return self.read(user_logic.ul_version+offset)

    def get_all(self):
        s = ""
        for i in range(128):
            s += f"\n{hex(self.read_val(i*4))}"
        return s

    def print(self):
        self.logger.info(f"User logic build version: {self.get_all()}")

@unique
class user_logic_common(IntEnum):
    dummy = user_logic.ul_common + 0x0000_0000
    select = user_logic.ul_common + 0x0000_0004
    reset_ctrl = user_logic.ul_common + 0x0000_0008
    reset_status = user_logic.ul_common + 0x0000_000C
    dummy_regs = user_logic.ul_common + 0x0000_03C0

class UserLogicCommon(CruModule):

    def __init__(self, comm) -> None:
        super().__init__(comm, "UserLogicCommon")

    def get_dummy(self):
        return self.read(user_logic_common.dummy)

    def get_select(self):
        return self.read(user_logic_common.select)

    def write_select(self, data):
        self.write(user_logic_common.select, data)

    def read_reset_ctrl(self):
        return self.read(user_logic_common.reset_ctrl)

    def write_reset_ctrl(self, data):
        self.write(user_logic_common.reset_ctrl, data)

    def read_reset_status(self):
        return self.read(user_logic_common.reset_status)

    def reset_all(self):
        self.write_reset_ctrl(0xff)
        self.write_reset_ctrl(0x0)


class UserLogicLink(CruModule):

    def __init__(self, comm, dw, link) -> None:
        super().__init__(comm, f"UserLogicLink_{dw}:{link}")
        self.base_addr = get_link_address(dw, link)

    def write(self, address, value):
        super().write(self.base_addr + address, value)

    def read(self, address):
        return super().read(self.base_addr + address)

    def get_busy(self):
        return self.read(user_logic_link.lnk_busy)

    def is_busy(self):
        busy = (self.get_busy())
        return busy > 0

    def get_num_link_err_phy(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_link_err_phy)

    def get_num_link_err_data(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_link_err_data)

    def get_num_pkt_processed(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_processed)

    def get_num_pkt_err_protocol(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_protocol)

    def get_num_pkt_err_corrupt_sop(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_corrupt_sop)

    def get_num_pkt_err_corrupt_eop(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_corrupt_eop)

    def get_num_pkt_err_corrupt_rdh(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_corrupt_rdh)

    def get_num_pkt_err_len_mismatch(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_len_mismatch)

    def get_num_pkt_err_checksum_mismatch(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_checksum_mismatch)

    def get_num_pkt_err_unexpected_index(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_unexpected_index)

    def get_num_pkt_err_link_err_phy(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_link_err_phy)

    def get_num_pkt_err_link_err_data(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_link_err_data)

    def get_num_pkt_err_oversized(self):
        return self.read(user_logic_link.lnk_gbt_pkt_dec_num_pkt_err_oversized)

    def get_fifo_status(self):
        return self.read(user_logic_link.lnk_pkt_assembler_fifo_status)

    def get_assembler_num_pkt_processed(self):
        return self.read(user_logic_link.lnk_pkt_assembler_num_pkt_processed)

    def get_all(self):
        d = {}
        d['busy'] = self.is_busy()
        d['num_link_err_phy'] = self.get_num_link_err_phy()
        d['num_link_err_data'] = self.get_num_link_err_data()
        d['num_pkt_processed'] = self.get_num_pkt_processed()
        d['num_pkt_err_protocol'] = self.get_num_pkt_err_protocol()
        d['num_pkt_err_corrupt_sop'] = self.get_num_pkt_err_corrupt_sop()
        d['num_pkt_err_corrupt_eop'] = self.get_num_pkt_err_corrupt_eop()
        d['num_pkt_err_corrupt_rdh'] = self.get_num_pkt_err_corrupt_rdh()
        d['num_pkt_err_len_mismatch'] = self.get_num_pkt_err_len_mismatch()
        d['num_pkt_err_checksum_mismatch'] = self.get_num_pkt_err_checksum_mismatch()
        d['num_pkt_err_unexpected_index'] = self.get_num_pkt_err_unexpected_index()
        d['num_pkt_err_link_err_phy'] = self.get_num_pkt_err_link_err_phy()
        d['num_pkt_err_link_err_data'] = self.get_num_pkt_err_link_err_data()
        d['num_pkt_err_oversized'] = self.get_num_pkt_err_oversized()
        d['fifo_status'] = self.get_fifo_status()
        d['assembler_num_pkt_processed'] = self.get_assembler_num_pkt_processed()
        return d

class UserLogicEP(CruModule):

    def __init__(self, comm, dw) -> None:
        super().__init__(comm, "UserLogicEP")
        self.base_addr = get_ep_address(dw)

    def write(self, address, value):
        super().write(self.base_addr + address, value)

    def read(self, address):
        return super().read(self.base_addr + address)

    def get_num_pkt_processed(self):
        return self.read(user_logic_ep.arbiter_num_pkt_processed)