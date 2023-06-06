# Running the daq_test.py script

## Before the test

1. Setup the config file for ```CRU_ITS/software/config/o2-readout-exe``` following the instructions [here](https://github.com/AliceO2Group/Readout/blob/master/doc/configurationParameters.md)
2. Make output directory (as specified in 1.) and mount it:
``` shell
sudo mount -t tmpfs -o size=32G tmpfs <PATH>
```
3. Setup the CRU endpoint configuration (e.g. roc_flpits11_sn0171_ep0.cfg) and configure the CRU. **Note**: this was previously done withing the DAQ test script, but was removed as it impacted the configuration of links not related to the test.
4. Setup the daq_test.py configuration.
5. Power on the Readout Unit(s).
6. From ```CRU_ITS/software/py/``` run

``` shell
./testbench(_<ID>).py initialize boards
./testbench(_<ID>).py initialize_all_rdos
```
7. Depending on daq_test configuration powering scheme, power on the detector. E.g.:
``` shell
./testbench(_<ID>).py power_on_ib_stave
```

## Run the test

1. On a separate shell go to the ```CRU_ITS/software/py/``` and run

``` shell
./daq_test.py [-c RELATIVE_PATH_TO_CONFIG_FILE]
```

## Interrupt the test

If you wish to sanely interrupt the run press ```q```.

## After the test

1. Decode the data by running (from a specific FEE ID)

```shell
./decode.py [-f=<PATH TO RAW FILE>, default=/dev/stdin] [-s=<OFFSET IN BYTES>, default=0] [-i=<FEE ID>, default=0]
```

1. (bis) to decode the data from multiple FEE ID at the same time, just run the multiple instances in parallel with different FEE ID

``` shell
for gbt_ch in 0 1; do for fee_id_offset in 0 256 512; do ./decode.py -f=/tmp/ramdisk/data.raw -i=$(($gbt_ch + $fee_id_offset)) & done done
```

1. (tris) to decode the data from lz4 compressed (and multiple fee_ids)

``` shell
for gbt_ch in 0 1; do for fee_id_offset in 0 256 512; do lz4 -d /tmp/ramdisk/data.lz4 | ./decode.py -i=$(($gbt_ch + $fee_id_offset)) & done done
```

## Mapping the channels to the PCI endopoint

- Run:

``` shell
o2-roc-list-cards
```

You will see a list of CRUs connected with the correct Endpoint ID for each PCIe ID.
In ```readout.cfg``` select the the PCIe ID with endpoint 0 to read out the data.

## **Alternative** Mapping the channels to the PCI endopoint

- Run:

``` shell
[its@flpits1.cern.ch COMMON]$ o2-roc-reg-read --id=<PCIe ID 1> --channel=0 --address=0x500
0x0
[its@flpits1.cern.ch COMMON]$ o2-roc-reg-read --id=<PCIe ID 2> --channel=0 --address=0x500
0x11111111
```

The first is mapped to the endpoint 0, the second to the endpoint 1.
In ```readout.cfg``` select the the PCIe ID with endpoint 0 to read out the data.

## Selecting the correct numa in readout.cfg

- Run:

``` shell
o2-roc-list-cards
```

You will see a list of CRUs connected with the correct NUMA for each PCIe ID.

## Configuration file for daq_test.py

### TESTBENCH section

| Parameter | Description | Values | Notes |
| - | - | - | - |
| YML | Path to yml file for configuring the testbench | | |

### GITHASH section

| Parameter | Description | Values | Notes |
| - | - | - | - |
| CRU | CRU FPGA design version | Hex | |
| RDO | RU main FPGA design version  | Hex | |
| PA3 | RU aux FPGA design version  | Hex | |
| CHECK_HASH | Check of hash configuration | Boolean | |

### PB section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| LIMIT_TEMPERATURE_SOFTWARE                              | | Float (deg C) | |
| LIMIT_TEMPERATURE_HARDWARE                              | | Float (deg C) | |
| POWERUNIT_1_OFFSET_AVDD | List of offsets of the AVDD channels of the Powerunit on I2C-1 | List of hex value | |
| POWERUNIT_1_OFFSET_DVDD | List of offsets of the DVDD channels of the Powerunit on I2C-1 | List of hex value | |
| POWERUNIT_2_OFFSET_AVDD | List of offsets of the AVDD channels of the Powerunit on I2C-2 | List of hex value | |
| POWERUNIT_2_OFFSET_DVDD | List of offsets of the DVDD channels of the Powerunit on I2C-2 | List of hex value | |

### TRIGGER section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| MODE                      | see RuTriggeringMode | CONTINUOUS, PERIODIC, DUMMY_CONTINUOUS, PERIODIC_LIMITED | |
| PERIOD_BC                 | RU Continuous mode trigger frequency or "periodic" trigger period expressed in BCs | See [table 4](https://www.overleaf.com/read/sybgrjhpghdz) for continuous mode allowed settings| |
| NUM_TRIGGERS              | Number of triggers to send when configured in PERIODIC_LIMITED mode | 32b int | |
| USE_LTU                   | Use LTU for triggering the RU, GBTx2 source is automatically set if True | Boolean | |
| USE_RUN_SERVER            | The LTU is controlled by run server or manually. USE_LTU and GBTx2 source is automatically set if True | Boolean | |
| TRIGGERED_STROBE_DURATION | Strobe length in "triggered" mode (in ns) | | |
| SOURCE | see TriggerSource | GBTx2, SEQUENCER | |
| TF     | Number of TF to run for when using the SEQUENCER | 1-511 | |
| HBF_PER_TF | Number of HBF for each TF | 1-511 | |
| HBA_PER_TF | Number of HBA for each TF | 1-511 | Must be <= HBF_PER_TF |

### ALPIDE section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| POWERING_SCHEME               | Powering scheme for the stave, see SensorPoweringScheme | POWERUNIT, NONE, DUAL_POWERUNIT, HLL0_POWERUNIT, MONITOR | |
| AVDD                          | AVDD settings for the sensors (in V) | float | |
| DVDD                          | DVDD settings for the sensors (in V) | float | |
| VBB                           | VBB settings for the sensors (in V) | float | |
| AVDD_MAX_CURRENT              | AVDD settings for the sensors max current (in A) | float | |
| DVDD_MAX_CURRENT              | DVDD settings for the sensors max current (in A) | float | |
| PATTERN                       | Masking and pulsing scheme, see SensorMatrixPattern | EMPTY, IMAGE, ROW, PIXEL, TWO_PIXELS_PER_REGION, MAX_100KHZ_1GBTx, MAX_100KHZ_3GBTX, MAX_100KHZ_1GBTX_OB, ONE_PIXEL, ALL_PIXELS, FRACTION | |
| DRIVER_DAC                    | DTU main driver dac settings | 0-15 or 0x0-0xF | |
| PRE_DAC                       | DTU pre-emphasis driver dac settings | 0-15 or 0x0-0xF | |
| PLL_DAC                       | DTU PLL chargepump dac settings | 0-15 or 0x0-0xF | |
| CLOCK_GATING                  | If True, enables clock gating | Boolean | |
| SKEW_START_OF_READOUT         | If True, enables skew start of readout | Boolean | |
| CLUSTERING                    | If True, enables sensor clustering | Boolean | |
| OB_LOWER_MODULES              | List of modules to use in the test of the OB stave (Lower HS) | in range(1,8) | |
| OB_UPPER_MODULES              | List of modules to use in the test of the OB stave (Upper HS) | in range(1,8) | |
| EXCLUDED_SLAVE_CHIPIDEXT_LIST | Extended chipids to be excluded from the test of the OB stave | valid extended chipid for a slave chip | On upper stave the ```chipid[7]=1``` |
| DISABLE_MANCHESTER            | If True, disables Manchester encoding | Boolean | |
| ANALOGUE_PULSING              | | Boolean | |
| PULSE_TO_STROBE               | | Boolean | |
| SEND_PULSES                   | | Boolean | |
| ENABLE_STROBE_GENERATION      | | Boolean | |


### READOUT section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| DRY            | If True, no data are read from the lanes | Boolean | |
| GPIO_CONNECTORS        | List of connectors to be used for the readout of the OB stave | | |
| EXCLUDE_GTH_LIST          | List of GTH to be deactivated in the readout | | |
| EXCLUDE_GPIO_LIST         | List of GPIO to be deactivated in the readout | | |
| ONLY_MASTERS              | If True only OB master chips are read out| Boolean | |


### PA3 section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| READ_VALUES  | If True, reads the PA3 values during datataking | Boolean | |
| SCRUBBING    | If True, runs scrubbing during the test | Boolean | |

### READOUT_PROC
| Parameter | Description | Values | Notes |
| - | - | - | - |
| ACTIVE   | If True, activates the readout process | Boolean | |
| CFG      | Relative path to config file for o2-readout-exe from the python script folder | | |

### TEST section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| DURATION                       | DAQ running time in seconds | int | |
| READ_SENSORS_DURING_DATATAKING | If True, gates the triggers to the sensor and uses the window to read values from the sensors | Boolean | |
| EVENT_ANALYSYS_ONLINE          | If True, analyses the data online (not implemented yet)  | Boolean | |

## The following sections are used in the obtest configuration files:

### THRESHOLD section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| ITHR           | ITHR register setting | | optimum 50|
| VCASN          | VCASN register setting | | optimum 60|
| VCASN2         | VCASN2 register setting | | optimum 72|
| VPULSEH        | VPULSEH register setting | | optimum 170|
| VRESETD        | VRESETD register setting | | optimum 147|
| IDB            | IDB register setting | | optimum 29|
| NINJ           | NINJ register setting | | optimum 21|
| EXCLUDED_ROWS  | EXCLUDED_ROWS setting | | |
| STEP_ROWS      | STEP_ROWS setting | | |
| START_CHARGE   | START_CHARGE setting | | optimum 0 for non tuned threshold scan|
| END_CHARGE     | END_CHARGE setting | | optimum 50 for non tuned threshold scan|
| FRAME_DURATION | FRAME_DURATION register setting | | optimum 199|
| FRAME_GAP      | FRAME_GAP register setting | | optimum 0|
| PULSE_DELAY    | PULSE_DELAY register setting | | optimum 0|
| PULSE_DURATION | PULSE_DURATION register setting | | optimum 400|

### FAKEHIT section
| Parameter | Description | Values | Notes |
| - | - | - | - |
| ITHR               | ITHR register setting | | optimum 50|
| VCASN              | VCASN register setting. Not used when VCASN is taken from yml file. | | optimum 60|
| VCASN2             | VCASN2 register setting. Not used when VCASN is taken from yml file. | | optimum 72|
| VPULSEH            | VPULSEH register setting | | optimum 170|
| VRESETD            | VRESETD register setting | | optimum 147|
| IDB                | IDB register setting | | optimum 29|
| MODE               | RU trigger mode | | CONTINUOUS for fake hit scan|
|FREQUENCY           | Trigger frequency | integer or `MIN` | MIN is the minimal trigger frequency possible. It allows for FRH data on Outer Barrel without Busy events. |
|HEARTBEAT_FREQUENCY | Heartbeat trigger frequency | integer or `MIN` | MIN is the minimal HB frequency possible. It allows for FRH data on Outer Barrel without Busy events. |
|SOURCE              | see RuTriggeringSource | GBTx0, GBTx2 | |
