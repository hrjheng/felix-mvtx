"""Continually run tests in a loop using the CANbus High Level Protocol.
Reads out githash value, counter values for the CAN HLP module, and tests write
and read using the CAN_TEST register found in the CAN HLP module's wishbone slave.
Test statistics are printed when the program is terminated (CTRL+C)"""

import can_hlp
import can_hlp_test
import time
import datetime
import sys
import logging


def can_hlp_test_loop(socketcan_if, can_dev_ids, githash_expect, log_filename):
    can = can_hlp.CanHlp(socketcan_if)

    timeout_ms = 100
    flush_can = True

    total_tests = 0
    failed_tests = 0

    log_interval = 10
    start = time.time()
    last_test_iteration = start

    logging.basicConfig(filename=log_filename,
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO)

    logger = logging.getLogger('can_hlp_test_logger')
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.info('Starting CAN HLP test')
    logger.info('Node IDs to test: ' + str([hex(id) for id in can_dev_ids]))

    while True:
        try:
            if flush_can:
                can.flushHLP()
                flush_can = False

            for can_dev_id in can_dev_ids:
                try:
                    test_data = can_hlp_test.can_hlp_test(can, can_dev_id, timeout_ms)

                    if test_data['githash'] != githash_expect:
                        failed_tests += 1
                    elif test_data['test_reg_write'] != test_data['test_reg_read']:
                        failed_tests += 1

                except (can_hlp.CanHlpTimeout, can_hlp.CanHlpWrongResponse, can_hlp.CanHlpWrongId, can_hlp.CanErrorFrame) as re:
                    failed_tests += 1
                    flush_can = True

                total_tests += 1

        except KeyboardInterrupt as ki:
            logger.info("")
            logger.info("Test stopped. Time: {}".format(datetime.datetime.now()))
            logger.info("Number of failed calls to can_hlp_test: {}/{}".format(failed_tests, total_tests))
            logger.info("{0:0.2f} calls to can_hlp_test per second".format(total_tests/(time.time()-start)))
            logger.info("")
            logger.info("Counter values: ")
            logger.info(can.getCounters())

            try:
                can.flushHLP(timeout_ms)
                for can_dev_id in can_dev_ids:
                    hw_counters = can_hlp_test.can_hlp_test_get_hw_counters(can, can_dev_id, timeout_ms)

                    logger.info("")
                    logger.info("HW Counter values for ID {:02X}:".format(can_dev_id))
                    logger.info(hw_counters)

            except Exception as ae:
                logger.warning("Got exception while reading count registers after test.")

            break

        if(time.time() - last_test_iteration) > log_interval:
            last_test_iteration = time.time()

            logger.info("")
            logger.info("Number of failed calls to can_hlp_test: {}/{}".format(failed_tests, total_tests))
            logger.info("{0:0.2f} calls to can_hlp_test per second".format(total_tests / (time.time() - start)))
            logger.info("Counter values: ")
            logger.info(can.getCounters())


if __name__ == '__main__':
    # PP1-I-6
    # can_dev_ids = {0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F}

    # PP1-I-7
    # can_dev_ids = {0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1}

    dev_ids = {0x00, 0x0B}

    # Change this to reflect githash, it is not updated automatically from repo
    ghash_expect = 0x7D0A1F6C

    log_filename = 'can_hlp_test_pp1-i6_log.txt'

    can_hlp_test_loop('can0', dev_ids, ghash_expect, log_filename)