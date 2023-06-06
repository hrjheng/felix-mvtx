# Testing Bitfiles

## Identifying the setup you want to run and gaining access to it

The up-to-date configuration of the system is reflected in the [crate_mapping](../modules/board_support_software/software/py/crate_mapping.py).
The test setup are at the bottom of the file and they are indicated with the crate names: 'IB-test','IB-table','ML-test','OL-test'.

If you need to run any test on any of the setups use mattermost [group](https://mattermost.web.cern.ch/aliitscomm/channels/b301-setup-flpits11).
If you are not a member, contact @mlupi, @avelure, @freidt, or @gaglieri.
The group acts as a mutex to access the setup.

In the group, check if any user is currently controlling a setup.
Generally, a user writes `taking <setup name>` at the beginning of a session.
A user should write `releasing <setup name>` at the end of a session: user tend to forget.
If this happens, just tag them in the mattermost channel with `@<user>`.

**NOTE:** the setups are often referred in the group with a different name then the crate name given in `crate_mapping.py`:

- IB-test: referred to as IBS (Inner Barrel Stave)
- ML-test: referred to as MLS (Middle Layer Stave)
- OL-test: referred to as OLS (Outer Layer Stave)

IB-table: has this name because the RU associated with is laying on a table.
It is a setup used for electric measurements needing access to the board.

## Accessing the First Level Processor (FLP)

The Readout Units (RUs) for the test setup (B301) are connected to the ```flpits11.cern.ch``` and the ```flpits12.cern.ch```.
The user is ```its```.
Ask the password to @mlupi, @jschamba, or @avelure.

1. Log into the FLP
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
  - If you need to update only the part of RUs bitifles connected to the subrack, update the ```yml``` corresponding to the selected testbench (in ```../config```) with the correct GBT channels.
    The parameter to edit is the ```CTRL_AND_DATA_LINK_LIST```.
5. Make sure all the RUs are powered on (this guide **DOES NOT** provide instructions on how to power them on.
6. You can verify that the main FPGA is programmed by calling

```shell
./testbench[_xyz].py log_input_power
```

and checking that the current consumption is in a range from 1.5 to 1.8 A.
In case the board is power off, this command will fail.

7. You can verify the version of the bitfile present by calling

```shell
./testbench[_xyz].py info_for_log_entry
```

8. Make sure the correct bitfile is loaded into the main FPGA.

## Loading the bitfile into the RU's main FPGA

Load the bitfile according to the guide in [UpdateBitfiles.md](UpdateBitfiles.md)

## Control the power of the staves

The staves can be powered on and off with the following commands.

### IB-test setup

1. Power on (the check interlock flag is required since the stave has no PT100 connected).

``` shell
./testbench_ibs.py power_on_ib_stave
```

2. Log currents and voltages

``` shell
./testbench_ibs.py log_values_ib_stave
```

3. Power off

``` shell
./testbench_ibs.py power_off_ib_stave true
```

### ML-test setup

1. Power on
**NOTE** this command needs to be run by @jiddon until the [issue #71](https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/71) is solved.

``` shell
./obtest.py -c ../config/obtest_mls.cfg -t PowerOn -s 24 -v True
```

2. Log currents and voltages

``` shell
./testbench_mls.py log_values_ml_stave
```

3. Power off

``` shell
./testbench_mls.py power_off_ml_stave true
```

### OL-test setup

1. Power on
**NOTE** this command needs to be run by @jiddon until the [issue #71](https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/71) is solved.

``` shell
./obtest.py -c ../config/obtest_ols.cfg -t PowerOn -s 42 -v True
```

2. Log currents and voltages

``` shell
./testbench_ols.py log_values_ob_stave
```

3. Power off

``` shell
./testbench_ols.py power_off_ob_stave true
```

### PP1O4 HL0 (DBL) setup

1. Power on

``` shell
./testbench_pp1o4_hl0.py power_on_all_ib_staves
```

2. Log currents and voltages

``` shell
./testbench_pp1o4_hl0.py log_values_ib_staves
```

3. Power off

``` shell
./testbench_pp1o4_hl0.py power_off_all_ib_staves true
```


## Start the testing

1. Run the deployment test.

``` shell
cd deployment
./deployment_test.py -c ./deployment_test_<setup_name>.yml
```

2. Decode the data

``` shell
cd ../../sh/
./decode_<setup_name>.sh
./decode_threshold_<setup_name>.sh
```
