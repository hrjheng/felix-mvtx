"""File implementing the control for the CANbus HLP wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule

import ws_can_hlp_monitor

@unique
class WsCanHlpAddress(IntEnum):
    """memory mapping for the ws_identity got from can_hlp_wb_slave_regs_pkg.vhd"""
    CTRL           = 0x00
    STATUS         = 0x01
    CAN_PROP_SEG   = 0x02
    CAN_PHASE_SEG1 = 0x03
    CAN_PHASE_SEG2 = 0x04
    CAN_SJW        = 0x05
    CAN_CLK_SCALE  = 0x06
    CAN_TEC        = 0x07
    CAN_REC        = 0x08
    TEST_REG       = 0x09
    FSM_STATES     = 0x0A

@unique
class WsCanHlpCtrlBits(IntEnum):
    """Bit mapping for CTRL register."""
    TRIPLE_SAMPLING_EN = 0
    RETRANSMIT_EN      = 1
    TEST_MODE_EN       = 2

@unique
class WsCanHlpStatusBits(IntEnum):
    """Bit mapping for STATUS register."""
    ERROR_ACTIVE  = 0
    ERROR_PASSIVE = 1
    BUS_OFF       = 2

@unique
class CanHlpFsmStates(IntEnum):
    ST_IDLE               = 0
    ST_CAN_MSG_RECEIVED   = 1
    ST_WB_READ_SETUP      = 2
    ST_WB_READ_INITIATE   = 3
    ST_WB_READ_DATA       = 4
    ST_WB_READ_DATA_WAIT1 = 5
    ST_WB_READ_DATA_WAIT2 = 6
    ST_WB_WRITE_SETUP     = 7
    ST_WB_WRITE_INITIATE  = 8
    ST_CAN_MSG_SEND       = 9
    ST_SETUP_HLP_TEST     = 10
    ST_SETUP_HLP_STATUS   = 11
    ST_SETUP_HLP_ALERT    = 12
    ST_HLP_NODE_ID_ERROR  = 13
    ST_HLP_LENGTH_ERROR   = 14
    ST_HLP_UNKNOW         = 15

@unique
class CanRxFsmStates(IntEnum):
    ST_IDLE               = 0
    ST_RECV_SOF           = 1
    ST_RECV_ID_A          = 2
    ST_RECV_SRR_RTR       = 3
    ST_RECV_IDE           = 4
    ST_RECV_ID_B          = 5
    ST_RECV_EXT_FRAME_RTR = 6
    ST_RECV_R1            = 7
    ST_RECV_R0            = 8
    ST_RECV_DLC           = 9
    ST_RECV_DATA          = 10
    ST_RECV_CRC           = 11
    ST_RECV_CRC_DELIM     = 12
    ST_SEND_RECV_ACK      = 13
    ST_RECV_ACK_DELIM     = 14
    ST_RECV_EOF           = 15
    ST_ERROR              = 16
    ST_WAIT_ERROR_FLAG    = 17
    ST_DONE               = 18
    ST_WAIT_BUS_IDLE      = 19

@unique
class CanTxFsmStates(IntEnum):
    ST_IDLE               = 0
    ST_WAIT_FOR_BUS_IDLE  = 1
    ST_SETUP_SOF          = 2
    ST_SETUP_ID_A         = 3
    ST_SETUP_SRR_RTR      = 4
    ST_SETUP_IDE          = 5
    ST_SETUP_ID_B         = 6
    ST_SETUP_EXT_RTR      = 7
    ST_SETUP_R1           = 8
    ST_SETUP_R0           = 9
    ST_SETUP_DLC          = 10
    ST_SETUP_DATA         = 11
    ST_SETUP_CRC          = 12
    ST_SETUP_CRC_DELIM    = 13
    ST_SETUP_ACK_SLOT     = 14
    ST_SETUP_ACK_DELIM    = 15
    ST_SETUP_EOF          = 16
    ST_SETUP_ERROR_FLAG   = 17
    ST_SEND_SOF           = 18
    ST_SEND_ID_A          = 19
    ST_SEND_SRR_RTR       = 20
    ST_SEND_IDE           = 21
    ST_SEND_ID_B          = 22
    ST_SEND_EXT_RTR       = 23
    ST_SEND_R1            = 24
    ST_SEND_R0            = 25
    ST_SEND_DLC           = 26
    ST_SEND_DATA          = 27
    ST_SEND_CRC           = 28
    ST_SEND_CRC_DELIM     = 29
    ST_SEND_RECV_ACK_SLOT = 30
    ST_SEND_ACK_DELIM     = 31
    ST_SEND_EOF           = 32
    ST_SEND_ERROR_FLAG    = 33
    ST_ARB_LOST           = 34
    ST_BIT_ERROR          = 35
    ST_ACK_ERROR          = 36
    ST_RETRANSMIT         = 37
    ST_DONE               = 38

class WsCanHlp(WishboneModule):
    """wishbone slave used for control and status of CAN bus"""

    def __init__(self, moduleid, board_obj, monitor_module):
        """init"""
        super(WsCanHlp, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                       name="CANbus HLP")

        assert isinstance(monitor_module, ws_can_hlp_monitor.WsCanHlpMonitor)
        self._monitor = monitor_module

        self.CAN_SYSTEM_CLK_MHZ = 160

        # The width of the clock scale register is determined by
        # C_CAN_CLK_SCALE_range in can_hlp_wb_slave_regs_pkg.vhd,
        # which depends on C_TIME_QUANTA_WIDTH in can_hlp_pkg.vhd
        self.CAN_CLOCK_SCALE_WIDTH = 8

        # This is the default value, however it is configurable.
        # The bit rate depends on the number of time quanta and the clock scale
        self.CAN_TIME_QUANTA_PER_BIT = 16

        # 1 Mbit is maximum data rate in the CAN protocol
        self.MAX_BITRATE_HARDWARE = 1000000

        self.STATUS_REG_ERROR_STATE_BITMASK = 0x7
        self.STATUS_REG_CAN_RX_BIT_IDX = 3
        self.STATUS_REG_CAN_TX_BIT_IDX = 4

    def get_control_reg(self, commitTransaction=True):
        ctrl_reg = self.read(WsCanHlpAddress.CTRL, commitTransaction=commitTransaction)
        return {
            'triple_sampling_enabled': bool(ctrl_reg & (1 << WsCanHlpCtrlBits.TRIPLE_SAMPLING_EN)),
            'retransmit_enabled': bool(ctrl_reg & (1 << WsCanHlpCtrlBits.RETRANSMIT_EN)),
            'test_mode_enabled': bool(ctrl_reg & (1 << WsCanHlpCtrlBits.TEST_MODE_EN))
        }

    def set_control_reg(self, triple_sampling=False, retransmit=True, test_mode=False, commitTransaction=True):
        """Set control register"""
        ctrl_reg = int(triple_sampling) << WsCanHlpCtrlBits.TRIPLE_SAMPLING_EN
        ctrl_reg |= int(retransmit) << WsCanHlpCtrlBits.RETRANSMIT_EN
        ctrl_reg |= int(test_mode) << WsCanHlpCtrlBits.TEST_MODE_EN
        self.write(WsCanHlpAddress.CTRL, ctrl_reg, commitTransaction=commitTransaction)

    def enable_triple_sampling(self):
        """Enable triple sampling of bits in the CAN controller."""
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=True,
                             retransmit=ctrl_fields['retransmit_enabled'],
                             test_mode=ctrl_fields['test_mode_enabled'])

    def disable_triple_sampling(self):
        """Disable triple sampling of bits in the CAN controller."""
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=False,
                             retransmit=ctrl_fields['retransmit_enabled'],
                             test_mode=ctrl_fields['test_mode_enabled'])

    def enable_retransmit(self):
        """Enable retransmission of packages in the CAN controller"""
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=ctrl_fields['triple_sampling_enabled'],
                             retransmit=True,
                             test_mode=ctrl_fields['test_mode_enabled'])

    def disable_retransmit(self):
        """Disable retransmission of packages in the CAN controller"""
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=ctrl_fields['triple_sampling_enabled'],
                             retransmit=False,
                             test_mode=ctrl_fields['test_mode_enabled'])

    def enable_test_mode(self):
        """Enable test mode in the CAN HLP module

        In this mode HLP_TEST messages will be transmitted continuously from the
        node/RU (until it is disabled). Transmission is initiated from the RU itself,
        there is no corresponding request in the HLP protocol.
        The test mode can be useful for testing. The CAN_TX_MSG_SENT register should
        increase for the RU that is in test mode, and the other RUs on the same CAN
        bus line should see a corresponding increase in their CAN_RX_MSG_RECV registers.
        """
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=ctrl_fields['triple_sampling_enabled'],
                             retransmit=ctrl_fields['retransmit_enabled'],
                             test_mode=True)

    def disable_test_mode(self):
        """Disable test mode in the CAN HLP module"""
        ctrl_fields = self.get_control_reg()
        self.set_control_reg(triple_sampling=ctrl_fields['triple_sampling_enabled'],
                             retransmit=ctrl_fields['retransmit_enabled'],
                             test_mode=False)

    def get_status(self, commitTransaction=True):
        """Read status and return name of current controller state"""
        status_reg = self.read(WsCanHlpAddress.STATUS, commitTransaction=commitTransaction)
        error_state = WsCanHlpStatusBits(status_reg & self.STATUS_REG_ERROR_STATE_BITMASK).name
        status_dict = {'ERROR_STATE': error_state,
                       'CAN_RX_VALUE': (status_reg >> self.STATUS_REG_CAN_RX_BIT_IDX) & 1,
                       'CAN_TX_VALUE': (status_reg >> self.STATUS_REG_CAN_TX_BIT_IDX) & 1}
        return status_dict

    def get_can_transmit_error_counter(self, commitTransaction=True):
        """Get the Transmit Error Counter (TEC) value for the CAN controller.
        Note that this is an internal counter in the controller which can increase
        and decrease based on transmit errors or successful transmits."""
        return self.read(WsCanHlpAddress.CAN_TEC, commitTransaction=commitTransaction)

    def get_can_receive_error_counter(self, commitTransaction=True):
        """Get the Receive Error Counter (REC) value for the CAN controller.
        Note that this is an internal counter in the controller which can increase
        and decrease based on receive errors or successfully received messages."""
        return self.read(WsCanHlpAddress.CAN_REC, commitTransaction=commitTransaction)

    def get_can_clock_scale(self, commitTransaction=True):
        """Get the current clock scale value for the time quanta generator
        in the CAN controller. This value along with the number of time quantas
        per bit determines the bitrate for CAN bus"""
        return self.read(WsCanHlpAddress.CAN_CLK_SCALE, commitTransaction=commitTransaction)

    def set_can_clock_scale(self, clock_scale_value, commitTransaction=True):
        """Set the clock scale value for the time quanta generator in the
        CAN controller. This value along with the number of time quantas
        per bit determines the bitrate for CAN bus"""
        assert clock_scale_value < 2**self.CAN_CLOCK_SCALE_WIDTH, \
            "Clock scale value too large, the clock scale register is {} bits wide".format(self.CAN_CLOCK_SCALE_WIDTH)

        self.write(WsCanHlpAddress.CAN_CLK_SCALE, clock_scale_value, commitTransaction=commitTransaction)

    def get_possible_bitrates(self, num_time_quantas_per_bit=None, hw_supported_only=True):
        """Get the possible bitrates and corresponding clock scale values that
        can be used with the CAN controller, for the specified number of time
        quantas per bit.

        With hw_supported_only=True, only hardware supported bitrates (up to 1Mbit) are returned.
        With hw_supported_only=False, all possible bitrates are returned (e.g. for simulation)

        Return value: dict where key is bitrate, value is the clock scale value"""
        bitrates = dict()

        if num_time_quantas_per_bit is None:
            num_time_quantas_per_bit = self.get_number_of_time_quantas_per_bit()

        # The CAN controller needs a minimum of 4 clock cycles per time quanta.
        # The maximum bit rate it can handle can be higher than the 1 Mbit specified
        # in the protocol. Higher rates than 1 Mbit can be used to speed up simulation,
        # but can not be used in the hardware.
        max_bitrate_controller = self.CAN_SYSTEM_CLK_MHZ*1E6/(num_time_quantas_per_bit*4)

        for clock_scale in range(0, 2**self.CAN_CLOCK_SCALE_WIDTH):
            bitrate_bps = self.calculate_bitrate(num_time_quantas_per_bit, clock_scale)

            # Only allow bit rate settings that the controller can handle
            if bitrate_bps <= max_bitrate_controller:
                if not hw_supported_only:
                    # Allow any bit rate the controller can handle
                    bitrates[bitrate_bps] = clock_scale

                elif hw_supported_only and bitrate_bps <= self.MAX_BITRATE_HARDWARE:
                    # Allow bit rates supported in hardware by the CAN specification only
                    bitrates[bitrate_bps] = clock_scale

        return bitrates

    def calculate_bitrate(self, num_time_quantas_per_bit, clock_scale):
        """Calculate the bitrate (in bps) for the specified number of
        time quantas per bit and clock scale value"""
        return self.CAN_SYSTEM_CLK_MHZ*1E6/(num_time_quantas_per_bit*(1+clock_scale))

    def _segment_reg_to_time_quanta_count(self, segment):
        """Get number of time quantas in a segment, i.e. PROP, PHASE1 and PHASE2 segments.
        Each '1' bit starting from the LSB counts as a time quanta,
        until the first '0' bit is encountered."""
        num_time_quantas = 0

        while segment & 1 == 1:
            num_time_quantas = num_time_quantas + 1
            segment = segment >> 1

        return num_time_quantas

    def _time_quanta_count_to_segment_reg(self, num_time_quantas):
        return (2**num_time_quantas)-1

    def get_prop_segment_time_quanta_count(self):
        prop_seg_reg = self.read(WsCanHlpAddress.CAN_PROP_SEG)
        return self._segment_reg_to_time_quanta_count(prop_seg_reg)

    def get_phase_segment1_time_quanta_count(self):
        phase_seg1_reg = self.read(WsCanHlpAddress.CAN_PHASE_SEG1)
        return self._segment_reg_to_time_quanta_count(phase_seg1_reg)

    def get_phase_segment2_time_quanta_count(self):
        phase_seg2_reg = self.read(WsCanHlpAddress.CAN_PHASE_SEG2)
        return self._segment_reg_to_time_quanta_count(phase_seg2_reg)

    def get_number_of_time_quantas_per_bit(self):
        num_time_quantas = 1 # Sync segment - fixed

        num_time_quantas += self.get_prop_segment_time_quanta_count()
        num_time_quantas += self.get_phase_segment1_time_quanta_count()
        num_time_quantas += self.get_phase_segment2_time_quanta_count()

        return num_time_quantas

    def set_prop_segment_time_quanta_count(self, num_time_quantas, commitTransaction=True):
        prop_seg_reg = self._time_quanta_count_to_segment_reg(num_time_quantas)
        self.write(WsCanHlpAddress.CAN_PROP_SEG, prop_seg_reg, commitTransaction=commitTransaction)

    def set_phase_segment1_time_quanta_count(self, num_time_quantas, commitTransaction=True):
        phase_seg1_reg = self._time_quanta_count_to_segment_reg(num_time_quantas)
        self.write(WsCanHlpAddress.CAN_PHASE_SEG1, phase_seg1_reg, commitTransaction=commitTransaction)

    def set_phase_segment2_time_quanta_count(self, num_time_quantas, commitTransaction=True):
        phase_seg2_reg = self._time_quanta_count_to_segment_reg(num_time_quantas)
        self.write(WsCanHlpAddress.CAN_PHASE_SEG2, phase_seg2_reg, commitTransaction=commitTransaction)

    def get_bitrate(self):
        """Get the currently configured bitrate (in bps) in the CAN controller"""

        clock_scale = self.get_can_clock_scale()
        num_time_quantas = self.get_number_of_time_quantas_per_bit()

        return self.calculate_bitrate(clock_scale, num_time_quantas)

    def set_bitrate(self, bitrate_bps, num_time_quantas=None, hw_supported_only=True, commitTransaction=True):
        """Set CAN bus bitrate (by changing clock scale for time quanta generator)
        Legal bitrate values must be used, use get_possible_bitrates() to see which values are possible.
        Up to 1 Mbit is supported by hardware. Setting hw_supported_only to False allows for higher values
        (e.g. for simulation).
        Note that the possible bit rates depend on the time segment settings in the controller.
        Note: This function calculates a clock scale based on the configuration of the time segments
        in the controller. It does not change the time segments, and the possible bitrates also depends
        on the time segment settings."""
        if num_time_quantas is None:
            num_time_quantas = self.get_number_of_time_quantas_per_bit()

        bitrates = self.get_possible_bitrates(num_time_quantas, hw_supported_only)

        assert bitrate_bps in bitrates, \
            "Bitrate of {} bps with {} time quantas not supported ({})".format(bitrate_bps,
                                                                               num_time_quantas,
                                                                               "hardware" if hw_supported_only else "simulation")
        self.set_can_clock_scale(bitrates[bitrate_bps])

    def _state_type_to_bit_width(self, state_type):
        max_val = len(state_type)-1
        return max_val.bit_length()

    def get_fsm_states(self, commitTransaction=True):
        """Get states for CAN HLP, CAN Rx Frame, and CAN Tx Frame FSMs."""
        fsm_state_reg = self.read(WsCanHlpAddress.FSM_STATES, commitTransaction=commitTransaction)

        hlp_fsm_bit_width = self._state_type_to_bit_width(CanHlpFsmStates)
        can_rx_fsm_bit_width = self._state_type_to_bit_width(CanRxFsmStates)
        can_tx_fsm_bit_width = self._state_type_to_bit_width(CanTxFsmStates)

        hlp_fsm_state = CanHlpFsmStates(fsm_state_reg & ((2**hlp_fsm_bit_width)-1))
        can_rx_fsm_state_tmp = fsm_state_reg >> hlp_fsm_bit_width
        can_rx_fsm_state = CanRxFsmStates(can_rx_fsm_state_tmp & ((2**can_rx_fsm_bit_width)-1))
        can_tx_fsm_state_tmp = fsm_state_reg >> (hlp_fsm_bit_width + can_rx_fsm_bit_width)
        can_tx_fsm_state = CanTxFsmStates(can_tx_fsm_state_tmp & ((2**can_tx_fsm_bit_width)-1))

        return (hlp_fsm_state, can_rx_fsm_state, can_tx_fsm_state)

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = "--- CANBUS HLP module ---\n"
        for address in WsCanHlpAddress:
            name = address.name
            value = self.read(address.value)
            config_str += "    - {0} : {1:#06X}\n".format(name, value)
        return config_str

    def reset_counters(self, commitTransaction=True):
        """Resets all the counters in the monitor module"""
        self._monitor.reset_all_counters(commitTransaction=commitTransaction)

    def read_counters(self, reset_after=False, commitTransaction=True):
        """Latches and reads all the counters in the monitor module"""
        return self._monitor.read_counters(reset_after=reset_after, commitTransaction=commitTransaction)
