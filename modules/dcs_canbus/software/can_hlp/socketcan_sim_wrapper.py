"""SocketCAN simulation wrapper
This class acts as an wrapper between a virtual SocketCAN interface (e.g. vcan0),
and the .txt files representing the DP0 and DP1 FIFOs for wishbone transactions
in the simulation.

The class listens to the virtual SocketCAN interface, and writes each wishbone
transaction request from the "host" (ie. CanHlpComm) to the DP0 FIFO file.

For wishbone read responses (coming from the simulation), the class monitors the DP1
FIFO file, and puts any new data from the DP1 FIFO on the virtual SocketCAN interface,
so that they can be picked up by CanHlpComm.
"""

import can
import os
import sys
import time
from threading import Thread
from queue import Queue

from simulation_if import SocketComm
from simulation_if import chunks

class FifoFileToCanbus:
    """SocketCAN simulation wrapper

    Args:
        canbus (str): Name of virtual SocketCAN interface to use, e.g. vcan0.
        sim (socket): SocketComm object for connecting to sim
    """
    def __init__(self, canbus: can.ThreadSafeBus, sim: SocketComm):
        self.canbus_obj = canbus
        self.sim = sim
        self.thread = Thread(target=self.forward_data, daemon=True)
        self.thread.start()
        self.sim.en_timeout = False

    def forward_data(self):
        while True:
            lines = self.sim.fetch()
            for line in lines:
                # Fifo files should contain one hex string per line,
                # with each line representing one CAN bus frame.
                # Expected line format:
                # Byte 0: Arbitration ID MSB
                # Byte 1: Arbitration ID LSB
                # Byte 2 to 9: Data
                # Byte 2 to 9 is optional (empty package is possible)
                # Only standard 11-bit arbitration ID is supported.
                # Additional bits in MSB of arbitration ID is ignored.
                assert len(line) >= 4, "Expect at least 2 bytes per CAN frame in DP1 file."
                assert len(line) %2 == 0, "Expect even number of characters (nibbles) in DP1 file."

                # Mask out 11 LSBs, the standard CAN arbitration ID is 11 bits
                arb_id = int(line[:4], 16) & 0x07FF
                data = bytearray()

                for byte_chunk in chunks(line[4:],2):
                    data.append(int(byte_chunk, 16))

                msg = can.Message(is_extended_id=False, arbitration_id=arb_id, data=data)
                self.canbus_obj.send(msg)

    def __del__(self):
        self.sim.close()


class CanbusListener(can.Listener):
    def __init__(self, sim: SocketComm):
        self.sim = sim

    def on_message_received(self, msg: can.Message):
        hex_str = f"{msg.arbitration_id:04X}"
        hex_str += "".join([f"{byte:02X}" for byte in msg.data])
        hex_str += '\n'
        self.sim.flush(hex_str)


class CanbusToFifoFile:
    def __init__(self, canbus: can.ThreadSafeBus, sim: SocketComm):
        self.canbus_obj = canbus
        self.can_listener = CanbusListener(sim)

        listeners = [
            self.can_listener,  # Callback function
        ]

        self.notifier = can.Notifier(self.canbus_obj, listeners)

    def stop(self):
        self.notifier.stop()

    def __del__(self):
        self.stop()


class SocketCanSimWrapper:
    def __init__(self, can_if):
        self.sim = SocketComm(host=("localhost", 32229))
        self.canbus = can.ThreadSafeBus(can_if, bustype='socketcan', receive_own_messages=False)

        self.fifo_to_canbus = FifoFileToCanbus(self.canbus, self.sim)
        self.canbus_to_fifo = CanbusToFifoFile(self.canbus, self.sim)

    def stop(self):
        self.canbus_to_fifo.stop()
        self.sim.close()
        self.canbus.shutdown()

    def __del__(self):
        self.stop()


if __name__ == '__main__':
    # Note: When testing the file monitor, run something like:
    # echo 02AABBCCDDEE >> dp1_fifo.txt
    # Text editors don't necessarily write all the data in one step..
    sim_wrapper = SocketCanSimWrapper("vcan0")

    try:
        while True:
            time.sleep(1)
    finally:
        sim_wrapper.stop()
