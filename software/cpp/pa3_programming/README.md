# Usage


## Check all valid CHs
`pa3jtag -c`

## Program all valid RUs
`pa3jtag -a ACTION -f DAT_FILE_PATH`

## Program all valid RUs on CRU endpoint

`pa3jtag -a ACTION -f DAT_FILE_PATH -e <EP>`

## Program a single RU on CRU endpoint

`pa3jtag -a ACTION -f DAT_FILE_PATH -e <EP> -c <GBT_CH>`

For instance:

```
./pa3jtag -a PROGRAM -f RU_auxFPGA_v0209_200420_1129_3850a9b.dat
./pa3jtag -a ERASE -f RU_auxFPGA_v0209_200420_1129_3850a9b.dat -e 1
./pa3jtag -a DEVICE_INFO -f RU_auxFPGA_v0209_200420_1129_3850a9b.dat -e 1 -c 11
```

# ACTIONs:

`DEVICE_INFO` - Prints all device info

`READ_IDCODE` - Prints only IDCODE and checks against file

`ERASE` - Full device erase, takes about 1 min

`PROGRAM` - Erase and then Program device, takes about 12 min

`VERIFY` - Verify data on device, takes about 57 min

# Dependencies

This program is compiled against and supports ReadoutCard v0.33.1, tested at uib lab.

# Modifications

1. In ```dp_exit()```: Removed if(speed_up) branch. The program exited with error with this if condition branch, the syndrome was the device couldn't be reached if the exit was done in a speed up way. The speed up in the exit function is insignificant.

2. In ```dp_load_row_data()```: Renamed ```test_sp``` to ```CG_write```.

3. In ```goto_jtag_state()```: the first instance of ```if (mode_stream_tms)``` is inside the case structure; and the second instance is outside the case structure. They serve different purposes. So far there's no way to combine them into one.

4. ```dp_do_shift_in_out_32bit_mode()```: In the first ```for``` loop,  the function shifts in ```tdi_data``` and ```tms_data``` in 32-bit or shorter packages; in the second ```for``` lop, the function shifts out ```tdo_words```, and in the last ```for``` loop, consturcts the ```tdo_data``` in the FLP memory. The function ends with JTAG state change.

5. ```take_26bit_tdi_out()```: this function reads the ```tdi_data``` from the ```.dat``` file into the data structure ```tmp```.

6. ```dp_do_shift_in_32bit_mode_sb_return_tdi()``` is a sub-function of ```take_26bit_tdi_out```, it reads from ```.dat``` file and output the ```tdi_data``` to a data structure in memory.

7. ```dp_do_shift_in_32bit_mode``` and ```dp_do_shift_in_32bit_mode_sb``` differ in that the latter handles the special case where the start bit (sb) is not 0.

8. ```dp_poll_device```, in this function a 'fake read back' replaced the ```DRSCAN_out```, inorder to accelerate the program or verify process.

# SCA.cpp

```SCA.cpp``` includes the functions that interfaces the GBT-SCA chip via the ```ReadoutCard``` driver.

Basic SCA interfacing functions names are inherited from SCA.py of the O2 framework.

1. ```wr()```: Write 64 bit packet (data + cmd) to the SCA interface and execute the command.

2. ```sca_write()```: Wrapper of ```wr()```, adds hardware delay.

3. ```rd()```: Read from the SCA interface.

JTAG functions wraps ```sca_write()``` specifying the ```Gbt_Sca_Chs``` with various words and word length.

# FLP.cpp

```FLP.cpp``` creates the CRU cardIds, gbt link numbers for each CRU.