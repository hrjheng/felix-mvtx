"""File to implement the transition board mapping in different RUs

https://twiki.cern.ch/twiki/bin/view/ALICE/ITS_WP10_Transboard"""

from enum import IntEnum, unique

@unique
class TransitionBoardVersion(IntEnum):
    """Different Transition Boards version"""
    V1_L     = 0
    V2_0     = 1
    V2_5     = 2
    V1K_2_5B = 3


def select_transition_board(ru_main_revision, transition_board_version):
    """Function to select the correct transition board"""
    assert ru_main_revision in [1,2]
    transition_board_version = TransitionBoardVersion(transition_board_version)
    if transition_board_version == TransitionBoardVersion.V1_L:
        return TransitionBoardV1L(ru_main_revision=ru_main_revision)
    elif transition_board_version == TransitionBoardVersion.V2_0:
        raise NotImplementedError
        #return TransitionBoardV20(ru_main_revision=ru_main_revision)
    elif transition_board_version == TransitionBoardVersion.V2_5:
        return TransitionBoardV25(ru_main_revision=ru_main_revision)
    elif transition_board_version == TransitionBoardVersion.V1K_2_5B:
        raise NotImplementedError
        #return TransitionBoardV25B(ru_main_revision=ru_main_revision)
    else:
        raise NotImplementedError


class TransitionBoard():
    LANES = 28
    MODULES = 7
    GPIO_CONNECTORS = 4
    """General transition board"""

    def __init__(self, version, ru_main_revision):
        self.version = version
        self.gpio_subset_map = []*self.GPIO_CONNECTORS
        self.gpio_sensor_mask = {i: None for i in range(self.LANES)}
        self.gpio_chipid2lane_lut = [None]*self.GPIO_CONNECTORS
        self.gpio_chipidext2lane_lut = [None]*self.GPIO_CONNECTORS
        self.gpio_lane2chipid_lut = {}
        self.gpio_lane2chipidext_lut = {}
        self.gpio_module2lanes_lut = {i:[] for i in range(1,self.MODULES+1)}
        self.gpio_lane2module_lut = {}

        self.verify_version(ru_main_revision)

        self._set_gpio_subset_map()
        self._set_gpio_sensor_mask()
        self._set_gpio_chipid2lane_lut()
        self._set_gpio_lane2chipid_lut()
        self._set_module2lanes_lut()
        self._set_lane2module_lut()

    def _set_gpio_subset_map(self):
        """Sets the gpio subset map
        Connector map (lanes in data for each connector)
        """
        raise NotImplementedError

    def _set_gpio_sensor_mask(self):
        """Sets the gpio sensor mask

        GPIO_SENSOR_MASK = {lane_id:one_hot_mask}
        if 0 does not mask (i.e. awaits data from this chipid[2:0])
        if 1 does not wait for those data before going to timeout.
        """
        raise NotImplementedError

    def _set_gpio_chipid2lane_lut(self):
        """List of dictionaries
        Index in list is connector,
        Dict is chipid:lane"""
        raise NotImplementedError

    def _set_gpio_lane2chipid_lut(self):
        """dictionary {lane: [chipid_list]}"""
        raise NotImplementedError

    def verify_version(self, ru_main_revision):
        """Verifies the RU main and secondary revision against the transition board compatibility"""
        raise NotImplementedError

    def check_gpio_subset_map(self):
        """General assertions for gpio subset map"""
        assert len(self.gpio_subset_map) == self.GPIO_CONNECTORS
        for ls in self.gpio_subset_map:
            assert len(ls) == self.MODULES
        tot_ls = [i for ls in self.gpio_subset_map for i in ls]
        assert len(set(tot_ls)) == len(tot_ls), "len(set(tot_ls)) = {0}, len(tot_ls) = {1}".format(len(set(tot_ls)), len(tot_ls))
        for i in range(self.LANES):
            assert i in tot_ls

    def check_gpio_sensor_mask(self):
        """General assertions for gpio sensor mask"""
        for i in range(self.LANES):
            assert i in self.gpio_sensor_mask.keys()

    def get_gpio_lane(self, chipid, connector):
        """Returns the lane relative to the connector/chipid pair"""
        assert connector in range(self.GPIO_CONNECTORS)
        assert self.gpio_chipid2lane_lut[connector] is not None
        assert chipid in self.gpio_chipid2lane_lut[connector].keys()
        return self.gpio_chipid2lane_lut[connector][chipid]

    def _set_gpio_chipidext2lane_lut(self):
        """List of dictionaries
        Index in list is connector,
        Dict is chipid_extended:lane
        """
        self.gpio_chipidext2lane_lut = []
        for idx, d in enumerate(self.gpio_chipid2lane_lut):
            if idx<2: # Lower HS
                self.gpio_chipidext2lane_lut.append(d)
            else: # Upper HS
                d_ext = {}
                for key, value in d.items():
                    d_ext[1<<7|key] = value
                self.gpio_chipidext2lane_lut.append(d_ext)

    def _set_module2lanes_lut(self):
        """Creates a dictionary of {module: [lane]}"""
        for lane in range(self.LANES):
            if lane in self.gpio_lane2chipid_lut.keys():
                module = self.gpio_lane2chipid_lut[lane]>>4
                self.gpio_module2lanes_lut[module].append(lane)

    def _set_lane2module_lut(self):
        """Creates a dictionary {lane: module}"""
        for module, lanes in self.gpio_module2lanes_lut.items():
            for lane in lanes:
                assert lane not in self.gpio_lane2module_lut.keys(), f'lane {lane} in {self.gpio_lane2module_lut.keys()}'
                self.gpio_lane2module_lut[lane] = module


