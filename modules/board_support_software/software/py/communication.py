"""Communication classes for the RU main FPGA design.

The provided communication classes are either direct or via simulation. They all share the common base class Communication
"""

import logging

from collections import defaultdict
from struct import unpack


class WishboneReadError(Exception):
    """basic class to define a wishbone read error exception"""

    def __init__(self, value="", data=0, address=0, rderr_flag=0):
        super(WishboneReadError, self).__init__()
        self.value = value.format(data, address, rderr_flag)
        self.data = data
        self.address = address
        self.rderr_flag = rderr_flag

    def __str__(self):
        return repr(self.value)

    def __data__(self):
        return repr(self.data)

    def __address__(self):
        return repr(self.address)

    def __rderr_flag__(self):
        return repr(self.rderr_flag)

    def print_info(self):
        """returns the args of the exception"""
        print("rderr_flag: {0}".format(self.rderr_flag))
        print("data: {0}".format(self.data))
        print("address: {0}".format(self.address))


class AddressMismatchError(Exception):
    """basic class to define an error mismatch between the address requested by
    the read command and the one received in the packafe read from the board"""
    def __init__(self, value="", requested_address=0, rd_address=0, rderr_flag=0):
        super(AddressMismatchError, self).__init__()
        self.value = value.format(requested_address, rd_address, rderr_flag)
        self.requested_address = requested_address
        self.rd_address = rd_address
        self.rderr_flag = rderr_flag

    def __str__(self):
        return repr(self.value)

    def __requested_address__(self):
        return repr(self.requested_address)

    def __rd_address__(self):
        return repr(self.rd_address)

    def __rderr_flag__(self):
        return repr(self.rderr_flag)


def _get_wb_reads(data):
    """ Returns a byte array to a tuple list [(addr,data)] """
    assert len(data) % 4 == 0
    vals = unpack('HH' * int(len(data) / 4), data)
    addr = vals[1::2]
    dats = vals[0::2]
    return list(zip(addr, dats))


def _as_int_array(data):
    """Return data byte stream as list of unsigned integers"""
    assert len(data) % 4 == 0
    return unpack('I' * int(len(data) / 4), data)


