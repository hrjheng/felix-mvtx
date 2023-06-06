# Instructions for updating bitfiles of Readout Units (RUs) and Common Readout Unit (CRU)

## Readout Unit

The bitfile update is composed of four steps:
- Flash the bitfile into the Flash memory
- Load the bitfile into the FPGA (from the flash memory)
- Verify the new githash
- Compile a log entry

### Preparation

1. Log into the FLP in which the RUs are connected (See [CRU/FLP/RU mapping](https://espace.cern.ch/alice-project-itsug-electronics/_layouts/15/WopiFrame.aspx?sourcedoc=/alice-project-itsug-electronics/Shared%20Documents/Matteo/cru_to_ru_mapping.xlsx&action=default)).
The user is ```its```.
Ask the password to the commissioning coordinator.
2. Open a tmux session ([Documentation](https://tmuxcheatsheet.com))

``` shell
tmux new -s <username>
```

3. If you do not already have it, create a folder with your CERN user in the home of the its user.
Clone this repository inside the folder by running:

``` shell
cd
mkdir <username>
cd <username>
git clone https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS.git
```

4. From ```CRU_ITS/software/py```
  - Enter the ReadoutCard environment (see [Direct use of O2 ReadoutCard](../doc/HowTo.md))
  - Select the ```testbench[|_xyz].py``` file relative to the CRU the RUs are connected to.
  The name follows the following pattern ```testbench_<subrack(s)>_<half/quadrantlayer><layer>```.
  - Identify the CRU gbt channel the RUs are connected to (See [CRU/FLP/RU mapping](https://espace.cern.ch/alice-project-itsug-electronics/_layouts/15/WopiFrame.aspx?sourcedoc=/alice-project-itsug-electronics/Shared%20Documents/Matteo/cru_to_ru_mapping.xlsx&action=default)).
5. Make sure all the RUs are powered on (this guide **DOES NOT** provide instructions on how to power them on.
6. Run

``` shell
./testbench[_xyz].py log_input_power
```

   Make sure that the current they draw is around 1.6 A (from 1.5 A to 1.8 A).
   This means that the main FPGA (XCKU) is programmed and that you can use the XCKU FIFO procedure.
   If it is around 1.0 A, you need to try to load the [goldfile](#test-loading-of-the-golden-bitfile-into-the-fpga) or, if that doesn't help, follow the [PA3 I2C procedure](#flashing-the-bitfile-via-pa3-i2c).

### Flashing the bitfile (via XCKU FIFO)

This paragraph describes the recommended way of loading the bitfile.
Options in square brackets are optional.
It will take around 1 minute for each RU.

Run

``` shell
./testbench[|_xyz].py flash_all_rdo_bitfiles <BITFILE_PATH> [--bitfile_block=<bitfile start block list>] [--scrubfile_block=<scrubfile start block list>][--use_ultrascale_fifo=True] [--exclude_rdo_list=<list of RDOs not to flash>]
```

- **NOTE:** the bitfiles are available in the FLP in ```/shareFS/its/RU_bitfiles/<tag_name>/v<version>/```.
You will find 4 bitfiles for each githash, ending in ```.bit```, ```_bs.bit```, ```_bs_ecc.bit```, ```_ecc.bit```.
You need to enter the ```BITFILE_PATH``` to any of the four bitfiles: the script will select the correct type for you.

- **NOTE:** the  ```--use_ultrascale_fifo=True```, default, option requires a bitfile with the wb2fifo module implemented.
It is present from ```RU v0.1.7```, it is **NOT** present in the ```powerunit_controller v0.2``` and earlier: follow the PA3 I2C procedure.
- **NOTE:** the ```--bitfile_block``` and ```--scrubfile_block``` are the addresses of the bitfiles on the flash.
They are optional to provide. If not provided, the existing positions in flash are used.
They can be either a value or a list of values (with length, the same as the RU list).
They have to be **TWO DIFFERENT VALUES per RU** and they have to be bigger than ```0x100``` and non-overlapping, separated by ```0x100```.
- **NOTE:** If not all RUs need to be flashed, specify the list of CRU gbt channels of the RUs to be skipped with the ```--exclude_rdo_list``` option

### Flashing the bitfile (via PA3 I2C)

This paragraph describes the fallback way of loading the bitfile.
It will take around 10 minutes for each RU.

Run

``` shell
./testbench[|_xyz].py flash_all_rdo_bitfiles <BITFILE> [--bitfile_block=<bitfile start block list>] [--scrubfile_block=<scrubfile start block list>] --use_ultrascale_fifo=False [--exclude_rdo_list=<list of RDOs not to flash>]
```


### Flashing the golden bitfile (via XCKU FIFO)
The flash memory contains a "golden" bitfile which can be used in case of problems with a recently loaded bitfile in the main bitfile location.
The goldfile location shouldn't overlap the locations of the main bitfile or scrubfile locations.
If a goldfile has previously been loaded, its location will automatically reused in the command below
(i.e. optional argument `--goldfile_block` is not needed).
In order to (re-) load this golden image, use the following command:

``` shell
./testbench[|_xyz].py flash_all_rdo_goldfiles <BITFILE_PATH> [--goldfile_block=<goldfile start block list>] [--use_ultrascale_fifo=True] [--exclude_rdo_list=<list of RDOs not to flash>]
```

- **NOTE:** If not all RUs need to be flashed, specify the list of CRU gbt channels of the RUs to be skipped with the ```--exclude_rdo_list``` option

### Test loading of the golden bitfile into the FPGA

- Run:

```shell
./testbench[|_xyz].py program_all_xcku --use_gold=True
```
In case of error, see [Errors section](#error-recovery-on-programming)

### Loading the regular bitfile into the FPGA

- Run:

```shell
./testbench[|_xyz].py program_all_xcku
```
In case of error, see [Errors section](#error-recovery-on-programming)

### Verify the new githash

- Run:

```shell
./testbench[|_xyz].py version
```

### Compile a log entry (**MANDATORY for B167 operations**)

1. Open the commissioning [logbook](https://alice-logbook.cern.ch/its-run3/date_online.php?p_cont=lc&p_cpn=1&p_cvm=Compact&pcf_cc=HUMAN).
2. Search in the Title key for ```RUs bitfile loaded```. Find the entry relative to the subrack you loaded and **ANSWER TO THIS THREAD**.
3. Paste the result of the following values into the log entry:

```shell
./testbench[|_xyz].py info_for_log_entry
```

### Error recovery on programming
In case a failure during programming happens try:

If golden bitfile failed:
```shell
./testbench[|_xyz].py pa3s <RDO number> program_xcku
./testbench[|_xyz].py pa3s <RDO number> get_bitfile_locations
./testbench[|_xyz].py flash_all_rdo_goldfiles <BITFILE> --goldfile_block=<block that is not the present one printed above> --exclude_rdo_list=<list of RDOs not to flash>
```

If regular bitfile failed:
```shell
./testbench[|_xyz].py pa3s <RDO number> program_xcku --use_gold=True
./testbench[|_xyz].py pa3s <RDO number> get_bitfile_locations
./testbench[|_xyz].py flash_all_rdo_bitfiles <BITFILE> --bitfile_block=<block that is not the present one printed above> --exclude_rdo_list=<list of RDOs not to flash>
```

Continue by redoing the steps from where the procedure failed.

## Common Readout Unit

The current bitfile in use is v3.10.0.
The SOF and POF files are available for download,  the bitfile (SOF) and the programming file (POF) from [here](https://cernbox.cern.ch/index.php/s/zs4JgSR8lhHYsfD)
If the link does not work, find the new link in [the Readme](https://gitlab.cern.ch/alice-cru/cru-fw/tree/develop)


### Modify grub.conf for updating Firmware without reboot
The boot configuration needs to be changed so that the Linux system doesn't reboot when the PCIe interface in the
CRU firmware disappears due to a firmware download. This needs to be done only once and will persist over reboots.

Edit the file `/etc/default/grub` and enter the following at the end of the line starting with `GRUB_CMD_LINE_LINUX=`:

```
ghes.disable=1
```

and then execute the following command (with root privilege or sudo):

```
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
```

The Linux system needs to be rebooted for this command line argument to take effect in the kernel.

### JTAG Server

The Quartus programming tool uses is propriatary jtag server for access: jtagd.

To check whether the tool manages to detect hardware, run:

``` shell
quartus_pgm -l
```

If the tool reports report that "No JTAG hardware available". Try the following before retry:

``` shell
sudo killall -9 jtagd
sudo jtagd
```

Success can also be confirmed with:

```
jtagconfig
```

### Programming

- Log into flpits11 (B301 setup) or flpits1 (B167 setup).
- Download the bitfile (SOF). Note that it might already be on each FLP under `/shareFS/its/CRU_bitfiles/`
- Connect the USB to the port of the CRU (in the back of the FLP). If you only have one CRU connected, the <CRU_NUM> parameter is 0. If you have more then one, then the order is assigned by quartus based on the peripherals in use (0 to N-1, for N-1 CRUs connected). There is currently no reliable way of understanding which CRU you are programming, without programming it. Connect more than one CRU only if you want to program all of them with the same bitfile.
- Run the command

``` shell
./cru_utils.py program_cru <CRU_NUM> <FILE.sof>
```

- After loading the bitfile, remove and reinsert the PCI devices of the CRU via the following command:

```
sudo ./cru_utils.py reload_cru <PCIID>
```

where <PCIID> is the lowest ID of the two endpoints of the CRU to be re-enumerated, e.g. `04:00.0`.

**HINT** Find the PCI ID like this:

``` shell
lspci | grep CERN
```

**NOTE:** It needs to be done twice in order for that to work properly.

- Initialize the CRUs in the FLP via o2-roc-config (for each <PCIe_ID> of the CRU)

How to initialize the CRU is described in the file `HowTo.md` in the `doc` folder; use the command:

``` shell
o2-roc-config --config-uri 'ini://<CFG_FILE>' --id <PCIe_ID> --force-config
```

or the cluster script in /software/sh/clusterssh_tools :

``` shell
./configure_all_crus.sh
```

- Compile a log entry

### Flashing

- Log into flpits11 (B301 setup) or flpits1 (B167 setup).
- Download the bitfile (POF). Note that it might already be on each FLP under `/shareFS/its/CRU_bitfiles/`
- Connect the USB to the port of the CRU (in the back of the FLP). If you only have one CRU connected, the <CRU_NUM> parameter is 0. If you have more then one, then the order is assigned by quartus based on the peripherals in use (0 to N-1, for N-1 CRUs connected). There is currently no reliable way of understanding which CRU you are programming, without programming it. Connect more than one CRU only if you want to program all of them with the same bitfile.
- Edit `software/config/cru_jtag_chain.cdf` with the path of the .pof-file.
- Run the command

``` shell
./cru_utils.py flash_cru <CRU_NUM> [<PATH_TO_JTAG_CHAIN.cdf>]
```

## POF File Generation (for Flash programming)

- open Quartus Programmer GUI
- Choose option "Convert Programming File" from File menu
- Select output programming file type as .pof
- Choose configuration device "CFI_1Gb"
- Click on "SOF Data under the heading "Input Files" to convert and then select "add file..."
- Browse for the SOF that is to be converted
- Select mode "passive parallel x16"
- Select "Generate" at the bottom