class TransitionBoardV1L(TransitionBoard):
    """TB V1l"""

    def __init__(self,
                 ru_main_revision):
        super(TransitionBoardV1L, self).__init__(version=TransitionBoardVersion.V1_L,
                                                 ru_main_revision=ru_main_revision)
        self.check_gpio_subset_map()
        self.check_gpio_sensor_mask()

    def _set_gpio_subset_map(self):
        """Sets the gpio subset map
        Connector map (lanes in data for each connector)
        """
        self.gpio_subset_map = [[0,1,2,10,11,12,13],
                                [3,14,15,16,17,26,27],
                                [18,19,20,22,23,24,25],
                                [4,5,6,7,8,9,21]]

    def _set_gpio_sensor_mask(self):
        """Sets the gpio sensor mask

        GPIO_SENSOR_MASK = {lane_id:one_hot_mask}
        if 0 does not mask (i.e. awaits data from this chipid[2:0])
        if 1 does not wait for those data before going to timeout.
        """
        self.gpio_sensor_mask = { 0:0b1110111,
                                  1:0b1011111,
                                  2:0b0000000,
                                  3:0b1111011,
                                  4:0b0000000,
                                  5:0b1110111,
                                  6:0b1111011,
                                  7:0b1101111,
                                  8:0b0111111,
                                  9:0b1111110,
                                 10:0b1111110,
                                 11:0b0111111,
                                 12:0b1101111,
                                 13:0b1111011,
                                 14:0b1011111,
                                 15:0b1101111,
                                 16:0b0111111,
                                 17:0b1111110,
                                 18:0b1110111,
                                 19:0b1011111,
                                 20:0b0000000,
                                 21:0b1011111,
                                 22:0b1111110,
                                 23:0b0111111,
                                 24:0b1101111,
                                 25:0b1111011,
                                 26:0b0000000,
                                 27:0b1110111}

    def verify_version(self, ru_main_revision):
        """Verifies the RU main and secondary revision against the transition board compatibility"""
        assert ru_main_revision == 1

