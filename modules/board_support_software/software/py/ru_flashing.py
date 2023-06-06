""" Methods of class XCKU used for Flash chip programming
"""
import os
import json

from proasic3_enums import FlashSelectICOpcode
from cru_swt_communication import CruSwtCommunication
from flx_swt_communication import FlxSwtCommunication


def flash_write_configfile_to_block(
    self,
    filename,
    block,
    use_ultrascale_fifo=True,
    ic=FlashSelectICOpcode.FLASH_BOTH_IC,
):
    """Write a XCKU configuration file to flash chip

    Parameters
    ----------
    filename : str
        Path to config bitfile with ECC
    block : int
        Starting block address of the image location to be written
    use_ultrascale_fifo : bool, optional
        Specifies if communication channel is via XCKU or SCA, by default True
        WARNING: via SCA is extremely slow and should only be used if XCKU communication is unavailable
    ic : FlashSelectICOpcode, optional
        Specifies which flash chip (1, 2 or both) to program, by default FlashSelectICOpcode.FLASH_BOTH_IC
    """
    bf_size = 24690880
    assert (
        os.path.getsize(filename) == bf_size
    ), f"Incorrect file size: please check {filename}"
    self.flash_write_file_to_block(filename, block, use_ultrascale_fifo, ic)


def flash_write_scrubfile_to_block(
    self,
    filename,
    block,
    use_ultrascale_fifo=True,
    ic=FlashSelectICOpcode.FLASH_BOTH_IC,
):
    """Write a XCKU scrubbing file to flash chip

    Parameters
    ----------
    filename : str
        Path to scrubbing bitfile with ECC
    block : int
        Starting block address of the image location to be written
    use_ultrascale_fifo : bool, optional
        Specifies if communication channel is via XCKU or SCA, by default True
        WARNING: via SCA is extremely slow and should only be used if XCKU communication is unavailable
    ic : FlashSelectICOpcode, optional
        Specifies which flash chip (1, 2 or both) to program, by default FlashSelectICOpcode.FLASH_BOTH_IC
    """
    bs_size = 18884960
    assert (
        os.path.getsize(filename) == bs_size
    ), f"Incorrect file size: please check {filename}"
    self.flash_write_file_to_block(filename, block, use_ultrascale_fifo, ic)


def flash_write_file_to_block(
    self,
    filename,
    block,
    use_ultrascale_fifo=True,
    ic=FlashSelectICOpcode.FLASH_BOTH_IC,
):
    """Write any type of file (config, scrubbing, ecc or not) to flash chip location

    Parameters
    ----------
    filename : str
        Path to file to be written
    block : int
        Starting block address of the image location to be written
    use_ultrascale_fifo : bool, optional
        Specifies if communication channel is via XCKU or SCA, by default True
        WARNING: via SCA is extremely slow and should only be used if XCKU communication is unavailable
    ic : FlashSelectICOpcode, optional
        Specifies which flash chip (1, 2 or both) to program, by default FlashSelectICOpcode.FLASH_BOTH_IC
    """
    assert block != 0, f"Block cannot be zero, that is the parameter page"
    assert block % 0x100 == 0, f"Block must be multiple of 0x100"

    gbt_channel = self.get_gbt_channel()
    file_size = os.path.getsize(filename)

    # If SWT is available, use optimized write function, x15 faster
    if isinstance(self.comm, CruSwtCommunication):
        self.sc_core_reset(
            ultrascale_write_f=self.pa3fifo.write_data_to_fifo_opt, reset_force=True
        )
    elif isinstance(self.comm, FlxSwtCommunication):
        self.sc_core_reset(
            ultrascale_write_f=self.pa3fifo.write_data_to_fifo_opt_flx, reset_force=True
        )
    else:
        self.sc_core_reset(
            ultrascale_write_f=self.pa3fifo.write_data_to_fifo, reset_force=True
        )

    if use_ultrascale_fifo:
        self.pa3fifo.reset_fifo()
        self.pa3fifo.reset_counters()

    try:
        self.pa3.flash_write_file(
            filename=filename,
            start_block=block,
            use_ultrascale_fifo=use_ultrascale_fifo,
            ic=ic,
        )
        if use_ultrascale_fifo:
            write_cnt = self.pa3fifo._read_write_counter(False)
            read_cnt = self.pa3fifo._read_read_counter(False)
            assert (write_cnt % 2**16) == (
                file_size / 2 % 2**16
            ), f"RU {gbt_channel}: Incorrect number of words written to Ultrascale-to-PA3 FIFO {write_cnt % 2**16}, expected {file_size/2 % 2**16}"
            assert (read_cnt % 2**16) == (
                file_size % 2**16
            ), f"RU {gbt_channel}: Incorrect number of words read from Ultrascale-to-PA3 FIFO {read_cnt % 2**16}, expected {file_size % 2**16}"
            ovf_cnt = self.pa3fifo._read_overflow_counter(False)
            assert (
                ovf_cnt == 0
            ), f"RU {gbt_channel}: Ultrascale-to-PA3 FIFO overflow {ovf_cnt}"
            uvf_cnt = self.pa3fifo._read_underflow_counter(False)
            assert (
                uvf_cnt == 0
            ), f"RU {gbt_channel}: Ultrascale-to-PA3 FIFO underflow {uvf_cnt}"
    except Exception as e:
        self.logger.error("Flash File Write Failed!")
        self.logger.error(e)
        raise Exception("Flash File Write Failed!")


