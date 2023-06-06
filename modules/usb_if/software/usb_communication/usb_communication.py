"""Communication classes implementation, used to communicate with a board, using the
FX3 chip and usb_if firmware.

The provided communication classes are either direct via libusb, over
the usb_comm server, or via simulation. They all share the common base
class Communication

"""

from queue import Queue, Empty  # python 3.x
from threading import Thread

import logging
import os
import signal
import socket
import subprocess
import sys
import time
import usb

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../../board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

import communication


class NetUsbTimeoutException(Exception):
    """basic class to handle netusbcomm timeout exception"""
    def __init__(self, signum=0):
        super(NetUsbTimeoutException, self).__init__()
        self.signum = signum

    def __signum__(self):
        return repr(self.signum)

def sig_alarm_handler(signum, frame):
    #print('received signal %s'%signum)
    raise NetUsbTimeoutException(signum)

def _cmp_serial(device, serialNr):
    """Compare the serial number of a device with the given serial number"""
    serial_str = usb.util.get_string(device, device.iSerialNumber)
    return serial_str[:-1] == serialNr

class PyUsbComm(communication.Communication):
    """Implementation of Communication class.

    This implements the communication class by establishing a direct
    Connection to the usb port via PyUsb.

    """
    _TIMEOUT_ERRNO = 110

    def __init__(self,
                 VID=0x04b4,
                 PID=0x0008,
                 IF=2,
                 PacketSize=1024,
                 serialNr=None,
                 enable_rderr_exception=False):

        super(PyUsbComm, self).__init__()
        if serialNr is not None:
            self.dev = usb.core.find(
                idVendor=VID, idProduct=PID, custom_match=lambda d: _cmp_serial(d, serialNr))
        else:
            self.dev = usb.core.find(idVendor=VID, idProduct=PID)

        if self.dev is None:
            raise Exception("no USB device found")

        cfg = self.dev.get_active_configuration()
        itf = cfg[(IF, 0)]
        self.epo = itf[0]  # endpoint towards the FX3 (in)
        self.epi = itf[1]  # endpoint from the FX3 (out) - DP1
        self.dp2 = itf[2]  # endpoint from the FX3 (out) - DP2
        self.dp3 = itf[3]  # endpoint from the FX3 (out) - DP3

        self._PacketSize = PacketSize

    def _do_write_dp0(self, data):
        written = self.epo.write(data)
        assert written == len(data), "Data mismatch: Bytes written: {0}, Data length: {1}".format(written,len(data))

    def _do_read_dp1(self, size):
        return self._read_data(self.epi, size)

    def _do_read_dp2(self, size):
        return self._read_data(self.dp2, size)

    def _do_read_dp3(self, size):
        return self._read_data(self.dp3, size)

    def _read_data(self, endpoint, length):
        """Read at least <length> bytes of data from the Endpoint.

        Tries to read <length> bytes from the endpoint, with a
        granularity of _PacketSize. This is due to the restrictions of
        the libusb implementation, which requires a readout size as
        multiple of the packet size to prevent data loss.

        Returns when at least <length> bytes have been read, or if a
        Timeout occurs.

        """
        remaining = length
        assert length % 4 == 0
        msg = bytearray()
        try:
            while remaining > 0:
                chunk = endpoint.read(self._round_to_packet_size(remaining))
                msg.extend(chunk)
                remaining -= len(chunk)
        except usb.core.USBError as e_usb:
            if e_usb.errno != PyUsbComm._TIMEOUT_ERRNO:
                raise

        return msg

    def _round_to_packet_size(self, num):
        """Round given read size to minimum packet size of usb transaction"""
        return num - num % - self._PacketSize


def enqueue_output(out, queue):
    """Add message to message_queue"""
    for line in iter(out.readline, b''):
        queue.put(line)

ON_POSIX = 'posix' in sys.builtin_module_names


class UsbCommServer:
    """ Run usb_comm Server in subprocess.

    Convenience class to start / stop the usb_comm software from python
    """

    def __init__(self, executable=os.path.join(script_path, '../usb_comm_server/build/usb_comm'), serial=None):
        self.executable = os.path.realpath(executable)
        if not os.path.exists(self.executable):
            raise FileNotFoundError(f"usb_comm program not found at {self.executable}, please compile it")
        self.process = None
        self.message_queue = None
        self.message_thread = None
        self.logger = logging.getLogger("UsbCommServer")
        self.serial=serial

    def start(self):
        """Start the USB Comm Server program"""
        exe_args = [self.executable]
        if self.serial is not None:
            exe_args = [self.executable,
                        "--serial_number",
                        "{0}".format(self.serial)]
        self.process = subprocess.Popen(exe_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, close_fds=ON_POSIX)
        self.message_queue = Queue()
        self.message_thread = Thread(target=enqueue_output, args=(
            self.process.stdout, self.message_queue))
        self.message_thread.start()

    def stop(self):
        """Send stop signal to USB Comm Server program"""
        self.process.stdin.write(b'quit\n')
        self.process.stdin.flush()

    def is_stopped(self):
        """Check if the server is stopped or still running"""
        stopped = False
        if self.process:
            poll = self.process.poll()
            if poll is not None:
                stopped = True
                if poll < 0:
                    self.logger.warning("UsbCommServer terminated with signal %d",-poll)
        return stopped

    def read_messages(self):
        """Read all messages sent by the usb comm server program."""
        msg = ""
        try:
            while True:
                line = self.message_queue.get_nowait()  # or q.get(timeout=.1)
                msg += line.decode("utf-8")
        except Empty:
            pass  # finished
        return msg