class TransitionBoardV25(TransitionBoard):
    """TB 2_5"""

    def __init__(self, ru_main_revision):
        super(TransitionBoardV25, self).__init__(version=TransitionBoardVersion.V2_5,
                                                 ru_main_revision=ru_main_revision)
        self.check_gpio_subset_map()
        self.check_gpio_sensor_mask()

    def _set_gpio_subset_map(self):
        """Sets the gpio subset map
        Connector map (lanes in data for each connector)
        """
        self.gpio_subset_map = [[0,1,2,3,4,5,6],
                                [7,8,9,10,11,12,13],
                                [14,15,16,17,18,19,20],
                                [21,22,23,24,25,26,27]]

    def _set_gpio_chipid2lane_lut(self):
        """List of dictionaries
        Index in list is connector,
        Dict is chipid:lane"""
        self.gpio_chipid2lane_lut = [{24:6,  40:5,  56:4,  72:3,  88:2,  104:1,  120:0},
                                     {16:7,  32:8,  48:9,  64:10, 80:11, 96:12,  112:13},
                                     {24:20, 40:19, 56:18, 72:17, 88:16, 104:15, 120:14},
                                     {16:21, 32:22, 48:23, 64:24, 80:25, 96:26,  112:27}]
        self._set_gpio_chipidext2lane_lut()

    def _set_gpio_lane2chipid_lut(self):
        """Dictionary {lane:chipid}"""
        self.gpio_lane2chipid_lut = {lane: chipid for _, conn_dict in enumerate(self.gpio_chipid2lane_lut) for chipid, lane in conn_dict.items()}
        self.gpio_lane2chipidext_lut = {lane: chipid for _, conn_dict in enumerate(self.gpio_chipidext2lane_lut) for chipid, lane in conn_dict.items()}

    def _set_gpio_sensor_mask(self):
        """Sets the gpio sensor mask when connecting a IB to the GPIOs

        GPIO_SENSOR_MASK = {lane_id:one_hot_mask}
        if 0 does not mask (i.e. awaits data from this chipid[2:0])
        if 1 does not wait for those data before going to timeout.
        """
        self.gpio_sensor_mask = { 0:0b1111011,
                                  1:0b1110111,
                                  2:0b1101111,
                                  3:0b1011111,
                                  4:0b0111111,
                                  5:0b0000000,
                                  6:0b1111110,
                                  7:0b1111011,
                                  8:0b1110111,
                                  9:0b1101111,
                                 10:0b1011111,
                                 11:0b0111111,
                                 12:0b0000000,
                                 13:0b1111110,
                                 14:0b1111011,
                                 15:0b1110111,
                                 16:0b1101111,
                                 17:0b1011111,
                                 18:0b0111111,
                                 19:0b0000000,
                                 20:0b1111110,
                                 21:0b1111011,
                                 22:0b1110111,
                                 23:0b1101111,
                                 24:0b1011111,
                                 25:0b0111111,
                                 26:0b0000000,
                                 27:0b1111110}

    def verify_version(self, ru_main_revision):
        """Verifies the RU main and secondary revision against the transition board compatibility"""
        assert ru_main_revision == 2


class TransitionBoardV20(TransitionBoard):
    """TB 2.0"""

    def __init__(self, ru_main_revision):
        super(TransitionBoardV20, self).__init__(version=TransitionBoardVersion.V2_0,
                                                 ru_main_revision=ru_main_revision)
        self.check_gpio_subset_map()
        self.check_gpio_sensor_mask()

    def _set_gpio_subset_map(self):
        """Sets the gpio subset map
        Connector map (lanes in data for each connector)
        """
        raise NotImplementedError

    def _set_gpio_sensor_mask(self):
        """Sets the gpio sensor mask

        GPIO_SENSOR_MASK = {lane_id:one_hot_mask}
        if 0 does not mask (i.e. awaits data from this chipid[2:0])
        if 1 does not wait for those data before going to timeout.
        """
        raise NotImplementedError

    def verify_version(self, ru_main_revision):
        """Verifies the RU main and secondary revision against the transition board compatibility"""
        assert ru_main_revision == 1


class TransitionBoardV25B(TransitionBoard):
    """TB v1k-2.5b,
    on the twiki is marked as TB2.5A (correct name) but the silkscreen says TB2.5B"""

    def __init__(self, ru_main_revision):
        super(TransitionBoardV25B, self).__init__(version=TransitionBoardVersion.V1K_2_5B,
                                                 ru_main_revision=ru_main_revision)
        self.check_gpio_subset_map()
        self.check_gpio_sensor_mask()

    def _set_gpio_subset_map(self):
        """Sets the gpio subset map
        Connector map (lanes in data for each connector)
        """
        raise NotImplementedError

    def _set_gpio_sensor_mask(self):
        """Sets the gpio sensor mask

        GPIO_SENSOR_MASK = {lane_id:one_hot_mask}
        if 0 does not mask (i.e. awaits data from this chipid[2:0])
        if 1 does not wait for those data before going to timeout.
        """
        raise NotImplementedError

    def verify_version(self, ru_main_revision):
        """Verifies the RU main and secondary revision against the transition board compatibility"""
        assert ru_main_revision == 2