def flash_bitfiles_to_block(
    self,
    filename,
    blocks=[None, None],  # config and scrub block
    force_update_param=True,
    golden=False,
    use_ultrascale_fifo=True,
    force_overwrite=False,
    ic=FlashSelectICOpcode.FLASH_BOTH_IC,
):

    filename_ecc, filename_bsecc = _get_bitfile_names(filename=filename)
    blocks_changed = False

    current_bit, current_scrub, current_gold = self.pa3.get_bitfile_locations(ic=ic)

    # If desired blocks are not specified, use current
    if None in blocks:
        if not golden:
            blocks[0] = current_bit
            blocks[1] = current_scrub
            self.logger.info(
                f"Got blocks from current parameter page [0x{blocks[0]:04X}, 0x{blocks[1]:04X}]"
            )
        else:
            blocks[0] = current_gold
            self.logger.info(
                f"Got blocks from current parameter page [0x{blocks[0]:04X}]"
            )
    else:
        if not golden:
            if blocks[0] != current_bit or blocks[1] != current_scrub:
                blocks_changed = True
        else:
            if blocks[0] != current_gold:
                blocks_changed = True

    # Check if position is invalid, and automatically chose new if invalid
    new_blocks = self._check_block_validity(
        blocks, [current_bit, current_scrub], [current_gold], golden, force_overwrite
    )
    if new_blocks != blocks:
        blocks_changed = True
        blocks = new_blocks
    # Check if chosen blocks are in bad blocks list, and automatically chose new blocks
    new_blocks = self._check_bad_block_list(
        ic, blocks, [current_bit, current_scrub], [current_gold], golden
    )
    if new_blocks != blocks:
        blocks_changed = True
        blocks = new_blocks

    self.logger.info(
        f"""Flashing bitfile to {'golden ' if golden else ''}block 0x{blocks[0]:04X}"""
    )
    try:
        self.flash_write_configfile_to_block(
            filename=filename_ecc,
            block=blocks[0],
            use_ultrascale_fifo=use_ultrascale_fifo,
            ic=ic,
        )
    except Exception as e:
        print(e)
        self.logger.error(f"Could not flash bitfile on block 0x{blocks[0]:04X}")
        exit(1)

    if not golden:
        self.logger.info(f"""Flashing scrubfile to block 0x{blocks[1]:04X}""")
        try:
            self.flash_write_scrubfile_to_block(
                filename=filename_bsecc,
                block=blocks[1],
                use_ultrascale_fifo=use_ultrascale_fifo,
                ic=ic,
            )
        except Exception as e:
            print(e)
            self.logger.error(f"Could not flash scrubfile on block 0x{blocks[1]:04X}")
            exit(1)

    # Update parameter
    if force_update_param or blocks_changed:
        if golden:
            self.pa3.flash_update_parameter_page(
                bitfile_block=current_bit,
                scrubfile_block=current_scrub,
                goldfile_block=blocks[0],
                ic=ic,
            )
        else:
            self.pa3.flash_update_parameter_page(
                bitfile_block=blocks[0],
                scrubfile_block=blocks[1],
                goldfile_block=current_gold,
                ic=ic,
            )


def flash_bitfiles_to_all_blocks(
    self,
    filename,
    blocks=[None, None],
    goldblock=[None],
    force_update_param=True,
    use_ultrascale_fifo=True,
    force_overwrite=False,
    ic=FlashSelectICOpcode.FLASH_BOTH_IC,
):

    self.logger.info(f"###############################################")
    self.logger.info(f"Preparing flashing of default and golden blocks")

    self.flash_bitfiles_to_block(
        filename, blocks, False, False, use_ultrascale_fifo, force_overwrite, ic=ic
    )
    self.flash_bitfiles_to_block(
        filename, goldblock, False, True, use_ultrascale_fifo, force_overwrite, ic=ic
    )
    if force_update_param:
        self.pa3.flash_update_parameter_page(blocks[0], blocks[1], goldblock[0], ic=ic)

    self.logger.info(f"Completed flashing of all blocks!")


