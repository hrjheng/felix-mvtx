# DESCRIPTION
I2C interface to write and read registers on a chip connected to the I2C bus

# CRU CARD
## CRU FPGA I2C pins
NAME | FPGA PIN 
-----|----------
I2C\_SCL0 | F7
I2C\_SDA | F2
A10\_SI53XX\_SMB\_SCL | AY34
A10\_SI53XX\_SMB\_SDA | BD24
A10\_MP\_SCL | A17
A10\_MP\_SDA | B16
MMC\_A10\_TSENSE\_SMB\_SCL | BA35
MMC\_A10\_TSENSE\_SMB\_SDA | BD29
A10\_CPCIE\_SMB\_SCL | AV18
A10\_CPCIE\_SMB\_SDA | AV19
A10\_SFP\_SMB\_SCL | AR36
A10\_SFP\_SMB\_SDA | AT34
A10\_5338\_SMB\_SCL | BB25
A10\_5338\_SMB\_SDA | BB23
A10\_PEX\_I2C\_SCL | AR37
A10\_PEX\_I2C\_SDA | AH35

## I2C bus addresses

NAME | BUS ADDRESS| Component | Chip address | 
-----|------------|---|---
Temperature sensors | 0x00030000 | Arria 10 internal (MAX1619)<br> LTC2990 with remote sensors<br>LTC2990<br>LTC2990| 0x18<br>0x4C<br>0x4D<br>0x4F |
SFP+ module | 0x00030200 | ?<br>? | 0x50<br>0x51 |
Minipods | 0x00030300
|||TX Minipod| 0x28
|||TX Minipod| 0x29
|||RX Minipod| 0x30
|||RX Minipod| 0x31
|||-| 0x58
|||-| 0x59
|||-| 0x68
|||-| 0x69
PON refclock PLL | 0x00030400 | SI5344 | 0x68
Jitter cleaner PLL \#1 | 0x00030500 | SI5345 | 0x68
Jitter cleaner PLL \#2 | 0x00030600 | SI5345 | 0x68
SFP+ module \#2 (not used in ALICE) | 0x00030700
EEPROM | 0x00030800 | | 0x50

## Directory structure
```
sw
+-- CRUv1
+-- minipod
+-- register_maps
```
|||
|---|---|
| sw | I2C scripts
| CRUv1 | Scripts for old CRU hardware (SI5338 PLL) | 
| minpod | Minipod scripts |
| register_maps | PLL configuration files |

Modules have uppercase names, scripts have lowercase names.

## Scripts


### i2c_scan.sh/py

```
./i2c_scan.sh $PCIE_ID
```
or for a single base address
```
./i2c_scan.py -i $PCIE_ID -b base_address
```

Example:
```
ADD  0x4c  CHIP FOUND [ 0x80000000 ]
ADD  0x4e  CHIP FOUND [ 0x80000000 ]
ADD  0x4f  CHIP FOUND [ 0x80000000 ]
ADD  0x77  CHIP FOUND [ 0x80000000 ]
On I2C chain [ 0x00030000 ] found  4  chip/s
--
ADD  0x50  CHIP FOUND [ 0x80000025 ]
ADD  0x51  CHIP FOUND [ 0x80000025 ]
On I2C chain [ 0x00030200 ] found  2  chip/s
--
ADD  0x28  CHIP FOUND [ 0x800000ff ]
ADD  0x29  CHIP FOUND [ 0x800000ff ]
ADD  0x30  CHIP FOUND [ 0x800000ff ]
ADD  0x31  CHIP FOUND [ 0x800000ff ]
ADD  0x58  CHIP FOUND [ 0x800000ff ]
ADD  0x59  CHIP FOUND [ 0x800000ff ]
ADD  0x68  CHIP FOUND [ 0x800000ff ]
ADD  0x69  CHIP FOUND [ 0x800000ff ]
On I2C chain [ 0x00030300 ] found  8  chip/s
--
ADD  0x68  CHIP FOUND [ 0x80000000 ]
On I2C chain [ 0x00030400 ] found  1  chip/s
--
ADD  0x68  CHIP FOUND [ 0x80000003 ]
On I2C chain [ 0x00030500 ] found  1  chip/s
--
ADD  0x68  CHIP FOUND [ 0x80000000 ]
On I2C chain [ 0x00030600 ] found  1  chip/s
--
ADD  0x50  CHIP FOUND [ 0x8000007d ]
On I2C chain [ 0x00030800 ] found  1  chip/s
--

```

### ltc2990_i2c.py
There are 4 LTC2990 sensors on the board used to measure temperature and voltage.

