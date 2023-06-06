"""CANbus High Level Protocol.
Includes CanHlp class for communicating with Readout Unit via CAN bus, and
relevant exceptions, and a small set of wishbone registers found in the
CAN HLP module in the Ultrascale (as well as githash registers).

Should be integrated into the larger framework at some point."""

import can
from enum import IntEnum


class CanHlpCmd(IntEnum):
    ALERT = 0
    DATA = 1
    WRITE_CMD = 2
    WRITE_RESP = 3
    READ_CMD = 4
    READ_RESP = 5
    STATUS = 6
    TEST = 7


class CanHlpTimeout(Exception):
    pass

class CanHlpWrongId(Exception):
    pass

class CanHlpWrongResponse(Exception):
    pass

class CanHlpWrongResponseAddress(Exception):
    pass

class CanHlpReadError(Exception):
    pass

class CanErrorFrame(Exception):
    pass


class CanHlp(object):
    """CANbus High Level Protocol

    Args:
        can_if (str): Name of SocketCAN interface to use, e.g. can0.
    """

    C_BROADCAST_ID = 0x7F

    bus = None

    def __init__(self, can_if):
        self.bus = can.ThreadSafeBus(can_if, bustype='socketcan', receive_own_messages=False)

        self.counters = {'hlp_flushed': 0,
                         'hlp_read': 0,
                         'hlp_write': 0,
                         'hlp_alert': 0,
                         'hlp_status': 0,
                         'hlp_unknown': 0,
                         'hlp_timeout': 0,
                         'hlp_wrong_id': 0,
                         'hlp_wrong_response': 0,
                         'can_error_frame': 0,
                         'can_rx_msg': 0,
                         'can_tx_msg': 0}

    def getCounters(self):
        return self.counters

    def readHlp(self, dev_id, addr, timeout_ms=1000):
        """Read from wishbone address from Readout Unit using CAN bus HLP.

        A HLP read request is sent to the RU using CAN bus, where the 11-bit
        CAN bus ID contains the RU node ID (dev_id) and read request command ID.
            Arbitration ID(10:3) : dev_id
            Arbitration ID(2:0)  : CMD ID

        If dev_id = 0x7F (broadcast ID), any RU that hears the request will respond.

        Todo:
            Currently only one 16-bit value is returned, even for broadcast (last RU to respond).
            This could be changed to a list of values to support broadcast properly.

        Args:
            dev_id (uint): 8-bit Node ID of Readout Unit to access. ID 0x7F is reserved for broadcast
            addr (uint): 15-bit Wishbone address of register to read
            timeout_ms (uint): Timeout in milliseconds

        Raises:
            CanHlpTimeout: If no reply was received before timeout
            CanHlpWrongId: If a reply was received with the wrong ID (and dev_id was not 0x7F broadcast)
            CanHlpWrongResponse: If something else than a read response was received for this request

        Return:
            16-bit register data
        """
        assert (dev_id != self.C_BROADCAST_ID), "Broadcast not allowed with readHlp, use readHlpBroadcast"
        assert ((addr & 0x8000) == 0), "Address should be 15-bit"

        can_arb_id = dev_id << 3
        can_arb_id = can_arb_id | CanHlpCmd.READ_CMD

        data_out = bytearray([(addr >> 8) & 0xFF, addr & 0xFF])
        msg_out = can.Message(is_extended_id=False, arbitration_id=can_arb_id,
                              data=data_out)
        self.bus.send(msg_out)
        self.counters['can_tx_msg'] += 1

        data_recvd = None

        msg_in = self.bus.recv(timeout_ms/1000.0)  # Timeout in seconds.

        if msg_in is None:
            self.counters['hlp_timeout'] += 1
            raise CanHlpTimeout("CAN HLP read timed out")

        elif msg_in.is_error_frame:
            self.counters['can_error_frame'] += 1
            raise CanErrorFrame("Received error frame after HLP read")

        self.counters['can_rx_msg'] += 1

        # Mask out 3 LSBs, those are the cmd bits in arbitration id
        cmd = msg_in.arbitration_id & 0x0007

        if cmd != CanHlpCmd.READ_RESP:
            self.counters['hlp_wrong_response'] += 1
            raise CanHlpWrongResponse('Expected read response, got {:02x}'.format(cmd))

        addr_in = (msg_in.data[0] << 8) | msg_in.data[1]

        if (addr_in & 0x80) != 0:
            print("Read err")
            raise CanHlpReadError('Bit 15 was set - rd err')

        if addr_in != addr:
            print("Wrong addr")
            raise CanHlpWrongResponseAddress('Got addr {:04x} in response, expected {:04x}'.format(addr_in, addr))

        dev_id_in = msg_in.arbitration_id >> 3
        if dev_id_in != dev_id and dev_id != self.C_BROADCAST_ID:
            self.counters['hlp_wrong_id'] += 1
            raise CanHlpWrongId("Wrong ID received for read response, got {:02x}".format(cmd))

        data_recvd = (msg_in.data[2] << 8) | msg_in.data[3]

        self.counters['hlp_read'] += 1
        return data_recvd

    def readHlpBroadcast(self, addr, timeout_ms=1000):
        """Read from wishbone address from a list of Readout Units using CAN bus HLP broadcast reads commands.

        A HLP read request is sent to the RU using CAN bus, where the 11-bit
        CAN bus ID contains the RU node ID (dev_id) and read request command ID.
            Arbitration ID(10:3) : dev_id
            Arbitration ID(2:0)  : CMD ID

        Args:
            addr (uint): 15-bit Wishbone address of register to read
            timeout_ms (uint): Timeout in milliseconds

        Raises:
            CanHlpTimeout: If no reply was received before timeout
            CanHlpWrongId: If a reply was received with the wrong ID (and dev_id was not 0x7F broadcast)
            CanHlpWrongResponse: If something else than a read response was received for this request

        Return:
            A list of tuples of node ID and 16-bit register data, for the nodes that responded
        """
        assert ((addr & 0x8000) == 0), "Address should be 15-bit"

        can_arb_id = self.C_BROADCAST_ID << 3
        can_arb_id = can_arb_id | CanHlpCmd.READ_CMD

        data_out = bytearray([(addr >> 8) & 0xFF, addr & 0xFF])
        msg_out = can.Message(is_extended_id=False, arbitration_id=can_arb_id, data=data_out)
        self.bus.send(msg_out)
        self.counters['can_tx_msg'] += 1

        data_recvd = list()
        done = False

        while done is False:
            msg_in = self.bus.recv(timeout_ms/1000.0)

            if msg_in is None:
                done = True
                continue
            elif msg_in.is_error_frame:
                self.counters['can_error_frame'] += 1
                raise CanErrorFrame("Received error frame after HLP read")

            self.counters['can_rx_msg'] += 1

            # Mask out 3 LSBs, those are the cmd bits in arbitration id
            cmd = msg_in.arbitration_id & 0x0007

            if cmd != CanHlpCmd.READ_RESP:
                self.counters['hlp_wrong_response'] += 1
                raise CanHlpWrongResponse('Expected read response, got {:02x}'.format(cmd))

            data_recvd = (msg_in.data[2] << 8) | msg_in.data[3]

            dev_id_in = msg_in.arbitration_id >> 3

            if dev_id_in == self.C_BROADCAST_ID:
                self.counters['hlp_wrong_id'] += 1
                raise CanHlpWrongId("Sent broadcast read, got read response with broadcast ID")
            else:
                print("Got read response from {:02x}, data {:04x}".format(dev_id_in, data_recvd))
                data_recvd.append((dev_id_in, data_recvd))

        self.counters['hlp_read'] += 1
        return data_recvd

    def writeHlp(self, dev_id, addr, data, timeout_ms=1000):
        """Write to wishbone address in a Readout Unit using CAN bus HLP.

        A HLP write request is sent to the RU using CAN bus, where the 11-bit
        CAN bus ID contains the RU node ID (dev_id) and read request command ID.
            Arbitration ID(10:3) : dev_id
            Arbitration ID(2:0)  : CMD ID

        dev_id = 0x7F (broadcast ID) is not allowed, use writeHlpBroadcast for broadcast.

        Args:
            dev_id (uint): 8-bit Node ID of Readout Unit to access. Broadcast ID is not allowed.
            addr (uint): 15-bit Wishbone address of register to read
            data (uint): 16-bit data to write
            timeout_ms (uint): Timeout in milliseconds

        Raises:
            CanHlpTimeout: If no reply was received before timeout
            CanHlpWrongId: If a reply was received with the wrong ID (and dev_id was not 0x7F broadcast)
            CanHlpWrongResponse: If something else than a write response was received for this request

        Return:
            None
        """
        assert (dev_id != self.C_BROADCAST_ID), "Broadcast not allowed with writeHlp, use writeHlpBroadcast"
        assert ((addr & 0x8000) == 0), "Address should be 15-bit"

        can_arb_id = dev_id << 3
        can_arb_id = can_arb_id | CanHlpCmd.WRITE_CMD
        data_out = bytearray([(addr >> 8) & 0xFF, addr & 0xFF])
        data_out.append((data >> 8) & 0xFF)
        data_out.append(data & 0xFF)

        msg_out = can.Message(is_extended_id=False, arbitration_id=can_arb_id,
                              data=data_out)

        self.bus.send(msg_out)
        self.counters['can_tx_msg'] += 1

        msg_in = self.bus.recv(timeout_ms/1000.0)  # Timeout in seconds.

        if msg_in is None:
            self.counters['hlp_timeout'] += 1
            raise CanHlpTimeout("CAN HLP write timed out")
        elif msg_in.is_error_frame:
            self.counters['can_error_frame'] += 1
            raise CanErrorFrame("Received error frame after HLP write")

        self.counters['can_rx_msg'] += 1

        # Mask out 3 LSBs, those are the cmd bits in arbitration id
        cmd = msg_in.arbitration_id & 0x0007

        if cmd != CanHlpCmd.WRITE_RESP:
            self.counters['hlp_wrong_response'] += 1
            raise CanHlpWrongResponse('Expected write response, got {:02x}'.format(cmd))

        dev_id_in = msg_in.arbitration_id >> 3
        if dev_id_in != dev_id:
            self.counters['hlp_wrong_id'] += 1
            raise CanHlpWrongId("Wrong ID received for write response, got {:02x}".format(cmd))

        self.counters['hlp_write'] += 1

    def writeHlpBroadcast(self, addr, data, timeout_ms=1000):
        """Write to wishbone address in a list of Readout Units using CAN bus HLP broadcast write commands.

        A HLP write request is sent to the RU using CAN bus, where the 11-bit
        CAN bus ID contains the RU node ID (dev_id) and read request command ID.
            Arbitration ID(10:3) : dev_id
            Arbitration ID(2:0)  : CMD ID

        Args:
            addr (uint): 15-bit Wishbone address of register to read
            data (uint): 16-bit data to write
            timeout_ms (uint): Timeout in milliseconds

        Raises:
            CanHlpTimeout: If no reply was received before timeout
            CanHlpWrongId: If a reply was received with the wrong ID (and dev_id was not 0x7F broadcast)
            CanHlpWrongResponse: If something else than a write response was received for this request

        Return:
            List of device IDs that responded to the write request
        """
        assert ((addr & 0x8000) == 0), "Address should be 15-bit"

        can_arb_id = self.C_BROADCAST_ID << 3
        can_arb_id = can_arb_id | CanHlpCmd.WRITE_CMD
        data_out = bytearray([(addr >> 8) & 0xFF, addr & 0xFF])
        data_out.append((data >> 8) & 0xFF)
        data_out.append(data & 0xFF)

        msg_out = can.Message(is_extended_id=False, arbitration_id=can_arb_id,
                              data=data_out)

        self.bus.send(msg_out)
        self.counters['can_tx_msg'] += 1

        responding_dev_ids = list()
        done = False

        while done is False:
            msg_in = self.bus.recv(timeout_ms/1000.0)

            if msg_in is None:
                done = True
                continue
            elif msg_in.is_error_frame:
                self.counters['can_error_frame'] += 1
                raise CanErrorFrame("Received error frame after HLP write")

            self.counters['can_rx_msg'] += 1

            # Mask out 3 LSBs, those are the cmd bits in arbitration id
            cmd = msg_in.arbitration_id & 0x0007

            if cmd != CanHlpCmd.WRITE_RESP:
                self.counters['hlp_wrong_response'] += 1
                raise CanHlpWrongResponse('Expected write response, got {:02x}'.format(cmd))

            dev_id_in = msg_in.arbitration_id >> 3
            if dev_id_in == self.C_BROADCAST_ID:
                self.counters['hlp_wrong_id'] += 1
                raise CanHlpWrongId("Sent broadcast write, got write response with broadcast ID")
            else:
                print("Got write response from {:02x}".format(dev_id_in))
                responding_dev_ids.append(dev_id_in)

        self.counters['hlp_write'] += 1

        return responding_dev_ids

    def flushHLP(self, timeout_ms=500):
        """Flush any incoming CAN messages by discarding received messages until
           there are no new messages before the specified timeout.

        Args:
            timeout_ms (uint): Timeout in milliseconds to wait for messages
        """
        msg = self.bus.recv(timeout_ms/1000.0)  # Timeout in seconds.

        while msg is not None:
            self.counters['hlp_flushed'] += 1
            msg = self.bus.recv(timeout_ms/1000.0)  # Timeout in seconds.