def _get_bitfile_names(filename):
    """Properly formats the bitfile filenames for flashing"""
    filename = filename.replace(".bit", "")
    filename = filename.replace("_ecc", "")
    filename = filename.replace("_bs", "")
    filename_ecc = filename + "_ecc.bit"
    filename_bsecc = filename + "_bs_ecc.bit"
    assert os.path.isfile(os.path.realpath(filename_ecc)), "File not found {0}".format(
        filename_ecc
    )
    assert os.path.isfile(
        os.path.realpath(filename_bsecc)
    ), "File not found {0}".format(filename_bsecc)
    return filename_ecc, filename_bsecc


def _check_block_validity(
    self, blocks, current_default, current_golden, golden, force_overwrite=False
):
    used_blocks = blocks + current_default + current_golden
    for i, block in enumerate(blocks):
        # Is the block the parameter page or is the block not multiple of 0x100?
        if block == 0 or block % 0x100:
            new_block = _get_new_available_block(blocks_to_check_list=used_blocks)
            self.logger.warning(
                f"Bitfile position 0x{block:04X} is invalid, setting it to 0x{new_block:04X}"
            )
            blocks[i] = new_block

    # Check that the two chosen blocks are not identical,
    # not relevant for golden, as there are no scrub image
    if not golden:
        if blocks[0] == blocks[1]:
            blocks[1] = _get_new_available_block(blocks_to_check_list=used_blocks)

    # Check if overwriting other type
    overlap = False
    if not golden:
        for i, block in enumerate(blocks):
            if block in current_golden:
                self.logger.warning(
                    f"Default bitfile position 0x{block:04X} same as golden bitfile position in flash"
                )
                overlap = True
    else:
        for block in blocks:
            if block in current_default:
                self.logger.warning(
                    f"Golden position 0x{block:04X} same as default bitfile position in flash"
                )
                overlap = True

    assert not overlap or (
        overlap and force_overwrite
    ), "Overlap in bitfile positions, see warning before traceback for more \
                                                            information, provide force_overwrite=True to continue"
    return blocks


def _get_new_available_block(blocks_to_check_list, start_block=0x100):
    new_bitfile_block = start_block
    while new_bitfile_block in blocks_to_check_list:
        new_bitfile_block += 0x100
    return new_bitfile_block


def json_keys2int(x):
    """Hook for converting str key to int"""
    if isinstance(x, dict):
        return {int(k): v for k, v in x.items()}
    return x


def load_bad_block_lut_json(filename):
    # Check if status file exists
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
    if os.path.exists(path):
        with open(path, "r") as infile:
            json_data = json.load(infile, object_hook=json_keys2int)
    else:
        raise Exception("No LUT for bad blocks exists!")
    return json_data


def load_2_1_bad_block_luts():
    sn2bb_lut_manual_c1 = load_bad_block_lut_json("sn2bb_lut_manual_c1.json")
    sn2bb_lut_manual_c2 = load_bad_block_lut_json("sn2bb_lut_manual_c2.json")
    sn2bb_lut_c1 = load_bad_block_lut_json("sn2bb_lut_c1.json")
    sn2bb_lut_c2 = load_bad_block_lut_json("sn2bb_lut_c2.json")
    return sn2bb_lut_manual_c1, sn2bb_lut_manual_c2, sn2bb_lut_c1, sn2bb_lut_c2


def load_2_0_bad_block_luts():
    sn2bb_lut_2_0_manual = load_bad_block_lut_json("sn2bb_lut_2_0_manual.json")
    sn2bb_lut_2_0_c1 = load_bad_block_lut_json("sn2bb_lut_2_0_c1.json")
    sn2bb_lut_2_0_c2 = load_bad_block_lut_json("sn2bb_lut_2_0_c2.json")
    return sn2bb_lut_2_0_manual, sn2bb_lut_2_0_c1, sn2bb_lut_2_0_c2


def load_1_1_bad_block_luts():
    sn2bb_lut_1_1_manual = load_bad_block_lut_json("sn2bb_lut_1_1_manual.json")
    sn2bb_lut_1_1_c1 = load_bad_block_lut_json("sn2bb_lut_1_1_c1.json")
    sn2bb_lut_1_1_c2 = load_bad_block_lut_json("sn2bb_lut_1_1_c2.json")
    return sn2bb_lut_1_1_manual, sn2bb_lut_1_1_c1, sn2bb_lut_1_1_c2


