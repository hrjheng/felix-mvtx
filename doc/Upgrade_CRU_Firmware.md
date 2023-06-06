# Upgrade procedure for CRU firmware
First determine the version of ReadoutCard compatible with the CRU firmware to be installed (see the compatibility table in the [README.md](https://github.com/AliceO2Group/ReadoutCard/blob/master/README.md#compatibility) file
of the ReadoutCard github repository).

## FLP Suite

Make sure the installed [FLP Suite version](https://alice-o2-project.web.cern.ch/flp-suite) is compatible the CRU firmware version.

## Non-FLP Suite (OBSOLETE)

For CRU firmware version `v3.10.0` for example the compatible ReadoutCard version is at least `v0.28.0`.
Find the latest version of ReadoutCard corresponding to this table in the upgrade yum repository:

``` shell
yum makecache fast
yum search alisw | grep ReadoutCard
```

and install the latest version, e.g.:

``` shell
yum install ReadoutCard/v0.28.0-1
```

The update of this software package might also install new drivers, so make sure to reboot the workstation after
upgrading the ReadoutCard library.
After reboot, enter the ReadoutCard environment:

``` shell
module load ReadoutCard/v0.28.0-1
```

## Required steps

Make sure the local python libraries needed for CRU_ITS are installed into the associated python distribution as described in [Installation.md](
https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/-/blob/update_cru_v3_9_1/doc/Installation.md#installing-python-modules).

Download the CRU bitfiles from the [cernbox folder](https://cernbox.cern.ch/index.php/s/n03j2ZUQ4CeuKYB)
and install them on the CRU as described in
[UpdateBitfiles.md](https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/-/blob/development/doc/UpdateBitfiles.md).
In the local copy of the CRU_ITS software
repository, go to folder `./modules/cru_support_software/software/sh/`
and reenumerate the CRU (make sure the correct firmware version is detected
by ```o2-roc-list-cards```):

``` shell
export O2_INFOLOGGER_MODE=stdout
sudo ./reenumerate-pci.sh 3b:00.0 3c:00.0
o2-roc-list-cards
```

Update the `cru_table.py` file of firmware addresses by extracting this table from the CRU firmware repository:
Clone the repository for the desired git tag from the gitlab repository [cru-fw](https://gitlab.cern.ch/alice-cru/cru-fw). Go to the folder
`./cru-fw/COMMON/hdl` and use the `extract-cru-address-table.py` script in the folder
`CRU_ITS/modules/cru_support_software/software/py`, and finally copy the resulting `cru_table.py` file into the folder
`CRU_ITS/modules/cru_support_software/software/py`:

``` shell
cd cru-fw/COMMON/hdl/
~/ALICE/CRU_ITS/modules/cru_support_software/software/py/extract-cru-address-table.py
cp cru_table.py ~/ALICE/CRU_ITS/modules/cru_support_software/software/py/
```

Update the `roc_config_<xxx>.cfg` files with any changed configuration parameters as described in
[cru_template.cfg](https://github.com/AliceO2Group/ReadoutCard/blob/master/cru_template.cfg).
With this new configuration file, initialize the CRU as described in the file `HowTo.md`, using the command:

``` shell
o2-roc-config --config-uri 'ini://<CFG_FILE>' --id <PCIe_ID> --force-config
```

Update all CRU githashes of the configuration files in folder `./software/config`. Also update the python global
`EXPECTED_CRU_GITHASH` in file `software/py/testbench.py`. Add the CRU gihash lookup entry in
`modules/board_support_software/software/py/git_hash_lut.py`.

Check the latest call signatures of the various functions in the [ReadoutCard source repository](https://github.com/AliceO2Group/ReadoutCard.git)
especially in the source files in folder `./src/Cru` and update the python scripts in
`CRU_ITS/modules/cru_support_software/software/py`
accordingly.
