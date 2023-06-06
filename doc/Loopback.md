# Looping back

The CRU has the functionality to run a loopback test.
Data are transmitted and compared to the received values on the same link.
The loopback can be done in multiple points:

- Into the FPGA transceiver
- Fibre loopback
- Into the GBTx in the RU
- Into the XCKU of the RU

# Quick guide

To simply run a loopback test on both GBTx0 and GBTx1, run the following command:

``` shell
./testbench_*.py loopback_test_gbtx01 <TEST_TIME_SEC>
```

This test enables the internal FPGA loopback from GBTx0 downlink to the
GBTx0 and GBTx1 uplinks. The CRU checks whether the value matches the transmitted one. 
When the test has finished, error counts are printed on the screen.

**NOTE:** see [here](HowTo.md) which version of ReadoutCard to use!

## Enable loopback into the transceiver

### Before the test

From ```CRU_ITS/modules/cru-sw/COMMON/``` run:

``` shell
python standalone-startup.py -i <PCIeID> -lb
```

### Run test

See "Running the loopback test" section.

### After the test

After the test, reinitialize the CRU without the loopback switch

``` shell
python standalone-startup.py -i <PCIeID>
```

## Fibres loopback (Check fibres with loopback)

### Before the test

From ```CRU_ITS/modules/cru-sw/COMMON/``` run (if not executed before):

``` shell
python standalone-startup.py -i <PCIeID>
```

Loopback the fibres.

### Run test

See "Running the loopback test" section.

### After the test

After the test, reinitialize the fibre.

``` shell
python standalone-startup.py -i <PCIeID>
```

## GBTx loopback

### Before the test

From ```CRU_ITS/modules/cru-sw/COMMON/``` run (if not executed before):

``` shell
python standalone-startup.py -i <PCIeID>
```

Then set the GBTx loopback from ```CRU_ITS/software/py/``` run:

``` shell
./testbench_[xzy].py loopback_all_gbt_packets --in_fpga=False
```

### Run test

See "Running the loopback test" section and run using the ```-c 8bit``` flag.

### After the test

Repower the RU

## XCKU loopback

### Before the test

From ```CRU_ITS/modules/cru-sw/COMMON/``` run (if not executed before):

``` shell
python standalone-startup.py -i <PCIeID>
```

Then set the XCKU loopback from ```CRU_ITS/software/py/``` run:

``` shell
./testbench_[xzy].py loopback_all_gbt_packets --in_fpga=True
```

### Run test

See "Running the loopback test" section and run using the ```-c 8bit``` flag.

### After the test

After the test, reset the FPGA via the SCA by running:

``` shell
./testbench_[xzy].py reset_all_xcku
```

# Running the loopback test:

From ```CRU_ITS/modules/cru-sw/COMMON/``` run:

``` shell
python loopback.py -i <PCIeID> -l <links> -rst [-c 8bit]
```

The option ```-c 8bit``` is necessary for the XCKU, GBTx loopbacks.

For convenience, as it is easier to read, it is best to run it in two slots:

``` shell
python loopback.py -i <PCIeID> -l 0-5
```

``` shell
python loopback.py -i <PCIeID> -l 6-11
```

Run the test for 15 seconds minimum.
If a counter starts from a value other than 0, but does not increase, the issue is in the counter reset, not in the link. Just retry until they all start from 0.
If the counters are increasing, you found a bad fibre.

**NOTE:** CRU v2.7.3 is affected by the issue of the links being bad in the FPGA due to issues in the clock tree. Check an internal loopback **BEFORE** running the test.

# Running the loopback test with testbench:

from ```CRU_ITS/software/py``` run:

``` shell
./testbench.py cru start-gbt-loopback-test

# wait some time, then get statistics on errors
./testbench.py cru gbt stat

# to end the test:
./testbench.py cru stop-gbt-loopback-test
```
