"""Python to Systemverilog Simulation interface"""

import binascii
import errno
import logging
import os
import socket
import time
import random

from queue import Queue, Empty  # python 3.x
from threading import Thread, Lock
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy

from module_includes import *

from communication import Communication

COMM_SIM_PORT = 32225
GLOBAL_READ_TIMEOUT = 600
GLOBAL_WRITE_TIMEOUT = 60
GLOBAL_CONNECTION_TIMEOUT = 600

rundir = os.path.dirname(os.path.realpath(__file__)) +'/../../../../sim/regression/run/'

class SimulationServer:
    """RPC server handling communication between Python and Systemverilog"""
    stop_server = False

    def __init__(self, comm_sim_port=COMM_SIM_PORT):
        self.comm_port = comm_sim_port
        self.server = SimpleXMLRPCServer(("localhost", self.comm_port), logRequests=False)
        self.thrd = Thread(target=self.run, daemon=True)
        self.server.register_function(self.send_close,"send_close")

    def run(self):
        while not self.stop_server:
            self.server.handle_request()

    def send_close(self):
        return True

    def stop(self):
        self.stop_server = True
        ServerProxy(f"http://localhost:{self.comm_port}").send_close()

    def start(self):
        """Start RPC server"""
        self.thrd.start()

class SocketComm(object):
    """General low-level communication bridge between python and SystemVerilog simulations.

    This wrapper sends read/write actions to a socket, which
    will be checked by a simulation testbench and then forwarded to
    the simulation environment.
    """

    def __init__(self, host, verbose=0):
        self.verbose = verbose
        if isinstance(host[0], (list, tuple)):
            self.host = host
        else:
            self.host = [host]
        num_con = len(self.host)
        self.conn = [None]*num_con
        self.sock = [None]*num_con
        self.conn_thread = [None]*num_con
        self.en_timeout = True
        self.stopped = False
        self.open()
        self.wait_for_connection()

    def __del__(self):
        self.close()

    def open(self):
        """Open socket for data exchanges"""
        for i in range(len(self.host)):
            self.sock[i] = self._open(self.host[i])

    @staticmethod
    def _open(host):
        """Open socket for data exchanges"""
        assert host is not None, "Host must be defined before calling open"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(host)
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                raise OSError(e.errno, f"Socket address {host[1]} is already in use, a simulation is possibly running on this machine")
            else:
                raise
        sock.setblocking(False)
        sock.listen(1) # Accept only single client
        return sock

    def wait_for_connection(self):
        """Wait for a connection on a socket, non-blocking"""
        for i in range(len(self.sock)):
            self.conn_thread[i] = Thread(target=self._wait_for_connection, args=(i,), daemon=True)
            self.conn_thread[i].start()

    def _wait_for_connection(self, con_num):
        """Wait for a connection on a socket, non-blocking"""
        count = 0
        while self.conn[con_num] is None:
            try:
                self.conn[con_num], _ = self.sock[con_num].accept()
            except BlockingIOError:
                time.sleep(0.1)
                count += 0.1
                if count > GLOBAL_CONNECTION_TIMEOUT:
                    return
            except OSError:
                return

    def close(self):
        """Close socket to sim"""
        self.stopped = True
        for conn in self.conn:
            try:
                if conn is not None: # Try to get sim to close socket so it can exit with good exit code
                    sent = conn.send(bytearray(("EXIT\n").encode("utf-8"))) # If this is first socket to send, this will stop sim, other sockets will throw broken pipe here
                    sent = conn.send(bytearray(("EXIT\n").encode("utf-8"))) # Should throw broken pipe if sim is not busy
                    count = 0
                    while(sent != 0 and count < 3): # if not wait a bit and try again
                        time.sleep(0.5)
                        sent = conn.send(bytearray(("EXIT\n").encode("utf-8")))
                        count += 1
                    conn.close() # Force close if still not closing remotely
            except OSError:
                pass
        for sock in self.sock:
            try:
                if sock is not None:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
            except OSError:
                pass

    def check_conn(self, conn_num=0):
        """Waits for client connection or errors out"""
        if self.conn[conn_num] is None:
            self.conn_thread[conn_num].join(timeout=GLOBAL_CONNECTION_TIMEOUT)
            if self.conn[conn_num] is None:
                # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                raise KeyboardInterrupt(f"\n\n**** ERROR: Python reached timeout of {GLOBAL_CONNECTION_TIMEOUT}s waiting for connection to sim, exiting ***\n\n")
        return self.conn[conn_num]

    def fetch(self, conn_num=0):
        """Fetch lines from socket"""
        conn = self.check_conn(conn_num)
        data = b''
        count = 0
        while len(data) == 0 or data.decode()[-1] != '\n':
            try:
                chunk = conn.recv(1024)
            except BlockingIOError:
                if self.stopped:
                    break
                time.sleep(0.01)
                if self.en_timeout:
                    count += 0.01
                    if count > GLOBAL_READ_TIMEOUT:
                        # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                        raise KeyboardInterrupt(f"\n\n**** ERROR: Python reached timeout of {GLOBAL_READ_TIMEOUT}s waiting response from sim, exiting ****\n\n")
            except (ConnectionResetError, OSError):
                if self.stopped:
                    break
                # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                raise KeyboardInterrupt("\n\n**** ERROR: Simulator closed connection, exiting ****\n\n")
            else:
                if chunk == b'':
                    if self.stopped:
                        break
                    # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                    raise KeyboardInterrupt("\n\n**** ERROR: Simulator closed connection, exiting ****\n\n")
                data += chunk
        if self.verbose:
            print(f"RX: {data}")
        data = data.decode()
        return data.split('\n')[:-1]

    def flush(self, data=None, conn_num=0):
        """Flush data to socket"""
        conn = self.check_conn(conn_num)
        msg = ""
        if isinstance(data, str):
            msg = data
        elif isinstance(data, (list, tuple)):
            for line in data:
                msg += line
        elif isinstance(data, Queue):
            try:
                while True:
                    line = data.get_nowait()  # or q.get(timeout=.1)
                    msg += line
            except Empty:
                pass  # finished
        else:
            raise ValueError("Unknown data type passed to flush")
        if len(msg) == 0:
            msg = "NOP\n"
        msg = bytearray((msg).encode("utf-8"))
        assert len(msg) < 1024, "Buffer overflow in sending data"
        assert msg.decode()[-1] == '\n', f"Missing newline at end of string {msg}"
        if self.verbose:
            print(f"TX: {msg}")
        sent_tot = 0
        count = 0
        while sent_tot < len(msg):
            try:
                sent = conn.send(msg[sent_tot:])
            except BlockingIOError:
                if self.stopped:
                    break
                time.sleep(0.01)
                if self.en_timeout:
                    count += 0.01
                    if count > GLOBAL_WRITE_TIMEOUT:
                        # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                        raise KeyboardInterrupt(f"\n\n**** ERROR: Python reached timeout of {GLOBAL_WRITE_TIMEOUT}s waiting for writing to sim, exiting ****\n\n")
            except ConnectionResetError:
                if self.stopped:
                    break
                # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                raise KeyboardInterrupt("\n\n**** ERROR: Simulator closed connection, exiting ****\n\n")
            else:
                if sent == 0:
                    if self.stopped:
                        break
                    # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
                    raise KeyboardInterrupt("\n\n**** ERROR: Simulator closed connection, exiting ****\n\n")
                sent_tot += sent
        return 0

