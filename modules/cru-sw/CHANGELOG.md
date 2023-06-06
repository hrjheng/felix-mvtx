# Change log

## Numbering rule

Numbering is performed this way : **major.minor.fix**. The numbering logic is mostly driven by the firmware, that is true for the pcore and the cru-test repositories.
The tag number is changed only when something is dropped in the master branch, i.e. all git hash will not be tagged!


* Major number changes for any firmware architectural modification at the core level
* Minor number changes for bug fixes and/or feature modifications at component level (local address table, slaves, FSM, memory, ...). It requires the modification of the cru-test scripts
* Fix number changes for small fixes still staying compatible with the cru-test repo (timing fixes, code rewrite with no functionnality change, documentation, ...).


In practice for the users the cru-test and pcoresng with same **major.minor** must be compatible.


## Current version (not tagged yet)


## 3.5.0 - 2019-11-14

* Add current monitor  script

## 3.4.0 - 2019-10-14

* Add scripts to program serial flash
* Add Remote System Upgrade ip
* Add SFP monitoring script
* Add fw-hw compatibility check to startup

## 3.3.0 - 2019-09-12

* Update freq counter registers
* Updated SC library and added 2 new scripts
* add support for trigger mode configuration in DWRAPPER
* Use automatic phase scan by default

## 3.2.0 - 2019-07-18

* Add script to read EEPROM content
* Add script for pci reenumeration
* Add ctpemulator script (removed multiple scripts to handle ctpemulator)
* Update ddg to follow fw changes (new GBT data structure)
* Merge linkstat scripts
* Fixed SWT lib wrong addresses
* Updated DOC
* Update scripts for ONU upgrade to v1.0.1
* Make configTTC() clocking scheme dependent
* Use of OrderedDict to keep VHDL address table order
* CUTBYID always on for raw recording detectors

## 3.1.0 - 2019-06-03

* Added HC and CAL trigger generation in init.py
* Add allow rejection option in startup script
* Add option for userlogic configuration in startup script 
* Add script for core-ul
* Script made executable, autosetting when executing scripts

## 3.0.0 - 2019-03-25

* Address table update
* Health function removal in GBT.py
* Addition of sticky bit management for linkstat
* Add register dump script
* Update DDG scripts after HBF packet changes
* Update of scripts to reflect changes in DWRAPPER address map and insertion of RO\_protocol
* Added link remaping function to match the crossing to external clocking scheme
* Fix PON configuration
* Use consistent script names
* Add loopback report to linkstat
* Add ddg payload size option
* Add ddg random range option
* Add dwrapper packet statistics monitoring
* Change the gbtmux control related function to match firmware
* TTC: Added prescaler control and local flow control modes

## 2.7.1 - 2019-01-06

* Make GBT loopback configuration global
* Add the LED blinking functions
* Add checker script for GBTx

## 2.7.0 - 2018-12-11

* Added option to FORCE the start of run
* Fix in the script to manage the FBCT
* Add reset to loopback script
* Add missing dirty status report
* Add FIXED BC trigger in init.py
* Add trigger counter script
* Add temperature readout script
* Add GBT mode option to loopback script
* Add global clock selection report
* Add EP and PACKET COUNTER information in eventDump
* Add a software tool to check the data in readout
* Address table update and remove DWRAPPER HBID mingling function

## 2.6.0 - 2018-11-09

* Updated instructions
* Don't lock recovered PON clock to ref clock when using the local clock
* Change default trigger bits in patplayer, disable runenable trigger by default
* Added the possibility to set the CRUid
* Added support for LTU trig monitor function and start/stop override

## 2.5.1 - 2018-10-26

* Add instructions for data taking


## 2.5.0 - 2018-10-26

* Add trigger re-routing as downstream data option
* Add configuration report script
* Add FBCT control option
* Add core reset function
* Add single startup script
* Fixed index
* Checker for clk240 MHz clock
* Add control for sync pattern at runenable
* Add trigger select for DDg packets
* Script fix to be compatible with python3
* Modified SWT to use add name and not values
* Add the DDG shortcut control
* Move main modules to LIB
* Collect PLL register maps in one folder
* Add control for IDLEs between DDG packets, add DDG README
* Add shortcut to gbt-mux, devkit to standalone, minor changes
* Fix dwrapper enable bug (always specify wrapper)

## 2.4.0 - 2018-09-25

* Add option for ONU upstream calibration, add documentation
* Merge loopback scripts
* Add function for ddg reset
* Enable ZDB in external PLL
* Added a few options in the init of CTP
* Add some GBT and TTC methods, and update of linkstat.py
* Address table update related to TTC simplification
* Removed LEGACY\_DOCS
* Added detection of GTB/TRD wrapper type

## 2.3.0 - 2018-09-13

* Length mingling and padding length parameter removed
* Fix devkit PLL script, update I2C addresses
* Add phase scan to startup script

## 2.2.0 - 2018-08-30

* Fixed counter type setting function for GBT
* Fix SCA hardcoded address
* Fixed error in txcounter for MID
* Fixed scripts for ITS
* Add documentation and fix to patplayer
* Add pattern player methods to common TTC methods
* Corrected CTPemulator mode selection
* Added TOF script for DATAPATHWRAPPER
* Add general error counter read method to GBT.py
* Updated daq\_start.sh
* Make standalone startup globally executable
* Removed unused script
* Control clock disable in PLL (always enabled by default)
* Added functions to set CAL and HC period in CTP emulator
* Modified python prints for python2/3 compatibility


## 2.1.0 - 2018-08-27

* Remove unused flowstat register
* Change I2C slave addresses, add phase shift registers
* Matching GBT, TTC, BSP address footprint reduction
* Fixed TTC.py script for CTP emulator


## 2.0.0 - 2018-08-22

* Updated SCA to the new firmware
* Added SWT software
* Add select option for TTC downstream data
* Add CTP script
* Add mux link assignment
* Fixed a bug in SCA and updated option in sca prg
* fix bug in patternplayer script
* fix bug in cru-readout.py
* Change script options --id to follow the roc-* utilities style
* cleaned TPC script


## 1.5.0 - 2018-08-03

* Cleaned clock tree (now select in external PLL)
* Allow CTPemulator control


## 1.4.0 - 2018-08-02

* Fixed a bug in eventDump to retrieve the proper Link ID from the data
* Updated instruction to execute GBTSCA python program
* Added MFT folder
* Updated patplayer addresses
* Fixed a bug in patplayer script that ignored int(0) parameters
* Add DDG class to COMMON
* New organization of firmware version info

## 1.3.0 - 2018-07-18

* Updated ITS readout script
* Added README for eventDump and memDump software
* Updated SCA addresses with names
* Added fifo.py script to debug the data stream
* Addition of FEC monitoring
* GBT pattern generator taken out of links, GBT avalon slave update

## 1.2.0 - 2018-07-12

* Update address table for modified onu addresses



## 1.1.1 - 2018-07-11

* Addition of a new BSP.py
* Addition of ctpemu functions in TTC.py
* Support of updated firmware (Run enable control via BSP)
* Suppression of unused files


## 1.1.0 - 2018-07-11

* Support of updated firmware (BSP and TTC changes).


## 1.0.2 - 2018-07-06

* Added scripts for ddg and patternplayer modules



## 1.0.1 - 2018-07-05

* Addition of a change log
* Added scripts to init CRU for TPC and MID
* Added common scripts to check the readout data (eventDump and memDump)


## 1.0.0 - 2018-07-03

* Reorganisation of the repository
* Addition of an explicit address table (extracted from pack\_cru\_core.vhd)
* Usage of python scripts everywhere possible and removal of shell scripts
