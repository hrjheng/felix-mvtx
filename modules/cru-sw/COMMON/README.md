# COMMON tools

LIB contains the python modules that correspond to the modules of the firmware and the low-level software interface.
These modules define the functions and routines that the common tools and scripts can use to interact with the CRU.

## The list of the tools:
*  __standalone-startup.py__


*  event-dump.py
*  extract-cru-address-table.py
*  fifo.py
*  gbt-mode.py
*  gbt-mux.py
*  gbtx-checker.py
*  linkstat.py
*  loopback.py
*  mem-dump.py
*  monitor-pkt.py
*  onu-status.py
*  patplayer.py
*  pll-output.py
*  report.py
*  reset-clock-tree.py
*  reg-dump.py
*  roc-list-card.py
*  rsu.py
*  test-dwrapper.py
*  temperature.py

For details and usage examples see below.


### standalone-startup.py

Configures the card.
If one wants to use the local oscillator instead of the clock recovered from the PON link, use


```bash
./standalone-startup.py --id PCIE_ID -c local
```
If an LTU is connected then
```bash
./standalone-startup.py --id PCIE_ID -c ttc --pon-upstream --onu-address ONU_ADDR
```
If one wants to use the LTU in downstream direction only, the --pon-upstream and --onu-address options can be omitted.


#### List of all options:

| Option  |  Description                                                 |
|-----------------|--------------------------------------------------------------|
|  -i ID, --id ID			| PCIe address, e.g. 06:0.0 or card number e.g. #0. Both can be retrieved by using the o2-roc-list-cards command                     |
|  -l LINKS, --links LINKS      	| Specifiy link IDs, eg. all, 0-4 or 1,3,4,16	    	      		     				 |
|  -c {local,ttc}, --clock {local,ttc}  | Select which clock source to use: local oscillator or recovered PON clock, default is `local`.	 |
|  -v, --verbose           		|increase output verbosity     	    	  	     		      	     	     	      		 |
|  -p, --pon-upstream    		|Configure card for PON upstream as well (phase scanning for PON TX, etc.)				 |
|  -t {ctp,pattern,midtrg}, --ttc-downstream {ctp,pattern,midtrg} |Select the source of output of the TTC module (downstream trigger data): `ctp`, `pattern` or `midtrg`. Select CTP to simply forward either the real CTP or the CTPEmulator data, `pattern` for the pattern player data, and `midtrg` in case of MID (repeated 8-bit data in payload). Default is `ctp` |
|  -g {gbt,wb}, --gbt-mode {gbt,wb}	|GBT RX mode: GBT or WideBus (`wb`). Default is `gbt`  	      	  	 	     	     	    	 |
|  -o ONU\_ADDRESS, --onu-address ONU\_ADDRESS | address of the ONU module (must be unique when multiple CRUs are connected to the LTU)		 |
|  -m {packet,continuous}, --mode {packet,continuous} | Configures datapath mode according to the type of the incoming datastream. Default is `packet`. |
|  -lb, --internal-loopback | Enable GBT internal loopback	   	    	 	      	       	      	       		   	      	 |
|  -x {ttc,ddg,swt}, --gbt-mux {ttc,ddg,swt} | Sets the mux that controls the data source selection for the GBT TX input.	Default is `ttc`	 |
|  -d, --devkit                         | Required when configuring A10 development kit |


### event-dump.py


```bash
./event-dump.py PATH_TO_BIN_FILE
```
example:
```bash
./event-dump.py /tmp/output.bin | less

Link ID:  0
   0)   0x112200   0x112244  0xce9860c  0xce9860c        0x0 0x20000000     0x12ec  0x1f00403  <== RDH WORD1 RDH WORD0
   8)   0x112233   0x112266        0x0        0x0   0x112233   0x112255        0x3        0x0  <== RDH WORD3 RDH WORD2
  16)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0  <== DATA
  24)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0
  32)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0
  40)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0
  48)        0x0        0x0        0x0        0x0        0x0        0x0        0x0        0x0

```
The tool will display the data in 256 bit format



### extract-cru-address-table.py