class UsbCommSim(Communication, SocketComm):
    """Usb Communication wrapper connecting to simulation.

    This wrapper writes read/write actions to a set of fifos, which
    will be checked by a simulation testbench and then forwarded to
    the simulation environment

    """

    def __init__(self, ctlOnly=True):
        Communication.__init__(self)
        if ctlOnly:
            SocketComm.__init__(self, host=("localhost", 32226))
        else:
            SocketComm.__init__(self, host=(("localhost", 32226), ("localhost", 32227), ("localhost", 32228)))
        self.max_retries = 1
        self.ctlOnly = ctlOnly

        self.dp0_queue = Queue()
        self.dp_rx_queue = [Queue()]*3

    def flush_dp0(self):
        """Flush DP0: send data to fifo"""
        SocketComm.flush(self, self.dp0_queue, 0)

    def _do_write_dp0(self, data):
        string = ''.join(f"{byte:02x}" for byte in data)
        self.dp0_queue.put(string + '\n')
        self.flush_dp0()

    def _do_read_dp1(self, size):
        return self._read_data_sim(0, size, 10)

    def _do_read_dp2(self, size):
        assert not self.ctlOnly, "DP2 not enabled"
        return self._read_data_sim(1, size, 10)

    def _do_read_dp3(self, size):
        assert not self.ctlOnly, "DP3 not enabled"
        return self._read_data_sim(2, size, 10)

    def _get_data(self, fifo):
        if self.dp_rx_queue[fifo].empty():
            lines = self.fetch(fifo)
            for line in lines:
                self.dp_rx_queue[fifo].put(line)
        try:
            return self.dp_rx_queue[fifo].get_nowait()
        except Empty:
            return None

    def _read_data_sim(self, fifo, length, max_count=10):
        """Read data from fifo file"""
        cnt = 0
        remaining = length
        assert length % 4 == 0
        msg = b""
        last_read = False
        seconds = 0
        while (remaining > 0) and (seconds < GLOBAL_READ_TIMEOUT):
            string = self._get_data(fifo)

            hex_data = binascii.unhexlify(string)
            chunk = bytearray(hex_data)
            msg += chunk
            remaining -= len(chunk)
            if remaining > 0:
                if cnt >= max_count:
                    #print("Read {0}, remaining: {1}".format(len(msg),remaining))
                    if last_read:
                        break
                if len(chunk) == 0:
                    #print(">> communication >> usbcommsim >> _read_data_sim >> ALIVE!, remaining: {0}".format(remaining))
                    time.sleep(1)
                    seconds += 1
                    cnt += 1
                else:
                    cnt = 0 # Reset retry-counter
        if seconds == GLOBAL_READ_TIMEOUT:
            # Raise KeyboardInterrupt as it ends the whole unittest and doesn't continue
            raise KeyboardInterrupt("\n\n**** ERROR: Python reached timeout of {0}s waiting for a GBT read, simulation possibly stuck, exiting ****\n\n".format(GLOBAL_READ_TIMEOUT))
        return msg

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

