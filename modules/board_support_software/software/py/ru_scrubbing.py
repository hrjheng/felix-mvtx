""" Methods of class XCKU used for scrubbing
"""

import os
import json
import time
import signal
import re

import git_hash_lut

from proasic3_enums import FlashSelectICOpcode
from scrubbing_status import (
    ImageLocationStatus,
    ScrubbingRUStatus,
    Location,
    MAX_ALLOWED_SB_ERRORS,
    ImageStatus,
    InvalidLocation,
    ScrubbingStatusNotLoaded,
    CurrentScrubbingImageNotSafe,
    PA3FWNotMature,
)

SCRUBBING_STATUS_DIR = f"{os.path.expanduser('~')}/ITS_scrubbing_status"

# Create, load and update scrubbing status files


def create_and_store_new_scrubbing_status(
    self, from_page0=True, from_badblocksdb=False
):
    """Used to create preliminary scrubbing status files


    From page0
    - Creates scrubbing status of image locations specifeid on page 0 of flash.
    - Assumes programmed scrub image is identical to current loaded XCKU FW loaded
    - Assumes block is OK

    From badblocksdb
    - Create scrubbing status of image locations of all potential blocks, i.e.
    not already used on page 0 and not in bad blocks database for given chip
    - Assumes image has not been programmed yet, not to be used before programming

    RU status
    - Sets the scrubbing location to first available
    """
    ru_sn = self.get_sn()
    self.scrubbing_status = ScrubbingRUStatus()
    self.scrubbing_status.ru_sn = ru_sn

    if from_page0:
        for ic in range(1, 3):
            flash_scrub_block = self.pa3.get_scrub_block_location(ic=ic)

            scrub_image_location_status = ImageLocationStatus()

            scrub_image_location_status.location = Location(ic, flash_scrub_block)
            scrub_image_location_status.programmed_fw_version = self.git_tag()
            scrub_image_location_status._image_status = ImageStatus.OK
            scrub_image_location_status._page0 = True

            self.scrubbing_status.add_image_location(scrub_image_location_status)

    if from_badblocksdb:
        for ic in range(1, 3):
            potential_blocks = list(range(0x100, 0x2000, 0x100))

            # Remove used blocks in page0
            used_blocks = self.pa3.get_bitfile_locations(ic=ic)
            for block in used_blocks:
                potential_blocks.remove(block)
            # Remove bad blocks
            bad_blocks = self.get_bad_blocks(ic=ic)
            for block in bad_blocks:
                potential_blocks.remove(block)

            for block in potential_blocks:
                scrub_image_location_status = ImageLocationStatus()
                scrub_image_location_status.location = Location(ic, block)
                scrub_image_location_status._image_status = ImageStatus.NOT_PROGRAMMED
                scrub_image_location_status._page0 = False

                self.scrubbing_status.add_image_location(scrub_image_location_status)

    self.scrubbing_status.update_current_image_location()
    self.scrubbing_status.update_status()
    self.update_scrubbing_status_files()


def load_scrubbing_status(self, force=False):
    """Load scrubbing status from file"""
    if self.scrubbing_status is None or force:
        self.scrubbing_status = ScrubbingRUStatus()
        ru_sn = self.get_sn()

        # Check if status file exists
        if os.path.exists(f"{SCRUBBING_STATUS_DIR}/{ru_sn}.json"):
            with open(f"{SCRUBBING_STATUS_DIR}/{ru_sn}.json", "r") as infile:
                json_data = json.load(infile)
                self.scrubbing_status.load_json(ru_sn, json_data)
        else:
            self.logger.warning("No scrubbing status data exists!")
            return False
    return True


def update_scrubbing_status_files(self):
    """Update scrubbing status files"""
    assert self.scrubbing_status is not None
    ru_sn = self.get_sn()
    if not os.path.exists(SCRUBBING_STATUS_DIR):
        os.makedirs(SCRUBBING_STATUS_DIR)
    with open(f"{SCRUBBING_STATUS_DIR}/{ru_sn}.json", "w") as outfile:
        outfile.write(str(self.scrubbing_status))


# Scrub cycle configuration and execution methods


def configure_scrub_location(self, location):
    """Sets PA3 config based on the location parameter, overloaded based on type of location"""
    if type(location) is ImageLocationStatus:
        self._configure_scrub_imagelocation(location)
    elif type(location) is Location:
        self._configure_scrub_location(location)
    elif type(location) is FlashSelectICOpcode or type(location) is int:
        self._configure_scrub_location_page0(location)
    else:
        raise NotImplementedError(
            f"Function not defined for par:location of type {type(location)}"
        )