Updates cru\_table.py based on [pack\_cru\_core.vhd](https://gitlab.cern.ch/alice-cru/cru-fw/blob/master/pack_cru_core.vhd).

```bash
cp PATH_TO_CRU_FW/pack_cru_core.vhd .
./extract_cru_address_table.py
```



### fifo.py
This script allows the user to display the data stored in the last FIFO in the readout chain to debug the data stream (in case there are problems with the DMA)

```bash
./fifo.py [-h] -i PCIE_ID [-c] [-g] [-w WORD]
-c Init the CRU
-g enable INTERNAL data generator
-w number of words to display ... 0 infinite
```
example, showing 256 words from the internal data generator:

```
python fifo.py -i#0 -c -g -w256
20300002 0000000000000000000000000000000000000012200020000000DEAD20004003
20200000 000000000000000000000101123456780000000000000000CAFEBEEF00000000
20100000 0000000000000000000000000000000000000000000000000000000000000000
20000000 0000000000000001000000010000000100000000000000010000000100000001
20300000 0000000000000002000000020000000200000000000000020000000200000002
20200000 0000000000000003000000030000000300000000000000030000000300000003
20100000 0000000000000004000000040000000400000000000000040000000400000004
20000000 0000000000000005000000050000000500000000000000050000000500000005
20300000 0000000000000006000000060000000600000000000000060000000600000006
20200000 0000000000000007000000070000000700000000000000070000000700000007
20100000 0000000000000008000000080000000800000000000000080000000800000008
20000000 0000000000000009000000090000000900000000000000090000000900000009
20300000 000000000000000A0000000A0000000A000000000000000A0000000A0000000A
```

example, waiting data from GBT
```
./fifo.py -i#0 -c -w256
GBT link

```



### gbt-mode.py

Sets the GBT mode to GBT (`gbt`) or Wide Bus (`wb`) for the specified direction and links.

Example:
```
./gbt-mode.py -i#0 --links 0-5 --mode wb --direction rx
```



### gbt-mux.py

Sets the mux that controls the data source selection for the GBT TX input. Possible inputs are 

 * `ttc` (for TTC-PON, CTPEmulator, Pattern player, MID trigger scheme)
 * `ddg` (detector data generator)
 * `swt` (single word transaction)

The mux can be configured for each link. If the --shortcut option is specified, all links are put into shortcut mode (loopback every TX link's input directly to the RX links' output skipping the GBT, enabling the GBT to operate independently).

Example:
```
./gbt-mux -i#0 --link 0-5 --mux ddg
```



### gbtx-checker.py

Same as loopback.py, but checks the pattern generated by the GBTx chip instead of the pattern generator in the CRU. The pattern can be counter or static.

Example: Check counter pattern on link 13 in widebus mode, print only error counters (no FEC counter), reset counter in the beginning.
```
./gbtx-checker.py -i#0 --pattern counter --link 13 -mode wb -s cnt -rst 
```



### linkstat.py

Gives report about link health and status by displaying error counters, RX/TX clock frequencies, etc.
Everything should be locked and error counters should not change (can be nonzero, though), otherwise the link is definitely down. If indicated the links are in internal loopback mode, otherwise they are in normal mode.

Example:
```
./linkstat.py -i#0 -v
```

Possible output for a link:
```
=================================================================
Link #23: Wrapper 0 - Bank 3 - Link 5
-----------------------------------------------------------------
          Status bit           |           Sticky bit  
Bank PLL locked : YES          |    Phy up        : NO 
Locked to data  : NO           |    Data layer up : NO 
TX clock frequency: 240.47 MHz
RX clock frequency: 240.52 MHz
```

The sticky bit status is reseted with the following
```
./linkstat.py -i#0 --reset-sticky
```


### loopback.py

Runs loopback tests, and prints error counters (`cnt`), FEC counters (`fec`) or both (`all`) for the specified links using the GBT's internal data generator. It can operate in gbt or widebus mode (original mode settings are used if --mode is not specified). Each bit in [95:0] of the payload can be masked by using the --mask-[hi|mid|low] flags and a 32-bit mask. For resetting the counters to zero at the start, the -rst/--reset-counters option should be used. If everything is well configured and working, the counters are not changing. Otherwise it prints

 *  `pll_lock`	    : PLL error
 *  `lockedtodata`  : no valid incoming signal (e.g. missing link)
 *  `headerlock`    : can't find packet header in the stream

Example:
```
./loopback.py -i#0 --link 0-5 --mode wb --stat cnt --mask-low 0xFFFF0000
```
```bash
Note: standalone must have been executed first...

         seconds         error:0         error:1         error:2         error:3         error:4         error:5
               1               0               0               0    lockedtodata    lockedtodata    lockedtodata
               2               0               0               0    lockedtodata    lockedtodata    lockedtodata
               3               0               0               0    lockedtodata    lockedtodata    lockedtodata
               4               0               0               0    lockedtodata    lockedtodata    lockedtodata
               5               0               0               0    lockedtodata    lockedtodata    lockedtodata
               6               0               0               0    lockedtodata    lockedtodata    lockedtodata
               7               0               0               0    lockedtodata    lockedtodata    lockedtodata
```



### mem-dump.py
This tool is similar to event-dump.py, but it displays data in 32 bit format.
```bash
./mem-dump.py PATH_TO_BIN_FILE
```
example:
```bash
./mem-dump.py /tmp/output.bin | less

 0x1f00403 <== RDH WORD 0 (word 0)
    0x12ec <== RDH WORD 0 (word 1)
0x20000000 <== RDH WORD 0 (word 2) SIZE 8192 OFFSET 0
       0x0 <== RDH WORD 0 (word 3) LINK ID 0 EV 1
 0xce9860c <== RDH WORD 1 (word 0)
 0xce9860c <== RDH WORD 1 (word 1)
  0x112244 <== RDH WORD 1 (word 2)
  0x112200 <== RDH WORD 1 (word 3)
       0x0 <== RDH WORD 2 (word 0)
       0x3 <== RDH WORD 2 (word 1)
  0x112255 <== RDH WORD 2 (word 2)
  0x112233 <== RDH WORD 2 (word 3)
       0x0 <== RDH WORD 3 (word 0)
       0x0 <== RDH WORD 3 (word 1)
  0x112266 <== RDH WORD 3 (word 2)
  0x112233 <== RDH WORD 3 (word 3)
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0
       0x0

```



### monitor-pkt.py

Print packet statistics per link, and also dropped packets and total packets/sec per datapath wrapper.

Example:
```
./monitor-pkt.py -i#0
rejected packet =0, accepted packets=406928 and forced packets =0
rejected packet =0, accepted packets=406933 and forced packets =0
rejected packet =0, accepted packets=406934 and forced packets =0
rejected packet =0, accepted packets=406936 and forced packets =0
rejected packet =0, accepted packets=406937 and forced packets =0
rejected packet =0, accepted packets=406939 and forced packets =0
rejected packet =0, accepted packets=406940 and forced packets =0
rejected packet =0, accepted packets=406941 and forced packets =0
rejected packet =0, accepted packets=406943 and forced packets =0
rejected packet =0, accepted packets=406944 and forced packets =0
rejected packet =0, accepted packets=406945 and forced packets =0
rejected packet =0, accepted packets=406947 and forced packets =0
rejected packet =0, accepted packets=406948 and forced packets =0
rejected packet =0, accepted packets=406949 and forced packets =0
rejected packet =0, accepted packets=406951 and forced packets =0
rejected packet =0, accepted packets=406953 and forced packets =0
rejected packet =0, accepted packets=406954 and forced packets =0
rejected packet =0, accepted packets=406957 and forced packets =0
rejected packet =0, accepted packets=406957 and forced packets =0
rejected packet =0, accepted packets=406958 and forced packets =0
rejected packet =0, accepted packets=406960 and forced packets =0
rejected packet =0, accepted packets=406961 and forced packets =0
rejected packet =0, accepted packets=406963 and forced packets =0
rejected packet =0, accepted packets=406964 and forced packets =0
-----------------------------------------------------------------------------
Wrapper 0:  dropped packets:    4883516, 	total packets/sec:     923101
Wrapper 1:  dropped packets:    4883551, 	total packets/sec:     923101
```



### onu-status.py

Prints the confiugration state of the PON TX/RX modules. `ONU operational` requires a calibration step on the LTU to be OK.

Example:
```
./onu-status.py -i#0

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



### patplayer.py

Sends IDLE, SYNC or RESET patterns of configurable length. Default is IDLE, the SYNC and RESET can be triggered either by manually or by selecting a triggering bit from TTC\_DATA[31:0].
If enabled, asserting the global RUN\_ENABLE signal also triggers RESET.

The length of the SYNC and RESET patterns can be set, also the SYNC can be delayed.

| Option | Description |
|--------|------------|
|  -i ID, --id ID        |  PCIe address, e.g. 06:0.0 or card number e.g. #0. Both can be retrieved by using the o2-roc-list-cards command|
|  -v, --verbose         | Increase output verbosity |
|  -s SYNC, --sync SYNC  | 80-bit SYNC pattern in hexadecimal  |
|  -r RST, --reset RST   | 80-bit RST pattern in hexadecimal   |
|  -e IDLE, --idle IDLE  | 80-bit IDLE pattern in hexadecimal  |
|  --sync-length SYNCLEN | Length of the SYNC pattern, deafult is 1 |
|  --sync-delay DELAY    | Length of SYNC delay (send the SYNC this number of clock cycles later), default is 0 |
|  --reset-length RSTLEN | Length of the RST pattern, default is 1
|  --rst-trg-sel RSTTRG  | Select trigger for RESET from TTC\_DATA[0-31], default is 30 |
|  --sync-trg-sel SYNCTRG| Select trigger for SYNC from TTC\_DATA[0-31], default is 29  |
|  -ss, --sync-at-start | Enable automatically sending SYNC pattern when runenable goes high |
|  -t, --trg-sync        | Manually trigger SYNC pattern |
|  -u, --trg-rst         | Manually trigger RESET pattern|

Examples:

1. (TPC usecase) Send SYNC pattern of 0xCC when receiving Start-Of-Continuous (TTC\_DATA[9]) 

```
./patplayer.py -i#0 -s 0xCC -e 0x0 -r 0x0 --sync-trg-sel 9
```

2. Send a single SYNC pattern of 0xAA without delay, manually triggered

```
./patplayer.py -i#0 --idle 0x0 --sync 0xAA --reset 0x0 --sync-length=1 --sync-delay=0  --trg-sync
```

3. Select TTC\_DATA[4] to trigger the reset pattern (0xBB for two clock cycles).

```
./patplayer.py -i#0 --idle 0x0 --sync 0x0 --reset 0xBB --reset-length 2  --rst-trg-sel 4
```


### pll-output.py

Reports which outputs of the external PLLs are enabled.

Example:
```
./pll-output.py -i#0
```



### report.py

Prints a general report about the configured state of the card. 

Example:
```
./report.py -i#0

=========================================================================================
>>> Firmware short hash=0x946d668a
>>> Firmware build date and time=20181015  153050
>>> Altera chip ID=0x00540186-0x2855060b
=========================================================================================
Link ID 	GBT TX mode	GBT RX mode	    GBT mux	Datapath mode	Enabled in datapath
---------------------------------------------------------------------------------------------------
Link  0 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  1 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  2 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  3 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  4 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  5 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  6 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  7 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  8 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link  9 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 10 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 11 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 12 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 13 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 14 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 15 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 16 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 17 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 18 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 19 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 20 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 21 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 22 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
Link 23 :	        GBT	        GBT	    TTC:CTP	       packet	            Enabled
------------------------------
24 link(s) found in total
------------------------------
globalgen: | ttc240freq 240.47 MHz | glb240freq 240.47 MHz | ref240freq 240.47 MHz | clk not ok cnt     0 | 
Wrapper 0: | ref freq0 240.47 MHz  | ref freq1 0.00 MHz  | ref freq2 0.00 MHz  | ref freq3 0.00 MHz  | 
```


### reset-clock-tree.py

First resets the ONU logic (can only be reset manually), then toggles a system level reset signal

Example:
```
./reset-clock-tree.py -i#0
```


### reg-dump.py

Dumps configuration register values.

Example:
```
./reg-dump.py -i#0
```



### roc-list-card.py

Prints information about the cards in the system. To get information about all cards in the server use

```bash
./reset-clock-tree.py
```

otherwise specify the PCIe ID, e.g.
```
./reset-clock-tree.py -i#0
```

```bash
=========================================================================================
PCIe ID 02:00.0
=========================================================================================
>>> Firmware short hash=0x946d668a
>>> Firmware build date and time=20181015  153050
>>> Altera chip ID=0x00540186-0x2855060b
=========================================================================================
```

### rsu.py

Triggers firmware reloading from serial flash.

```bash
./rsu.py -i#0 --reload
```

For reading from/writing to the registers of the IP see
```bash
./rsu.py --help
```



## test-dwrapper.py


## temperature.py
Prints temperature values reported by the temperature sensors available on the board.

Example:
```
./temperature.py -i#0 
```
