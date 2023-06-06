""" Implementation of classes used to keep track of scrubbing status, based on flash chip and block address aka scrubbing location.

Nomenclature:

Scrubbing image:    A binary file used by the PA3 FPGA to scrub (aka reprogram) the XCKU configuration memory.
Image location:     An address to a specific block on a specific Flash IC on a specific RU. The block is the start block
                        of the scrubbing image, but the scrubbing image is programmed over multiple blocks on the flash chip.
"""

import logging
import json
from enum import IntEnum, unique

# Threshold for setting image status to CRITICAL upon SB errors
MAX_ALLOWED_SB_ERRORS = 10
# Above this threshold, a block location is determined as bad i.e. FATAL
MAX_ALLOWED_REPROGRAM_TRIES = 50


@unique
class ImageStatus(IntEnum):
    """Possible scrubbing status values for an image location"""

    OK = 0  # Scrubbing succeeded without errors, or never attempted
    WARNING = 1  # SB errors (but below threshold) detected in the previous scrub cycle
    CRITICAL = 2  # SB errors > threshold, DB errors or CRC mismatch detected in the previous scrub cycle - must be reprogrammed
    FATAL = 3  # Bad block detected during reprogram attempt or reprogram attemptet > threshold. Not to be used anymore - i.e. no more reprogram
    NOT_PROGRAMMED = 4  # Only defined, not yet programmed


@unique
class RUStatus(IntEnum):
    """Possible scrubbing status values for an RU"""

    OK = 0  # All images are either OK or WARNING
    WARNING = 1  # 1 or more images are CRITICAL/FATAL
    FATAL = 2  # All images are CRITICAL/FATAL
    NOT_LOADED = 3  # Is not loaded


class Location(object):
    """Address to location of a scrubbing image

    Attributes
    ----------
    ic : int
        The Flash IC identifier where the image exists
    start_block : int
        The block address of the start of the image
    """

    def __init__(self, ic, start_block):
        """
        Parameters
        ----------
            ic : int
                The Flash IC identifier where the image exists
            start_block : int
                The block address of the start of the image
        """
        self._ic = ic
        if type(start_block) == str:
            self._start_block = int(start_block, 0)
        else:
            self._start_block = start_block

    def __str__(self):
        return json.dumps(
            {"ic": self._ic, "start_block": hex(self._start_block)}, indent=4
        )

    @property
    def ic(self):
        """The Flash IC identifier where the image exists"""
        return self._ic

    @property
    def start_block(self):
        """The block address of the start of the image"""
        return self._start_block


