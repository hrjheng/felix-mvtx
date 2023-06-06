#!/usr/bin/env python3.9
"""Utilities for programming CRUs"""

import errno
import fire
import logging
import os
import subprocess
import time

QUARTUS_FOLDER = "/opt/intelFPGA_pro/17.1/qprogrammer/bin"
script_path = os.path.dirname(os.path.realpath(__file__))

class CruUtils:
    """A class to run basic programming tasks for the CRUs"""

    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger("CruUtils")

    def setup_logging(self):
        # Logging folder
        logdir = os.path.join(
            script_path,
            'logs/CruUtils')
        try:
            os.makedirs(logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(logdir, "cru_utils.log")
        log_file_errors = os.path.join(logdir,
                                       "cru_utils_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        fh2 = logging.FileHandler(log_file_errors)
        fh2.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        fh.setFormatter(formatter)
        fh2.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(fh2)
        logger.addHandler(ch)

        self.logger = logger

    def _get_crus(self):
        """Returns the CRUs connected to the blasters"""
        assert os.path.isfile(QUARTUS_FOLDER + '/quartus_pgm'), f"Cannot find Quartus installed at {QUARTUS_FOLDER}"
        quartus_l = subprocess.Popen(f"{QUARTUS_FOLDER}/quartus_pgm -l".split(), stdout=subprocess.PIPE)
        output = subprocess.run("grep PCIe40".split(), stdin=quartus_l.stdout, stdout=subprocess.PIPE).stdout.decode('utf8')
        assert output != '', "No CRUs found, run with sudo or add udev rule for user access (sudo ./cru_utils.py add_udev_cru)"
        crus = [line[3:] for line in output.splitlines()]
        return crus

    def program_cru(self, cru_num, file):
        """Programs the Altera device in the CRU, requires sudo or run add_udev_cru first"""
        crus = self._get_crus()
        assert cru_num in range(0, len(crus)), "cru_num out of range 0 to {0}".format(len(crus)-1)
        cmd = f"{QUARTUS_FOLDER}/quartus_pgm -c \'" + crus[cru_num] + "\' -m JTAG -o \"P;" + file + "@1\""
        self.logger.info("Programming CRU id {0} file {1}".format(crus[cru_num], file))
        quartus = subprocess.run(cmd, shell=True)
        if quartus.returncode == 0:
            self.logger.info("Programming completed successfully")
        else:
            self.logger.error("Programming failed, Quartus programmer exit code {0}".format(quartus.returncode))

    def set_jtag_blaster_frequency(self, cru_num):
        crus = self._get_crus()
        assert cru_num in range(0, len(crus)), "cru_num out of range 0 to {0}".format(len(crus)-1)
        cmd = f'{QUARTUS_FOLDER}/jtagconfig --setparam  \'{crus[cru_num]}\' JtagClock 6M'
        jbf = subprocess.run(cmd, shell=True)
        if jbf.returncode == 0:
            self.logger.info("Frequency set successfully")
        else:
            self.logger.error("Frequency set failed, Jbf programmer exit code {0}".format(jbf.returncode))
        return jbf.returncode

    def flash_cru(self, cru_num, chain_file=os.path.join(script_path,'../config/cru_jtag_chain.cdf')):
        """Programs the Flash device in the CRU, requires sudo or run add_udev_cru first"""
        chain_file = os.path.realpath(chain_file)
        assert os.path.isfile(chain_file), f"{chain_file} not existing"
        crus = self._get_crus()
        assert cru_num in range(0, len(crus)), "cru_num out of range 0 to {0}".format(len(crus)-1)
        set_freq = self.set_jtag_blaster_frequency(cru_num=cru_num)
        if set_freq == 0:
            cmd = f"{QUARTUS_FOLDER}/quartus_pgm -c \'{crus[cru_num]}\' {chain_file}"
            self.logger.info("Programming CRU id {0} file {1}".format(crus[cru_num], chain_file))
            quartus = subprocess.run(cmd, shell=True)
            if quartus.returncode == 0:
                self.logger.info("Flashing completed successfully")
            else:
                self.logger.error("Flashing failed, Quartus programmer exit code {0}".format(quartus.returncode))

    def reload_cru(self, pci_id):
        """Reloads CRU firmware by virtually unplugging the pci card and reinserting it, requires sudo"""
        assert os.getuid() == 0, "This command needs to be run as sudo"
        cmd = "modprobe -r uio_pci_dma"
        subprocess.run(cmd, shell=True)
        cmd = f"echo 1 > /sys/bus/pci/devices/0000:{pci_id}/remove".replace(":", "\:")
        print(cmd)
        subprocess.run(cmd, shell=True)
        cmd = f"echo 1 > /sys/bus/pci/devices/0000:{str(int(pci_id[:2])+1).zfill(2)+pci_id[2:]}/remove".replace(":", "\:")
        print(cmd)
        subprocess.run(cmd, shell=True)
        time.sleep(3)
        cmd = "echo 1 > /sys/bus/pci/rescan"
        print(cmd)
        subprocess.run(cmd, shell=True)
        time.sleep(1)
        cmd = "modprobe uio_pci_dma"
        subprocess.run(cmd, shell=True)

    def add_udev_cru(self):
        """Add udev rule for access to CRU JTAG for regular users"""
        assert os.getuid() == 0, "This command needs to be run as sudo"
        subprocess.run("echo \'SUBSYSTEM==\"usb\", ENV{DEVTYPE}==\"usb_device\", ATTR{idVendor}==\"09fb\", ATTR{idProduct}==\"6010\", MODE=\"0666\"\' > /etc/udev/rules.d/50-cru.rules", shell=True)
        print("Reboot machine for changes to take effect")


if __name__ == "__main__":
    cu = CruUtils()
    try:
        fire.Fire(cu)
    except:
        raise
