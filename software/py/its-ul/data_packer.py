#!/usr/bin/env python3
"""Convert file of lines of hex data (from UVM simulation) to binary format"""

import argparse
import logging
import sys
import os

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

import rdh_definitions
import trigger

RDH_VERSION = 6
RDH_SIZE = 64
BLOCK_SIZE = 8192
SOURCE_ID = 32
LANES_IB = 9
LANES_OB = 28
MAX_LANES = LANES_OB
B_PER_GBT_WORD = 16    # 128 bits
VERBOSE = False
PADDED_BYTES = 6
WORD_SIZE = 10

W0_POS_0_START = 0
W0_POS_0_STOP = WORD_SIZE
W0_POS_1_START = W0_POS_0_STOP
W0_POS_1_STOP = W0_POS_1_START+6

W1_POS_0_START = 0
W1_POS_0_STOP = 4
W1_POS_1_START = W1_POS_0_STOP
W1_POS_1_STOP = W1_POS_0_STOP+WORD_SIZE
W1_POS_2_START = W1_POS_1_STOP
W1_POS_2_STOP = W1_POS_2_START+2

W2_POS_0_START = 0
W2_POS_0_STOP = WORD_SIZE-2
W2_POS_1_START = W2_POS_0_STOP
W2_POS_1_STOP = W2_POS_1_START+8

W3_POS_0_START = 0
W3_POS_0_STOP = 2
W3_POS_1_START = W3_POS_0_STOP
W3_POS_1_STOP = W3_POS_1_START+WORD_SIZE
W3_POS_2_START = W3_POS_1_STOP
W3_POS_2_STOP = W3_POS_2_START+4

W4_POS_0_START = 0
W4_POS_0_STOP = WORD_SIZE-4
W4_POS_1_START = W4_POS_0_STOP
W4_POS_1_STOP = W4_POS_1_START+WORD_SIZE


