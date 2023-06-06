# Operating the FLP setup

## Setup the environment

From FLP Suite v0.18.x, all O2 modules are always present in the environment and the user
does not need to load them manually.

For older versions of FLP Suite, in order to use the correct environment two ways are currently possible.

### Direct use of O2 ReadoutCard (OBSOLETE)

Note that this method is no longer possible after FLP Suite v0.18.x.

``` shell
module load ReadoutCard
```

The current version to use with CRU firmware version v3.10.0 is v0.28.0-1, from FLP Suite v0.14.0, which can be called with:

``` shell
module load ReadoutCard/v0.28.0-1
```

For convenience, an alias is defined on the FLPs.
Just call

``` shell
rc
```

### Using Anaconda (OBSOLETE)

On ```flpits0.cern.ch``` and ```flpits1.cern.ch``` Anaconda is still used.
In order to run on these machines, a script is hosted in ```home```.
In order to set the environment, call

``` shell
source ~/setup_its.sh
```

## Setup the CRU after an FLP restart

The CRU is not configured at the FLP boot or after firmware load and reenumeration, and it needs to be configured.

**NOTE:** Use the `--force-config` flag with o2-roc-config after power up. The clock tree of the CRU will not be initialised otherwise!

``` shell
o2-roc-config --config-uri 'ini://<CFG_FILE>' --id <CRU_PCIE_ID> --force-config
```

The argument `--bypass-fw-check`, or simply `--bypass`, can be used if the latest firmware version of the CRU is not yet "officially" supported (the command checks for "supported" githashes and fails if the found githash is not one of the supported ones).
The `<CFG_FILE>` argument is the path of the configuration file for the corresponding CRU. The `<PCIe_ID>` argument is the PCIe ID of the CRU card to be configured, e.g. `04:00.0`.

**NOTE:** the configuration files are stored under the [config folder](../doc/software/config). They are named as `roc_flpits<flp_number>_pci<CRU PCIe ID>.cfg`

The format and examples of the roc configuration file are documented here:

