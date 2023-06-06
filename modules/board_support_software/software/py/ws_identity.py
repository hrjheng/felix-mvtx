"""file implementing the control for the ws_identity wishbone slave"""
from enum import IntEnum, unique
import warnings
import os
import json

from wishbone_module import WishboneModule

class WsIdentityAddress(IntEnum):
    """memory mapping for the ws_identity got from ws_identity_pkg.vhd"""
    GITHASH_LSB          = 0x00
    GITHASH_MSB          = 0x01
    SEED                 = 0x02
    DEAD1                = 0x03
    DEAD2                = 0x04
    OS_LSB               = 0x05
    DIPSWITCH_VAL        = 0x06
    DEAD3                = 0x07
    DNA_CHUNK_0          = 0x08
    DNA_CHUNK_1          = 0x09
    DNA_CHUNK_2          = 0x0A
    DNA_CHUNK_3          = 0x0B
    DNA_CHUNK_4          = 0x0C
    DNA_CHUNK_5          = 0x0D
    UPTIME_LSB           = 0x0E
    UPTIME_CSB           = 0x0F
    UPTIME_MSB           = 0x10
    TIME_SINCE_RESET_LSB = 0x11
    TIME_SINCE_RESET_CSB = 0x12
    TIME_SINCE_RESET_MSB = 0x13


@unique
class CounterType(IntEnum):
    """Enum for discriminating the uptime counters"""
    UPTIME   = 0
    TIME_SINCE_RESET = 1


@unique
class FeeIdLayer(IntEnum):
    """Uppermost bits of the layer identification of the Front End ID"""
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5
    L6 = 6


@unique
class FeeIdLayerId(IntEnum):
    """Uppermost bits of the layer identification of the Front End ID"""
    L0 = 0b0000_0000
    L1 = 0b0001_0000
    L2 = 0b0010_0000
    L3 = 0b0100_0000
    L4 = 0b0110_0000
    L5 = 0b1000_0000
    L6 = 0b1100_0000


class FeeIdLayerMask(IntEnum):
    """Mask for the layer identification of the FEE ID"""
    L0 = 0b1111_0000
    L1 = 0b1111_0000
    L2 = 0b1110_0000
    L3 = 0b1110_0000
    L4 = 0b1110_0000
    L5 = 0b1100_0000
    L6 = 0b1100_0000


def _decode_feeid(feeid):
    """Decodes the FEE ID"""
    for layer in FeeIdLayer:
        if feeid & FeeIdLayerMask[layer.name] == FeeIdLayerId[layer.name]:
            stave_number = feeid & (0xFF - FeeIdLayerMask[layer.name])
            return feeid, layer, stave_number
    raise ValueError(f"Layer not found for FEE ID {feeid}")

def _max_staves_per_layer(layer):
    """Returns the maximum number of staves per layer"""
    layer = FeeIdLayer(layer)
    if layer is FeeIdLayer.L0:
        return 12 + 2 # IB-test, IB-table (see crate_mapping.py)
    elif layer is FeeIdLayer.L1:
        return 16
    elif layer is FeeIdLayer.L2:
        return 20
    elif layer is FeeIdLayer.L3:
        return 24 + 1 # ML-test (see crate_mapping.py)
    elif layer is FeeIdLayer.L4:
        return 30
    elif layer is FeeIdLayer.L5:
        return 42 + 1 # OL-test (see crate_mapping)
    elif layer is FeeIdLayer.L6:
        return 48
    else:
        return ValueError

def _encode_feeid(layer, stave_number):
    layer = FeeIdLayer(layer)
    assert stave_number in range(_max_staves_per_layer(layer))
    return FeeIdLayerId[layer.name] | stave_number

def json_keys2int(x):
    """Hook for converting str key to int"""
    if isinstance(x, dict):
        return {int(k, 16): v for k, v in x.items()}
    return x