class GbtxSim(SocketComm):
    """Gbt Communication wrapper connecting to simulation.

    This wrapper writes read/write actions to a set of fifos, which
    will be checked by a simulation testbench and then forwarded to
    the simulation environment
    """

    SWT_CODE = 0x3
    SOP_CODE = 0x1
    EOP_CODE = 0x2

    def __init__(self, gbtxnum=0):
        super().__init__(host=("localhost", 32220+gbtxnum))
        self.gbtxnum = str(gbtxnum)

        self.logger = logging.getLogger("Gbtx"+self.gbtxnum+"Sim")

        self.tx_queue = Queue()
        self.swt_queue = Queue()
        self.data_queue = Queue()

    def writeToGbt(self,data):
        """Write to GBT port. Expects tuple (valid,data). Data is 10 byte bytearray"""
        valid,word = data
        assert len(word) == 10, "Data is not 80bit"

        string = ''.join(f"{byte:02x}" for byte in word)
        self.tx_queue.put(f"{valid:d} {string}\n")
        SocketComm.flush(self, data=self.tx_queue)

    def readFromGbt(self):
        """Read all data from gbt port"""
        lines_str = self.fetch()
        lines = [(line[0], line[1:]) for line in lines_str]
        data = []
        try:
            for line in lines:
                hexdata = binascii.unhexlify(line[1].strip())
                data.append((int(line[0]), hexdata))
        except binascii.Error as e:
            self.logger.exception("readFromGbt failed while decoding")
            self.logger.error("Lines: %r", lines)
            raise e
        return data

    def read_sort_data(self):
        data = self.readFromGbt()
        for v, d in data:
            package_type = d[0] >> 4
            if v or package_type in [self.SOP_CODE, self.EOP_CODE]:
                self.data_queue.put((v, d))
            elif package_type == self.SWT_CODE:
                self.swt_queue.put(d)

    def get_data(self):
        """return a GBT data word (datavalid=1)"""
        if self.data_queue.empty():
            self.read_sort_data()
        try:
            return self.data_queue.get_nowait()
        except Empty:
            return None, None

    def get_swt(self):
        """return a single word transaction"""
        if self.swt_queue.empty():
            self.read_sort_data()
        try:
            return self.swt_queue.get_nowait()
        except Empty:
            return None

