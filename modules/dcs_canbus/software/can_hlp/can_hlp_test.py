"""Run a simple test using the CANbus High Level Protocol.
Reads out githash value, counter values for the CAN HLP module, and tests write
and read using the CAN_TEST register found in the CAN HLP module's wishbone slave"""

import random
import os
import sys
import can_hlp

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path,
    '../../../board_support_software/software/py/')
sys.path.append(modules_path)

from ru_board import XckuModuleid
from ws_can_hlp import WsCanHlpAddress
from ws_can_hlp_monitor import WsCanHlpMonitorAddress
from ws_identity import WsIdentityAddress




def wb_addr(module_id, reg_addr):
    return (module_id << 8) | reg_addr

def can_hlp_test(can_hlp_if, can_dev_id, timeout_ms):
    githash_lsb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_LSB), timeout_ms)
    githash_msb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_MSB), timeout_ms)

    githash = None

    if githash_lsb is not None and githash_msb is not None:
        githash = (githash_msb << 16) | githash_lsb

    rand_data = random.randint(0, 2 ** 16 - 1)

    # Write a test value to TEST register in CAN module
    can_hlp_if.writeHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP, WsCanHlpAddress.TEST_REG), rand_data, timeout_ms)

    # Read back the data from the TEST register
    read_data = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP, WsCanHlpAddress.TEST_REG), timeout_ms)

    return {'githash': githash, 'test_reg_write': rand_data, 'test_reg_read': read_data}


def can_hlp_test_get_hw_counters(can_hlp_if, can_dev_id, timeout_ms):
    # Latch counters in HLP monitor module
    can_hlp_if.writeHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.LATCH_COUNTERS), 0x01, timeout_ms)

    counters = dict()

    can_rx_msg_recv_lsb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_RX_MSG_RECV_LOW), timeout_ms)
    can_rx_msg_recv_msb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_RX_MSG_RECV_HIGH), timeout_ms)
    counters['CAN_RX_MSG_RECV'] = (can_rx_msg_recv_msb << 16) | can_rx_msg_recv_lsb

    can_tx_msg_sent_lsb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_MSG_SENT_LOW), timeout_ms)
    can_tx_msg_sent_msb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_MSG_SENT_HIGH), timeout_ms)
    counters['CAN_TX_MSG_SENT'] = (can_tx_msg_sent_msb << 16) | can_tx_msg_sent_lsb

    hlp_read_lsb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_READ_LOW), timeout_ms)
    hlp_read_msb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_READ_HIGH), timeout_ms)
    counters['HLP_READ'] = (hlp_read_msb << 16) | hlp_read_lsb

    hlp_write_lsb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_WRITE_LOW), timeout_ms)
    hlp_write_msb = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_WRITE_HIGH), timeout_ms)
    counters['HLP_WRITE'] = (hlp_write_msb << 16) | hlp_write_lsb

    counters['HLP_STATUS'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_STATUS), timeout_ms)
    counters['HLP_ALERT'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_ALERT), timeout_ms)
    counters['HLP_UNKNOWN'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.HLP_UNKNOWN), timeout_ms)

    counters['CAN_TX_ACK_ERROR'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_ACK_ERROR), timeout_ms)
    counters['CAN_TX_ARB_LOST'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_ARB_LOST), timeout_ms)
    counters['CAN_TX_BIT_ERROR'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_BIT_ERROR), timeout_ms)
    counters['CAN_TX_RETRANSMIT'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_TX_RETRANSMIT), timeout_ms)
    counters['CAN_RX_CRC_ERROR'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_RX_CRC_ERROR), timeout_ms)
    counters['CAN_RX_FORM_ERROR'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_RX_FORM_ERROR), timeout_ms)
    counters['CAN_RX_STUFF_ERROR'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP_MONITOR, WsCanHlpMonitorAddress.CAN_RX_STUFF_ERROR), timeout_ms)

    return counters

def can_hlp_test_get_hw_error_status(can_hlp_if, can_dev_id, timeout_ms):
    error_status = dict()

    status_reg = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP, WsCanHlpAddress.STATUS), timeout_ms)

    if status_reg & 0x01 != 0:
        error_status['STATE'] = 'ERROR ACTIVE'
    elif status_reg & 0x02 != 0:
        error_status['STATE'] = 'ERROR PASSIVE'
    elif status_reg & 0x04 != 0:
        error_status['STATE'] = 'BUS OFF'

    error_status['TEC'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_TEC), timeout_ms)
    error_status['REC'] = can_hlp_if.readHlp(can_dev_id, wb_addr(XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_REC), timeout_ms)

    return error_status

if __name__ == '__main__':
    print("Starting CAN bus HLP test")

    can_hlp_if = can_hlp.CanHlp('can0')
    can_dev_id = 0x0B
    timeout_ms = 5

    try:
        test_result = can_hlp_test(can_hlp_if, can_dev_id, timeout_ms)

        print("githash: {:04X}".format(test_result['githash']))
        print("data written to test reg: {}".format(test_result['test_reg_write']))
        print("data read back from test reg: {}".format(test_result['test_reg_read']))

        sw_counters = can_hlp_if.getCounters()
        print('Software counters:')
        print(sw_counters)

        hw_counters = can_hlp_test_get_hw_counters(can_hlp_if, can_dev_id, timeout_ms)
        print('Hardware counters:')
        print(hw_counters)

        error_status = can_hlp_test_get_hw_error_status(can_hlp_if, can_dev_id, timeout_ms)
        print('Hardware error status:')
        print(error_status)

    except KeyboardInterrupt:
        print("C-C caught")
    finally:
        print("exiting SAFELY")