class Communication(object):
    """Basic Communication class between Host and Device.

    This abstract class provides the basic communication blocks used
    to write and read data between chip and host.

    Access to Wishbone is possible via single_write() or single_read()
    To send a batch of commands, the functions register_write(),
    register_read(), flush() and read_results() are used. In both
    cases, results are written as a 2-tuple in the form (addr,data).


    Access to data ports is given via read_DP2() and read_DP3(). The
    result is given as array of 4 byte ints.

    This is an abstract class, and is NOT intended to be used
    directly. Instead, use the actual implementations PyUsbComm,
    NetUsbComm, UsbCommSim, CruSwtCommunication, or Wb2GbtxComm.
    """

    def __init__(self, enable_rderr_exception=False):
        self._buffer = bytearray()
        self._read_bytes = 0
        self._enable_rderr_exception = enable_rderr_exception
        self.logger = logging.getLogger("Communication")
        self.log = True
        self.max_retries = 10

    def enable_log(self):
        """enables the exception throw when receiving a wishbone read error flag"""
        self.log = True

    def disable_log(self):
        """disables the exception throw when receiving a wishbone read error flag"""
        self.log = False

    def enable_rderr_exception(self):
        """enables the exception throw when receiving a wishbone read error flag"""
        self._enable_rderr_exception = True

    def disable_rderr_exception(self):
        """disables the exception throw when receiving a wishbone read error flag"""
        self._enable_rderr_exception = False

    def stop(self):
        """Perform any operation on close"""
        pass

    def _lock_comm(self):
        """Method allowing (but not forcing if not needed) to implement a locking mechanism in derived classes

           By default, the lock is kept only for the duration of a single transaction
           `keep_lock=True` allows to prevent unlocking in between atomic operations and requires a manual release
           via `release_kept_lock=True`.
           This feature is to be used with care in order not to starve DCS, but necessary e.g. for writing a
           new bitfile to the flash which should not be interrupted.

           For the moment, locking is only needed using DCS and CRU_ITS in parallel via the CRU.
           Other communication methods like CANbus, USB or RUv0, don't foresee such a mechanism.
        """
        pass

    def _unlock_comm(self):
        """Method allowing (but not forcing if not needed) to implement a locking mechanism in derived classes

           release_kept_lock allows to unlock a lock which was kept, see `_lock_comm` for details.
        """
        pass

    def single_write(self, module, address, data):
        """A Single write operation.

        Perform a single write operation to a given module and
        address. This sends the command directly to the
        device. Previously registered commands are not sent.

        """
        tmp_buffer = self._buffer
        self._buffer = bytearray()
        self._lock_comm()
        try:
            self.register_write(module, address, data)
            self.flush(lock=False)
        finally:
            self._unlock_comm()
        self._buffer = tmp_buffer

    def raw_sequence(self, sequence):
        tmp_buffer = self._buffer
        tmp_read_bytes = self._read_bytes
        self.buffer = bytearray()
        self._lock_comm()
        try:
            for command in sequence:
                module = (command >> 24) & 0x7F
                address = (command >> 16) & 0xFF
                data = command & 0xFFFF
                if (command >> 28) > 0x7:
                    self.register_write(module,address,data)
                    self.logger.debug("wrote to module " + hex(module) + " address " + hex(address) + " data " + hex(data))
                else:
                    self.register_read(module,address)
                    self.logger.debug("read from module "+ hex(module) + " address " + hex(address))
            self.flush(lock=False)

            val = _get_wb_reads(self._read_all_bytes(lock=False))
        finally:
            self._unlock_comm()
        self._buffer = tmp_buffer

        if(len(val)>0):
            self.logger.debug("readback: ")
        for v in range(len(val)):
            rd_data = val[v][1]
            complete_read_address = val[v][0] & 0x7FFF
            rderr_flag = (val[v][0] >> 15) & 1
            self.logger.debug("rd_data: " + hex(rd_data) + " complete_read_address: " + hex(complete_read_address) + " rderr_flag: " + hex(rderr_flag))

    def single_read(self, module, address, log=None):
        """A Single read operation.

        Perform a single read operation to a given module and
        address. This sends the command directly to the device and
        reads back the result. Previously registered commands are not
        sent.

        """
        if log is None:
            log = self.log

        tmp_buffer = self._buffer
        self._lock_comm()
        try:
            tmp_read_bytes = self._read_bytes
            self._buffer = bytearray()
            self._read_bytes = 0
            self.register_read(module, address)
            self.flush(lock=False)

            val = _get_wb_reads(self._read_all_bytes(lock=False))
        finally:
            self._unlock_comm()

        self._buffer = tmp_buffer
        self._read_bytes = tmp_read_bytes

        rd_data = val[0][1]
        complete_read_address = val[0][0] & 0x7FFF
        rderr_flag = (val[0][0] >> 15) & 1
        # rderr_flag validation
        if rderr_flag:
            message = ("The WbMstr reported a read error! data {0:04X}, "
                       "address {1:04X}, rderr_flag {2}")
            logmessage = message.format(
                rd_data, complete_read_address, rderr_flag)
            if self._enable_rderr_exception:
                if log:
                    self.logger.warning(logmessage)
                raise WishboneReadError(
                    message, rd_data, complete_read_address, rderr_flag)
            else:
                self.logger.error(logmessage)

        complete_address = module << 8 | address
        if complete_address != complete_read_address:
            message = ("The address read is different than the one requested! complete_address {0:04X},"
                       "complete_read_address {1:04X}, rderr_flag {2}")
            if log:
                logmessage = message.format(
                    complete_address, complete_read_address, rderr_flag)
                self.logger.warning(logmessage)
            raise AddressMismatchError(
                message, complete_address, complete_read_address, rderr_flag)

        if len(val) > 0:
            return val[0][1]
        else:
            return None

    def write_reg(self, module, address, data):
        """DEPRECATED! used for Probecard while waiting to modify local implementation"""
        raise DeprecationWarning("This function is deprecated, please use self.single write instead")
        self.single_write(module, address, data)

    def read_reg(self, module, address):
        """DEPRECATED! used for Probecard while waiting to modify local implementation"""
        raise DeprecationWarning("This function is deprecated, please use self.single read instead")
        return self.single_read(module, address)

    def register_write(self, module, address, data):
        """ Register a write register command in the buffer """
        assert module | 0x7F == 0x7F
        assert address | 0xFF == 0xFF
        data_low = data >> 0 & 0xFF
        data_high = data >> 8 & 0xFF

        self._buffer += bytearray([data_low, data_high,
                                   address, module | 0x80])

    def register_read(self, module, address):
        """ Register a read register command in the buffer """
        assert module | 0x7F == 0x7F
        assert address | 0xFF == 0xFF

        self._buffer += bytearray([0x00, 0x00, address, module])
        self._read_bytes += 4

    def register_read_custom_data(self, module, address, data):
        """ Register a read register command in the buffer with custom data field (not 0)"""
        assert module | 0x7F == 0x7F
        assert address | 0xFF == 0xFF
        assert data | 0xFFFF == 0xFFFF
        data_high = (data>>8) & 0xFF
        data_low  = (data>>0) & 0xFF

        self._buffer += bytearray([data_low, data_high, address, module])
        self._read_bytes += 4

    def flush(self, lock=True):
        """Flush the buffer.

        This function sends all previously registered commands to the
        device.

        """
        if lock:
            self._lock_comm()
        try:
            self._do_write_dp0(self._buffer)
        finally:
            if lock:
                self._unlock_comm()
        self._buffer = bytearray()

    def _read_all_bytes(self,log=None, lock=True):
        """Try to read all bytes of self._read_bytes"""
        if log == None:
            log = self.log

        retries = 0
        ret = bytearray()
        remaining = self._read_bytes
        if lock:
            self._lock_comm()
        try:
            while len(ret) < self._read_bytes and retries < self.max_retries:
                ret += self._do_read_dp1(remaining)
                remaining = self._read_bytes - len(ret)
                if len(ret) != self._read_bytes:
                    if log:
                        msg = "Result size mismatch. Expected %d bytes, read %d bytes. retry"
                        if retries > self.max_retries / 2:
                            self.logger.warning(msg, self._read_bytes,len(ret))
                        else:
                            self.logger.debug(msg, self._read_bytes,len(ret))

                retries += 1
        finally:
            if lock:
                self._unlock_comm()
        if log and len(ret) < self._read_bytes:
            self.logger.warning("Result size mismatch. Expected %d bytes, read %d bytes. Max number of retries reached",
                                self._read_bytes,len(ret))
        self._read_bytes = 0
        return ret

    def _check_result(self,val,log=None):
        """Check result of a _get_wb_reads list"""
        rd_data = val[1]
        complete_read_address = val[0] & 0x7FFF
        rderr_flag = (val[0] >> 15) & 1
        # rderr_flag validation
        if rderr_flag:
            message = ("The WbMstr reported a read error! data {0:04X}, "
                       "address {1:04X}, rderr_flag {2}")
            logmessage = message.format(
                rd_data, complete_read_address, rderr_flag)
            if self._enable_rderr_exception:
                if log:
                    self.logger.warning(logmessage)
                raise WishboneReadError(
                    message, rd_data, complete_read_address, rderr_flag)
            else:
                self.logger.error(logmessage)

    def read_results(self, log=None):
        """Read results from communication.

        This function reads the results from a previously flushed
        communication. The function expects 1 result per read command
        registered.

        Returns a List of data tuples in the form
        [(addr0,data0),(addr1,data1),...,(addrN,dataN)]

        """
        
        if log == None:
            log = self.log

        self._lock_comm()
        try:
            ret = self._read_all_bytes(log, lock=False)
        finally:
            self._unlock_comm()
        results = _get_wb_reads(ret)

        for val in results:
            self._check_result(val,log)

        return results

    def flush_and_read_results(self, log=None):
        """
        Combination of flush and read result encapsulated with LLA lock
        """
        self._lock_comm()
        try:
            self.flush(lock=False)
            results = self.read_results(log)
        finally:
            self._unlock_comm()
        return results

    def diagnose_read_results(self, log=None):
        """Read results for debugging and diagnose.

        This function reads results from a previously flushed communication.
        In comparison to read_results, this function does not check the results for read errors,
        but returns rderrorflag as part of the tuple.
        The return value is [(rderr0,addr0,data0),...,(rderrN,addrN,dataN)]
        """
        if log == None:
            log = self.log

        self._lock_comm()
        try:
            ret = self._read_all_bytes(log, lock=False)
        finally:
            self._unlock_comm()
        results = _get_wb_reads(ret)

        results_diag = []
        for val in results:
            rd_data = val[1]
            rd_address = val[0] & 0x7FFF
            rderr_flag = (val[0] >> 15) & 1
            results_diag.append( (rderr_flag,rd_address,rd_data) )

        return results_diag


    def _discardall(self,read_dp_func,maxReads=10):
        reads = 0
        nrbytes = len(read_dp_func(10240))
        total_bytes = nrbytes
        while reads < maxReads and nrbytes > 0:
            nrbytes = len(read_dp_func(102400))
            total_bytes += nrbytes
            reads += 1
        if total_bytes > 0:
            self.logger.debug("Discarded %d bytes for dp_function %r", total_bytes, read_dp_func.__name__)
        return nrbytes == 0

    def discardall_dp1(self,maxReads=10):
        return self._discardall(self._do_read_dp1,maxReads)
    def discardall_dp2(self,maxReads=10):
        return self._discardall(self._do_read_dp2,maxReads)
    def discardall_dp3(self,maxReads=10):
        return self._discardall(self._do_read_dp3,maxReads)

    def read_dp2(self, size):
        """ Reads <size> bytes of data from DP2.
        Returns a list of integers.
        """
        return _as_int_array(self._do_read_dp2(size))

    def read_dp3(self, size):
        """ Reads <size> bytes of data from DP3.
        Returns a list of integers.
        """
        return _as_int_array(self._do_read_dp3(size))

    def _do_write_dp0(self, data):
        """Implementation of writing to DP0"""
        raise NotImplementedError

    def _do_read_dp1(self, size):
        """Implementation of reading from DP1"""
        raise NotImplementedError

    def _do_read_dp2(self, size):
        """Implementation of reading from DP2"""
        raise NotImplementedError

    def _do_read_dp3(self, size):
        """Implementation of reading from DP3"""
        raise NotImplementedError