class GbtCruGbtxBridge(object):
    """GBT communication bridge between GBTX and GBT_CRU simulations"""
    GBT_CRU_TX = 3
    GBT_CRU_RX = 2
    GBTX_TX = 1
    GBTX_RX = 0

    def __init__(self, server):
        super(GbtCruGbtxBridge, self).__init__()
        self.gbtx0_queue = Queue()

        self.mutex = Lock()

        self.files_names = [
            (rundir + 'fifo_gbtx0_fp', 'w'),
            (rundir + 'fifo_gbtx0_tp', 'r'),
            (rundir + 'fifo_gbt_cru_fp','w'),
            (rundir + 'fifo_gbt_cru_tp','r')
        ]
        self.files = [None, None, None, None]
        self.open()

        self.server = server
        self.server.register_function(self.flush_gbtx, "flush_gbtx0")
        self.server.register_function(self.clear_gbtx, "clear_gbtx0")
        self.server.register_function(self.flush_gbt_cru,"flush_gbt_cru")
        self.server.register_function(self.clear_gbt_cru, "clear_gbt_cru")

    def open(self, filelist=range(4)):
        """(re)open buffer files for data exchanges"""

        for i in filelist:
            name, openmode = self.files_names[i]
            if not os.path.exists(name):
                open(name, 'w').close()
            fifo = open(name, openmode)
            fifo.seek(0, os.SEEK_END)
            self.files[i] = fifo

    def close(self):
        pass

    def flush_gbt_cru(self):
        """Flush GBT CRU - Copy from GBTX"""
        msg = self.files[self.GBTX_TX].read()
        if len(msg) == 0:
            msg = "NOP" + "\n"
        self.files[self.GBT_CRU_RX].write(msg)
        self.files[self.GBT_CRU_RX].flush()
        return 0

    def flush_gbtx(self):
        """Flush gbtx: Copy from CRU"""
        msg = self.files[self.GBT_CRU_TX].read()
        if len(msg) == 0:
            msg = "NOP" + "\n"
        self.files[self.GBTX_RX].write(msg)
        self.files[self.GBTX_RX].flush()
        return 0

    def clear_gbt_cru(self):
        """Clear buffers: Close and reopen files"""
        #print(">> communication >> usbcommsim >> clear >> called!")
        self.mutex.acquire()
        try:
            self.files[self.GBT_CRU_RX].close()
            self.files[self.GBT_CRU_TX].close()
            self.open([self.GBT_CRU_RX,self.GBT_CRU_TX])
        finally:
            self.mutex.release()
        return 0

    def clear_gbtx(self):
        """Clear buffers: Close and reopen files"""
        #print(">> communication >> usbcommsim >> clear >> called!")
        self.mutex.acquire()
        try:
            self.files[self.GBTX_RX].close()
            self.files[self.GBTX_TX].close()
            self.open([self.GBTX_RX,self.GBTX_TX])
        finally:
            self.mutex.release()
        return 0

class Wb2GbtxComm(Communication, GbtxSim):
    """Usb Communication wrapper connecting to GbtxLink of Simulation.

    This wrapper writes read/write actions to a set of fifos, which
    will be checked by a simulation testbench and then forwarded to
    the simulation environment

    """

    def __init__(self, gbtxnum=0, create_raw_data_files=True):
        self.dp2_file = None
        GbtxSim.__init__(self, gbtxnum=gbtxnum)
        Communication.__init__(self)
        if create_raw_data_files:
            self.dp2_file = open('raw_data_dp2_gbtx' + gbtxnum + '.dat', 'wb')

    def __del__(self):
        if self.dp2_file is not None:
            self.dp2_file.close()

    def flush(self):
        Communication.flush(self)

    def send_idle(self, numToSend=1):
        gbt_word = bytearray(10)
        for _ in range(numToSend):
            self.writeToGbt((0, gbt_word))

    def send_trigger(self, triggerType=0x10, bc=0xabc, orbit=0x43215678):
        """Provides trigger to the XCKU

        Inputs:
        trigger type: 12 bit
        bc:           12 bit
        orbit:        32 bit (only 31 used on the RUv0_CRU)

        TODO: update with proper documentation"""
        assert triggerType | 0xFFFF == 0xFFFF
        assert bc | 0xFFF == 0xFFF
        assert orbit | 0xFFFFFFFF == 0xFFFFFFFF
        trigger_data = binascii.unhexlify(f"{orbit:08x}{bc:04x}{triggerType:08x}")
        self.writeToGbt((1, trigger_data))

    def send_bc_counter(self, numToSend=1, start_bc=0, start_orbit=0, bc_wrap=3564):
        """Send a number of trigger messages with DATAVALID=0, only BC and ORBIT filled"""

        assert bc_wrap | 0xFFF == 0xFFF
        assert start_bc | 0xFFF == 0xFFF
        assert start_orbit | 0xFFFFFFFF == 0xFFFFFFFF
        assert start_bc < bc_wrap

        orbit = start_orbit
        bc = start_bc

        for _ in range(numToSend):
            trigger_data = binascii.unhexlify(f"{orbit:08x}{bc:04x}00000000")
            self.writeToGbt((0, trigger_data))
            if bc == (bc_wrap - 1):
                bc = 0
                orbit += 1
            else:
                bc += 1

    def send_invalid_swt(self, numToSend=1):
        """Send INVALID SWTs, as defined by GBT word [75:32] != 0x0

        SWT[79:76] SWT PREFIX
        SWT[75:32] UNUSED, and must be 0x0 to be valid
        SWT[31:0]  SWT Content

        This function randomly assigns one of the bytes in the unused range to a non-zero value and transmits it.
        """
        for _ in range(numToSend):
            gbt_word = bytearray(10)
            # Randomly assign one of the unused bytes to non-zero value
            gbt_word[random.randrange(1,5)] = random.randrange(1,0xFF)
            # Set SWT prefix
            gbt_word[0] = (self.SWT_CODE << 4)
            self.writeToGbt((0, gbt_word))

    def _do_write_dp0(self, data):
        for chunk in chunks(data, 4):
            chunk = chunk[::-1] # Reverse on write
            gbt_word = bytearray(10)
            gbt_word[6:10] = chunk
            #gbt_word[2:6] = chunk # uncomment for DWC
            gbt_word[0] = (self.SWT_CODE << 4)|(gbt_word[0] & 0x0F)
            self.writeToGbt((0, gbt_word))

    def _do_read_dp1(self, size):
        result = bytearray()
        reads_remaining = size/4
        while (reads_remaining > 0):
            data = self.get_swt()
            if data is not None:
                reads_remaining -= 1
                result += data[6:10][::-1] # Reverse on read
        return result

    def _do_read_dp2(self, size):
        """Implementation of reading from DP2. Read from GBTx datavalid"""
        result = bytearray()
        while (len(result) < size):
            gbt_datavalid, gbt_word = self.get_data()
            if gbt_word is not None:
                # Split packet
                word0 = bytearray(b'\x00\x00') + gbt_word[0:2]
                if gbt_datavalid:
                    word0[0]=0x80
                word1 = gbt_word[2:6]
                word2 = gbt_word[6:10]

                result += word0[::-1]
                result += word1[::-1]
                result += word2[::-1]
        if self.dp2_file:
            self.dp2_file.write(result)
        return result

    def _do_read_dp3(self, size):
        """Implementation of reading from DP3"""
        raise NotImplementedError

    def discardall_dp1(self,maxReads=10):
        return True
    def discardall_dp2(self,maxReads=10):
        return True
    def discardall_dp3(self,maxReads=10):
        return True