def _configure_scrub_imagelocation(self, location):
    # For safety
    self.pa3.clear_scrub_block_address()

    ic = location.location.ic
    start_block = location.location.start_block

    self.logger.info(
        f"Configuring PA3 for scrubbing with image from ImageLocationStatus on IC: {ic}, Start Block: {hex(start_block)}"
    )
    self.pa3.set_flash_select_ic(ic)
    if not location.is_page0():
        self.pa3.set_scrub_block_address(start_block)


def _configure_scrub_location(self, location):
    # For safety
    self.pa3.clear_scrub_block_address()

    ic = location.ic
    start_block = location.start_block

    self.logger.info(
        f"Configuring PA3 for scrubbing with image from Location on IC: {ic}, Start Block: {hex(start_block)}"
    )
    self.pa3.set_flash_select_ic(ic)
    self.pa3.set_scrub_block_address(start_block)


def _configure_scrub_location_page0(self, location):
    # For safety
    self.pa3.clear_scrub_block_address()

    ic = location

    self.logger.info(
        f"Configuring PA3 for scrubbing with image from page 0 on IC: {ic}"
    )
    self.pa3.set_flash_select_ic(ic)


def run_scrub_cycle(self, location=None, test=True, update_scrubbing_status_files=True):
    """Wrapper function for running scrub cycle, overloads does not work with direct access from Fire interface"""
    if location is None:
        return self._run_scrub_cycle(
            test=test, update_scrubbing_status_files=update_scrubbing_status_files
        )
    elif type(location) is ImageLocationStatus:
        return self._run_scrub_cycle_location(
            location=location,
            test=test,
            update_scrubbing_status_files=update_scrubbing_status_files,
        )
    elif type(location) is FlashSelectICOpcode or type(location) is int:
        return self._run_scrub_cycle_page0(location=location, test=test)
    else:
        raise NotImplementedError(
            f"run_scrub_cycle() not defined for par:location of type {type(location)}"
        )


def _run_scrub_cycle(self, test=True, update_scrubbing_status_files=True):

    if not self.load_scrubbing_status():
        raise ScrubbingStatusNotLoaded("Cannot scrub without scrubbing status loaded")

    self.pa3.stop_scrubbing_and_reset_on_db_error()

    if not self.scrubbing_status.is_safe_for_scrubbing():
        raise CurrentScrubbingImageNotSafe(
            "Current image is not safe - aborting scrub cycle"
        )

    image_location = self.scrubbing_status.get_current_image_location()

    if (not image_location.is_page0()) and (not self.pa3.is_pa3_fw_mature()):
        raise PA3FWNotMature("Current PA3 fw does not support custom block address")

    self.configure_scrub_location(image_location)

    if test:
        scrub_complete = self.pa3.run_single_scrub_test()
    else:
        scrub_complete = self.pa3.run_single_scrub()

    self.pa3.clear_scrub_block_address()
    success, results = self.determine_post_scrub_status()

    self.scrubbing_status.update_status_with_location_results(results)
    if update_scrubbing_status_files:
        self.update_scrubbing_status_files()

    return scrub_complete, success, results


def _run_scrub_cycle_location(
    self, location, test=True, update_scrubbing_status_files=True
):

    self.pa3.stop_scrubbing_and_reset_on_db_error()

    if not location.is_safe_for_scrubbing() and not test:
        raise CurrentScrubbingImageNotSafe(
            "Current image is not safe - aborting scrub cycle"
        )

    self.configure_scrub_location(location.location)

    if test:
        scrub_complete = self.pa3.run_single_scrub_test()
    else:
        scrub_complete = self.pa3.run_single_scrub()

    self.pa3.clear_scrub_block_address()
    success, results = self.determine_post_scrub_status()

    location.update_status_dict(results)
    if update_scrubbing_status_files:
        self.update_scrubbing_status_files()

    return scrub_complete, success, results


def _run_scrub_cycle_page0(self, location, test=True):

    self.pa3.stop_scrubbing_and_reset_on_db_error()

    self.configure_scrub_location(location)

    if test:
        scrub_complete = self.pa3.run_single_scrub_test()
    else:
        scrub_complete = self.pa3.run_single_scrub()

    success, results = self.determine_post_scrub_status()

    return scrub_complete, success, results


# Scrub loop

terminate_scrub = False


