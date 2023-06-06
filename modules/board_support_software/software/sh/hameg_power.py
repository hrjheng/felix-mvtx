#!/usr/bin/env python
import time
import sys, os

CURRENT_FOLDER = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(CURRENT_FOLDER + '/../py')
sys.path.append(CURRENT_FOLDER + '/../../../usb_if/software/usb_communication')

from hameg import Hameg

def main():
    if(len(sys.argv) < 2):
        exit("usage: hameg_power <1/0/setup>");

    do_power = sys.argv[1]

    psu = Hameg('/dev/ttyHAMEG')

    if do_power == 'setup':
        psu.set_remote_control()
        psu.activate_output(False)
        psu.configure_channel(1,7.0,2.0) # RUv0 CRU_emu
        psu.configure_channel(2,7.0,3.5) # RU
        psu.configure_channel(4,3.6,2.5) # PB
        psu.activate_channels([1,2,4])
    elif do_power == '1':
        psu.activate_output(True)
        time.sleep(1)
        psu.get_power_all()
        assert not psu.get_fuse_triggered(1)
        assert not psu.get_fuse_triggered(2)
        assert not psu.get_fuse_triggered(4)
    elif do_power == '0':
        psu.activate_output(False)
        time.sleep(1)
        psu.get_power_all()
        psu.set_local_control()
    else:
        print("Power command not recognized: {0}".format(do_power))

if __name__ == '__main__':
    main()