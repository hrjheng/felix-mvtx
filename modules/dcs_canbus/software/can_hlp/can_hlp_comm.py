"""CANbus High Level Protocol.
CanHlpComm class for communicating with Readout Unit via CAN bus,
based on the abstract Communication class.

The Communication class implements an interface with two fifos, dp0 and dp1,
for wishbone transactions.

dp0: wishbone transaction request (write or read)
dp1: wishbone transaction response (read result only)

In this class the transactions are put in two queues which represent dp0 and dp1:
- trx_request_fifo
- trx_response_fifo

When the flush member function is called, the data in trx_request_fifo (dp0) is
written to the CAN bus interface, using writeHLP from the CanHlp class.
"""

import binascii
import time
import queue
import logging
import sys
import traceback
from threading import Lock, Thread

from can_hlp import CanHlp, CanHlpTimeout, CanHlpWrongId, CanHlpWrongResponse
from communication import Communication
from simulation_if import GLOBAL_READ_TIMEOUT, chunks
from socketcan_sim_wrapper import SocketCanSimWrapper


class CanHlpComm(CanHlp, Communication):
    """CANbus High Level Protocol

    Args:
        can_if (str): Name of SocketCAN interface to use, e.g. can0.
        enable_rderr_exception (bool): Enable read error exceptions in
                                       base Communication class.
    """
    def __init__(self, can_if: str, timeout_ms=1000, initial_node_id=0, sim: bool=False, enable_rderr_exception=False, filter=False):
        CanHlp.__init__(self, can_if)
        Communication.__init__(self, enable_rderr_exception)

        self.timeout_ms = timeout_ms

        # DP0 queue not used at the moment, transactions are executed immediately
        # by _do_write_dp0 function
        self.dp0_wb_trx_request_queue = queue.Queue()
        self.dp1_wb_trx_response_queue = queue.Queue()

        self.dp0_mutex = Lock()
        self.dp1_mutex = Lock()

        self.can_errors_strings = {"ARB_LOST",
                                   "ACK_MISSING",
                                   "TIMEOUT",
                                   "CRC_ERROR"}
        self.sim = sim

        if self.sim:
            self.socketcan_sim_wrapper = SocketCanSimWrapper("vcan0")

        self.flush_dp0_thread = None

        self.logger = logging.getLogger("CanHlpComm")

        # Node ID for the RU we want to communicate with
        # Unless node id is set to the broadcast id (255), the node id
        # here has to match the node id that is set up with the dip switches
        # on the readout unit.
        self._can_node_id = initial_node_id


        # Filtering the messages which are meant to be processed by the other comm objects
        if filter:
            can_arb_id = self._can_node_id << 3
            self.bus.set_filters([{"can_id": can_arb_id, "can_mask": 0x7F8, "extended": False}])

        # error counters:
        self.timeout_count = 0
        self.wrong_response_count = 0
        self.wrong_id_count = 0

    def _lock_comm(self):
        pass

    def _unlock_comm(self):
        pass

    def roc_write(self, reg, data):
        #pass
        traceback.print_stack()

    def roc_read(self, reg):
        #pass
        traceback.print_stack()

    def reset_hlp_error_counters(self):
        """reset HLP error counters"""
        self.timeout_count = 0
        self.wrong_response_count = 0
        self.wrong_id_count = 0

    def get_timeout_count(self):
        return self.timeout_count

    def get_wrong_response_count(self):
        return self.wrong_response_count

    def get_wrong_id_count(self):
        return self.wrong_id_count


    def close(self):
        if self.sim:
            self.socketcan_sim_wrapper.stop()

    def close_connections(self):
        self.close()

    def _flush_dp0_thread(self):
        """Execute HLP transactions in separate thread"""
        dp0_empty = False

        while not dp0_empty:
            msg_out = None

            try:
                with self.dp0_mutex:
                    msg_out = self.dp0_wb_trx_request_queue.get_nowait()
            except queue.Empty:
                dp0_empty = True

            if msg_out is not None:
                if (msg_out['write_request']):
                    try:
                        self.writeHlp(msg_out['node_id'],
                                      msg_out['addr'],
                                      msg_out['data'],
                                      self.timeout_ms)
                    except CanHlpTimeout:
                        self.logger.warning(traceback.format_exc())
                        self.timeout_count += 1
                    except CanHlpWrongId:
                        self.logger.warning(traceback.format_exc())
                        self.wrong_id_count += 1
                    except CanHlpWrongResponse:
                        self.logger.warning(traceback.format_exc())
                        self.wrong_response_count += 1
                    except:
                        self.logger.exception(traceback.format_exc())

                else:
                    # Todo: Use try/except clause and catch errors, and put transaction
                    #       with rderr flag (bit 15 of addr) set if there is an error?
                    response_msg = {'node_id': msg_out['node_id'],
                                    'addr': msg_out['addr'],
                                    'data': 0x0000,
                                    'write_request': msg_out['write_request']}

                    try:
                        response_msg['data'] = self.readHlp(msg_out['node_id'], msg_out['addr'], self.timeout_ms)

                    except CanHlpTimeout:
                        response_msg['addr'] = msg_out['addr'] | 0x8000 # Set MSB bit (rd_err flag)
                        self.logger.warning(traceback.format_exc())
                        self.timeout_count += 1
                    except CanHlpWrongId:
                        response_msg['addr'] = msg_out['addr'] | 0x8000 # Set MSB bit (rd_err flag)
                        self.logger.warning(traceback.format_exc())
                        self.wrong_id_count += 1
                    except CanHlpWrongResponse:
                        response_msg['addr'] = msg_out['addr'] | 0x8000 # Set MSB bit (rd_err flag)
                        self.logger.warning(traceback.format_exc())
                        self.wrong_response_count += 1
                    except:
                        response_msg['addr'] = msg_out['addr'] | 0x8000 # Set MSB bit (rd_err flag)
                        self.logger.exception(traceback.format_exc())

                    with self.dp1_mutex:
                        self.dp1_wb_trx_response_queue.put_nowait(response_msg)

    def flush_dp0(self):
        """Flush DP0 fifo/queue (wishbone transaction requests)
        This spawns a new thread for executing the transactions on the CAN bus interface.
        The readHLP/writeHLP functions expects a reponse following a request, and especially
        for simulation this is problematic. If the simulation called readHLP/writeHLP directly,
        it would lead to a deadlock because readHLP/writeHLP waits for reponse from simulation,
        while the simulation waits for the python call to finish."""
        if self.flush_dp0_thread is None or not self.flush_dp0_thread.is_alive():
            self.flush_dp0_thread = Thread(target=self._flush_dp0_thread)
            self.flush_dp0_thread.start()
        return 0

    def clear(self):
        """Clear buffers"""
        with self.dp0_mutex:
            self.dp0_wb_trx_request_queue = queue.Queue()
        with self.dp1_mutex:
            self.dp1_wb_trx_request_queue = queue.Queue()
        return 0

    def _do_write_dp0(self, data):
        # Each bus command should be 4 bytes, and several commands can be queued
        assert len(data) % 4 == 0
        for chunk in chunks(data,4):
            msg = {
                'node_id': self._can_node_id,
                'addr': ((chunk[3] & 0x7F) << 8) | chunk[2],
                'data': (chunk[1] << 8) | chunk[0],
                'write_request': True if (chunk[3] & 0x80) == 0x80 else False
            }

            with self.dp0_mutex:
                self.dp0_wb_trx_request_queue.put_nowait(msg)
        self.flush_dp0()

    def _do_read_dp1(self, size):
        """Read data from fifo file.

            Args:
                size (uint): Number of bytes to read. Should be divisible by 4.

            Return:
                Bytearray containing (read) transaction results"""

        cnt = 0
        max_count = 10
        remaining = size
        assert size % 4 == 0
        msg_str = b""
        last_read = False
        seconds = 0

        while (remaining > 0) and (seconds < GLOBAL_READ_TIMEOUT):
            try:
                with self.dp1_mutex:
                    msg_in = self.dp1_wb_trx_response_queue.get_nowait()

                hex_data_str = "{:02X}{:02X}{:02X}{:02X}".format(msg_in['data'] & 0xFF,
                                                                 msg_in['data'] >> 8,
                                                                 msg_in['addr'] & 0xFF,
                                                                 msg_in['addr'] >> 8)

                hex_data = binascii.unhexlify(hex_data_str)

                chunk = bytearray(hex_data)
                msg_str += chunk
                remaining -= len(chunk)  # Should always be 4

                if remaining > 0:
                    if cnt >= max_count:
                        if last_read:
                            break
                    if len(chunk) == 0:
                        time.sleep(1)
                        seconds += 1
                        cnt += 1
                    else:
                        cnt = 0  # Reset retry-counter

            except queue.Empty:
                # Keep checking FIFO/queue if it is empty
                continue

        if seconds == GLOBAL_READ_TIMEOUT:
            # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
            raise KeyboardInterrupt("\n\n**** ERROR: CAN bus read timeout, simulation stuck, exiting ****\n\n")
        return msg_str

    def set_node_id(self, node_id: int):
        """Set the node ID of the Readout Unit to communicate with."""
        self._can_node_id = node_id

    def get_node_id(self):
        """Return the CAN node ID"""
        return(self._can_node_id)
