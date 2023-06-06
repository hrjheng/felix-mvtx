# HOW to configure CRU for your detector

Set the proper clock (to be done after each firmware upload or a power cycle of the machine)

## If you don't use the LTU

The common **standatalone-startup** script provides different options used to configure the CRU to match the requirements of the detector,
It is possible to enbale/disaable links, change the GBT mode and set the CRU for continuous or packet mode.

```bash
cd cru-sw
```

Example
```
./COMMON/standalone-startup.py -i#0 -c local -g gbt -lb -l 0,1,2,3,4,5,6,7,8 -x ddg -m continuous
```
This will configure the CRU in
- GBT mode
- links from 0 to 8
- CONTINUOUS readout mode
- internal SERDES loopback
- DDG set to TX

Example 2
```
./COMMON/standalone-startup.py -i#0 -c local -g gbt -lb -l 0,1,2,3,4,5,6 -x ttc -t pattern -m continuous
```
This will configure the CRU in
- GBT mode
- links from 0 to 6
- CONTINUOUS readout mode
- internal SERDES loopback
- PATPLAYER set to TX



## If you use the LTU

```
./COMMON/standalone-startup.py -i#0 -c ttc --pon-upstream --onu-address ONU_ADDR
```
If you want to use the LTU in downstream direction only, the --pon-upstream and --onu-address options can be omitted. The former configures the PON TX fPLL and does the phase scanning, the latter assigns a unique address to the ONU, both required for the calibration from the LTU-side. You can also get the calibration status (note that the `ONU operational` field will be `NOT OK` until the LTU doesn't execute the `fullcal` command):

```
./COMMON/onu-status.py -i#0

 PON calibration status:
   ONU address:	3
   ---
   ONU RX40 locked:	OK
   ONU phase good:	OK
   ONU RX locked:	OK
   ONU operational:	NOT OK
   ONU MGT TX ready:	OK
   ONU MGT RX ready:	OK
   ONU MGT TX pll lock:	OK
   ONU MGT RX pll lock:	OK

```



## SPECIFIC DETECTOR EXAMPLE

### TPC

```
./COMMON/standalone-startup.py -i#0 -c local -g wb -l 0-11 -x ttc -t pattern -m continuous
```



### ITS

```
./COMMON/standalone-startup.py -i#0 -c local -g gbt -l 0-3 -x swt -m packet
```



### TOF

```
./COMMON/standalone-startup.py -i#0 -c local -g gbt -l 0,1,2,3 -x swt -m packet
```

... more will come




## Check the CRU configuration

To check if the CRU is configured properly execute the **report** script
```
./COMMON/standalone-startup.py -i#0 -c local -l 0-11 -m continuous -lb -x ddg
=========================================================================================
>>> Firmware short hash=0x910ae122
>>> Firmware build date and time=20181026  131956
>>> Altera chip ID=0x00540186-0x28520504
=========================================================================================
Starting TTC PON calibration
Starting GBT calibration



./COMMON/report.py -i#0
=========================================================================================
>>> Firmware short hash=0x910ae122
>>> Firmware build date and time=20181026  131956
>>> Altera chip ID=0x00540186-0x28520504
=========================================================================================
Link ID         GBT TX mode     GBT RX mode         GBT mux     Datapath mode   Enabled in datapath
---------------------------------------------------------------------------------------------------
Link  0 :               GBT             GBT             DDG        continuous               Enabled
Link  1 :               GBT             GBT             DDG        continuous               Enabled
Link  2 :               GBT             GBT             DDG        continuous               Enabled
Link  3 :               GBT             GBT             DDG        continuous               Enabled
Link  4 :               GBT             GBT             DDG        continuous               Enabled
Link  5 :               GBT             GBT             DDG        continuous               Enabled
Link  6 :               GBT             GBT             DDG        continuous               Enabled
Link  7 :               GBT             GBT             DDG        continuous               Enabled
Link  8 :               GBT             GBT             DDG        continuous               Enabled
Link  9 :               GBT             GBT             DDG        continuous               Enabled
Link 10 :               GBT             GBT             DDG        continuous               Enabled
Link 11 :               GBT             GBT             DDG        continuous               Enabled
Link 12 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 13 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 14 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 15 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 16 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 17 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 18 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 19 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 20 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 21 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 22 :               GBT             GBT         TTC:CTP        continuous              Disabled
Link 23 :               GBT             GBT         TTC:CTP        continuous              Disabled
------------------------------
24 link(s) found in total
------------------------------
globalgen: | ttc240freq 0.00 MHz | lcl240freq 240.47 MHz | ref240freq 240.47 MHz | clk not ok cnt     0 |
Wrapper 0: | ref freq0 240.47 MHz  | ref freq1 0.00 MHz  | ref freq2 0.00 MHz  | ref freq3 0.00 MHz  |

```



## Start the DMA 

These commands will create a ramdisk of **2GB** and start the dma software

```
mkdir /tmp/ramdisk
mount -t tmpfs -o size=2048M tmpfs /tmp/ramdisk
o2-roc-bench-dma --verbose   --id=#0 --links=0-15  --no-errorche --loopback=DDG --generator=1 --bytes=2048Mi  --to-file-bin=/tmp/ramdisk/output.bin
```

**Please use readout to collect data with DMA. o2-roc-bench-dma should be used just to validate the firmware**



## Collect DATA without LTU

The data taking starts upon receiving either SOT or SOC. By default the CTPEmulator is in periodic trigger mode which will send the SOT. If one needs continuous data taking, use the `-md continuous` option.
```
./COMMON/cru-readout.py -i#0 -cid CRUID
cd ../CTP
```
Send **SOC**
```
./CTP/ctpemulator.py -i#0 -md continuous
```

Send **SOT**
```
./CTP/ctpemulator.py -i#0 -md periodic
```



## Collect DATA using the LTU

```
./COMMON/cru-readout.py -i#0 -cid CRUID
```
Then send SOT or SOC using the LTU.


## Send End-Of-Trigger or End-Of-Continuous

```
./CTP/ctpemulator.py -i#0 -eox
```

## ANALYZE data

```bash
./COMMON/event-dump.py /tmp/ramdisk/output.bin | less

Link ID:  10
   0)        0x0        0x0        0x0        0x0        0xa 0x20002000     0xdead 0x20004003
   8)        0x0        0x0      0x101 0x12345678        0x0        0x0 0xcafebeef        0x0
  16)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0
  24)        0x0        0x1        0x1        0x1        0x0        0x1        0x1        0x1
  32)        0x0        0x2        0x2        0x2        0x0        0x2        0x2        0x2
  40)        0x0        0x3        0x3        0x3        0x0        0x3        0x3        0x3
  48)        0x0        0x4        0x4        0x4        0x0        0x4        0x4        0x4
  56)        0x0        0x5        0x5        0x5        0x0        0x5        0x5        0x5
  64)        0x0        0x6        0x6        0x6        0x0        0x6        0x6        0x6
  72)        0x0        0x7        0x7        0x7        0x0        0x7        0x7        0x7
  80)        0x0        0x8        0x8        0x8        0x0        0x8        0x8        0x8
  88)        0x0        0x9        0x9        0x9        0x0        0x9        0x9        0x9
  96)        0x0        0xa        0xa        0xa        0x0        0xa        0xa        0xa
 104)        0x0        0xb        0xb        0xb        0x0        0xb        0xb        0xb

```