class PrefetchCommunication(Communication):
    """Prefetch Communication controller.

    Optimized communication control which provides functions to
    record a set of wishbone transactions, and later prefetch the same
    set of wishbone transactions in a single usb packet.
    """
    def __init__(self, comm,enable_rderr_exception=False):
        """Initialize with given comm object as actual communication controller"""
        super(PrefetchCommunication, self).__init__(enable_rderr_exception)
        self.comm = comm
        self.logger = logging.getLogger("PrefetchCommunication")
        self.recording = True
        self.prefetch_mode = False
        self.sequence = bytearray()
        # prefetched commands in form {Addr: [1,0,0,1]} where 1=Write, 0=Read
        self.prefetched_commands = defaultdict(list)
        # prefetched results in form {Addr: [d0,d1,d2,...]}
        self.prefetched_results = defaultdict(list)
        self.prefetched_read_buffer = bytearray()

    def stop(self):
        self.comm.stop()

    def discardall_dp1(self,maxReads=10):
        return self.comm.discardall_dp1(maxReads)

    def discardall_dp2(self,maxReads=10):
        return self.comm.discardall_dp2(maxReads)

    def discardall_dp3(self,maxReads=10):
        return self.comm.discardall_dp3(maxReads)

    def start_recording(self):
        """Start recording wishbone access commands"""
        self.recording = True
        self.sequence = bytearray()

    def stop_recording(self):
        """Finish recording wishbone access commands. Return the sequence of commands generated so far"""
        self.recording = False
        return self.sequence

    def prefetch(self):
        """Prefetch mode. Load sequence of commands, send to usb, store results"""
        # Check that prefetched values are empty
        self._prefetch_empty_buffer(True)
        nrReads = 0
        for i in range(0,len(self.sequence),4):
            write_cmd = (self.sequence[i+3]>>7)&1
            if not write_cmd:
                nrReads += 1
            address = ((self.sequence[i+3]&0x7F) << 8) | self.sequence[i+2]
            self.prefetched_commands[address].append(write_cmd)
        # prefetch send command
        self._lock_comm()
        try:
            self.comm._do_write_dp0(self.sequence)
            # prefetch receive results
            results = self.comm._do_read_dp1(nrReads*4)
        finally:
            self._unlock_comm()
        for i in range(0,len(results),4):
            addr = results[i+2] | ((results[i+3] &0x7F)<<8)
            self.prefetched_results[addr].append(results[i:i+4])

        self.prefetch_mode = True

    def load_sequence(self,sequence):
        """Load given sequence of commands to communication (no call to usb yet)"""
        self.sequence = sequence
        self.recording = False

    def stop_prefetch_mode(self, checkEmpty=True):
        self.prefetch_mode = False
        self._prefetch_empty_buffer(checkEmpty)

    def get_sequence(self):
        """Return the current sequence of commands"""
        return self.sequence

    def _prefetch_empty_buffer(self,checkEmpty=True):
        if checkEmpty:
            for addr,cmds in self.prefetched_commands.items():
                if len(cmds) > 0:
                    self.logger.warning("Prefetch_empty_buffer: Address %04X}: There are %d unsent commands",addr,len(cmds))
            for addr,dat in self.prefetched_results.items():
                if len(dat) > 0:
                    self.logger.warning("Prefetch_empty_buffer: Address %04X: There are %d unread results",addr,len(dat))

        self.prefetched_commands = defaultdict(list)
        self.prefetched_results = defaultdict(list)
        self.prefetched_read_buffer = bytearray()

    def _prefetch_handle_error(self):
        self._prefetch_empty_buffer(False)
        self.logger.debug("Prefetch mode failed, back to normal mode. Sequence: %r",self.sequence)
        self.prefetch_mode = False

    def _prefetch_write_dp0(self,data):
        for i in range(0,len(data),4):
            write_cmd = data[i+3]>>7 &1
            address = ((data[i+3]&0x7F) << 8) | data[i+2]
            if self.prefetched_commands[address]:
                rw = self.prefetched_commands[address].pop(0)
                if rw != write_cmd:
                    self.logger.error("Prefetch: Next command is Write=%d, while Write=%d was expected . Command: 0x%s",
                                      rw,write_cmd, ["{0:02X}".format(x) for x in data[i:i+4][::-1]])
                    self._prefetch_handle_error()
                if not write_cmd:
                    if self.prefetched_results[address]:
                        self.prefetched_read_buffer += self.prefetched_results[address].pop(0)
                    else:
                        self.logger.error("Prefetch: wishbone read command has no corresponding readback value Address: %04X . Command: 0x%s",
                                          address, ["{0:02X}".format(x) for x in data[i:i+4][::-1]])
                        self._prefetch_handle_error()


            else:
                self.logger.error("Prefetch: wishbone command not registered in prefetch. Command: 0x%s",
                                  ["{0:02X}".format(x) for x in data[i:i+4][::-1]])
                self._prefetch_handle_error()


    def _prefetch_read_dp1(self,size):
        if len(self.prefetched_read_buffer) != size:
            self.logger.error("Prefetch: Read results has unexpected length: Requested: %d, In Buffer: %d",
                              size,len(self.prefetched_read_buffer))
            self._prefetch_handle_error()

        result = self.prefetched_read_buffer
        self.prefetched_read_buffer = bytearray()
        return result


    def _do_write_dp0(self, data):
        if self.prefetch_mode:
            self._prefetch_write_dp0(data)
        # in case prefetch fails, it turns off prefetch_mode: write normally to wishbone
        if not self.prefetch_mode:
            # forward to comm
            if self.recording:
                self.sequence += data
            self.comm._do_write_dp0(data)

    def _do_read_dp1(self, size):
        if self.prefetch_mode:
            return self._prefetch_read_dp1(size)
        else:
            return self.comm._do_read_dp1(size)

    def _do_read_dp2(self, size):
        return self.comm._do_read_dp2(size)

    def _do_read_dp3(self, size):
        return self.comm._do_read_dp3(size)
