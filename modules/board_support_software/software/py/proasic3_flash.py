"""Flash interface higher-level functions"""

from typing import List, Dict

import math
import os
import random
import time
from itertools import zip_longest
import warnings

from timeout_decorator.timeout_decorator import timeout

from ecc_conversion.ecc_functions import make_ecc_file
from ecc_conversion.generateScrubbingFile import Scrub
from ecc_conversion.makeparameters import make_parameter_file_and_ecc
from proasic3_convenience import Flash, Fifo, Ecc, BLOCK_COUNT, PAGE_SIZE, PAGE_SIZE_ECC, PAGE_PER_BLOCK, ADDRESS_MAX
from proasic3_enums import Pa3Register, \
    FlashCmdOpcode, FifoWriterCmdOpcode, \
    FlashSelectICOpcode, EccCmdOpcodes

EXEC = 0x80


class ProAsic3Flash(Flash, Fifo, Ecc):
    """Flash interface higher-level functions"""

    def __init__(self, conv_init, write_fifo_f, write_ultrascale_fifo_f=None, reset_f=None):
        super(ProAsic3Flash, self).__init__(conv_init)
        self.write_fifo_reg_multi_byte = write_fifo_f  # expecting function that takes data
        self.write_ultrascale_fifo = write_ultrascale_fifo_f  # expecting function that takes data
        self.reset_pa3 = reset_f # expecting function with no parameters.

    def _get_page_size(self, ECC=False):
        if ECC or self.ecc_on():
            return PAGE_SIZE_ECC
        else:
            return PAGE_SIZE

    def _flash_erase_blocks(self, start_block, num_blocks):
        """Erase a range of blocks from the FLASH"""
        assert start_block + num_blocks in range(BLOCK_COUNT)
        stop_block = (start_block + num_blocks)
        self.logger.info(f"Erasing blocks 0x{start_block:04X} to 0x{stop_block:04X} pages 0x{start_block * 0x40:06X} to 0x{stop_block * 0x40:06X}.")
        try:
            for block in range(start_block, stop_block):
                page_adr = block * PAGE_PER_BLOCK
                self.set_flash_address(whole_address=page_adr)

                self.set_flash_command_register(FlashCmdOpcode.BLOCK_ERASE)
                self.flash_wait_ready()
        except TimeoutError as e:
            self.logger.info(f"Reached page 0x{page_adr:06X} of 0x{stop_block:06X} before timeout.")
            raise e

    def flash_write_data(self, data, start_block, ECC=False, override_page_size=0, use_ultrascale_fifo=False, ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Write a binary file to flash
        warning : erases whole blocks.
        """
        self.logger.debug("Starting write to flash...")
        self.logger.debug("This function will fail if it encounters a bad block. In case, increment the start block by e.g. 0x100 to solve the issue.")
        page_address = start_block * PAGE_PER_BLOCK
        assert 0 <= page_address < ADDRESS_MAX, \
            "Page address invalid: does not fit in flash address space."
        assert len(data) > 0, "Empty data provided"
        page_size = self._get_page_size(ECC)
        if override_page_size:
            self.set_flash_page_size(override_page_size)
        else:
            self.set_flash_page_size(page_size)
        if not self.ecc_ok():
            raise RuntimeError("ECC is not in an OK state.")

        size_pages = math.ceil(len(data) / page_size)
        size_blocks = int(math.ceil(size_pages / PAGE_PER_BLOCK))
        self.logger.debug(f"Writing a file to the flash.\nSize is {size_blocks:04X} blocks.")

        self.set_flash_select_ic(ic)

        self._flash_erase_blocks(start_block, size_blocks)

        self.set_fifo_writer_command_register(FifoWriterCmdOpcode.CLEAR_ERRORS)

        # Set bitfile start page addr
        address_of_start_block = start_block * PAGE_PER_BLOCK
        self.set_flash_address(whole_address=address_of_start_block)
        self.logger.info(f"Writing file to page 0x{address_of_start_block:06X} / block 0x{start_block:04X}.")

        _fws_val, fws_dict = self.get_fifo_writer_status()  # fws = fifo_writer_status
        assert fws_dict['READY'], "PA3 write controller reports busy."
        if use_ultrascale_fifo:
            self.set_fifo_writer_command_register(FifoWriterCmdOpcode.WRITE_XILINX)
        else:
            self.set_fifo_writer_command_register(FifoWriterCmdOpcode.WRITE_BUS)  # Start writing with wb bus as input
        if (len(data) % page_size) != 0:
            self.logger.debug("Filling out the bytearray.")
            delta_l = page_size - (len(data) % page_size)
            data.extend([0xFF] * delta_l)
        if use_ultrascale_fifo:  # ultrascale transfer
            if not callable(self.write_ultrascale_fifo):
                raise ValueError("Xilinx fifo writing function not given or not callable.")
            for Bytes in grouper(data, 2):
                concat = int().from_bytes(Bytes, 'little')
                self.write_ultrascale_fifo(concat)
        else:  # I2C slow transfer
            for Bytes in grouper(data, 16):
                self.write_fifo_reg_multi_byte(Pa3Register.FIFO_DATA_WR, Bytes)

        self.set_fifo_writer_command_register(FifoWriterCmdOpcode.STOP)
        try:
            self.flash_wait_ready()
        except TimeoutError as e:
            self.logger.info("Timeout reached while waiting for fifo writer stop.")
            raise e
        self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC1)

        self.logger.debug("Write to flash done.")

    @timeout(30, exception_message="FLASH never ready")
    def flash_wait_ready(self):
        """Waits until PA3 flash status register returns ready"""
        i = 0
        kvalues = set()
        while True:
            flash_status_value, flash_status = self.get_flash_status()
            kvalues.add(hex(flash_status_value))
            ready = flash_status['done_sticky'] and not flash_status['activity']
            error = flash_status['Error_bit']
            if ready:
                break
            if error:
                self.logger.warning("Hardware reports flash Error bit")
                raise ValueError("Hardware reports flash Error bit")
            i += 1
            if i % 100 == 0:
                self.logger.info(f"Flash waiting iteration:{i}, status:0x{flash_status_value:02X} statuses observed:{kvalues}")

    def _flash_empty_read_fifo(self):
        """Empty the FLASH Read FIFO"""
        while (self.read_reg(Pa3Register.FIFO_STATUS) & 0b10) == 0:
            # Todo: Timeouts?
            self.read_reg(Pa3Register.FIFO_DATA_RD)

    @timeout(50, exception_message="INTERNAL_RD_FIFO_EMPTY bit not low")
    def _flash_poll_internal_rd_fifo_not_empty(self):
        """
        Poll the INTERNAL_RD_FIFO_EMPTY bit for negative value
        """
        while True:
            status_val, _status_dict = self.get_fifo_status()
            if (status_val & 0b10) == 0:
                break

    def flash_verify_data(self, file_data, start_block, ECC=False, override_page_size=0, chip_num=0):
        """Verifies a binary file in flash
        ECC bits in file are not checked against flash directly.
        """
        assert chip_num in range(2), f"{chip_num}"
        self.logger.info("Starting verification of flash in chip {}".format(chip_num))

        page_address = start_block * PAGE_PER_BLOCK
        assert 0 <= page_address < ADDRESS_MAX, \
            "Page address invalid: does not fit in flash address space"
        if ECC:
            page_size = PAGE_SIZE_ECC
            ecc_size = 3
        else:
            page_size = PAGE_SIZE
            ecc_size = 0
        chunk_size = 128
        if not self.ecc_ok():
            raise RuntimeError("ECC is not in an OK state.")

        if chip_num == 0:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC1)
        else:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC2)

        if (len(file_data) % page_size) != 0:
            self.logger.debug("Filling out the bytearray.")
            delta_l = page_size - (len(file_data) % page_size)
            file_data.extend([0xFF] * delta_l)

        for page in range(math.ceil(len(file_data)/page_size)):
            page_data = self.flash_read_page(page_address+page, ECC=ECC, override_page_size=override_page_size)
            # ECC is added to bitile as 3 bytes every 128byte chunk
            for chunk in range(0, PAGE_SIZE, chunk_size):
                for i in range(chunk_size):
                    assert page_data[chunk+i] == file_data[page_size*page+(chunk//chunk_size*(chunk_size+ecc_size))+i], "Verification failed at page {0} block {1} byte {2} flash data {3} file data {4}".format(page, int(page//PAGE_PER_BLOCK), page_size*page+i, page_data[chunk+i], file_data[page_size*page+(chunk/chunk_size*(chunk_size+ecc_size))+i])
        self.logger.info("Verification completed successfully on chip {}".format(chip_num))


    def flash_compare_file(self, filename, start_block):
        """To be explained...."""
        with open(os.path.realpath(filename), 'rb') as infile:
            file_data = bytearray(infile.read())
        is_data_ecc_encoded=True
        override_page_size=4192
        chip_num=0
        self.disable_ecc()
        self.logger.info("Starting verification of flash in chip {}".format(chip_num))

        page_address = start_block * PAGE_PER_BLOCK
        assert 0 <= page_address < ADDRESS_MAX, \
            "Page address invalid: does not fit in flash address space"
        if is_data_ecc_encoded:
            page_size = PAGE_SIZE_ECC
            ecc_size = 3
        else:
            page_size = PAGE_SIZE
            ecc_size = 0
        chunk_size = 128
        chunk_size_ecc = 131
        if not self.ecc_ok():
            raise RuntimeError("ECC is not in an OK state.")

        if chip_num == 0:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC1)
        else:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC2)

        if (len(file_data) % page_size) != 0:
            self.logger.debug("Filling out the bytearray.")
            delta_l = page_size - (len(file_data) % page_size)
            file_data.extend([0xFF] * delta_l)

        for page in range(math.ceil(len(file_data)/page_size)):
            page_data = self.flash_read_page(page_address+page, ECC=is_data_ecc_encoded, override_page_size=override_page_size)
            # ECC is added to bitile as 3 bytes every 128byte chunk
            page_file = file_data[page_size*page : page_size*page + page_size]
            if page_data == page_file:
                #self.logger.info(f"PAGE {page} OK")
                print(".", end="", flush=True)
            else:
                print("")
                self.logger.error(f"Page {page} NOK")
                for i, byte in enumerate(page_file):
                    if byte != page_data[i]:
                        self.logger.error(f"Byte {i} NOK - Chunk {i // chunk_size_ecc} - File {hex(byte)} - Flash {hex(page_data[i])}")

        self.enable_ecc()

    def flash_compare_file_with_ecc(self, filename, start_block):
        """To be explained...."""
        with open(os.path.realpath(filename), 'rb') as infile:
            file_data = bytearray(infile.read())
        is_data_ecc_encoded=False
        override_page_size=4192
        chip_num=0
        self.logger.info("Starting verification of flash in chip {}".format(chip_num))

        page_address = start_block * PAGE_PER_BLOCK
        assert 0 <= page_address < ADDRESS_MAX, \
            "Page address invalid: does not fit in flash address space"
        if is_data_ecc_encoded:
            page_size = PAGE_SIZE_ECC
            ecc_size = 3
        else:
            page_size = PAGE_SIZE
            ecc_size = 0
        chunk_size = 128
        #chunk_size_ecc = 131
        if not self.ecc_ok():
            raise RuntimeError("ECC is not in an OK state.")

        if chip_num == 0:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC1)
        else:
            self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC2)

        if (len(file_data) % page_size) != 0:
            self.logger.debug("Filling out the bytearray.")
            delta_l = page_size - (len(file_data) % page_size)
            file_data.extend([0xFF] * delta_l)

        sb_errors = 0

        for page in range(math.ceil(len(file_data)/page_size)):
            page_data = self.flash_read_page(page_address+page, ECC=is_data_ecc_encoded)
            # ECC is added to bitile as 3 bytes every 128byte chunk
            page_file = file_data[page_size*page : page_size*page + page_size]
            if page_data == page_file:
                #self.logger.info(f"PAGE {page} OK")
                print(".", end="", flush=True)
            else:
                print("")
                self.logger.error(f"Page {page} NOK")
                for i, byte in enumerate(page_file):
                    if byte != page_data[i]:
                        self.logger.error(f"Byte {i} NOK - Chunk {i // chunk_size} - File {hex(byte)} - Flash {hex(page_data[i])}")
                        sb_errors += 1

        #self.enable_ecc()
        self.logger.info(f"Bit errors: {sb_errors}")


    def flash_read_page(self, page_address, ECC=False, override_page_size=None):
        """Reads a page from the flash and returns it as a bytearray
        """
        assert 0 <= page_address < ADDRESS_MAX, \
            "Page address invalid: does not fit in flash address space"
        data_size = 0x1000  # data size is always! 0x1000, no matter ecc or not. unless override
        self.set_flash_page_size(self._get_page_size(ECC))
        if override_page_size:
            self.set_flash_page_size(override_page_size)
            data_size = override_page_size

        # Empty read fifo
        self._flash_empty_read_fifo()  # ok
        self.set_flash_address(whole_address=page_address)
        self.set_flash_command_register(FlashCmdOpcode.PAGE_READ)
        page_buf = []
        try:
            for i in range(data_size):
                self._flash_poll_internal_rd_fifo_not_empty()
                val = self.get_fifo_rx_data()
                page_buf.append(val)
        except TimeoutError as e:
            self.logger.info("Reached page", hex(i), "of", hex(data_size), "before timeout.")
            raise e
        return bytearray(page_buf)

    def _dump_page(self, page_buf, page_address, to_screen=False, path='.', file_base_name='page_dump'):
        """Dumps the selected page to file.
        if to_screen is True it writes it into the logfile"""
        page_buf = get_words_from_list(xs=page_buf)

        if to_screen:
            self.logger.info(page_buf)
        else:
            directory = path + '/flash_dump/'
            if not os.path.exists(directory):
                os.makedirs(directory)
            filename = '{0}_{1}'.format(file_base_name, page_address)
            with open(directory + filename, 'w+') as f:
                f.write(page_buf)
            self.logger.info("Dumped page {0} to file {1}".format(page_address, directory + filename))

    def save_page(self, page_address, to_screen=False):
        """Dumps the selected page to the screen/logfile."""
        data = self.flash_read_page(page_address, self.ecc_on())
        self._dump_page(data, 0, to_screen=to_screen)

    def get_page_zero(self, ic=FlashSelectICOpcode.FLASH_IC1):
        self.set_flash_select_ic(ic)
        data = self.flash_read_page(0, self.ecc_on())
        self.set_flash_select_ic(FlashSelectICOpcode.FLASH_IC1)
        return data

    def get_bitfile_locations(self, verbose=False, ic=FlashSelectICOpcode.FLASH_IC1, page0=None):
        """Returns the locations of the various bitfiles."""
        if page0 is None:
            data = self.get_page_zero()
        else:
            data = page0

        bitfile_raw = int.from_bytes(data[0:4], 'big')
        scrubfile_raw = int.from_bytes(data[12:12 + 4], 'big')
        goldfile_raw = int.from_bytes(data[24:24 + 4], 'big')

        bitfile_page = bitfile_raw >> 8
        scrubfile_page = scrubfile_raw >> 8
        goldfile_page = goldfile_raw >> 8

        bitfile_block = bitfile_page // PAGE_PER_BLOCK
        scrubfile_block = scrubfile_page // PAGE_PER_BLOCK
        goldfile_block = goldfile_page // PAGE_PER_BLOCK

        if verbose:
            self.logger.info(f"Default         on page 0x{bitfile_page:06X}, block 0x{bitfile_block:04X}")
            self.logger.info(f"Scrub default   on page 0x{scrubfile_page:06X}, block 0x{scrubfile_block:04X}")
            self.logger.info(f"Gold            on page 0x{goldfile_page:06X}, block 0x{goldfile_block:04X}")

        return bitfile_block, scrubfile_block, goldfile_block

    def get_default_block_location(self, ic=FlashSelectICOpcode.FLASH_IC1, page0=None):
        default_block, _, _ = self.get_bitfile_locations(ic=ic, page0=page0)
        return default_block

    def get_golden_block_location(self, ic=FlashSelectICOpcode.FLASH_IC1, page0=None):
        _, _, golden_block = self.get_bitfile_locations(ic=ic, page0=page0)
        return golden_block

    def get_scrub_block_location(self, ic=FlashSelectICOpcode.FLASH_IC1, page0=None):
        _, scrub_block, _, = self.get_bitfile_locations(ic=ic, page0=page0)
        return scrub_block

    def test_readback(self, block=0x300):
        """
        Test readback of page 0 in a block.
        :return: None
        """

        self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_DISABLE)

        address = block * PAGE_PER_BLOCK
        my_seed = random.randint(15485867, 654188383)  # for repeatability
        self.logger.info(f"Random seed for flash random data: {my_seed}")
        random.seed(my_seed)
        # entropy of around ~~ 5.54345
        my_randoms = random.sample(list(range(0xff + 1)) * 17, 0x1000)

        assert len(my_randoms) == 0x1000

        self.flash_write_data(data=my_randoms, start_block=block)

        ret_data = self.flash_read_page(address)
        self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_ENABLE)

        for cnt, t in enumerate(zip(my_randoms, ret_data)):
            a, b = t
            if a != b:
                self.logger.error(f"Mismatch in data {cnt} {a} {b}")
                break
        else:
            self.logger.info("Flash readback test successful.")
        self.logger.info(list(zip(my_randoms, ret_data))[0:10])

    def _speed_test(self):
        """Tests the spead of raw reads from page 0."""
        t0_n = time.monotonic()
        n = 20
        for _ in range(n):
            self.flash_read_page(0)
        t1_n = time.monotonic()
        ds = t1_n - t0_n
        bps = (n + 1) * 4096 / ds
        self.logger.info(f"Done reading {n + 1} pages in {ds} seconds\n"
                         f" for a speedy total of {bps} bytes per second.")

    def flash_verify_file(self, filename, start_block, ECC=True, override_page_size=False, chip_num=0):
        """Verifies a bitfile written to flash.
            ECC is not verified.
        """
        print(f"block: {hex(start_block)}")
        print(f"ecc: {ECC}")
        print(f"chip_num: {hex(chip_num)}")

        page_size_actual = self._get_page_size(ECC)
        with open(os.path.realpath(filename), 'rb') as infile:
            data = bytearray(infile.read())
        self.logger.debug(
            "Data length is {} with {} pages or {} blocks".format(len(data), len(data) / (page_size_actual),
                                                                  len(data) / (page_size_actual * PAGE_PER_BLOCK)))
        self.flash_verify_data(data, start_block, ECC, override_page_size=override_page_size, chip_num=chip_num)

    def flash_write_file(self, filename, start_block, ECC=True, use_ultrascale_fifo=False, ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Write a binary file to flash
        """
        if ECC:
            page_size = PAGE_SIZE_ECC
        else:
            page_size = PAGE_SIZE
        with open(os.path.realpath(filename), 'rb') as infile:
            data = bytearray(infile.read())
        self.logger.debug(
            "Data length is {} with {} pages or {} blocks".format(len(data), len(data) / (page_size),
                                                                  len(data) / (page_size * PAGE_PER_BLOCK)))

        self.flash_write_data(data, start_block, ECC, use_ultrascale_fifo=use_ultrascale_fifo, ic=ic)

    def generate_and_write_all_firmware(self, bitfile_name, bitfile_block, scrubfile_block):
        """Generates all bitfiles and loads them to flash."""
        warnings.warn("This function will be removed in the near future", PendingDeprecationWarning)
        ok = self._write_warning()
        if not ok:
            return
        self.logger.info("Starting generation and writing of bitfiles...")
        self.logger.info("Please be patient, this might take a while.")
        s = Scrub()
        scrubfile_name = s.generate_scrubbing_file(bitfile_name)
        self.logger.info("Generated blind scrubbing file " + scrubfile_name)
        # Make ECC bit-and blind-scrubbing -file
        bitfile_ecc = make_ecc_file(bitfile_name)  # first,
        scrubfile_ecc = make_ecc_file(scrubfile_name)

        self.write_config_and_scrubbing_file(ecc_bitfile=bitfile_ecc, ecc_scrubfile=scrubfile_ecc,
                                             bitfile_block=bitfile_block, scrubfile_block=scrubfile_block, skipwarn=ok,
                                             update_param=True)

        self.update_parameter_page(bitfile_block, scrubfile_block)
        self.logger.info("Bitfiles and parameter file written to flash.")

    def write_config_and_scrubbing_file(self, ecc_bitfile, ecc_scrubfile, bitfile_block, scrubfile_block,
                                        skipwarn=False, update_param=False, use_ultrascale_fifo=False,
                                        ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Writes the bitfile and scrubfile to flash and alternatively updates the parameter page"""
        warnings.warn("This function will be removed in the near future", PendingDeprecationWarning)
        if not skipwarn:
            ok = self._write_warning()
            if not ok:
                return
        self.flash_write_file(ecc_bitfile, bitfile_block, use_ultrascale_fifo=use_ultrascale_fifo, ic=ic)
        self.flash_write_file(ecc_scrubfile, scrubfile_block, use_ultrascale_fifo=use_ultrascale_fifo, ic=ic)
        if update_param:
            self.update_parameter_page(bitfile_block, scrubfile_block, ic=ic)

    def update_parameter_page(self, bitfile_block, scrubfile_block, goldfile_block=None, ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Update the parameter page in flash"""
        timestr = time.strftime("%Y-%m-%d-%H_%M")
        if goldfile_block is None:
            _, _, goldfile_block = self.get_bitfile_locations()
            self.logger.info(f"No gold file block given, using current flash value gold : {goldfile_block:#04x}")

        if goldfile_block > BLOCK_COUNT:
            goldfile_block = 0
            self.logger.info("Gold image pointer is invalid, setting it to 0.")

        paramfile_dir = "logs/paramfiles"
        if not os.path.exists(paramfile_dir):
            os.makedirs(paramfile_dir)
        paramfile_name = paramfile_dir + "/paramfile_autogen" + timestr + ".bit"
        _, parameters = make_parameter_file_and_ecc(paramfile_name=paramfile_name,
                                                 startblock=bitfile_block,
                                                 scrubstartblock=scrubfile_block,
                                                 goldstartblock=goldfile_block,
                                                 verbose=False)
        self.logger.info(f"Update parameter page - [0x{bitfile_block:04X},0x{scrubfile_block:04X},0x{goldfile_block:04X}]")
        self.flash_write_data(data=parameters, start_block=0, ECC=True, use_ultrascale_fifo=False, ic=ic)

    def _write_warning(self):
        """Method for displaying a console warning with a decision"""
        cc = input("Warning: This will write files to the flash. Continue? (c or n cancels)\n")
        if cc.lower() in ['c', 'n']:
            self.logger.info("Writing cancelled.")
            return False
        else:
            return True

    def find_bad_blocks(self) -> Dict[int, List[int]]:
        """Scan both chips to get bad blocks"""
        bad_blocks = {}
        for ic, flash_device in zip([0b01, 0b10], [0, 1]):
            self.set_flash_select_ic(ic)
            data = self._find_bad_blocks()
            bad_blocks[flash_device] = data
        return bad_blocks

    def _find_bad_blocks(self) -> List[int]:
        """Bad block info is in page 0 or 1 of every block, located at byte no 0x1000"""
        self.set_flash_page_size(0x1001)
        self.disable_ecc()  # clears ecc errors, clears read buffer of size 256
        bad_blocks = []

        page_addresses = [page + offset for page
                          in range(0x40, 2 ** 13 * 0x40, 0x40)
                          for offset in [0, 1]
                         ]

        page_range = range(0, 0x1000 // 256)  # len = 16, max = 15 [0,16)
        self.disable_ecc()  # the first one of these will affect trx size
        self.set_flash_page_size(0x1001)  # trying to compensate for fw "effects"
        for page in page_addresses:  # loop all blocks [0,0x1000) = [0,256*16)
            # write address. and read123
            self.disable_ecc()  # make sure that we are zeroed.
            self.set_flash_address(whole_address=page)
            self.write_reg(Pa3Register.FLASH_CTRL, FlashCmdOpcode.PAGE_READ | EXEC)  # read page cmd
            for _ in page_range:  # loop single page, order is critical
                while self.read_reg(Pa3Register.FIFO_STATUS) & 0xf == 8:
                    pass
                self.disable_ecc()  # make sure that we are zeroed.
            # exit page loop to read final bytes
            data = self.read_reg(Pa3Register.FIFO_DATA_RD)  # get 1 byte, automatically skip ecc bytes
            if data != 0x00:
                block_address = page // 0x40
                bad_blocks.append(block_address)
        self.logger.info(f"Bad blocks data: \n{[hex(x) for x in bad_blocks]}")
        return bad_blocks


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def get_words_from_list(xs, word_grouping=4, group_grouping=4, **kwargs) -> str:
    """
    Group string with words grouped in firstformat and groups grouped in second format with their respective separators and group sizes
    Ex. get_words_from_list([1,2,3,4,1,2,3,4], word_grouping=2, group_grouping=2, group_sep=" -- ", firstformat=lambda x:f"{x:X}") -> "0x12 0x34 -- 0x12 0x34 -- "

    :return: str

    :param xs: list of iterables

    :param int word_grouping: how many iterables in a word

    :param int group_grouping: how many words in a group (separated by group_sep)

    :param kwargs: firstformat (lambda x: f"{x:02X}"), secondformat (lambda x: "0x" + "".join(x)), word_sep (" "), group_sep (newline)

    """
    # config:
    firstformat = kwargs.get("firstformat", lambda x: f"{x:02X}", )
    secondformat = kwargs.get("secondformat", lambda x: "0x" + "".join(x))
    word_sep = kwargs.get("word_sep", " ")
    group_sep = kwargs.get("group_sep", "\n")

    # logic:
    first_format = map(firstformat, xs)
    joined_words = map(secondformat, grouper(first_format, word_grouping, fillvalue=""))
    joined_groups = map(lambda x: word_sep.join(x) + group_sep, grouper(joined_words, group_grouping, fillvalue=""))
    output_string = "".join(joined_groups)
    return output_string