class Packer():
    def __init__(self, logger, filename='/dev/stdin', offset=0, print_interval=100000):
        self.logger = logger
        self.f = open(filename, 'rb')
        self.offset = offset
        self.print_interval = print_interval

    def gearbox80128(self, data):
        if len(data) <= 0:
            return data
        self.logger.info("Gearboxing...")

        buf_pos = 0
        new_data = bytearray()

        for i in range(0, len(data), 16):
            if buf_pos % 8 == 0:
                word = data[i:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 1:
                word = data[i+4:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
                word = data[i:i+4]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 2:
                word = data[i:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 3:
                word = data[i+8:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
                word = data[i:i+8]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 4:
                word = data[i+2:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
                word = data[i:i+2]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 5:
                word = data[i:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 6:
                word = data[i+6:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
                word = data[i:i+6]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)
            elif buf_pos % 8 == 7:
                word = data[i:i+WORD_SIZE]
                #print(f"{word.hex()}, {len(word)}")
                new_data.extend(word)

            buf_pos += 1

        # Pad bytes if uneven packet
        if len(new_data) % 16 != 0:
            new_data.extend(bytes([255])*(16 - (len(new_data) % 16)))

        # print("result")
        # for i in range(0, len(new_data), 16):
        #     print(new_data[i:i+16].hex())

        return new_data

    def gearbox12880(self, data):
        if len(data) <= 0:
            return data
        self.logger.info("Reverse gearboxing...")

        buf_pos = 0
        word_pos = 0
        new_data = bytearray()
        partial_word = bytearray()
        padding = bytearray([0x0, 0x0, 0x0, 0x0, 0x0, 0x0])

        for i in range(0, len(data), 16):
            if buf_pos % 5 == 0:
                print(f"{data[i:i+16].hex()}")

                if word_pos == 0:
                    word = data[i:i+W0_POS_0_STOP]
                    self.logger.info(f"Getting word 0 pos 0, ctrl word {hex(word[W0_POS_0_STOP-W0_POS_0_START-1])}")
                    new_data.extend(word)
                    new_data.extend(padding)
                    word_pos += 1

                if word_pos == 1:
                    if data[i+W0_POS_1_STOP-1] != 0xFF:
                        partial_word = bytearray(data[i+W0_POS_1_START:i+W0_POS_1_STOP])
                        self.logger.info(f"Getting word 0 pos 1, ctrl word {hex(partial_word[W0_POS_1_STOP-W0_POS_1_START-1])}")
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

            elif buf_pos % 5 == 1:
                print(f"{data[i:i+16].hex()}")

                if word_pos == 1:
                    self.logger.info("Getting word 1 pos 0")
                    word = data[i:i+W1_POS_0_STOP]
                    partial_word[0:0] = word # insert in front
                    new_data.extend(partial_word)
                    new_data.extend(padding)
                    word_pos += 1

                if word_pos == 2:
                    if data[i+W1_POS_1_STOP-1] != 0xFF:
                        word = data[i+W1_POS_1_START:i+W1_POS_1_STOP]
                        self.logger.info(f"Getting word 1 pos 1, ctrl word {hex(word[W1_POS_1_STOP-W1_POS_1_START-1])}")
                        new_data.extend(word)
                        new_data.extend(padding)
                        word_pos += 1
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

                if word_pos == 3:
                    if data[i+W1_POS_2_STOP-1] != 0xFF:
                        partial_word = bytearray(data[i+W1_POS_2_START:i+W1_POS_2_STOP])
                        self.logger.info(f"Getting word 1 pos 2, ctrl word {hex(partial_word[(W1_POS_2_STOP-W1_POS_2_START)-1])}")
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

            elif buf_pos % 5 == 2:
                print(f"{data[i:i+16].hex()}")

                if word_pos == 3:
                    self.logger.info("Getting word 2 pos 0")
                    word = data[i:i+W2_POS_0_STOP]
                    partial_word[0:0] = word # insert in front
                    new_data.extend(partial_word)
                    new_data.extend(padding)
                    word_pos += 1

                if word_pos == 4:
                    if data[i+W2_POS_1_STOP-1] != 0xFF:
                        partial_word = bytearray(data[i+W2_POS_1_START:i+W2_POS_1_STOP])
                        self.logger.info(f"Getting word 2 pos 1, ctrl word {hex(partial_word[W2_POS_1_STOP-W2_POS_1_START-1])}")
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

            elif buf_pos % 5 == 3:
                print(f"{data[i:i+16].hex()}")

                if word_pos == 4:
                    self.logger.info("Getting word 3 pos 0")
                    word = data[i:i+W3_POS_0_STOP]
                    partial_word[0:0] = word # insert in front
                    new_data.extend(partial_word)
                    new_data.extend(padding)
                    word_pos += 1

                if word_pos == 5:
                    if data[i+W3_POS_1_STOP-1] != 0xFF:
                        word = data[i+W3_POS_1_START:i+W3_POS_1_STOP]
                        self.logger.info(f"Getting word 3 pos 1, ctrl word {hex(word[W3_POS_1_STOP-W3_POS_1_START-1])}")
                        new_data.extend(word)
                        new_data.extend(padding)
                        word_pos += 1
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

                if word_pos == 6:
                    if data[i+W3_POS_2_STOP-1] != 0xFF:
                        partial_word = bytearray(data[i+W3_POS_2_START:i+W3_POS_2_STOP])
                        self.logger.info(f"Getting word 3 pos 2, ctrl word {hex(partial_word[W3_POS_2_STOP-W3_POS_2_START-1])}")
                    else:
                        self.logger.info("Found padding, no more data read")
                        break


            elif buf_pos % 5 == 4:
                print(f"{data[i:i+16].hex()}")

                if word_pos == 6:
                    self.logger.info("Getting word 4 pos 0")
                    word = data[i:i+W4_POS_0_STOP]
                    partial_word[0:0] = word # insert in front
                    new_data.extend(partial_word)
                    new_data.extend(padding)
                    word_pos += 1

                if word_pos == 7:
                    if data[i+W4_POS_1_STOP-1] != 0xFF:
                        word = bytearray(data[i+W4_POS_1_START:i+W4_POS_1_STOP])
                        self.logger.info(f"Getting word 4 pos 1, ctrl word {hex(word[W4_POS_1_STOP-W4_POS_1_START-1])}")
                        new_data.extend(word)
                        new_data.extend(padding)
                        word_pos = 0
                    else:
                        self.logger.info("Found padding, no more data read")
                        break

            buf_pos += 1

        # Pad bytes if uneven packet
        if len(new_data) % 16 != 0:
            new_data.extend(bytes([255])*(16 - (len(new_data) % 16)))

        # print("result")
        # for i in range(0, len(new_data), 16):
        #     print(new_data[i:i+16].hex())

        return new_data

    def ul_convert(self, rdh, data, unpack=True):
        self.logger.info("Converting data....")
        print(rdh)
        if unpack:
            data = self.gearbox12880(data)
        else:
            data = self.gearbox80128(data)
        rdh['next_packet_offset'] = len(data) + RDH_SIZE
        rdh['memory_size'] = len(data) + RDH_SIZE
        print(rdh)
        return rdh, data


    def pack(self, unpack=False):

        iblock = self.offset

        boffset = 0
        block = bytearray()
        while(True):
            # first read RDH to get memsize
            rdh_block, rdh_len = self.read_and_check_len(name='RDH', expected_len=RDH_SIZE, verbose=VERBOSE)
            if rdh_len==0 or (rdh_block[rdh_definitions.Rdh6ByteMap.VERSION]==0 and rdh_block[rdh_definitions.Rdh6ByteMap.SIZE]==0):
                break #EOF
            iblock += 1
            memsize = rdh_block[rdh_definitions.Rdh6ByteMap.MEMSIZE_MSB] << 8 | rdh_block[rdh_definitions.Rdh6ByteMap.MEMSIZE_LSB]

            gbt_words_in_block = round(memsize/B_PER_GBT_WORD)
            assert gbt_words_in_block in range(512+1), f"Packet bigger than 8 kB: {gbt_words_in_block} > 512"

            if (iblock-boffset)%self.print_interval==0:
                self.logger.info(f'------------ block {iblock} size 0x{memsize:x}------------')
            rdh = self.decode_rdh(rdh_block)

            # then read remaining data
            data_block_len = memsize-RDH_SIZE
            data_block, _ = self.read_and_check_len(name='DATA', expected_len=data_block_len)

            # skip the remaining data up to the next packet
            junk_block_len = rdh['next_packet_offset'] - memsize
            _, _ = self.read_and_check_len(name='JUNK', expected_len=junk_block_len)
            assert RDH_SIZE + data_block_len + junk_block_len == rdh['next_packet_offset']

            rdh, data_block = self.ul_convert(rdh, data_block, unpack)

            rdh_block = self.encode_rdh(rdh)

            block.extend(rdh_block)
            if len(data_block) > 0:
                block.extend(data_block)

        return block


    def read_and_check_len(self, name, expected_len, verbose=False):
        """If a positive expected len is given, the data are read from file and checked for the correct size"""
        if expected_len<=0:
            return [],0
        else:
            data_block = self.f.read(expected_len)
            data_len  = len(data_block)
            if data_len != 0:  # ie EOF (len=0), just return
                assert data_len==expected_len, f'{name} block is incomplete: {data_len}/{expected_len} B'
            if verbose:
                self.logger.info(f'{name} read {data_len}/{expected_len}')
            return data_block, data_len

    @staticmethod
    def encode_rdh(rdh):
        rdh_block = bytearray(RDH_SIZE)

        # WORD 0
        rdh_block[rdh_definitions.Rdh6ByteMap.VERSION] = RDH_VERSION
        rdh_block[rdh_definitions.Rdh6ByteMap.SIZE] = RDH_SIZE
        rdh_block[rdh_definitions.Rdh6ByteMap.FEEID_MSB] = (rdh['feeid'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.FEEID_LSB] = rdh['feeid'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.PRIORITY] = rdh['priority']
        rdh_block[rdh_definitions.Rdh6ByteMap.SOURCE_ID] = rdh['source_id']
        rdh_block[rdh_definitions.Rdh6ByteMap.NEXT_PACKET_OFFSET_MSB] = (rdh['next_packet_offset'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.NEXT_PACKET_OFFSET_LSB] = rdh['next_packet_offset'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.MEMSIZE_MSB] = (rdh['memory_size'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.MEMSIZE_LSB] = rdh['memory_size'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.LINK_ID] = rdh['linkid']
        rdh_block[rdh_definitions.Rdh6ByteMap.PACKET_COUNTER] = rdh['packet_counter']
        rdh_block[rdh_definitions.Rdh6ByteMap.CRU_ID_MSB] = (rdh['dwrapper_id'] << 4) + ((rdh['cru_id'] >> 8) & 0xF)
        rdh_block[rdh_definitions.Rdh6ByteMap.CRU_ID_LSB] = rdh['cru_id'] & 0xFF

        # WORD 1
        rdh_block[rdh_definitions.Rdh6ByteMap.BC_MSB] = (rdh['trg'][1] >> 8) & 0xF
        rdh_block[rdh_definitions.Rdh6ByteMap.BC_LSB] = rdh['trg'][1] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.ORBIT_SB3] = (rdh['trg'][0] >> 24) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.ORBIT_SB2] = (rdh['trg'][0] >> 16) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.ORBIT_SB1] = (rdh['trg'][0] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.ORBIT_SB0] = rdh['trg'][0] & 0xFF

        # Word 2
        rdh_block[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB3] = (rdh['trg_type'] >> 24) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB2] = (rdh['trg_type'] >> 16) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB1] = (rdh['trg_type'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB0] = rdh['trg_type'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.PAGE_CNT_MSB] = (rdh['pages_count'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.PAGE_CNT_LSB] = rdh['pages_count'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.STOP_BIT] = rdh['stop']

        # Word 3
        rdh_block[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB3] = (rdh['detfield'] >> 24) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB2] = (rdh['detfield'] >> 16) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB1] = (rdh['detfield'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB0] = rdh['detfield'] & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.PAR_MSB] = (rdh['par'] >> 8) & 0xFF
        rdh_block[rdh_definitions.Rdh6ByteMap.PAR_LSB] = rdh['par'] & 0xFF

        return rdh_block


    @staticmethod
    def decode_rdh(rdh):
        #GBT WORD 0
        h_ver = rdh[rdh_definitions.Rdh6ByteMap.VERSION]
        h_len = rdh[rdh_definitions.Rdh6ByteMap.SIZE]
        feeid = rdh[rdh_definitions.Rdh6ByteMap.FEEID_MSB] << 8 | rdh[rdh_definitions.Rdh6ByteMap.FEEID_LSB]
        priority = rdh[rdh_definitions.Rdh6ByteMap.PRIORITY]
        source_id = rdh[rdh_definitions.Rdh6ByteMap.SOURCE_ID]
        next_packet_offset = rdh[rdh_definitions.Rdh6ByteMap.NEXT_PACKET_OFFSET_MSB]<<8 | rdh[rdh_definitions.Rdh6ByteMap.NEXT_PACKET_OFFSET_LSB]
        memory_size = rdh[rdh_definitions.Rdh6ByteMap.MEMSIZE_MSB]<<8 | rdh[rdh_definitions.Rdh6ByteMap.MEMSIZE_LSB]
        linkid = rdh[rdh_definitions.Rdh6ByteMap.LINK_ID]
        packet_counter = rdh[rdh_definitions.Rdh6ByteMap.PACKET_COUNTER]
        cru_id = (rdh[rdh_definitions.Rdh6ByteMap.CRU_ID_MSB] & 0xF)<<8 | rdh[rdh_definitions.Rdh6ByteMap.CRU_ID_LSB]
        dwrapper_id = (rdh[rdh_definitions.Rdh6ByteMap.DWRAPPER_ID]>>4) & 0xF

        #GBT WORD 1
        bc = (rdh[rdh_definitions.Rdh6ByteMap.BC_MSB] << 8 | rdh[rdh_definitions.Rdh6ByteMap.BC_LSB]) & 0xFFF
        orbit = rdh[rdh_definitions.Rdh6ByteMap.ORBIT_SB3] << 24 | rdh[rdh_definitions.Rdh6ByteMap.ORBIT_SB2] << 16 | rdh[rdh_definitions.Rdh6ByteMap.ORBIT_SB1] << 8 | rdh[rdh_definitions.Rdh6ByteMap.ORBIT_SB0]

        #GBT WORD 2
        trg_type = rdh[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB3] << 24 | rdh[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB2] << 16 | rdh[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB1] << 8 | rdh[rdh_definitions.Rdh6ByteMap.TRG_TYPE_SB0]
        pages_count = rdh[rdh_definitions.Rdh6ByteMap.PAGE_CNT_MSB] << 8 | rdh[rdh_definitions.Rdh6ByteMap.PAGE_CNT_LSB]
        stop_bit = rdh[rdh_definitions.Rdh6ByteMap.STOP_BIT]

        #GBT WORD 3
        det_field = rdh[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB3] << 24 | rdh[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB2] << 16 | rdh[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB1] << 8 | rdh[rdh_definitions.Rdh6ByteMap.DET_FIELD_SB0]
        par = rdh[rdh_definitions.Rdh6ByteMap.PAR_MSB] << 8 | rdh[rdh_definitions.Rdh6ByteMap.PAR_LSB]

        triggers = []
        for flag in trigger.BitMap:
            if trg_type >> flag.value & 1 == 1:
                triggers.append(flag.name)

        rdh = {
            'feeid'              : feeid,
            'priority'           : priority,
            'source_id'          : source_id,
            'next_packet_offset' : next_packet_offset,
            'memory_size'        : memory_size,
            'linkid'             : linkid,
            'packet_counter'     : packet_counter,
            'cru_id'             : cru_id,
            'dwrapper_id'        : dwrapper_id,
            'trg'                : (orbit, bc),
            'trg_type'           : trg_type,
            'detfield'           : det_field,
            'par'                : par,
            'stop'               : stop_bit,
            'pages_count'        : pages_count,
            'triggers'           : triggers
            }

        assert h_ver == RDH_VERSION, "wrong rdh version = 0x{0:x}, rdh: {1}".format(h_ver, rdh)
        assert h_len == RDH_SIZE, "wrong rdh length = 0x{0:x}, rdh: {1}".format(h_len, rdh)
        assert source_id == SOURCE_ID, "wrong source id = 0x{0:x}, rdh: {1}".format(source_id, rdh)
        assert priority == 0, "wrong priority = {0}, rdh: {1}".format(priority, rdh)
        assert par == 0, "wrong block par = 0x{0:x}, rdh: {1}".format(par, rdh)
        assert trg_type >> len(trigger.BitMap) == 0, "Invalid trigger type = 0x{0:x}, rdh: {1}".format(trg_type, rdh)
        assert trigger.BitMap.PP.name not in triggers,  "PP not expected {0}".format(triggers)
        assert trigger.BitMap.CAL.name not in triggers, "CAL not expected {0}".format(triggers)
        return rdh

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputfile", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-o", "--outputfile", required=False, help="Path to file to write", default="output.bin")
    parser.add_argument("-u", "--unpack", required=False, help="Switch, if set unpack instead of pack", action='store_true')

    args = parser.parse_args()
    input = args.inputfile
    output = args.outputfile
    unpack = args.unpack

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logger = logging.getLogger("packer")

    packer = Packer(logger, input)
    if not unpack:
        block = packer.pack()
    else:
        block = packer.pack(unpack=True)

    with open(output, "wb") as f:
        f.write(block)