def get_bad_blocks(self, ic=FlashSelectICOpcode.FLASH_BOTH_IC, manual=True):
    """Returns the list of bad blocks in the flash memory from the lut"""
    try:
        sn = self.identity.get_sn()
    except Exception:
        self.logger.warning("Could not get RU SN, returning empty bad blocks list")
        return []
    bb_list = []

    # Load bad block LUT from JSON files
    (
        sn2bb_lut_manual_c1,
        sn2bb_lut_manual_c2,
        sn2bb_lut_c1,
        sn2bb_lut_c2,
    ) = load_2_1_bad_block_luts()
    sn2bb_lut_2_0_manual, sn2bb_lut_2_0_c1, sn2bb_lut_2_0_c2 = load_2_0_bad_block_luts()
    sn2bb_lut_1_1_manual, sn2bb_lut_1_1_c1, sn2bb_lut_1_1_c2 = load_1_1_bad_block_luts()

    if sn is not None:
        if self.ru_main_revision == 2 and self.ru_minor_revision == 1:
            if (
                ic == FlashSelectICOpcode.FLASH_IC1
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_c1.keys():
                    bb_list.extend(sn2bb_lut_c1[sn])
                else:
                    self.logger.debug("Bad blocks for ic 0 not in bad block LUT")
            if (
                ic == FlashSelectICOpcode.FLASH_IC2
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_c2.keys():
                    bb_list.extend(sn2bb_lut_c2[sn])
                else:
                    self.logger.debug("Bad blocks for ic 1 not in bad block LUT")
            if manual and (
                ic == FlashSelectICOpcode.FLASH_IC1
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_manual_c1.keys():
                    bb_list.extend(sn2bb_lut_manual_c1[sn])
            if manual and (
                ic == FlashSelectICOpcode.FLASH_IC2
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_manual_c2.keys():
                    bb_list.extend(sn2bb_lut_manual_c2[sn])
        elif self.ru_main_revision == 2 and self.ru_minor_revision == 0:
            if (
                ic == FlashSelectICOpcode.FLASH_IC1
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_2_0_c1.keys():
                    bb_list.extend(sn2bb_lut_2_0_c1[sn])
                else:
                    self.logger.debug("Bad blocks for ic 0 not in bad block LUT")
            if (
                ic == FlashSelectICOpcode.FLASH_IC2
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_2_0_c2.keys():
                    bb_list.extend(sn2bb_lut_2_0_c2[sn])
                else:
                    self.logger.debug("Bad blocks for ic 1 not in bad block LUT")
            if manual:
                if sn in sn2bb_lut_2_0_manual.keys():
                    bb_list.extend(sn2bb_lut_2_0_manual[sn])
        elif self.ru_main_revision == 1 and self.ru_minor_revision == 1:
            if (
                ic == FlashSelectICOpcode.FLASH_IC1
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_1_1_c1.keys():
                    bb_list.extend(sn2bb_lut_1_1_c1[sn])
                else:
                    self.logger.debug("Bad blocks for ic 0 not in bad block LUT")
            if (
                ic == FlashSelectICOpcode.FLASH_IC2
                or ic == FlashSelectICOpcode.FLASH_BOTH_IC
            ):
                if sn in sn2bb_lut_1_1_c2.keys():
                    bb_list.extend(sn2bb_lut_1_1_c2[sn])
                else:
                    self.logger.debug("Bad blocks for ic 1 not in bad block LUT")
            if manual:
                if sn in sn2bb_lut_1_1_manual.keys():
                    bb_list.extend(sn2bb_lut_1_1_manual[sn])
        else:
            self.logger.debug(
                f"Bad blocks for RUv{self.ru_main_revision}.{self.ru_minor_revision} not in bad block LUT"
            )
    return sorted(list(set(bb_list)))  # Remove duplicates and sort for display purposes


def _check_bad_block_list(self, ic, blocks, current_default, current_golden, golden):
    """Checks if the blocks passed as input are good or bad"""
    bad_blocks = self.get_bad_blocks(ic)
    if bad_blocks is not None:
        if blocks[0] in bad_blocks:
            self.logger.warning(
                f"bitfile_block 0x{blocks[0]:04X} in bad_blocks list [{','.join(f'0x{x:04X}' for x in bad_blocks)}]"
            )
            blocks[0] = _get_new_available_block(
                blocks_to_check_list=bad_blocks
                + blocks
                + current_default
                + current_golden,
                start_block=blocks[0] + 0x100,
            )
            self.logger.warning(
                f"bitfile_block changed to next available multiple of 0x0100 at 0x{blocks[0]:04X}"
            )
        if not golden:
            if blocks[1] in bad_blocks:
                self.logger.warning(
                    f"scrubfile_block 0x{blocks[1]:04X} in bad_blocks list [{','.join(f'0x{x:04X}' for x in bad_blocks)}]"
                )
                blocks[1] = _get_new_available_block(
                    blocks_to_check_list=bad_blocks
                    + blocks
                    + current_default
                    + current_golden,
                    start_block=blocks[1] + 0x100,
                )
                self.logger.warning(
                    f"scrubfile_block changed to next available multiple of 0x0100 at 0x{blocks[1]:04X}"
                )
    return blocks