Example:
```
./ltc2990.py -i#0
HIP TEMPERATURE [ 0x4c ]
CHIP INT TEMP [ 0.0 ]
CHIP VCC      [ 2.5 ]
T1 :  36.875
CHIP TEMPERATURE [ 0x4e ]
CHIP INT TEMP [ 0.0 ]
CHIP VCC      [ 2.5 ]
T1 :  30.8125 
T3 :  27.125
CHIP TEMPERATURE [ 0x4f ]
CHIP INT TEMP [ 0.0 ]
CHIP VCC      [ 2.5 ]
T1 :  39.125 
T3 :  33.5625
```

### max1619_i2c.py
Read onboard MAX1619 digital thermometer.

Example:
```
./max1619_i2c.py -i#0
```

### read_eeprom.py
Reads serial eeprom content (CRU production info).

Fields:
 * "cn": contractor name
 * "io": minipod configuration (RX/TX)
 * "pn": serial number of the board
 * "dt": date of production

Example:
```
./read_eeprom.py -i#0
{"cn": "FEDD", "dt": "2019-06-17", "io": "24/24", "pn": "p40_fv22b10242", "serial_number_p40": "18-02409 - 0189"}
```

### read_sfp.py
Reads SFP info and status.

Example:
```
./read_sfp.py -i#0
       Vendor:	GO!FOTON        
  Part Number:	SOGX2629-PSGA   
Serial Number:	A6961181600403  
  Temperature:	      31.2 C
          Vcc:	       3.3 V
      Tx Bias:	      23.3 mA
     Tx Power:	       3.8 dBm
     Rx Power:	      -9.8 dBm
```

### si534x_i2c.py
Script to control, configure and read status of SI5344 and SI5345 PLLs.

Parameters:
```
  -h, --help            show this help message and exit
  -i ID, --id ID        PCIe address, e.g. 06:0.0. It can be retrieved by
                        using the o2-roc-list-cards command
  -p {1,2,3}, --pll {1,2,3}
                        select PLL, 1: SI5345 #1, 2: SI5345 #2, 3: SI5344
  -c COM, --command COM
                        reset-pll, read-pll-config, config-pll, config-pll-
                        all, report-status, read-reg, write-reg, clear-sticky
  -x MAP, --reg-map1 MAP
                        register map for SI5345 PLL1 created by clock builder
                        pro
  -y MAP, --reg-map2 MAP
                        register map for SI5345 PLL2 created by clock builder
                        pro
  -z MAP, --reg-map3 MAP
                        register map for SI5344 PLL created by clock builder
                        pro
  -o OUTPUT, --output OUTPUT
                        output file
  -s, --show-sticky     Report sticky bits as well
  -d DATA, --data DATA  value in hexa
  -e ADDR, --reg-address ADDR
                        I2C address in hexa
  --hard-reset          Select hard reset. Default is Soft reset
```

### minipod/mptx-disable.py

Disables TX Minipods' output. (See I2C Bus addresses table above for the TX minipods' chip address)

```
  -h, --help            show this help message and exit
  -i ID, --id ID        card ID
  -c CHIP_ADDR, --chip-addr CHIP_ADDR
                        I2C address of Minipod chip, e.g. 0x29
  -e, --enable          enable selected channels, default is disable
  -l LINKS, --links LINKS
                        specifiy link IDs, eg. all, 1-4 or 1,3,11
```

Examples:
```
./mptx-disable.py -i#0 -c 0x28 -l 0-3
0 0                                        <- previous state (0:enabled, 1: disabled)
0 1111                                     <- new state
```

### minipod/mprx-opt-pwr.py
Reads RX Minipods' input received optical power.

Example:
```
./mprx-opt-pwr.py -i#0

 RX input optical powers

        0x30                    0x31           
Link   Power [uW]       Link   Power [uW]      
------------------      ------------------     
   0 :  349.0              0 :  342.4           
   1 :  319.3              1 :  336.4           
   2 :  274.0              2 :  367.9           
   3 :  344.9              3 :  211.5           
   4 :  291.9              4 :  349.1           
   5 :  343.2              5 :  365.4           
   6 :  311.3              6 :  330.2           
   7 :  341.7              7 :  377.0           
   8 :  304.0              8 :  318.5           
   9 :  318.6              9 :  371.7           
  10 :    0.0             10 :    0.0           
  11 :    0.0             11 :    0.0  
  ```

### minipod/mp-temp.py

Reads Minipod temperatures.

Example:
```
./mp-temp.py -i#0
Addr	Type	Temperature [C]
---------------------------------
0x28 	 TX 	 43.82
0x29 	 TX 	 41.67
0x30 	 RX 	 36.49
0x31 	 RX 	 37.32
Unknown chip at address 0x58
Unknown chip at address 0x59
Unknown chip at address 0x68
Unknown chip at address 0x69
```