def load_dna_lut_json(filename):
    # Check if status file exists
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
    if os.path.exists(path):
        with open(path, "r") as infile:
            json_data = json.load(infile, object_hook=json_keys2int)
    else:
        raise Exception("No LUT for dna exists!")
    return json_data


class WsIdentity(WishboneModule):
    """wishbone slave used to identify the firmware and the FPGA"""

    def __init__(self, moduleid, board_obj):
        """init"""
        super(WsIdentity, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                       name="Identity")
        self.fee_id = None # Data member for storing in memory information
                           # about the feeid and avoiding repeated access
                           # to hardware. see get_fee_id()
        self.dna = None # Data member for storing in memory information
                        # about the dna and avoiding repeated access
                        # to hardware. see get_dna()
        self.ru_dna_lut = load_dna_lut_json("ru_dna_lut.json")
        self.ru_2_0_dna_lut = load_dna_lut_json("ru_2_0_dna_lut.json")
        self.ru_sim_dna_lut = load_dna_lut_json("ru_sim_dna_lut.json")

    def get_git_hash(self, commitTransaction=True):
        """Gets git hash"""
        self._request_git_hash()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=2)
            return self._format_git_hash(results)

    def _request_git_hash(self):
        """Requests the githash"""
        for address in [WsIdentityAddress.GITHASH_MSB, WsIdentityAddress.GITHASH_LSB]:
            self.read(address, commitTransaction=False)

    def _format_git_hash(self, results):
        assert len(results) == 2
        ret = 0
        for i, address in enumerate([WsIdentityAddress.GITHASH_MSB, WsIdentityAddress.GITHASH_LSB]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def get_uptime_cycles(self, cnt_type=CounterType.UPTIME, commitTransaction=True):
        cnt_type = CounterType(cnt_type)
        if cnt_type == CounterType.UPTIME:
            reg_list = [WsIdentityAddress.UPTIME_LSB, WsIdentityAddress.UPTIME_CSB, WsIdentityAddress.UPTIME_MSB]
        else:
            reg_list = [WsIdentityAddress.TIME_SINCE_RESET_LSB, WsIdentityAddress.TIME_SINCE_RESET_CSB, WsIdentityAddress.TIME_SINCE_RESET_MSB]
        self._request_uptime(reg_list)
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=len(reg_list))
            return self._format_uptime(reg_list, results)

    def get_uptime_seconds(self, cnt_type=CounterType.UPTIME, commitTransaction=True):
        LHC_FREQUENCY = 40.07897e6 #Hz
        WB_CLK_PERIOD = 1/(4*LHC_FREQUENCY)
        uptime_cycles = self.get_uptime_cycles(cnt_type, commitTransaction)
        uptime_seconds = WB_CLK_PERIOD*uptime_cycles
        return uptime_seconds

    def get_uptime(self):
        return self.get_uptime_seconds(CounterType.UPTIME)

    def get_time_since_reset(self):
        return self.get_uptime_seconds(CounterType.TIME_SINCE_RESET)

    def get_delta_time(self, wait=50, cnt_type=CounterType.UPTIME):
        """Reads the same counter twice with a board.wait in between for verification purposes"""
        cnt_type = CounterType(cnt_type)
        if cnt_type == CounterType.UPTIME:
            reg_list = [WsIdentityAddress.UPTIME_LSB, WsIdentityAddress.UPTIME_CSB, WsIdentityAddress.UPTIME_MSB]
        else:
            reg_list = [WsIdentityAddress.TIME_SINCE_RESET_LSB, WsIdentityAddress.TIME_SINCE_RESET_CSB, WsIdentityAddress.TIME_SINCE_RESET_MSB]
        self._request_uptime(reg_list)
        self.board.wait(wait_value=wait, commitTransaction=False)
        self._request_uptime(reg_list)
        reg_list = reg_list + reg_list
        results = self.board.flush_and_read_results(expected_length=len(reg_list))
        start_time = stop_time = 0
        stop_offset = len(reg_list)//2
        for i, address in enumerate(reg_list):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            self.logger.debug(f"{i}: 0x{results[i][1]:04x}")
            if i in range(stop_offset):
                self.logger.debug(f"{i}: 0x{start_time:012x}")
                start_time = start_time | results[i][1]<<(16*i)
                self.logger.debug(f"{i}: 0x{start_time:012x}")
            else:
                j = i-stop_offset
                self.logger.debug(f"{i}: 0x{stop_time:012x}")
                stop_time = stop_time | results[i][1]<<(16*j)
                self.logger.debug(f"{i}: 0x{stop_time:012x}")
        delta = stop_time-start_time
        return delta, start_time, stop_time

    def _request_uptime(self, reg_list):
        for address in reg_list:
            self.read(address, commitTransaction=False)

    def _format_uptime(self, reg_list, results):
        assert len(results) == len(reg_list)
        ret = 0
        for i, address in enumerate(reg_list):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = ret | results[i][1]<<(16*i)
        return ret

    def get_date(self):
        raise NotImplementedError

    def get_os(self):
        """Returns the OS code
        0: Unix
        1: Windows
        2: others
        0xaffe: simulation"""
        os = self.read(WsIdentityAddress.OS_LSB)
        assert  os < 3 or os == 0xaffe, "OS value is out of range"
        return os

    def get_dipswitch(self, commitTransaction=True):
        """Returns value of RU DIPSWITCH"""
        dipval = self.read(WsIdentityAddress.DIPSWITCH_VAL, commitTransaction=commitTransaction)
        if commitTransaction:
            assert (dipval | 0x3ff) == 0x3ff, "DIPSWITCH value out of range"
            return dipval

    def get_dna(self, force_read=False):
        """Returns the unique DNA value of the FPGA, in simulation it returns 0x76543210FEDCBA9876543210"""
        if self.dna is None or force_read:
            dna = self._read_dna()
            if dna == 0:
                self.logger.warning("DNA value read was 0, trying old method.")
                self._latch_dna_old()
                dna = self._read_dna()
            assert dna > 0, "DNA value is zero"
            assert dna < 0xfffffffffffffffffffffffd, "DNA value is out of range"
            self.dna = dna
        return self.dna

    def _latch_dna_old(self):
        """Old firmware (prior to v0.6.0) need to latch DNA before reading.
           This method is only here to enable upgrading old firmwares with a newer software suite."""
        WsIdentityAddress_DNA_DO_READ = 0x07
        self.write(WsIdentityAddress_DNA_DO_READ, 0x1, commitTransaction=False)
        self.firmware_wait(wait_value=97, commitTransaction=True)

    def _read_dna(self):
        """Read DNA value from the device"""
        dna = self.read(WsIdentityAddress.DNA_CHUNK_0)
        dna = dna | self.read(WsIdentityAddress.DNA_CHUNK_1) << 16
        dna = dna | self.read(WsIdentityAddress.DNA_CHUNK_2) << 32
        dna = dna | self.read(WsIdentityAddress.DNA_CHUNK_3) << 48
        dna = dna | self.read(WsIdentityAddress.DNA_CHUNK_4) << 64
        dna = dna | self.read(WsIdentityAddress.DNA_CHUNK_5) << 80
        return dna

    def is_2_1(self):
        dna = self.get_dna()
        if dna in self.ru_dna_lut.keys():
            return True
        return False

    def is_2_0(self):
        dna = self.get_dna()
        if dna in self.ru_2_0_dna_lut.keys():
            return True
        return False

    def get_sn(self):
        """Returns RU SN from the DNA, or None if not present"""
        dna = self.get_dna()
        sn = self.decode_sn(dna)
        if sn is None:
            self.logger.warning(f"DNA {dna:024X} not in dna LUT json")
        return sn

    def decode_sn(self, dna):
        if dna in self.ru_dna_lut.keys():
            return self.ru_dna_lut[dna]
        elif dna in self.ru_2_0_dna_lut.keys():
            return self.ru_2_0_dna_lut[dna]
        elif dna in self.ru_sim_dna_lut.keys():
            return self.ru_sim_dna_lut[dna]
        else:
            return None

    def check_git_hash_and_date(self, expected_git_hash=None):
        warnings.warn("check_git_hash_and_date() is deprecated; use check_git_hash().", DeprecationWarning)
        self.check_git_hash(expected_git_hash=expected_git_hash)

    def check_git_hash(self, expected_git_hash=None):
        """gets git hash and git date"""
        assert (expected_git_hash is None) or (expected_git_hash | 0xFFFFFFFF == 0xFFFFFFFF)
        githash = self.get_git_hash()
        message_hash = ">> git hash: 0x{0:08x}".format(githash)
        self.logger.info(message_hash)
        if expected_git_hash is not None:
            assert githash==expected_git_hash, f"Expected 0x{expected_git_hash:08X}, got 0x{githash:08X}"

    def will_be_programmed(self):
        """Returns True if the PA3 will program the XCKU upon power up"""
        return self.get_dipswitch() & 0x1 == 1

    def get_fee_id(self, force_read=False, commitTransaction=True):
        """Returns the FEE ID.
        If the feeid is stored already as a data member it returns it
        directly without accessing the hardware (force with force_read flag).
        If not stored as data member, then it reads it from the board.
        """
        if self.fee_id is None or force_read:
            ds = self.get_dipswitch(commitTransaction=commitTransaction)
            if commitTransaction:
                self.fee_id = ds >> 2
                return self.fee_id
        else:
            return self.fee_id

    def get_decoded_fee_id(self, feeid=None):
        """
        Decodes the FEE ID
           Return:
        feeid, layer, stave number
        """
        if feeid is None:
            feeid = self.get_fee_id()
        return self.decode_fee_id(feeid)

    @staticmethod
    def decode_fee_id(feeid):
        """Decodes the FEE ID
              Return:
                 feeid, layer, stave number"""
        for layer in FeeIdLayer:
            if feeid & FeeIdLayerMask[layer.name] == FeeIdLayerId[layer.name]:
                stave_number = feeid & (0xFF - FeeIdLayerMask[layer.name])
                return feeid, layer, stave_number
        raise ValueError(f"Layer not found for FEE ID {feeid}")

    @staticmethod
    def decode_stave_name(layer, stave):
        assert layer in range(7)
        assert stave in range(48)
        return f"L{layer}_{stave:02}"

    def get_stave_name(self):
        """Returns the stave name L{layer:1}_{stave:02}"""
        try:
            _, l, s = self.get_decoded_fee_id()
            return self.decode_stave_name(l,s)
        except ValueError as ve:
            self.logger.error('FEEID decoding error')
            self.logger.error(ve)
            return 'test'

    def get_layer(self):
        _, layer, _ = self.get_decoded_fee_id()
        return layer

    def is_on_layer(self, layer):
        """returns True if the board has a FEE ID that belong to that layer"""
        layer = FeeIdLayer(layer)
        _, set_layer, _ = self.get_decoded_fee_id()
        return layer == set_layer

    def is_ib(self):
        """Returns True if board is on Inner Barrel"""
        return self.get_layer() in range(0,2+1)

    def is_ml(self):
        """Returns True if board is on Middle Layer"""
        return self.get_layer() in range(3,4+1)

    def is_ol(self):
        """Returns True if board is on Outer Layer"""
        return self.get_layer() in range(5,6+1)

    def is_ob(self):
        """Returns True if board is on Outer Barrel"""
        return self.get_layer() in range(3,6+1)

    def is_fee_id_correct(self, layer, stave):
        expected_fee_id = _encode_feeid(layer, stave)
        fee_id = self.get_fee_id()
        return expected_fee_id == fee_id

    def get_seed(self):
        """Returns the seed used to generate the bitfile.
        Changing this value at bitfile compilation time,
        will affect the seed used by Vivado to generate the bitfile"""
        return self.read(WsIdentityAddress.SEED)

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsIdentityAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
