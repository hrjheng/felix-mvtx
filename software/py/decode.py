#!/usr/bin/env python3.9

import sys
import os
import argparse
import logging
import json
import numpy as np

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

from alpide_readout_flags import TrailerFlag

import trigger
import rdh_definitions
import ws_identity

RDH_VERSION = 8
RDH_SIZE = 32
BLOCK_SIZE = 8192
SOURCE_ID = 32
LANES_IB = 9
LANES_OB = 28
MAX_LANES = LANES_OB
B_PER_FELIX_WORD = 32    # 256 bits

# TODO: remove after closing RUv1_Test #104
ib_lane_lut = {i:i for i in range(LANES_IB)}
ob_lane_lut = {i:i for i in range(LANES_OB)}


class Decode:
    def __init__(self, logger, filename='/dev/stdin', do_fhr=False, feeid=None, offset=0, skip_data=False, print_interval=100000, assert_on_pcount=True, thscan=False, thscan_injections=25,
                 accept_decreasing_address=True, check_lane_list="", counter_path="", warn_on_padding_misaligned=False, warn_on_expect_no_data=False, thscan6=False):
        self.logger = logger
        self.f = open(filename, 'rb')
        self.feeid = feeid
        self.offset = offset
        self.skip_data = skip_data
        self.print_interval = print_interval
        self.assert_on_pcount = assert_on_pcount
        self.thscan = thscan
        self.thscan6 = thscan6
        self.thscan_injections = thscan_injections
        self.accept_decreasing_address = accept_decreasing_address
        self.check_lane_list = check_lane_list
        self.counter_dict = None
        if counter_path != "":
            counter_file = open(counter_path, "r")
            self.counter_dict = json.load(counter_file)
            counter_file.close()
        self.warn_on_expect_no_data = warn_on_expect_no_data
        self.warn_on_padding_misaligned = warn_on_padding_misaligned

        self.counter_rdh = 0
        self.counter_rdh_page_zero_no_stop = 0

        self.counter_tdh = 0
        self.counter_tdh_no_continuation = 0

        self.counter_tdt = 0
        self.counter_tdt_packet_done = 0
        self.counter_tdt_gbt_word_inside = 0

        # {feeid: linkid}-dict to verify that the association does not change during the run.
        # Note that in the data the two endpoints of the same CRU have the same linkids
        self.feeid2linkid_lut = {}

        self.bytes_read = 0
        self.total_hits = 0

        self.fhr = False
        if do_fhr and feeid is not None:
            self.fhr = True
            self.fhr_filename = f"fhr_pixels_{feeid}.npy"
            self.data_pixels = np.zeros((3, 512, 1024), dtype=int)  # chip, y(row), x(col)
        elif thscan and feeid is not None:
            self.thscan_filename = f"thscan_pixels_{feeid}.npy"
            self.data_pixels = np.zeros((3, 512, 1024, 50), dtype=int)  # chip, y(row), x(col), charge

    def __del__(self):
        self.f.close()

    @staticmethod
    def regaddr2xy(reg, addr):
        x = reg << 5 | addr >> 9 & 0x1E | (addr ^ addr >> 1) & 0x1
        y = addr >> 1 & 0x1FF
        return x, y

    def decode_flags(self, flags):
        """Table in page 61 of readout"""
        ret_flags = []
        if flags >> TrailerFlag.BUSY_VIOLATION & 1 == 0:
            # Readout event.
            # Meaning of flags is as described previously.
            # Flags are ortogonal and can be set independently of one another provided that the event they describe has occurred.
            for flag in TrailerFlag:
                if flags >> flag.value & 1 == 1:
                    ret_flags.append(flag.name)
        elif flags == 0b1100:
            # Indicates that the event is transmitted in DATA OVERRUN mode and any event flags in the Start FIFO are overridden.
            # The flag override will be in place until the Start FIFO is fully emptied.
            ret_flags.append('DataOverrun')
        elif flags == 0b1100:
            # Indicates that the event is transmitted whilst the FATAL condition is asserted and any event flags in the Start FIFO are overridden.
            # This means that the identifier information for at least one event has been lost due to FIFO overflow.
            # The readout flag configuration will be maintained until a GRST/RORST is issued to clear the FATAL condition even if the chip recovers as a result of DATA OVERRUN mode and is back in sync.
            ret_flags.append('FATAL')
            self.logger.info('FATAL readout flag observed!')
        return ret_flags

    def decode_alpide(self, data, accept_decreasing_address=False, thscan_current_charge=-1, thscan_current_row=-1):
        assert len(data) >= 2, 'chip data is too short: {}<2'.format(len(data))
        assert data[0] & 0xF0 == 0xE0 or data[0] & 0xF0 == 0xA0 or data[0] == 0xF0 or data[0] == 0xF1, f'first byte 0x{data[0]:02X} is not a valid chip header, busy on or busy off\n {list(map(hex,data))}'
        ret_list = [] # List returning the hits data from different chips
        busy_on = busy_off = 0
        i = 0
        chips = 0
        reg = None
        hits = []
        hits_number = 0
        chip_header_found = False
        chip_trailer_found = False
        previous_encoder_id = 0
        previous_hit = 0
        previous_region = 0
        while i < len(data):
            #self.logger.info(f"chips {chips}, i {i}")
            if chips > 7:
                assert data[i] == 0x00, 'bad padding: 0x{:02X} != 0x00'.format(data[i])
            else:
                if data[i] == 0xF1: # BUSY ON
                    self.logger.info(f"BUSY_ON at Byte {i}")
                    busy_on+=1
                    i+=1
                elif data[i] == 0xF0: # BUSY OFF
                    self.logger.info(f"BUSY_OFF at Byte  {i}")
                    busy_off+=1
                    i+=1
                elif data[i] & 0xF0 == 0xE0: # EMPTY
                    chip_header_found = False
                    chip_trailer_found = True
                    chipid = data[i] & 0xF
                    bc = data[i+1]
                    ret_list.append({'chipid': chipid, 'bc': bc, 'flags': None, 'hits': [], 'busy_on': busy_off, 'busy_off': busy_off})
                    busy_on = busy_off = 0 # reset busy
                    i+=2 # skip to next
                else:
                    if chip_header_found:
                        if data[i] & 0xE0 == 0xC0:  # REGION HEADER
                            assert i + 2 < len(data), 'No data would fit (at least a data short after region header!)'
                            reg = data[i] & 0x1F
                            assert reg >= previous_region, f"Region decreased, {previous_region}->{reg}, chipid {chipid}"
                            previous_priority_encoder = 0 # reset priority_encoder
                            previous_address = 0          # reset hit_address
                            previous_region = reg
                            i += 1 # skip to next
                        elif data[i] & 0xC0 == 0x40:  # DATA SHORT
                            assert i + 1 < len(data), 'data short does not fit'
                            assert reg is not None, f"data short 0x{data[i]:0x}{data[i+1]:0x} at {i} before region header {list(map(hex,data))}. bc 0x{bc:0x}, chipid {chipid}, chips {chips}"
                            addr = (data[i] & 0x3F) << 8 | data[i+1]
                            if addr < previous_address:
                                if accept_decreasing_address:
                                    self.logger.info(f"Address should be non-decreasing 0x{previous_address:04X}->0x{addr:04X} in region 0x{reg:02X}")
                                else:
                                    raise RuntimeError(f"Address should be non-decreasing 0x{previous_address:04X}->0x{addr:04X} in region 0x{reg:02X}")
                            hits_number +=1
                            self.total_hits += 1
                            previous_encoder_id = addr >> 10
                            previous_hit = addr & 0x3FF
                            previous_address = previous_encoder_id << 10 | previous_hit
                            #hits.append(Decode.regaddr2xy(reg, addr))
                            if self.fhr:
                                x,y = Decode.regaddr2xy(reg, addr)
                                self.data_pixels[(chipid%3), y, x] += 1
                            elif self.thscan:
                                x,y = Decode.regaddr2xy(reg, addr)
                                if y == thscan_current_row:
                                    self.data_pixels[(chipid%3), y, x, thscan_current_charge] += 1
                            i += 2
                        elif data[i] & 0xC0 == 0x00:  # DATA LONG
                            assert i + 2 < len(data), f"data long does not fit at {i} 0x{data[i]} {list(map(hex,data))}. bc 0x{bc:0x}, chipid {chipid}, chips {chips}"
                            assert reg is not None, 'data long before region header'
                            addr = (data[i] & 0x3F) << 8 | data[i+1]
                            #self.logger.info(f"chipid {chipid} reg 0x{reg:01x} 0x{addr:03x}")
                            if addr < previous_address:
                                if accept_decreasing_address:
                                    self.logger.info(f"Address should be non-decreasing 0x{previous_address:04X}->0x{addr:04X} in region 0x{reg:02X}")
                                else:
                                    raise RuntimeError(f"Address should be non-decreasing 0x{previous_address:04X}->0x{addr:04X} in region 0x{reg:02X}")
                            hits_number +=1
                            self.total_hits += 1
                            #hits.append(Decode.regaddr2xy(reg, addr))
                            if self.fhr:
                                x,y = Decode.regaddr2xy(reg, addr)
                                self.data_pixels[(chipid%3), y, x] += 1
                            elif thscan:
                                x,y = Decode.regaddr2xy(reg, addr)
                                if y == thscan_current_row:
                                    self.data_pixels[(chipid%3), y, x, thscan_current_charge] += 1
                            assert data[i+2] & 0x80 == 0x00, f"{i}, {list(map(hex, data[i:i+3]))} region {reg} chip {chipid}, \n\n data before {list(map(hex, data[:i]))} \n\n data after {list(map(hex, data[i+1:]))} "
                            bits = data[i+2]
                            while bits != 0x00:
                                addr += 1
                                if bits & 0x1 == 0x1:
                                    hits_number +=1
                                    self.total_hits += 1
                                    #hits.append(Decode.regaddr2xy(reg, addr))
                                    if self.fhr:
                                        x,y = Decode.regaddr2xy(reg, addr)
                                        self.data_pixels[(chipid%3), y, x] += 1
                                    elif thscan:
                                        x,y = Decode.regaddr2xy(reg, addr)
                                        if y == thscan_current_row:
                                            self.data_pixels[(chipid%3), y, x, thscan_current_charge] += 1
                                bits >>= 1
                            previous_encoder_id = addr >> 10
                            previous_hit = addr & 0x3FF
                            previous_address = previous_encoder_id << 10 | previous_hit
                            i += 3
                        elif data[i] & 0xF0 == 0xB0:  # CHIP TRAILER
                            chip_trailer_found = True
                            chip_header_found = False
                            flags = data[i] & 0x0F
                            if flags != 0:
                                flags = self.decode_flags(flags)
                            else:
                                flags = []
                            #ret_list.append({'chipid': chipid, 'bc': bc, 'flags': flags, 'hits_number': hits_number, 'busy_on': busy_on, 'busy_off': busy_off, 'hits': hits})
                            ret_list.append({'chipid': chipid, 'bc': bc, 'flags': flags, 'hits_number': hits_number, 'busy_on': busy_on, 'busy_off': busy_off})
                            busy_on = busy_off = 0
                            i+=1 # skip to next
                        else:
                            assert False, 'bad byte: 0x{0:02X}, data {1}'.format(data[i], data)
                    else:
                        if data[i] & 0xF0 == 0xA0: # CHIP HEADER
                            chip_header_found = True
                            chip_trailer_found = False
                            chips += 1
                            chipid = data[i] & 0xF
                            bc = data[i+1]
                            # reset all
                            reg = None
                            #hits = []
                            hits_number = 0
                            previous_region = 0
                            i+=2 # skip to next
                        elif data[i] == 0x00: # padding
                            i+=1
                        else:
                            assert False, 'bad byte: 0x{0:02X}, data {1}'.format(data[i], list(map(hex, data)))
        assert chip_trailer_found
        return ret_list

    @staticmethod
    def decode_diagnostic(data):
        """method to decode diagnostic data (ideally the error specific data can be decoded here,
        but there doesn't appear to be any documentation on the exact form of this data)"""
        diagnostic_data = ((data[7] << 56)
                            | (data[6] << 48)
                            | (data[5] << 40)
                            | (data[4] << 32)
                            | (data[3] << 24)
                            | (data[2] << 16)
                            | (data[1] << 8)
                            | data[0])
        lane_error_id = data[8]
        diagnostic_lane_id = data[9]

        diagnostic_dict = {
            'diagnostic_data'       : diagnostic_data,
            'lane_error_id'         : lane_error_id,
            'diagnostic_lane_id'    : diagnostic_lane_id
            }

        return diagnostic_dict

    @staticmethod
    def decode_tdh(tdh):
        """method to decode the trigger header"""
        trigger_type = (tdh[1] & 0b1111) << 8 | tdh[0]
        internal_trigger = (tdh[1] >> 4) & 1
        no_data = (tdh[1] >> 5) & 1
        continuation = (tdh[1] >> 6) & 1
        trigger_bc = (tdh[3] & 0b1111) << 8 | tdh[2]
        trigger_orbit = (tdh[8] << 32) | (tdh[7] << 24)  | (tdh[6] << 16) | (tdh[5] << 8) | tdh[4]
        tdh_id = tdh[9]

        tdh = {
            'trigger_type'      : trigger_type,
            'internal_trigger'  : internal_trigger,
            'no_data'           : no_data,
            'continuation'      : continuation,
            'trigger_bc'        : trigger_bc,
            'trigger_orbit'     : trigger_orbit,
            'tdh_id'            : tdh_id
            }

        return tdh

    @staticmethod
    def decode_tdt(tdt):
        """method to decode the trigger trailer"""
        lane_status = ((tdt[6] << 48)
                        | (tdt[5] << 40)
                        | (tdt[4] << 32)
                        | (tdt[3] << 24)
                        | (tdt[2] << 16)
                        | (tdt[1] << 8)
                        | tdt[0] << 8)
        packet_done = tdt[8] & 1
        transmission_timeout = (tdt[8] >> 1) & 1
        packet_overflow = (tdt[8] >> 2) & 1
        lane_starts_violation = (tdt[8] >> 3) & 1
        lane_timeouts = (tdt[8] >> 4) & 1
        tdt_id = tdt[9]
        tdt = {
            'lane_status'           : lane_status,
            'packet_done'           : packet_done,
            'transmission_timeout'  : transmission_timeout,
            'packet_overflow'       : packet_overflow,
            'lane_starts_violation' : lane_starts_violation,
            'lane_timeouts'         : lane_timeouts,
            'tdt_id'                : tdt_id
            }

        return tdt

    @staticmethod
    def decode_ihw(ihw):
        """decodes the ihw (for now just active lane map)"""
        active_lane_binary = ((ihw[3] & 0b1111) << 24) | (ihw[2] << 16) | (ihw[1] << 8) | ihw[0]
        active_lanes = [(active_lane_binary >> lane) & 1 == 1 for lane in range(MAX_LANES)]
        ihw_id = ihw[9]

        ihw = {
            "active_lanes" : active_lanes,
            "ihw_id"       : ihw_id
        }

        return ihw

    @staticmethod
    def decode_cdw(cdw):
        """decodes the calibration data words (TODO: find example to see how this is implemented)"""
        user_field = ((cdw[5] << 40)
                      | (cdw[4] << 32)
                      | (cdw[3] << 24)
                      | (cdw[2] << 16)
                      | (cdw[1] << 8)
                      | cdw[0])
        counter = (cdw[8] << 16) | (cdw[7] << 8) | cdw[6]
        cdw_id = cdw[9]

        cdw = {
            "user_field" : user_field,
            "counter"    : counter,
            "cdw_id"     : cdw_id
        }

        return cdw

    @staticmethod
    def decode_ddw(ddw):
        """decodes the ddw  (currently not implemented according to the doc i have access to)"""
        return {"ddw_id" : ddw[9]}

    @staticmethod
    def decode_rdh(rdh):
        # GBT WORD 0
        h_ver = rdh[rdh_definitions.Rdh8ByteMap.VERSION]
        h_len = rdh[rdh_definitions.Rdh8ByteMap.SIZE]
        feeid = rdh[rdh_definitions.Rdh8ByteMap.FEEID_MSB] << 8 | rdh[rdh_definitions.Rdh8ByteMap.FEEID_LSB]
        source_id = rdh[rdh_definitions.Rdh8ByteMap.SOURCE_ID]
        det_field = rdh[rdh_definitions.Rdh8ByteMap.DET_FIELD_SB3] << 24 | rdh[rdh_definitions.Rdh8ByteMap.DET_FIELD_SB2] << 16 | \
            rdh[rdh_definitions.Rdh8ByteMap.DET_FIELD_SB1] << 8 | rdh[rdh_definitions.Rdh8ByteMap.DET_FIELD_SB0]

        # GBT WORD 1
        bc = (rdh[rdh_definitions.Rdh8ByteMap.BC_MSB] << 8 | rdh[rdh_definitions.Rdh8ByteMap.BC_LSB]) & 0xFFF
        orbit = rdh[rdh_definitions.Rdh8ByteMap.ORBIT_SB4] << 32 | \
            rdh[rdh_definitions.Rdh8ByteMap.ORBIT_SB3] << 24 | rdh[rdh_definitions.Rdh8ByteMap.ORBIT_SB2] << 16 | \
            rdh[rdh_definitions.Rdh8ByteMap.ORBIT_SB1] << 8 | rdh[rdh_definitions.Rdh8ByteMap.ORBIT_SB0]

        # GBT WORD 2
        trg_type = rdh[rdh_definitions.Rdh8ByteMap.TRG_TYPE_SB3] << 24 | rdh[rdh_definitions.Rdh8ByteMap.TRG_TYPE_SB2] << 16 | \
            rdh[rdh_definitions.Rdh8ByteMap.TRG_TYPE_SB1] << 8 | rdh[rdh_definitions.Rdh8ByteMap.TRG_TYPE_SB0]
        pages_count = rdh[rdh_definitions.Rdh8ByteMap.PAGE_CNT_MSB] << 8 | rdh[rdh_definitions.Rdh8ByteMap.PAGE_CNT_LSB]
        stop_bit = rdh[rdh_definitions.Rdh8ByteMap.STOP_BIT]
        priority = rdh[rdh_definitions.Rdh8ByteMap.PRIORITY]

        triggers = []
        for flag in trigger.BitMap:
            if trg_type >> flag.value & 1 == 1:
                triggers.append(flag.name)

        rdh = {
            'feeid'              : feeid,
            'priority'           : priority,
            'source_id'          : source_id,
            'trg'                : (orbit, bc),
            'trg_type'           : trg_type,
            'detfield'           : det_field,
            'stop'               : stop_bit,
            'pages_count'        : pages_count,
            'triggers'           : triggers
            }

        assert h_ver == RDH_VERSION, "wrong rdh version = 0x{0:x}, rdh: {1}".format(h_ver, rdh)
        assert h_len == RDH_SIZE, "wrong rdh length = 0x{0:x}, rdh: {1}".format(h_len, rdh)
        assert source_id == SOURCE_ID, "wrong source id = 0x{0:x}, rdh: {1}".format(source_id, rdh)
        assert priority == 0, "wrong priority = {0}, rdh: {1}".format(priority, rdh)
        assert trg_type >> len(trigger.BitMap) == 0, "Invalid trigger type = 0x{0:x}, rdh: {1}".format(trg_type, rdh)
        assert trigger.BitMap.PP.name not in triggers, "PP not expected {0}".format(triggers)
        assert trigger.BitMap.CAL.name not in triggers, "CAL not expected {0}".format(triggers)
        return rdh

    @staticmethod
    def decode_payload(self, payload, lanes={}):
        assert len(payload) % 16 == 0
        assert len(payload) >= 32  # at least header + trailer
        header = payload[0:10]
        assert header[9] == 0xE0
        # lanes =(header[4]<<16|header[3]<<8|header[2])&0xFFFFFFF #(28 bit, TODO: why 28?)
        iword = 1
        trailer = None
        while iword * 16 < len(payload):
            word = payload[iword*16:iword*16+10]
            if word[9] == 0xF0:  # trailer
                trailer = word
                break
            laneidx = word[9]
            if laneidx not in lanes:
                lanes[laneidx] = []
            lanes[laneidx] += word[0:9]
            iword += 1
        if trailer:
            pass
        return lanes

    def read_and_check_len(self, name, expected_len, verbose=False):
        """If a positive expected len is given, the data are read from file and checked for the correct size"""
        if expected_len<=0:
            return [],0
        else:
            data_block = self.f.read(expected_len)
            data_len  = len(data_block)
            if data_len != 0:  # ie EOF (len=0), just return
                if data_len != expected_len:
                    self.logger.error(f'{name} block is incomplete: {data_len}/{expected_len} B')
                #assert data_len==expected_len, f'{name} block is incomplete: {data_len}/{expected_len} B'
            if verbose:
                self.logger.info(f'{name} read {data_len}/{expected_len}')
            self.bytes_read += data_len
            return data_block, data_len

    def main(self):
        if self.offset != 0:
            assert filepath != '/dev/stdin', "/dev/stdin is not a supported input with an offset!"
            assert self.offset%B_PER_FELIX_WORD==0, f"The offset should be at the beginning of a GBT word (offset multiple of {B_PER_FELIX_WORD})"
            self.f.seek(self.offset)

        lanes = {}
        iblock = self.offset
        iblock_event = self.offset
        current_pages_count = -1
        previous_rdh = {}
        rdh = {}
        previous_event_complete = False
        is_continuous_mode = False
        eoc_received = False
        is_triggered_mode = False
        eot_received = False
        timed_out_transmission_blocks = []
        timed_out_lanes_blocks = []
        other_feeids_count = 0
        feeids = []
        linkids = []
        packet_id_jumps = []
        bc_count = None
        event_count = 0
        current_cdw_field = None
        cdw_found = False

        events_cnt = {t.name:0 for t in trigger.BitMap}

        thscan_current_row = -1
        thscan_current_charge = -1
        thscan_injections_observed = self.thscan_injections # clean start

        boffset = 0
        prev_felix_hdr = [0*32]
        while True:
            gbt_block_started = False
            # first read FELIX header
            felix_hdr, felix_hdr_len = self.read_and_check_len(name="FELIX", expected_len=B_PER_FELIX_WORD)
            if felix_hdr_len == 0:
                break  # EOF
            if felix_hdr_len != B_PER_FELIX_WORD:
                # not enough bytes for a FELIX header
                continue
            if felix_hdr[31] != 0xAB:
                # Not a FELIX Header
                prev_felix_hdr = felix_hdr
                continue

            # check that the padding is ending on 256 byte boundary
            if self.warn_on_padding_misaligned:
                if (prev_felix_hdr[30:] == b'\xff\xff') and (((self.bytes_read - B_PER_FELIX_WORD) % 256) != 0):
                    self.logger.warning(f"bytes_read {self.bytes_read}: FELIX header not properly aligned")
            prev_felix_hdr = felix_hdr

            gbt_id = felix_hdr[rdh_definitions.FLX1ByteMap.GBT_ID]
            #print(f"FELIX header found: Version {felix_hdr[rdh_definitions.FLX1ByteMap.VERSION]}",
            #      f"FLXID {felix_hdr[rdh_definitions.FLX1ByteMap.FLXID]} GBT_ID {gbt_id}")
            if gbt_id not in linkids:
                linkids.append(gbt_id)

            packet_cnt = felix_hdr[25] + ((felix_hdr[26] << 8) & 0xf00)
            #print("packet_cnt", packet_cnt)
            byte_cnt = packet_cnt * 32

            # Now read all of the DMA words
            dma_block, dma_block_len = self.read_and_check_len(name="DMA", expected_len=byte_cnt)
            if dma_block_len != byte_cnt:
                self.logger.error(f"bytes_read {self.bytes_read}: Couldn't read full DMA block, read/expected {dma_block_len}/{byte_cnt}")
                continue

            start = 0
            for i in range(packet_cnt):
                count = dma_block[i*32 + 30] + ((dma_block[i*32 + 31] << 8) & 0x300)

                if count == 3:
                    gbt_block_started = True
                    iblock += 1
                    # process RDH
                    rdh = self.decode_rdh(dma_block[(i*32):((i+1)*32)])
                    #print("found RDH, feeid ", rdh['feeid'])
                    if rdh['feeid'] not in feeids:
                        feeids.append(rdh['feeid'])
                        # stores the feeid-linkid pair at the first occurrence
                        # of a certain feeid
                        self.feeid2linkid_lut[rdh['feeid']] = gbt_id
                        # commodity to scan the data and printout feeids
                        if self.feeid is None:
                            self.logger.info(f"List of identified feeids {feeids}")
                    if rdh['feeid'] != self.feeid:
                        other_feeids_count += 1
                        gbt_block_started = False
                        # Done with this FELIX DMA packet
                        break

                    if rdh['pages_count'] == 0:
                        iblock_event += 1
                        for t in trigger.BitMap:
                            if t.name in rdh['triggers']:
                                events_cnt[t.name] += 1
                    if trigger.BitMap.SOC.name in rdh['triggers']:
                        is_continuous_mode = True
                    if trigger.BitMap.EOC.name in rdh['triggers']:
                        if not is_continuous_mode:
                            self.logger.info("EOC received without a SOC")
                        eoc_received = True
                    if trigger.BitMap.SOT.name in rdh['triggers']:
                        is_triggered_mode = True
                    if trigger.BitMap.EOT.name in rdh['triggers']:
                        if not is_triggered_mode:
                            self.logger.info("EOT received without a SOT")
                        eot_received = True
                    start = i + 1
                else:
                    continue

                if gbt_block_started :
                    # process data block

                    assert gbt_id == self.feeid2linkid_lut[rdh['feeid']], \
                        f"LinkID associated to FEEID {rdh['feeid']} changed during the run expected {self.feeid2linkid_lut[rdh['feeid']]} got {gbt_id} bytes_read {self.bytes_read} trigger: 0x{rdh['trg']} packet_cnt {packet_cnt} i {i} start {start}"
                    assert rdh['pages_count'] in [0,current_pages_count+1], f"Incorrect pages count {rdh['pages_count']}, previous was {current_pages_count}:\nprevious RDH {previous_rdh}\ncurrent RDH {rdh}"
                    current_pages_count = rdh['pages_count']
                    if rdh['pages_count'] == 0 and previous_rdh != {}:
                        assert not previous_event_complete, "previous event was already complete"
                        assert not (rdh['trg'] == previous_rdh['trg']), f"Trigger time same as previous event bytes_read {self.bytes_read}\nprevious rdh\t{previous_rdh}\n \
                        current rdh\t{rdh}\n\n\t\t(Maybe you wanted to run on a threshold scan file? Use -ts flag to force thresholdscan analysis)"
                    elif rdh['pages_count'] != 0:
                        if rdh['stop'] != 1:
                            assert not previous_event_complete, "previous event was already complete"
                        assert rdh['trg']==previous_rdh['trg'], f"Incorrect trigger information in RDH: \nprevious {previous_rdh} \ncurrent {rdh}"
                        assert rdh['triggers']==previous_rdh['triggers'], f"Incorrect trigger type in RDH: \nprevious {previous_rdh} \ncurrent {rdh}"
                        assert rdh['detfield']==previous_rdh['detfield'], f"Incorrect detector field in RDH: \nprevious {previous_rdh} \ncurrent {rdh}"
                        assert rdh['feeid']==previous_rdh['feeid'], f"Incorrect feeid in RDH: \ncurrent {rdh} \nprevious {previous_rdh}"
                    previous_rdh = rdh
                    self.counter_rdh +=1
                    if rdh['stop']==0 and rdh['pages_count']==0:
                        self.counter_rdh_page_zero_no_stop+=1
                        self.logger.debug(f"RDH received! Here's the RDH {self.counter_rdh_page_zero_no_stop}: {rdh}")
                    header_found = False
                    trailer_found = False
                    active_lanes = []

                    pr_count = 3
                    for iword in range(start, packet_cnt):
                        count = dma_block[iword*32 + 30] + ((dma_block[iword*32 + 31] << 8) & 0x300)
                        d_count = count - pr_count
                        #print("in data, count ", count, d_count)
                        pr_count = count
                        for k in range(d_count):
                            gbt_start = iword * 32 + k * 10
                            gbt_end = gbt_start + 10
                            gbt_word = dma_block[gbt_start:gbt_end]
                            if gbt_word[9]==0xE0: # ITS HEADER (IHW)
                                assert iword==start, f"ITS header should be at the beginning of the packet: {iword} != 0"
                                ihw = self.decode_ihw(gbt_word)
                                #one would not expect active lanes to change across course of run
                                active_lanes = ihw["active_lanes"]
                                if check_lane_list:
                                    current_lanes = [i for i in range(MAX_LANES) if active_lanes[i]]
                                    assert current_lanes == expected_lane_list, f"Expected lane list does not match active lanes, expected: {expected_lane_list}, active: {current_lanes}"
                            elif gbt_word[9]==0xE8: # TRIGGER HEADER (TDH)
                                tdh = self.decode_tdh(gbt_word)
                                self.counter_tdh+=1
                                if tdh['continuation']==0:
                                    self.counter_tdt_gbt_word_inside = 0 # reset counter here
                                    self.counter_tdh_no_continuation += 1
                                    self.logger.debug(f"TDH received! Here's the TDH {self.counter_tdh_no_continuation}: {tdh}")
                                    #if self.counter_tdh_no_continuation > self.counter_rdh_page_zero_no_stop:
                                    #    self.logger.error(f"TDH no cont before RDH page 0 no stop {self.counter_tdh_no_continuation} > {self.counter_rdh_page_zero_no_stop}")
                                header_found = True
                                # assert tdh['trigger_orbit'] == rdh['trg'][0], f"orbit in TDH is different than RDH: tdh orbit: {tdh['trigger_orbit']}, rdh orbit: {rdh['trg'][0]}"
                                current_bc = tdh['trigger_bc']
                                no_data = tdh['no_data']
                                if no_data and warn_on_expect_no_data:
                                    self.logger.warning(f"No data expected from TDH in block: {iblock}, word: {iword}")
                                if tdh['trigger_bc'] != 0: # don't count first TDH
                                    for t in trigger.BitMap:
                                        if tdh['trigger_type'] >> t.value & 1 == 1:
                                            events_cnt[t.name] += 1

                            elif gbt_word[9]==0xF0: # TRIGGER TRAILER (TDT)
                                trailer_found = True
                                tdt = self.decode_tdt(gbt_word)
                                self.counter_tdt+=1
                                if tdt['packet_done']==1:
                                    self.counter_tdt_packet_done+=1
                                    self.logger.debug(f"TDT received! Here's the TDT {self.counter_tdt_packet_done}: {tdt}: {self.counter_tdt_gbt_word_inside:16}")
                                    self.counter_tdt_gbt_word_inside = 0 # reset counter here

                                assert self.counter_tdt_packet_done <= self.counter_tdh_no_continuation, f"TDT packet done before TDH no continuation {self.counter_tdt_packet_done} > {self.counter_tdh_no_continuation}"
                                if tdt['lane_timeouts']:
                                    self.logger.warning(f"lane timeouts in TDT: {tdt}, event {event_count}")
                                    timed_out_lanes_blocks.append(iblock)
                                if tdt["lane_starts_violation"]:
                                    self.logger.warning(f"lane start violations in TDT: {tdt}, event {event_count}")
                                if tdt["packet_overflow"]:
                                    self.logger.warning(f"packet overflow in TDT: {tdt}, event {event_count}")
                                if tdt["transmission_timeout"]:
                                    self.logger.warning(f"transmission timeout in TDT: {tdt}, event {event_count}")
                                    timed_out_transmission_blocks.append(iblock)
                                previous_event_complete = tdt["packet_done"]

                                # There is still no info on what each of the 2 bits per lane means, so I will leave this here:
                                lane_status = tdt["lane_status"]

                            elif gbt_word[9]>>5 == 0b001: # IB
                                self.counter_tdt_gbt_word_inside += 1
                                assert header_found, f"Trigger header not found before chip data, bytes read {self.bytes_read}"
                                laneidx = gbt_word[9]&0x1F
                                if laneidx in ib_lane_lut.keys():
                                    assert active_lanes[ib_lane_lut[laneidx]], "Lane {0} not in header: {1}.".format(laneidx, active_lanes)
                                if laneidx not in lanes:
                                    lanes[laneidx] = []
                                    if gbt_word[0] & 0xff in (0xF0, 0xF1): # BUSY OFF or BUSY ON
                                        assert laneidx == (gbt_word[1] & 0x0f), f"IB: lane index 0x{gbt_word[9]:x} and chip header 0x{gbt_word[1]:x} don't agree"
                                    else:
                                        assert laneidx == (gbt_word[0] & 0x0f), f"IB: lane index 0x{gbt_word[9]:x} and chip header 0x{gbt_word[0]:x} don't agree"
                                lanes[laneidx] += gbt_word[0:9]
                            elif gbt_word[9]>>5 == 0b101: # IB DIAGNOSTIC DATA
                                ddata = self.decode_diagnostic(gbt_word)
                                self.logger.warning(f"IB diagnostic data received: {ddata['diagnostic_data']}, lane error id: {ddata['lane_error_id']}")
                            elif gbt_word[9]>>5 == 0b110: # OB DIAGNOSTIC DATA
                                ddata = self.decode_diagnostic(gbt_word)
                                self.logger.warning(f"OB diagnostic data received: {ddata['diagnostic_data']}, lane error id: {ddata['lane_error_id']}")
                            elif gbt_word[9]==0xE4: # DIAGNOSTIC DATA WORD (DDW)
                                ddw = self.decode_diagnostic(gbt_word)
                                self.logger.debug(f"DDW received, but nothing to do! Here's the DDW: {ddw}")
                            elif gbt_word[9]==0xF8: # CALIBRATION DATA WORD (CDW)
                                assert self.thscan, f"CDW found in data not from threshold scan! Block: {iblock} (if this data was from a TS, rerun decode with -ts flag)"
                                cdw_found = True
                                cdw = self.decode_cdw(gbt_word)
                                if current_cdw_field is None:
                                    current_cdw_field = cdw["user_field"]
                                elif current_cdw_field != cdw["user_field"]:
                                    assert cdw['counter'] == 0, f"CDW counter not reset upon user field change before byte {self.bytes_read}. Previous field: {current_cdw_field}, current field: {cdw['counter']}"
                                    current_cdw_field = cdw["user_field"]
                                else:
                                    self.logger.debug(f"CDW received, but nothing to do! Here's the CDW: {cdw}")
                                if self.thscan:
                                    new_row = cdw['user_field'] & 0xFFFF
                                    new_charge = (cdw['user_field'] >> 16) & 0xFFFF
                                    if thscan_injections_observed == self.thscan_injections:
                                        if thscan6 and thscan_current_row >= 0:
                                            assert new_row >= thscan_current_row%5, f"Row not increasing (or resetting to 0 after row 5) after thscan_injections: previous {thscan_current_row} new {new_row}"
                                        else:
                                            assert new_row >= thscan_current_row, f"Row not increasing after thscan_injections: previous {thscan_current_row} new {new_row}"
                                        if new_row == thscan_current_row :  # rolling charge at change of row
                                            assert new_charge > thscan_current_charge, f"Charge not incrasing after max thscan_injections: previous {thscan_current_charge} new {new_charge} [previous row {thscan_current_row} current row {new_row}]"
                                        else:
                                            if thscan_current_charge != -1 and rdh['triggers'] != ['EOT']:
                                                assert new_charge < thscan_current_charge, "Charge not decreasing after row change: previous {thscan_current_charge} new {new_charge}\nRDH: {rdh}"
                                        thscan_injections_observed = 1
                                        thscan_current_row = new_row
                                        thscan_current_charge = new_charge
                                        if thscan_current_row % 20 == 0 and thscan_current_charge == 0:
                                            self.logger.info(f"THSCAN_ANALYSIS: Row {thscan_current_row:4}\t\tCH {thscan_current_charge:4}\t\tInjects/Total: {thscan_injections_observed}/{thscan_injections}")
                                    else:
                                        assert new_row == thscan_current_row, f"Row not correct before reaching max thscan_injections: expected {thscan_current_row} got {new_row}"
                                        assert new_charge == thscan_current_charge, f"Charge not correct before reaching max thscan_injections: expected {thscan_current_charge} got {new_charge} [previous row {thscan_current_row}, current row {new_row} observed injections {thscan_injections_observed}]"
                                        thscan_injections_observed += 1

                            if previous_event_complete:
                                event_count += 1
                                if not self.skip_data:
                                    previous_bc_count = bc_count
                                    bc_count = None
                                    for lane, data in lanes.items():
                                        try:
                                            chip_data = self.decode_alpide(data, self.accept_decreasing_address, thscan_current_charge, thscan_current_row)
                                            for i, d in enumerate(chip_data):
                                                if bc_count:
                                                    # assert d['bc']==bc_count, f"bc_count on chip {i}, lane {lane} not matching the one of the other chips: 0x{d['bc']:02x} != 0x{bc_count:02x}"
                                                    pass
                                                else:
                                                    bc_count = d['bc']
                                                    # if not self.thscan: # thscan does not need to check this. Check is done in line 377 and following
                                                    #     assert bc_count != previous_bc_count, f"Previous and current bc counts are the same! 0x{bc_count:2x} == 0x{previous_bc_count:2x}"
                                        except:
                                            self.logger.info(f"Error in block before byte {self.bytes_read} for lane {lane}")
                                            raise
                                        if (iblock_event-boffset)%self.print_interval==0:
                                            for d in chip_data:
                                                self.logger.info(f"iblock_event {iblock_event}, Lane {lane}, bytes_read {self.bytes_read}: {d}")
                                lanes = {}
                                previous_event_complete = False
                                header_found = False
                                trailer_found = False
                    gbt_block_started = False

                # Done with this FELIX DMA packet
                break

        if self.fhr:
            np.save(self.fhr_filename, self.data_pixels)
        elif self.thscan:
            np.save(self.thscan_filename, self.data_pixels)
        if is_continuous_mode:
            if eoc_received:
                self.logger.info("Feeid {}: Run was executed in continuous mode: {} blocks, EOC received".format(self.feeid, iblock_event))
            else:
                self.logger.info("Feeid {}: Run was executed in continuous mode: {} blocks".format(self.feeid, iblock_event))
        elif is_triggered_mode:
            if eot_received:
                self.logger.info("Feeid {}: Run was executed in triggered mode: {} blocks, EOT received".format(self.feeid, iblock_event))
            else:
                self.logger.info("Feeid {}: Run was executed in triggered mode: {} blocks".format(self.feeid, iblock_event))
        else:
            if eot_received or eoc_received:
                self.logger.info("Feeid {}: Decoder restarted: {} blocks. EOC received: {} EOT received {}".format(self.feeid, iblock_event, eoc_received, eot_received))
            else:
                self.logger.info("Feeid {}: Decoder restarted: {} blocks".format(self.feeid, iblock_event))
        self.logger.info("Feeid {}: Total number of hits decoded: {}".format(self.feeid, self.total_hits))
        if len(packet_id_jumps):
            self.logger.info("ERROR: Packet jumps present: ")
            for bk, prev, seq in packet_id_jumps:
                self.logger.info(f"\tblock {bk}\tprevious {prev}\tcurrent {seq}")
        if len(timed_out_transmission_blocks):
            self.logger.info("{0} timed out transmission blocks at offset(s) {1}".format(
                len(timed_out_transmission_blocks), timed_out_transmission_blocks))
        if len(timed_out_lanes_blocks):
            self.logger.info("Timed out lanes blocks at offset {0}".format(timed_out_lanes_blocks))
        if other_feeids_count:
            self.logger.info("{} blocks not analysed due to different feeid".format(other_feeids_count))
        self.logger.info(f"trigger_counted: {events_cnt}")
        if self.counter_dict is not None:
            #TODO: multiple links in single decode script
            assert self.counter_dict["CRU_PACKETS"] == iblock, f"Mismatch between packets sent and packets decoded (SENT: {self.counter_dict['CRU_PACKETS']}, DECODED: {iblock})"
            if is_triggered_mode:
                assert self.counter_dict["TRIGGERS_SENT"] == events_cnt['PHYSICS'], f"Mismatch between triggers sent and triggers decoded (SENT: {self.counter_dict['TRIGGERS_SENT']}, DECODED: {events_cnt['PHYSICS']})"
        self.logger.info(f"Identified feeids: {feeids}")
        self.logger.info(f"Identified links: {linkids}")
        assert not all((is_continuous_mode, is_triggered_mode)), "Run in triggered and continuous mode"

        if self.thscan and not cdw_found:
            self.logger.error("No CDW found in threshold scan")
        self.logger.info(f"RDH: {self.counter_rdh:16}\t\t RDH (page 0,nstop){self.counter_rdh_page_zero_no_stop:16}")
        self.logger.info(f"TDH: {self.counter_tdt:16}\t\t TDH (no cont)     {self.counter_tdh_no_continuation:16}")
        self.logger.info(f"TDT: {self.counter_tdt:16}\t\t TDT (packet done) {self.counter_tdt_packet_done:16}")

        self.f.close()
        return events_cnt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-i", "--feeid", type=int, required=False, help="FEE ID to analyse: leave blank to print only the list of identified feeids, as soon as they are discovered", default=None)
    parser.add_argument("-p", "--print_interval", type=int, required=False, help="Print interval for ALPIDE decoded data", default=100001) # set to uneven to print RDH with stop == 0
    parser.add_argument("-s", "--offset", type=int, required=False, help="**Advanced feature:** Byte offset for the data decoding to seek to. NOTE: the offset should point to a valid RDH. NOTE: not supported without input file (i.e. with input in stdin)", default=0)
    parser.add_argument("--skip_data", required=False, help="Switch, if enabled only runs on RDH", action='store_true')
    parser.add_argument("--assert_on_pcount", required=False, help="Switch, if enabled asserts on the RDH packet counter", action='store_true')
    parser.add_argument("-fhr", "--do_fhr", required=False, help="Switch, if enabled saves the pixel data for a FakeHitRate run", action='store_true')
    parser.add_argument("-ts", "--thscan", required=False, help="Switch, if enabled asserts on the RDH packet counter", action='store_true')
    parser.add_argument("-ti", "--thinjections", type=int, required=False, help="Number of injections per charge in thresholdscan (default 25),\nCan only be used with the -ts action active.", default=25)
    parser.add_argument("-ada", "--accept_decreasing_address", required=False, help="Switch to only prints for decreasing address instead of raising an error", action='store_true')
    parser.add_argument("-ts6", "--thscan6", required=False, help="Switch, if enabled asserts on the RDH packet counter", action='store_true')
    parser.add_argument("-cll", "--check_lane_list", required=False, help=f"If a list is passed here, the list of lanes is checked against the list and an assert is risen. Argument is a comma-separated list. No brackets are required. lane in range({MAX_LANES}). Anything else is ignored!", default="")
    parser.add_argument("-cp", "--counter_path", required=False, help=f"If a path to counters.json file is supplied, the final counters in the decode will be compared and an assert is risen", default="")
    parser.add_argument("-w", "--warn_on_expect_no_data", required=False, help=f"Will give a warning when there is a TDH with the expect no data bit set", action='store_true')
    parser.add_argument("-wpm", "--warn_on_padding_misaligned", required=False, help=f"Will give a warning when padding is not ending on a 256byte boundary", action='store_true')
    args = parser.parse_args()

    filepath = args.filepath
    feeid = args.feeid
    offset = args.offset
    skip_data = args.skip_data
    print_interval = args.print_interval
    assert_on_pcount = args.assert_on_pcount
    thscan = args.thscan
    thscan6 = args.thscan6
    thscan_injections = args.thinjections
    accept_decreasing_address =  args.accept_decreasing_address
    warn_on_expect_no_data = args.warn_on_expect_no_data

    if args.check_lane_list == "":
        check_lane_list = False
    else:
        check_lane_list = True
        expected_lane_list = [int(item) for item in args.check_lane_list.split(',')]

    counter_path = args.counter_path

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    if feeid is not None:
        feeid_ru = (feeid & 0x7000) >> 8 | (feeid & 0x1F)
        _,l,s = ws_identity.WsIdentity.decode_fee_id(feeid_ru)
        name = ws_identity.WsIdentity.decode_stave_name(l,s)
        logger = logging.getLogger(f"decode{name}")
    else:
        logger = logging.getLogger("decode")

    decode = Decode(logger=logger,
                    filename=filepath,
                    do_fhr=args.do_fhr,
                    feeid=feeid,
                    offset=offset,
                    skip_data=skip_data,
                    print_interval=print_interval,
                    assert_on_pcount=assert_on_pcount,
                    thscan=thscan,
                    thscan_injections=thscan_injections,
                    accept_decreasing_address=accept_decreasing_address,
                    check_lane_list=check_lane_list,
                    counter_path=counter_path,
                    warn_on_padding_misaligned=args.warn_on_padding_misaligned,
                    warn_on_expect_no_data=warn_on_expect_no_data,
                    thscan6=thscan6)

    decode.main()