def _create_connection_nonblock(host,port):
    """Create a non-blocking connection via socket"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)
    try:
        sock.connect((host,port))
    except BlockingIOError as be:
        if be.errno == 115:
            pass
        else:
            raise be
    return sock

class NetUsbComm(communication.Communication):
    """Network usb communication class.

    This class implements the Communication class by implementing a
    network communication with the UsbComm C++ program.

    """

    def __init__(self,
                 ctlOnly=False,
                 HOSTNAME='127.0.0.1', #'localhost'
                 PORT_CONTROL=30000,
                 PORT_DATA0=30001,
                 PORT_DATA1=30002,
                 Timeout=None,
                 enable_rderr_exception=False):
        super(NetUsbComm, self).__init__()

        self.socketControl = None
        self.socketData0 = None
        self.socketData1 = None

        self.timeout = Timeout
        self.hostname = HOSTNAME
        self.port_control = PORT_CONTROL
        self.port_data0 = PORT_DATA0
        self.port_data1 = PORT_DATA1

        self.ctlOnly = ctlOnly
        self.open_connection(ctlOnly)

        self.write_retries = 10
        self.server = None

        signal.signal(signal.SIGALRM, sig_alarm_handler)

    def stop(self):
        self.close_connections()

    def _read_data(self, sock, length):
        """read data from socket"""
        remaining = length
        assert length % 4 == 0
        msg = b""
        try:
            while remaining > 0:
                signal.alarm(int(10*self.timeout))
                chunk = sock.recv(remaining)
                msg += chunk
                remaining -= len(chunk)
        except NetUsbTimeoutException as e:
            #self.logger.warning(traceback.format_exc())
            pass
        except socket.timeout:
            #self.logger.warning(traceback.format_exc())
            pass
        except BlockingIOError as be:
            #self.logger.warning(traceback.format_exc())
            pass
        finally:
            signal.alarm(0)
        return msg

    def set_server(self, server):
        self.server = server

    def open_connection(self,ctlOnly=False):
        self.ctlOnly = ctlOnly
        signal.alarm(int(10*self.timeout))
        try:

            self.socketControl = socket.create_connection(
                (self.hostname, self.port_control), self.timeout)
    #        self.socketControl = _create_connection_nonblock(self.hostname,self.port_control)
            if ctlOnly:
                self.socketData0 = None
                self.socketData1 = None
            else:
                self.socketData0 = socket.create_connection(
                    (self.hostname, self.port_data0), self.timeout)
                self.socketData1 = socket.create_connection(
                    (self.hostname, self.port_data1), self.timeout)
               #self.socketData0 =_create_connection_nonblock(self.hostname,self.port_data0)
               #self.socketData1 =_create_connection_nonblock(self.hostname,self.port_data1)
            time.sleep(0.1)
        except:
            raise
        finally:
            signal.alarm(0)

    def _reconnect_attempt(self):
        """Try to reconnect to server"""

        #check if server is running
        if self.server and self.server.is_stopped():
            self.server.start()
#        else:
#            try:
#                self.server.stop()
#            except Exception as e:
#                self.logger.exception("Error while reconnect: shutdown server")
#            time.sleep(0.5)
#            self.server.start()

        time.sleep(0.5)
        self.logger.info("Attempt to reconnect to server")
        self.close_connections()
        time.sleep(0.5)
        self.open_connection(ctlOnly = self.ctlOnly)
        time.sleep(0.5)


    def close_connections(self):
        """Close all open sockets"""
        for sock in (self.socketControl,
                     self.socketData0,
                     self.socketData1):
            try:
                if sock is not None:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
            except:
                self.logger.exception("Error while shutting down socket {0}".format(sock))
        self.socketControl = None
        self.socketData0 = None
        self.socketData1 = None


    def _do_write_dp0(self, data):
        try:
            signal.alarm(15)
            self.socketControl.sendall(data)
            signal.alarm(0)
        except NetUsbTimeoutException as e:
            self.logger.exception("error while sendall(data), timeout run with %s",e)
            self.logger.error("Data may have been lost due to %s",e)
            self._reconnect_attempt()
        except:
            self.logger.exception("error while sendall(data)")
            self._reconnect_attempt()

    def _do_read_dp1(self, size):
        return self._read_data(self.socketControl, size)

    def _do_read_dp2(self, size):
        if self.socketData0 is None:
            raise Exception(
                "Communication module was started with Control only")
        return self._read_data(self.socketData0, size)

    def _do_read_dp3(self, size):
        if self.socketData1 is None:
            raise Exception(
                "Communication module was started with Control only")
        return self._read_data(self.socketData1, size)
