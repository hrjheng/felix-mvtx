"""Run a scan attempting communication on all node IDs to reveal which IDs are connected to the CAN bus"""

import can_hlp
import os
import sys

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path,
    '../../../board_support_software/software/py/')
sys.path.append(modules_path)

from ru_board import XckuModuleid
from ws_identity import WsIdentityAddress

def wb_addr(module_id, reg_addr):
    return (module_id << 8) | reg_addr

print("Starting CAN HLP node scan.")

try:
    can = can_hlp.CanHlp('vcan0')
    can_dev_id = 0x00
    can_ids_and_githash = dict()
    timeout_ms = 100

    while can_dev_id <= 0xFF:
        if can_dev_id == can_hlp.CanHlp.C_BROADCAST_ID:
            can_dev_id = can_dev_id+1
            continue

        try:
            githash_lsb = can.readHlp(can_dev_id, wb_addr(XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_LSB), timeout_ms)
            githash_msb = can.readHlp(can_dev_id, wb_addr(XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_MSB), timeout_ms)

            githash = 0
            if githash_lsb is None:
                print('readHLP() for githash_lsb did not return anything')
            elif githash_msb is None:
                print('readHLP() for githash_msb did not return anything')
            else:
                githash = (githash_msb << 16) | githash_lsb

                print("ID {:02X} githash: {:04X}".format(can_dev_id, githash))

                can_ids_and_githash[can_dev_id] = githash

        except can_hlp.CanHlpTimeout:
            print("Timeout for ID {:02X}".format(can_dev_id))

        can_dev_id = can_dev_id+1

except KeyboardInterrupt:
    print("C-C caught")
finally:
    print("exiting SAFELY")