def run_scrub_loop(self, with_test=True, sleep_sec=10):
    self.logger.info("Starting scrubbing loop - end gracefully with Ctrl-C")

    # Signal handling for graceful exit
    def signal_handling(signum, frame):
        global terminate_scrub
        terminate_scrub = True

    signal.signal(signal.SIGINT, signal_handling)

    while True:

        # Load status from file each cycle, allow hacking status files with scrubbing on
        if not self.load_scrubbing_status(force=True):
            self.logger.error("Could not load scrubbing status, aborting....")
            return False

        self.logger.info("Starting scrub cycle")

        # Update RU scrub status
        self.scrubbing_status.update_status()
        self.scrubbing_status.update_current_image_location()

        # Check if RU is ok
        if not self.scrubbing_status.is_safe_for_scrubbing():
            self.logger.error("RU scrubbing status: not safe for scrubbing, exiting...")
            self.update_scrubbing_status_files()
            return False

        if with_test:
            # Scrub test and update RU scrub status
            self.logger.info("Run scrub test cycle")
            _, success, _ = self.run_scrub_cycle(
                test=True, update_scrubbing_status_files=False
            )

            if not success:
                self.logger.error("Test scrub cycle failed")
                self.update_scrubbing_status_files()
                continue  # Get new image the next cycle

            # Check if current image is fine, if not get next available
            self.scrubbing_status.update_current_image_location()

        self.pa3.smap_abort_and_verify()

        # Real scrub and update RU scrub status
        self.logger.info("Run real scrub cycle")
        _, success, _ = self.run_scrub_cycle(
            test=False, update_scrubbing_status_files=False
        )

        # Write files
        self.update_scrubbing_status_files()

        time.sleep(sleep_sec)
        self.logger.info("Scrub cycle completed")
        if terminate_scrub:
            break
    self.logger.info("Endded scrubbing loop gracefully")
    return True


# Post scrub update status methods


def get_pa3_post_scrub_metrics(self):
    """Extract post-scrub metrics from the PA3"""
    crc = self.pa3.config_controller.get_crc()
    sb_error = self.pa3.ecc.has_sb_error_occurred()
    sb_payload = self.pa3.ecc.get_ecc_sb_error_payload_counter()
    sb_ecc = self.pa3.ecc.get_ecc_sb_error_eccbits_counter()
    sb_total = sb_payload + sb_ecc
    db_error = self.pa3.ecc.has_db_error_occurred()

    return crc, sb_error, sb_payload, sb_ecc, sb_total, db_error


def determine_post_scrub_status(self):
    """Determine post-scrub status of image location based on PA3 metrics"""
    (
        crc,
        sb_error,
        sb_payload,
        sb_ecc,
        sb_total,
        db_error,
    ) = self.get_pa3_post_scrub_metrics()
    loaded_ver = self.git_tag()

    success = True
    results = {"sb_error": False, "sb_errors": 0, "db_error": False, "crc_error": False}

    if db_error:
        self.logger.warning("DB error occurred")
        results["db_error"] = True
        success = False

    # It does not make sense to register CRC error upon DB-error
    if not db_error:
        if crc in git_hash_lut.ru_scrubcrc2ver_lut:
            scrub_crc_version = git_hash_lut.ru_scrubcrc2ver_lut[crc]
            if scrub_crc_version != loaded_ver:
                self.logger.warning(
                    f"CRC mismatch, matched incorrect RU FW version: {scrub_crc_version} - Expected: {loaded_ver}"
                )
                results["crc_error"] = True
                success = False
        else:
            self.logger.warning(
                f"CRC mismatch, does not match any known RU FW version: {hex(crc)}"
            )
            results["crc_error"] = True
            success = False

    if sb_error and sb_total > 0:
        self.logger.warning(
            f"SB error(s) occurred: {sb_payload}(payload) + {sb_ecc}(ecc) = {sb_total}"
        )
        results["sb_error"] = True
        results["sb_errors"] = sb_total
        if sb_total > MAX_ALLOWED_SB_ERRORS:
            self.logger.warning("SB error threshold reached")
            success = False

    return success, results


# Checking and reflashing methods


def check_and_update_scrub_status_iter_locations(self):
    """Runs a test scrub cycle on all currently safe locations and determine its status"""
    if not self.load_scrubbing_status(force=True):
        self.logger.error("Could not load scrubbing status, aborting....")
        return False

    locations = (
        self.scrubbing_status.get_all_safe_locations()
    )  # We never retest a critical image location, as we can get mixed results

    for location in locations:
        self.run_scrub_cycle(
            location=location, test=True, update_scrubbing_status_files=True
        )


