# CANbus DCS interface

This module includes the DCS High Level Protocol (HLP), which is a master on the wishbone bus in the UltraScale FPGA design. In addition to the master interface, it also has a WB slave interface with a few status/count registers available.

It uses the [Canola CAN controller](https://github.com/svnesbo/canola) for the CANbus interface.

The github repository for the CAN controller includes extensive testbenches for the controller. Those testbenches are not included in this module.

More details and figures are included in doc/can_hlp.pdf.

## CANbus DCS HLP simulation

The standalone testbench for CAN HLP is based on the [Bitvis UVVM utility library](https://github.com/UVVM/UVVM_All), and has a Bus Functional Model (BFM) for CAN HLP which builds on a UVVM BFM for CAN bus. The testbench tests basic functionality of the HLP protocol.

### Running the simulation

Change directory to the top level repo directory (ie. RU\_mainFPGA/), and run:

```bash
make environment
cd modules/dcs_canbus/sim/can/scripts
make
```

Note: The simulation test bench is also ran as part of the continuous integration tests.


## CANbus Regression on RU_mainFPGA

In order to instantiate the vcan0 interface run the following script (centos7) from the repo root folder:

``` shell
sudo ./modules/dcs_canbus/software/can_hlp/SocketCANGateway/setup_can_centos7.sh
```

For SCL6/centos6 installations run instead:

``` shell
sudo ./modules/dcs_canbus/software/can_hlp/SocketCANGateway/setup_can_centos6.sh
```

## Using the DCS CAN HLP module in RU hardware

### RU hardware setup

#### CAN-bus termination

The CAN-bus lines requires 120 ohm termination at each end of the line. The CAN adapter needs to have internal termination enabled, or in the case of the PEAK CAN to USB adapter there are some solder links to enable termination (refer to the manual).

#### CAN HLP Device ID

The device ID for the CAN HLP module is set by DIPSWITCH(9:2) in the FPGA design.


### CAN Timing in UltraScale FPGA design

By default the CAN controller is configured for 250 kbit with 16 time quantas per bit:

- Sync segment: 1 time quanta (fixed, can not be changed)
- Propagation segment: 6 time quantas
- Phase segment 1: 5 time quantas
- Phase segment 2: 4 time quantas

The clock scale register is by default 39, i.e. the clock scale is 39 + 1 = 40, and the time quanta clock is 160 MHz / 40 = 4 Mhz. The baud rate is then 4 MHz / 16 quantas = 250 kbit.

These settings are configured with the CAN_PROP_SEG, CAN_PHASE_SEG1, CAN_PHASE_SEG2, and CAN_CLK_SCALE registers. They all affect the baud rate of the controller.

In addition the CAN_SJW registers configures the maximum number of time quantas the controller is allowed to jump while synchronizing to falling edges while receiving a frame.

#### Note about the segment registers

These number of quantas for a segment is not written as numerical value to these registers. The value from these registers are right shifted until the first zero is encountered, at which point the segment ends.

Examples:

- CAN_PHASE_SEG1 = 0b000001 --> Phase segment 1 is one time quanta long
- CAN_PHASE_SEG1 = 0b000011 --> Phase segment 1 is two time quantas long
- CAN_PHASE_SEG1 = 0b001111 --> Phase segment 1 is four time quantas long
- CAN_PHASE_SEG1 = 0b101111 --> Phase segment 1 is four time quantas long (ends at first zero)


### PA3 CAN passthrough

It's important to note that the PA3 also needs to be programmed with version v0207 or later. The signals to/from the CAN transceiver connect to the PA3 (because of limited number of 3.3V IOs on the UltraScale), and are connected to IOs that go to the UltraScale in the FPGA design for the PA3. The PA3 is essentially used as a level-shifter.


### Communicating with CAN HLP

Scripts are provided in the modules/dcs\_canbus/software/can\_hlp/ directory for communicating with the CAN\_HLP module via CAN-bus using a SocketCAN interface, and should work with the PEAK CAN to USB adapter on linux, which supports SocketCAN natively (some python packages may be necesary).
The AnaGate CAN controller does not support SocketCAN natively, but AnaGate provides a little program that acts as a bridge between the controller's TCP/IP interface and a virtual SocketCAN interface.


#### PEAK CAN to USB

To set up a can0 network interface at 1Mbps for the CAN adapter, run:

```bash
modules/dcs_canbus/software/can_hlp/setup_socketcan.sh
```

You only have to do this one time (but it will not persist after reboots).

To test communication, run this python script (you may have to edit the interface name to match your setup, ie. can0 or vcan0):

```bash
modules/dcs_canbus/software/can_hlp/can_hlp_test.py
```

This will read out the git hash, read out some counter registers in the CAN HLP WB slave, and test writing to a TEST register in the CAN HLP WB slave.

The CanHLP class provides readHLP() and writeHLP() functions that can be used to read/write to other registers.

#### AnaGate CAN controller

Connect the AnaGate controller and set up ethernet on the computer so that they are on the same network. The AnaGate controller is configured with the IP address 192.168.1.254 by default, so the following settings for ethernet can be used on the computer:

IP: 192.168.1.2
Mask: 255.255.255.0
Gateway: 0.0.0.0

Run the script to set up the virtual CAN bus interface:

```bash
modules/dcs_canbus/software/can_hlp/SocketCANGateway/InitVCAN.sh
```

Next run the bridge:

```bash
modules/dcs_canbus/software/can_hlp/SocketCANGateway/x86_64_Release/SocketCANGateway vcan0 --baudrate=250000 --termination=1 --highspeed=1 --canport=0
```

That will configure the AnaGate controller to use the vcan0 interface, run at 250kbit, use internal termination, highspeed CAN, and use the first CAN port on the AnaGate (CAN A port on AnaGate Quattro).

Now the test script can be run (edit vcan0/can0 in the script to reflect the SocketCAN interface you are using).

```bash
modules/dcs_canbus/software/can_hlp/can_hlp_test.py
```

#### Test loop script

The script can\_hlp\_test\_loop.py continuously reads and verifies the git hash value over CAN, writes a random number to a test register over CAN, and reads it back and verifies the value. The script can be stopped by pressing CTRL+C, then it will print the number of attempted and successful CAN transactions.

The CAN interface must be edited in this script to match your setup, and the githash must also be edited to match the githash of the FPGA design that is running on the RU board (it does not retrieve it automatically with git).