class ImageLocationStatus(object):
    """Holds current scrubbing status + scrubbing statistics of an image location

    Properties
    ----------
    location : Location
        Address to location of a scrubbing image
    programmed_fw_version : str
        FW version image currently programmed on location - currently not used
    image_status : ImageStatus
        Current image status

    Methods
    ----------
    load_json(json_data)
        Parses JSON file and updates object attributes accordingly
    update_status(sb_error:bool, sb_errors:int, db_error:bool, crc_error:bool)
        Update the image location status after a read
    update_status_dict(status:dict)
        Update the image location status after a read
    is_not_programmed()
        Returns True if location is not programmed yet
    is_fatal()
        Returns True if location image status is Fatal
    is_critical()
        Returns True if location image status is Critical
    is_warning()
        Returns True if location image status is Warning
    is_ok()
        Returns True if location image status is OK
    is_enabled()
        Returns True if location is enabled
    is_safe_for_scrubbing()
        Returns True if location is safe for scrubbing
    is_page0()
        Returns True if location originates from page0 parameters

    Hidden attributes
    -----------------
    _enabled : boolean (default: True)
        Used for manual control via file intervention, e.g. disabling non-page 0 blocks
    _page0 : boolean (default: True)
        If true, location originates from page0 configuration. Required to be true if we use old (< v02.0D) PA3 firmware with the location.
    _total_num_reads : int
        Total number of reads ever done of this image location
    _num_reads_since_reprogram : int
        The number of reads done of this image location since it was last (re)programmed
    _num_reprogram_retries : int
        The total number of reprograms executed on this image location
    _total_num_sb_errors : int
        The total number of SB errors ever observed
    _total_num_db_errors : int
        The total number of DB errors ever observed
    _total_num_crc_errors : int
        The total number of CRC errors ever observed
    _reads_before_reprogram_list : list
        List of the number of reads that was done before a reprogram was required
    _pages_with_db_errors : list
        NotImplemented - List of pages where DB errors have been observed
    """

    def __init__(self):
        self.logger = logging.getLogger("ImageLocationStatus")

        self._location = None

        self._enabled = True

        self._page0 = True

        self._programmed_fw_version = ""
        self._image_status = None

        # Statistics
        self._total_num_reads = 0
        self._num_reads_since_reprogram = 0
        self._total_num_reprogram = 0
        self._num_reprogram_retries = 0
        self._total_num_sb_errors = 0
        self._total_num_db_errors = 0
        self._total_num_crc_errors = 0
        self._reads_before_reprogram_list = []
        self._pages_with_db_errors = []

    ##############
    # Properties #
    ##############

    @property
    def location(self):
        if self._location is None:
            self.logger.warning("Image location is not set")
        return self._location

    @location.setter
    def location(self, location):
        if self._location is None:
            self._location = location
        else:
            self.logger.error("Cannot change location for image")

    @property
    def programmed_fw_version(self):
        return self._programmed_fw_version

    @programmed_fw_version.setter
    def programmed_fw_version(self, fw_ver):
        self._programmed_fw_version = fw_ver

    @property
    def image_status(self):
        return self._image_status

    ###########
    # Methods #
    ###########

    def __str__(self):
        """Return JSON formatted ``str`` of self."""
        output = {
            "location": json.loads(str(self._location)),
            "enabled": self._enabled,
            "page0": self._page0,
            "programmed_fw_version": self._programmed_fw_version,
            "image_status": self._image_status,
            "total_num_reads": self._total_num_reads,
            "num_reads_since_reprogram": self._num_reads_since_reprogram,
            "total_num_reprogram": self._total_num_reprogram,
            "num_reprogram_retries": self._num_reprogram_retries,
            "total_num_sb_errors": self._total_num_sb_errors,
            "total_num_db_errors": self._total_num_db_errors,
            "total_num_crc_errors": self._total_num_crc_errors,
            "reads_before_reprogram_list": self._reads_before_reprogram_list,
            "blocks_with_db_errors": self._pages_with_db_errors,
        }
        return json.dumps(output, indent=4)

    def load_json(self, json_data):
        """Parses JSON file and updates object attributes accordingly"""
        self._location = Location(
            json_data["location"]["ic"], json_data["location"]["start_block"]
        )
        self._enabled = json_data["enabled"]
        self._page0 = json_data["page0"]
        self._programmed_fw_version = json_data["programmed_fw_version"]
        self._image_status = ImageStatus(json_data["image_status"])
        self._total_num_reads = json_data["total_num_reads"]
        self._num_reads_since_reprogram = json_data["num_reads_since_reprogram"]
        self._total_num_reprogram = json_data["total_num_reprogram"]
        self._num_reprogram_retries = json_data["num_reprogram_retries"]
        self._total_num_sb_errors = json_data["total_num_sb_errors"]
        self._total_num_db_errors = json_data["total_num_db_errors"]
        self._total_num_crc_errors = json_data["total_num_crc_errors"]
        self._reads_before_reprogram_list = json_data["reads_before_reprogram_list"]
        self._pages_with_db_errors = json_data["blocks_with_db_errors"]

    # Status methods

    def update_status(
        self, sb_error: bool, sb_errors: int, db_error: bool, crc_error: bool
    ):
        """Update the image location status after a read

        To be called following each read of the image, e.g. immediately after a test scrub cycle or a real scrub cycle.

        Parameters
        ----------
            sb_error : bool
                Was an SB error detected?
            sb_errors : int
                How many SB errors were detected?
            db_error : bool
                Was a DB error detected?
            crc_error : bool
                Was CRC error / mismatch detected?

        Returns
        -------
        boolean
            False if status changed, True if status remained the same.
        """
        # Update the read stats
        self._stat_update_read()

        old_image_status = self._image_status

        if self._image_status == ImageStatus.FATAL:
            self.logger.error("Cannot update status of image that is FATAL")
        elif crc_error:
            self.logger.warning("Image status updated: CRITICAL")
            self._image_status = ImageStatus.CRITICAL
            self._total_num_crc_errors += 1
            if self._num_reprogram_retries >= MAX_ALLOWED_REPROGRAM_TRIES:
                self.logger.warning("Image status updated: FATAL")
                self._image_status = ImageStatus.FATAL
        elif db_error:
            self.logger.warning("Image status updated: CRITICAL")
            self._image_status = ImageStatus.CRITICAL
            self._total_num_db_errors += 1
            if self._num_reprogram_retries >= MAX_ALLOWED_REPROGRAM_TRIES:
                self.logger.warning("Image status updated: FATAL")
                self._image_status = ImageStatus.FATAL
        elif sb_error:
            if sb_errors > MAX_ALLOWED_SB_ERRORS:
                self.logger.warning("Image status updated: CRITICAL")
                self._image_status = ImageStatus.CRITICAL
            else:
                self.logger.warning("Image status updated: WARNING")
                self._image_status = ImageStatus.WARNING
            self._total_num_sb_errors += sb_errors
            self._num_reprogram_retries = 0
        else:
            self.logger.info("OK")
            self._image_status = ImageStatus.OK
            self._num_reprogram_retries = 0

        if old_image_status != self._image_status:
            return False
        else:
            return True

    def update_status_dict(self, status: dict):
        """Update the image location status after a read, see ``update_status``

        Parameters
        ----------
            status : dict[sb_error, sb_errors, db_error, crc_error]

        Returns
        -------
        boolean
            False if status changed, True if status remained the same.

        """
        return self.update_status(
            status["sb_error"],
            status["sb_errors"],
            status["db_error"],
            status["crc_error"],
        )

    def is_not_programmed(self):
        return self.image_status is ImageStatus.NOT_PROGRAMMED

    def is_fatal(self):
        return self.image_status is ImageStatus.FATAL

    def is_critical(self):
        return self.image_status is ImageStatus.CRITICAL

    def is_warning(self):
        return self.image_status is ImageStatus.WARNING

    def is_ok(self):
        return self.image_status is ImageStatus.OK

    def is_enabled(self):
        return self._enabled

    def is_safe_for_scrubbing(self):
        """Returns True if image location is safe to be used for scrubbing"""
        return (self.is_ok() or self.is_warning()) and self.is_enabled()

    def is_page0(self):
        return self._page0

    # Methods to update statistics

    def _stat_update_read(self):
        """Update statistics following a read

        To be called by update_status()"""
        self._total_num_reads += 1
        self._num_reads_since_reprogram += 1

    def stat_update_reprogram(self):
        """Update statistics following a reprogram"""
        self._total_num_reprogram += 1

        self._reads_before_reprogram_list.append(self._num_reads_since_reprogram)
        self._num_reads_since_reprogram = 0

        self._num_reprogram_retries += 1