def reflash_scrub_block(self, filename, location, update_scrubbing_status_files=True):
    """Wrapper function for reflashing scrub block, overloads does not work with direct access from Fire interface"""
    if type(location) is ImageLocationStatus:
        return self._reflash_scrub_block_location(
            filename,
            location=location,
            update_scrubbing_status_files=update_scrubbing_status_files,
        )
    elif type(location) is FlashSelectICOpcode or type(location) is int:
        return self._reflash_scrub_block_page0(filename, location=location)
    else:
        raise NotImplementedError(
            f"reflash_scrub_block() not defined for par:location of type {type(location)}"
        )


def _reflash_scrub_block_location(
    self, filename, location, update_scrubbing_status_files=True
):
    self.pa3.stop_scrubbing_and_reset_on_db_error()
    scrubfile_block = location.location.start_block
    ic = location.location.ic

    pattern = "v\d+.\d+.\d+"
    fw_ver = re.search(pattern, filename).group()

    self.logger.info(f"Reflashing block {hex(scrubfile_block)} on IC #{ic}")
    self.flash_write_scrubfile_to_block(filename, scrubfile_block, ic=ic)
    location.programmed_fw_version = fw_ver
    location.stat_update_reprogram()
    if update_scrubbing_status_files:
        self.update_scrubbing_status_files()


def _reflash_scrub_block_page0(self, filename, location):
    self.pa3.stop_scrubbing_and_reset_on_db_error()
    ic = location
    scrubfile_block = self.pa3.get_scrub_block_location(ic=ic)

    self.logger.info(f"Reflashing block {hex(scrubfile_block)} on IC #{ic}")
    self.flash_write_scrubfile_to_block(filename, scrubfile_block, ic=ic)


def reflash_all_critical_locations(self, filename):
    """Reflashes all image locations marked as CRITICAL"""
    if not self.load_scrubbing_status(force=True):
        self.logger.error("Could not load scrubbing status, aborting....")
        return False

    locations = self.scrubbing_status.get_all_critical_locations()

    for location in locations:
        try:
            self.reflash_scrub_block(filename, location=location)
        except:
            location._image_status = ImageStatus.FATAL
            continue
        self.run_scrub_cycle(location=location, update_scrubbing_status_files=True)

    self.scrubbing_status.update_current_image_location()
    self.scrubbing_status.update_status()
    self.update_scrubbing_status_files()


def flash_all_not_programmed_locations(self, filename):
    """Reflashes all image locations marked as NOT_PROGRAMMED"""
    if not self.load_scrubbing_status(force=True):
        self.logger.error("Could not load scrubbing status, aborting....")
        return False

    locations = self.scrubbing_status.get_all_not_programmed_locations()

    for location in locations:
        try:
            self.reflash_scrub_block(filename, location=location)
        except:
            location._image_status = ImageStatus.FATAL
            continue
        self.run_scrub_cycle(location=location, update_scrubbing_status_files=True)

    self.scrubbing_status.update_current_image_location()
    self.scrubbing_status.update_status()
    self.update_scrubbing_status_files()


# Basic checking methods not using scrubbing status


def check_scrub_ok(
    self, use_scrub_status=False, ic=FlashSelectICOpcode.FLASH_IC1, logging=True
):
    """Determines whether scrubbing passes all checks during the test phase"""
    assert (
        ic == FlashSelectICOpcode.FLASH_IC1 or ic == FlashSelectICOpcode.FLASH_IC2
    ), f"Scrub check can only be executed on one flash chip at the time"
    self.pa3.stop_scrubbing_and_reset_on_db_error()
    if use_scrub_status:
        _, success, _ = self.run_scrub_cycle(
            test=True, update_scrubbing_status_files=True
        )
    else:
        _, success, _ = self.run_scrub_cycle(location=ic, test=True)

    if logging and success:
        self.logger.info(f"RU SN{self.identity.get_sn()} Flash {ic}: Scrub OK")
    elif not success:
        self.logger.warning(f"RU SN{self.identity.get_sn()} Flash {ic}: Scrub NOT OK")

    return success


def check_scrub_and_reflash(self, filename, ic=FlashSelectICOpcode.FLASH_IC1):
    success = self.check_scrub_ok(ic=ic)
    if not success:
        self.reflash_scrub_block(filename=filename, location=ic)
