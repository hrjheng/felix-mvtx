# CRU test repository

## Prerequisite

* To work the computer requires the rorc lib to be installed and to have python.
  * Serach and install with yum -> `yum search ReadoutCard`
  * Example: `module load ReadoutCard/v0.10.1-1`, the drivers are installed in `/opt/alisw/el7/ReadoutCard/`
* The CRU address table must be constructed from the VHDL file. For
that the up to date *pack\_cru\_core.vhd* must be placed in the **COMMON** directory and the 
*./extract\_cru\_address\_table.py* command executed.
This produces a *cru\_table.py* file used by the various python scripts.




## Design components

Organisation

The repository is composed of various sub-components:
* [COMMON](COMMON/README.md): Contains the support scripts for starting the CRU board
* [I2C](I2C/README.md): I2C tools for reading/writing I2C slaves of the CRU
* [GBTSC](GBTSC/README.md): GBT EC - SCA configuration



## Startup

Standard steps:
1. The firmware must be (re)loaded in the CRU (check the [cru-fw git repository](https://gitlab.cern.ch/alice-cru/cru-fw/blob/master/preint/README.md))
2. Run `./COMMON/reenumerate-pci.sh` with the PCIe ID of the CRU(s) as arguments. Alternatively, warm reboot the machine (no poweroff on the boards)
3. The board must be checked with the `roc-list-card`, the **PCI Addr** is then provided

Example output from `roc-list-card` (currently some values are 0, this is related to address table changes):
```
===========================================================================================
  #   Type   PCI Addr   Vendor ID   Device ID   Serial   FW Version      Card ID          
-------------------------------------------------------------------------------------------
  0   CRU    02:00.0    0x1172      0xe001      33554941 20180705-131936-8c09c74f 00540186-2855fe10
==========================================================================================
```

* 20180705 is the date
* 2131936 is the time
* 8c09c74f is the git hash number of the firmware
* 00540186-2855fe10 is the ALTERA chip number
																 

Then more details are provided in this [documentation](./DETECTORS.md).