class SimComm(SocketComm):
    """Simulation environment communication bridge between python and SystemVerilog simulations.

    This wrapper writes read/write actions to a socket, which
    will be checked by a simulation testbench and then forwarded to
    the simulation environment.
    """

    CLR_CODE = 0x1
    DS_CODE  = 0x2
    PA3_CODE = 0x3

    def __init__(self):
        super().__init__(host=("localhost", 32224))
        self.tx_queue = Queue()

    def flush(self):
        super().flush(self.tx_queue, 0)

    def _write_to_sim_comm(self, data):
        """
        Write to sim_comm.
        Expects a word 'data'.
        Data is 5 byte bytearray
        """
        assert len(data) == 5, "Data is not 40bit"
        string = ''.join(f'{byte:02x}' for byte in data)
        self.tx_queue.put(string + '\n')
        self.flush()

    def enable_cable_length_randomization(self):
        """enables the randmisation of the SAMTEC cable length in the Systemverilog testbench"""
        enable = 1
        data = bytearray(5)
        data[0] = self.CLR_CODE
        data[4] = enable
        self._write_to_sim_comm(data)

    def disable_cable_length_randomization(self):
        """disables the randmisation of the SAMTEC cable length in the Systemverilog testbench"""
        disable = 0
        data = bytearray(5)
        data[0] = self.CLR_CODE
        data[4] = disable
        self._write_to_sim_comm(data)

    def set_dipswitches(self, feeid, pa3_bits=0b11):
        """Sets the dipswitches to a certain value"""
        assert feeid    | 0xFF == 0xFF, feeid
        assert pa3_bits | 0x3 == 0x3, pa3_bits
        ds = (feeid<<2) | pa3_bits
        data = bytearray(5)
        data[0] = self.DS_CODE
        data[3] = (ds>>8) & 0xFF
        data[4] = (ds>>0) & 0xFF
        self._write_to_sim_comm(data)

    def set_pa3_in(self, los, lol):
        """Sets the dipswitches to a certain value"""
        assert los    | 0x1 == 0x1, los
        assert lol    | 0x1 == 0x1, lol
        ds = (los<<8) | (lol<<9)
        data = bytearray(5)
        data[0] = self.PA3_CODE
        data[3] = (ds>>8) & 0xFF
        data[4] = (ds>>0) & 0xFF
        self._write_to_sim_comm(data)