[https://github.com/AliceO2Group/ReadoutCard/blob/master/README.md#card-configurator]

For more information about the o2-roc-config command arguments, one can also run:

``` shell
o2-roc-config --help
```

There is a shell script in the software/sh folder that tries to figure out the correct config files to use and does the configuration for you:

``` shell
cd software/config
../sh/config_cru.sh 02 03 04 05
```

where `02 03 04 05` are the CRU PCIe IDs to configure (i.e. `02:00.0, 03:00.0 04:00.0 05:00.0`). Remember that with the latest libO2ReadoutCard version
each endpoint needs to be configured separately with its own configuration file.

### Issues with PDA initialisation

Tracked [here](https://alice.its.cern.ch/jira/browse/ODC-64), observed [here](https://alice-logbook.cern.ch/its-run3/date_online.php?p_cont=comd&p_cid=29671)

``` shell
[its@flpits11] roc-list-card
 Error: Failed to initialize PDA
 [o2::roc::ErrorInfo::_PdaStatusCode*] = 1
 [Possible causes]:
 o Driver module not inserted (> modprobe uio_pci_dma)
 o PDA kernel module version doesn't match kernel version
 o PDA userspace library version incompatible with PDA kernel module version (> modinfo uio_pci_dma)
 [Error message] = Failed to initialize PDA
[its@flpits11]  modprobe uio_pci_dma
 modprobe: FATAL: Module uio_pci_dma not found.
```

Can be solved by (as admin)

``` shell
yum reinstall pda-kadapter-dkms-1.1.0-0.noarch
```

## Start the readout process

(use a separate shell, since you will need a different environment then ReadoutCard)

Create a ramdisk (with sudo) if you want to read out the data there.

``` shell
mkdir /tmp/ramdisk
sudo mount -t tmpfs -o size=4G tmpfs /tmp/ramdisk
```

The size of the disk should be higher than the specified file size in the o2-readout-exe config file.

This allows you to launch the

``` shell
o2-readout-exe file://home/its/git/CRU_ITS/software/config/<CFG_FILE>
```

### For FLP Suite older than 0.18.x

First, setup the O2 environment for the CRU:

``` shell
module load Readout/v1.5.9-3
```
Use the latest version of Readout, currently `v1.5.9-3`, from FLP Suite v0.14.0.

Export the follwing variable to see the logging

``` shell
export O2_INFOLOGGER_MODE=stdout
```

### Older readout versions

* v.1.6 with CRU v3.7.0
``` shell
module load Readout/its-consistency-patch-1
```

* v1.0.6
``` shell
module load Readout/v1.0.6-1
```


* v1.0.5
``` shell
module load Readout/v1.0.5-1
```

* v28.1

``` shell
module load Readout/v0.28-1
```

* V27.2

``` shell
module load Readout/v0.27.1-2
```

* V26.1

``` shell
module load Readout/v0.26-1
```

* V25.2

``` shell
module load Readout/v0.25.2-1
```

* V19.0

``` shell
module load Readout/v0.19.0-1
```

## Communicating with a RU (via SWT)

All the following operations, unless differently stated, are executed in the WP10 shell, i.e. with Anaconda3 setting the Python3 environment.

Setup the environment

``` shell
source ~/setup_its.sh
```

Navigate to the CRU_ITS repository and the folder software/py (~/git/CRU_ITS/software/py in B167).
The description is assuming that you are using the CRU on PCIeID=04:00.0 (if not use ```testbench_*.py```

``` shell
./testbench.py cru initialize --gbt_ch=<YOUR_GBT_CHANNEL>
```

Where the number provided to gbt_ch is the link number you want to communicate with.

The next command will let you read the version number of the CRU and RDO

``` shell
./testbench.py version
```

If you want to talk to another board then:

``` shell
./testbench.py cru set_gbt_channel --gbt_ch=<YOUR_GBT_CHANNEL>
./testbench.py cru sca intialize
```

## Notes on Fire

A couple of notes on Fire, used to generate a Command-Line-Interface in testbench:

* It is really slow, it can be used as a debug, development, test order of commands.
* it is not meant to be called in shell script with single calls to testbench (No error handling between two CLI calls, unless you implement them!)
* It shows you the methods and objects available in testbench:

``` shell
./testbench.py
```

* It shows you the methods and objects available in the ```rdo`` object:

``` shell
./testbench.py rdo
```

* It can provide help on any method:

``` shell
./testbench.py <METHOD> -- --help
```


## Interaction with the SCA/PA3:

The SCA and PA3 can be communicated with without enabling the SWT mode in the CRU as will be described in the next section.

``` shell
./testbench.py cru sca log_adcs_reads
```

Reports ADC values of the RU board.

``` shell
./testbench.py cru pa3 version
```

Reports the version of the PA3.

## Interaction with the RU via SWT:

First switch the GBT TX mux to SWT downloads (default after ```cru.initialize```).

``` shell
./testbench.py cru set_gbt_mux_to_swt
```

to switch back to TTC ("trigger") instead of SWT transmitted in downlink, use instead:

``` shell
./testbench.py cru set_gbt_mux_to_trigger
```

if necessary, we can reset the CRU core to remove any data left in the SWT FIFOs (done in ```cru.initialize```:

``` shell
./testbench.py cru reset_sc_cores
```

## Controlling the power unit via SWT:

(Select ```powerunit_1``` or ```powerunit_2``` depending if it is the top connector or bottom connector)

First initialise the power unit (once)

``` shell
./testbench.py rdo powerunit_1 initialize
```

Then setup and power the module

``` shell
./testbench.py power_on_IBs --module_list=[<MODULES_CONNECTED>] --avdd=<AVDD_IN_V> --dvdd=<DVDD_IN_V>
```

**NOTE:** the function has also other otional parameters.


## Send triggers
Again in the WP10 shell:

``` shell
./testbench.py cru send_sot                      # Sends a start-of-trigger (SOT) command
./testbench.py cru send_physics_trigger          # send a "PHYSICS" trigger
./testbench.py cru send_physics_trigger          # send a "PHYSICS" trigger
./testbench.py cru send_eot                      # Sends an end-of-trigger (EOT) command
./testbench.py cru send_soc                      # Sends a start-of-continuous (SOC) command
./testbench.py cru send_eoc                      # Sends a end-of-continuous (EOC) command
```

# Data readout from ALPIDE

A dedicated script handles that (provided that you enabled the readout in the first section)

``` shell
./daq_test.py
```

It has a lot of parameters to configure it (read the code...) and it is pre-release.

At the end of the execution you can CTRL-C the readout process to get the data at you selected location.

## Dumping data
To dump the resulting file:

``` shell
python eventDump.py /tmp/ramdisk/output.bin | more
```

## Data integrity check
To dump the resulting file:

``` shell
python decode.py <PATH_TO_DATA_FILE> [block_offset] [FEE_ID]
```