class ScrubbingRUStatus(object):
    """Holds current scrubbing status of a specific RU and each image location

    Properties
    ----------
    ru_sn : int
        Serial number of the specific RU
    ru_status : RUStatus
        The current RU scrubbing status
    ru_status_name : str
        The name of the current RU scrubbing status

    Methods
    ----------
    load_json(json_data)
        Parses JSON file and updates object attributes accordingly
    add_image_location(image_location : ImageLocationStatus)
        Adds new ImageLocationStatus object to RU list
    update_status()
        Loops over all image locations and determines current scrubbing status
    update_status_with_location_results(results : dict)
        Updates the current image location with results
    is_loaded()
        Returns True if the status has been loaded from file
    is_fatal()
        Returns True if current RU status is FATAL
    is_warning()
        Returns True if current RU status is WARNING
    is_ok()
        Returns True if current RU status is OK
    is_safe_for_scrubbing()
        Returns True if any image location of the RU is safe for scrubbing
    get_current_image_location()
        Returns the current image location, if status is loaded
    get_image_location(index : int)
        Returns the image location of ``index``
    get_all_enabled_locations()
        Returns list of all enabled locations
    get_all_safe_locations()
        Returns list of all locations that are safe for scrubbing and enabled
    get_all_critical_locations()
        Returns list of all locations that are CRITICAL and enabled
    get_all_not_programmed_locations()
        Returns list of all locations that are NOT_PROGRAMMED and enabled
    update_current_image_location()
        If the current image is not safe for scrubbing, update it with the next available location
    is_current_image_safe_for_scrubbing()
        Returns True if current image is safe for scrubbing
    """

    def __init__(self):
        self.logger = logging.getLogger("ScrubbingRUStatus")
        self._ru_sn = None

        self._ru_status = RUStatus.NOT_LOADED
        self._num_critical_images = 0

        self._image_locations = []
        self._current_image_location_index = None

    ##############
    # Properties #
    ##############

    @property
    def ru_sn(self):
        if self._ru_sn is None:
            self.logger.warning("RU SN is not set")
        return self._ru_sn

    @ru_sn.setter
    def ru_sn(self, ru_sn):
        if self._ru_sn is None:
            self._ru_sn = ru_sn
        else:
            self.logger.error("Cannot change SN for RU")

    @property
    def ru_status(self):
        return self._ru_status

    @property
    def ru_status_name(self):
        return self._ru_status.name

    ###########
    # Methods #
    ###########

    def __str__(self):
        """Return JSON formatted ``str`` of self."""
        image_status_json = []
        for image_loc in self._image_locations:
            image_status_json.append(json.loads(str(image_loc)))
        output = {
            "ru_sn": self._ru_sn,
            "ru_status": self._ru_status,
            "num_critical_images": self._num_critical_images,
            "current_image_location_index": self._current_image_location_index,
            "image_locations": image_status_json,
        }
        return json.dumps(output, indent=4)

    def load_json(self, ru_sn, json):
        """Parses JSON file and updates object attributes accordingly"""
        if ru_sn != json["ru_sn"]:
            self.logger.error("RU SN does not match JSON RU SN!")
            raise InvalidJSON
        self._ru_sn = json["ru_sn"]
        self._ru_status = RUStatus(json["ru_status"])
        self._num_critical_images = json["num_critical_images"]
        self._current_image_location_index = json["current_image_location_index"]
        for image_loc in json["image_locations"]:
            image_location_status = ImageLocationStatus()
            image_location_status.load_json(image_loc)
            self._image_locations.append(image_location_status)

    def add_image_location(self, image_location):
        """Adds new ImageLocationStatus object to RU list

        Parameters
        ----------
        image_location : ImageLocationStatus
            Location that belongs to the RU
        """
        self._image_locations.append(image_location)

    def update_status(self):
        """Loops over all image locations and determines scrubbing status.

        To be executed when an RU image location status changes
        """
        num_critical = 0
        for image_loc in self._image_locations:
            if image_loc.is_critical() or image_loc.is_fatal():
                num_critical += 1
        if num_critical >= len(self._image_locations):
            self._ru_status = RUStatus.FATAL
        elif num_critical > 0:
            self._ru_status = RUStatus.WARNING

        else:
            self._ru_status = RUStatus.OK
        self._num_critical_images = num_critical

    def update_status_with_location_results(self, results: dict):
        """Updates the current image location with results

        Parameters
        ----------
            results : dict[sb_error, sb_errors, db_error, crc_error]
        """
        self.get_current_image_location().update_status_dict(results)
        self.update_status()

    # Status getters

    def is_loaded(self):
        """Returns True if the RU SN is set, and a minimum of 1 image locations have been defined"""
        if (
            len(self._image_locations) == 0
            or self._current_image_location_index is None
            or self._ru_sn is None
        ):
            return False
        return True

    def is_fatal(self):
        return self.ru_status is RUStatus.FATAL

    def is_warning(self):
        return self.ru_status is RUStatus.WARNING

    def is_ok(self):
        return self.ru_status is RUStatus.OK

    def is_safe_for_scrubbing(self):
        return self.is_ok() or self.is_warning()

    # Current image location

    def get_current_image_location(self):
        """Returns the current image location, if status is loaded"""
        if not self.is_loaded():
            raise ScrubbingStatusNotLoaded
        return self.get_image_location(self._current_image_location_index)

    def get_image_location(self, index: int):
        """Returns the image location of ``index``"""
        if not self.is_loaded():
            raise ScrubbingStatusNotLoaded
        return self._image_locations[index]

    def get_all_enabled_locations(self):
        """Returns list of all enabled locations"""
        return [loc for loc in self._image_locations if loc.is_enabled()]

    def get_all_safe_locations(self):
        """Returns list of all locations that are safe for scrubbing and enabled"""
        return [
            loc
            for loc in self.get_all_enabled_locations()
            if loc.is_safe_for_scrubbing()
        ]

    def get_all_critical_locations(self):
        """Returns list of all locations that are CRITICAL and enabled"""
        return [loc for loc in self.get_all_enabled_locations() if loc.is_critical()]

    def get_all_not_programmed_locations(self):
        """Returns list of all locations that are NOT_PROGRAMMED and enabled"""
        return [
            loc for loc in self.get_all_enabled_locations() if loc.is_not_programmed()
        ]

    def update_current_image_location(self):
        """If the current image is not safe for scrubbing, update it with the next available location"""
        if not self.is_current_image_safe_for_scrubbing():
            self.logger.info("Current image not safe: updating image location")
            self._set_current_image_location_index(
                self._get_next_available_image_location_index()
            )

    def _set_current_image_location_index(self, index: int):
        """Set the current image to a new ``index`` in the list"""
        self._current_image_location_index = index

    def _get_next_available_image_location_index(self):
        """Loops over image location until finding OK/WARNING image"""
        for i, image_loc in enumerate(self._image_locations):
            if image_loc.is_ok() or image_loc.is_warning():
                return i
        self.logger.fatal("No OK image locations could be found")
        self._ru_status = RUStatus.FATAL
        return None  # Resets the current image location

    def is_current_image_safe_for_scrubbing(self):
        """Returns True if current image is safe for scrubbing"""
        if not self.is_loaded():
            return False
        return self.get_current_image_location().is_safe_for_scrubbing()


class ScrubbingStatusNotLoaded(Exception):
    pass


class InvalidJSON(Exception):
    pass


class InvalidLocation(Exception):
    pass


class CurrentScrubbingImageNotSafe(Exception):
    pass


class PA3FWNotMature(Exception):
    pass
