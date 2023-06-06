# Anagate - SocketCANGateway - HowTo

## Software Source
Software downloaded from http://www.anagate.de/download/API/SocketCANGateway.tar.bz2

## Usage

Command: `./SocketCANGateway -i <anagate interface IP> -b <bitrate> -p <connector> <socket can adapter>`

Example lab1: `./SocketCANGateway -i 192.168.2.3 -b 250000 -p 1 vcan0`


| Parameter | Values |
| ------    | ------ |
| Bitrate   | 250000 (default)   |
| Connector | 0=A, 1=B, 2=C, 3=D |
| Socket    | vcan0 (fixed in CRU_ITS) |

## Anagate ip/hostnames
### Lab 1:
 - 192.168.2.3
   + B/1: IBS, MLS and OLS

### P2:
 - ALITSANA001 / 128.141.199.25:
   + A/0: L3_06 - L3_11 / PP1-O-2(5)
   + B/1: L4_08 - L4_14 / PP1-O-2
   + C/2: L3_00 - L3_05 / PP1-O-(2)5
   + D/3: L4_00 - L4_07 / PP1-O-5
 - ALITSANA003 / 128.141.199.252:
   + A/0: L6_36 - L6_47 / PP1-O-0
   + B/1: L6_24 - L6_35 / PP1-I-7
   + C/2: L5_32 - L5_41 / PP1-O-6
   + D/3:
 - ALITSANA004 / 128.141.199.251:
   + A/0: L3_12 - L3_17 / PP1-I-2(5)
   + B/1: L4_15 - L4_22 / PP1-I-2
   + C/2: L3_18 - L3_23 / PP1-I-5
   + D/3: L4_23 - L4_29 / PP1-I-(2)5
 - ALITSANA005 / 128.141.199.238:
   + A/0: L5_21 - L5_31 / PP1-I-6
   + B/1: L0_06 - L0_11 / PP1-O-4
   + C/2:
   + D/3: L1_08 - L1_15 / PP1-O-4
 - ALITSANA4X001 / 128.141.199.13:
   + A/0: L6_12 - L6_23 / PP1-O-7
   + B/1: L6_00 - L6_11 / PP1-I-0
   + C/2: L5_10 - L5_20 / PP1-O-1
   + D/3: L5_00 - L5_09 / PP1-I-1
 - ALITSANA007 / 172.26.77.239:
   + A/0: L0_00 - L0_05 / PP1-I-3
   + B/1: L1_00 - L1_07 / PP1-I-3
   + C/2: L2_00 - L2_09 / PP1-I-4
   + D/3: L2_10 - L2_19 / PP1-O-3
