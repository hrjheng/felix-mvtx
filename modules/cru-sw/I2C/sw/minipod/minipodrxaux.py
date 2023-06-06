#!/usr/bin/env python

import setThisPath

"""
Constants and logfile strings for MinipodRx class.

"""

import I2C
from I2C import *

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


powerclass = ["<1.5W","<2.0W","<2.5W","<3.5W"]
oklatched = ["OK","LATCHED"]
withinlimitsraised = ["WITHIN LIMIT","RAISED"]
enadbl = ["ENA","DBL"]
dblena = ["DBL", "ENA"]
noyes = ["NO ", "YES"]
maxbw = ["MAX-BW-QDR-10Gbps", "MAX-BW-DDR/SDR-5/2.5Gbps", "RESERVED                ", "RESERVED                "]
control = ["NOT PROVIDED     ", "GLOBAL CONTROL   ", "SELECTIVE CONTROL", "RESERVED         "]
groupsingle = ["GROUP", "SINGLE"]
omapave = ["OMA", "PAVE"]


# Register specific dictionary value is a 
# list of tuples.
#
# Tuple #0 : Header
#
# for X > 0:
# Tuple #X: (register bit index, info, flags set by the bit(s) [, optional channel number])

reg_values_page0 = {

# LOS Latched RX Channel 11--8: Coded 1 when asserted, Latched, Clears on Read.
9 : [('LOS ALARM\tLPG\t','\t[',']\tLATCHED STATUS OF LOS FOR ALL CHS, 1 => LATCHED\n'),
     (3, "LATCHED LOS",oklatched, 11),            
     (2, "LATCHED LOS",oklatched, 10),  
     (1, "LATCHED LOS",oklatched, 9),  
     (0, "LATCHED LOS",oklatched, 8)],

# LOS Latched RX Channel 7--0: Coded 1 when asserted, Latched, Clears on Read.
10 : [('\t\t\t','\t[',']' ),
      (7,"LATCHED LOS",oklatched, 7),            
      (6,"LATCHED LOS",oklatched, 6),  
      (5,"LATCHED LOS",oklatched, 5),  
      (4,"LATCHED LOS",oklatched, 4),
      (3,"LATCHED LOS",oklatched, 3),            
      (2,"LATCHED LOS",oklatched, 2),  
      (1,"LATCHED LOS",oklatched, 1),  
      (0,"LATCHED LOS",oklatched, 0)],

# High/Low Internal Temperature Alarm Latched: Coded 1 when asserted, Latched, Clears on Read.
13 : [('TEMP ALARM\tLPG\t','\t[',']\tALARM STATUS OF TEMP, 1 => CROSSED LIMIT\n'),
      (7,"HIGH TEMP ALARM", withinlimitsraised, None),            
      (6,"LOW  TEMP ALARM", withinlimitsraised, None) ],


# High/Low Internal 3.3 Vcc/2.5 Vcc Alarm Latched: Coded 1 when asserted, Latched, Clears on Read.
14 : [('VOL ALARM\tLPG\t','\t[',']\t\tALARM STATUS OF VOLTGAE(3.3V & 2.5V), 1 => CROSSED LIMIT\n'),
      (7,"HIGH 3.3V ALARM", withinlimitsraised, None),            
      (6,"LOW  3.3V ALARM", withinlimitsraised, None),
      (3,"HIGH 2.5V ALARM", withinlimitsraised, None),            
      (2,"LOW  2.5V ALARM", withinlimitsraised, None)],


# Registers 22--27:
# High/Low RX Power Alarm Latched Channel 11--0: Coded 1 when asserted, Latched, Clears on Read.
22 : [('PWR ALARM\tLPG\t','\t[',']\t\tALARM STATUS OF PWRo FOR ALL CH,1 => CROSSED LIMIT\n'),
      (7,"HIGH PWRo ALARM", withinlimitsraised, 11),            
      (6,"LOW  PWRo ALARM", withinlimitsraised, 11),
      (3,"HIGH PWRo ALARM", withinlimitsraised, 10),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 10)],

23 : [(  '\t\t\t','\t[',']'),  
      (7,"HIGH PWRo ALARM", withinlimitsraised, 9),            
      (6,"LOW  PWRo ALARM", withinlimitsraised, 9),
      (3,"HIGH PWRo ALARM", withinlimitsraised, 8),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 8)],

24 : [('\t\t\t','\t[',']' ), 
      (7,"HIGH PWRo ALARM", withinlimitsraised, 7),            
      (6,"LOW  PWRo ALARM", withinlimitsraised, 7),
      (3,"HIGH PWRo ALARM", withinlimitsraised, 6),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 6) ],

25 : [('\t\t\t','\t[',']'),
      (7,"HIGH PWRo ALARM", withinlimitsraised, 5),        
      (6,"LOW  PWRo ALARM", withinlimitsraised, 5),
      (3,"HIGH PWRo ALARM", withinlimitsraised, 4),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 4)],

26 : [('\t\t\t','\t[',']'), 
      (7,"HIGH PWRo ALARM", withinlimitsraised, 3),            
      (6,"LOW  PWRo ALARM", withinlimitsraised, 3),
      (3,"HIGH PWRo ALARM", withinlimitsraised,2),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 2)],

27 : [('\t\t\t','\t[',']'),
      (7,"HIGH PWRo ALARM", withinlimitsraised, 1),            
      (6,"LOW  PWRo ALARM", withinlimitsraised, 1),
      (3,"HIGH PWRo ALARM", withinlimitsraised, 0),            
      (2,"LOW  PWRo ALARM", withinlimitsraised, 0)],


# Internal Temperature Monitor MSB: Integer part coded in signed 2s complement.
28 : [('INTRNL 3.3V\tLPG\t','\t[',']\tR[32:33]:MINIPOD INTERNAL 3.3V')],


# Internal Temperature Monitor LSB: Fractional part in units of 1deg/256 coded in binary.
29 : [('\t\t\t','\t[', '] \tINTERNAL TEMPERATURE = ')],


# Registers 32--33 
# Internal 3.3 Vcc Monitor: Voltage in 100 mV units coded as 16 bit unsigned integer, Byte 32 is MSB.
32 : [('INTRNL 3.3V\tLPG\t','\t[',  '] \tR[32:33]:MINIPOD INTERNAL 3.3V')],

33 : [('\t\t\t','\t[',  '] \tINTERNAL 3.3V = ')],


# Internal 2.5 Vcc Monitor: Voltage in 100 mV units coded as 16 bit unsigned integer, Byte 34 is MSB.
34 : [('INTRNL 2.5V \tLPG \t','\t[',  ']','\tR[34:35]:MINIPOD INTERNAL 2.5V')],

35 : [('\t\t\t','\t[',  '] \tINTERNAL 2.5V = ')],


# Registers from 64--65 to  86--87
# RX Optical Input, PAVE, Monitor Channel 11: Optical power in 0.1 mW units coded as 16 bit unsigned integer, even # bytes are MSBs.
64 : [('TXOUT PWR \tLPG \t','\t[',  ']','\tR[64:87]:MINIPOD RX OPTICAL INPUT POWER FOR ALL CHS\n')],
65 : [('\t\t\t','\t[',  '] \tCH11 = ')],

66 : [('\t\t\t','\t[',  ']')],
67 : [('\t\t\t','\t[',  '] \tCH10 = ')],

68 : [('\t\t\t','\t[',  ']')],
69 : [('\t\t\t','\t[',  '] \tCH9 = ')],

70 : [('\t\t\t','\t[',  ']')],
71 : [('\t\t\t','\t[',  '] \tCH8 = ')],

72 : [('\t\t\t','\t[',  ']')],
73 : [('\t\t\t','\t[',  '] \tCH7 = ')],

    74 : [('\t\t\t','\t[',  ']')],
75 : [('\t\t\t','\t[',  '] \tCH6 = ')],

76 : [('\t\t\t','\t[',  ']')],
77 : [('\t\t\t','\t[',  '] \tCH5 = ')],

78 : [('\t\t\t','\t[',  ']')],
79 : [('\t\t\t','\t[',  '] \tCH4 = ')],

80 : [('\t\t\t','\t[',  ']')],
81 : [('\t\t\t','\t[',  '] \tCH3 = ')],

82 : [('\t\t\t','\t[',  ']')], 
83 : [('\t\t\t','\t[',  '] \tCH2 = ')],

84 : [('\t\t\t','\t[',  ']')],
85 : [('\t\t\t','\t[',  '] \tCH1 = ')],

86 : [('\t\t\t','\t[',  ']')],
87 : [('\t\t\t','\t[',  '] \tCH0 = ')],

88 : [('ELASPED TIME \tLPG \t','\t[',  '] \tR[88:89]:ELASPED/POWER ON TIME')],
89 : [( '\t\t\t','\t[',  '] \tELASPED TIME = ')],


# RX Channel 11--8 Disable: Writing 1 deactivates the electrical output, Default is 0.
92 : [('CHNL STS','\tLPG','\t', '\t[', ']','\tSTATUS OF ALL CHS,1 => DISABLE'),
      (3,"OPT.OUT", enadbl,  11),            
      (2,"OPT.OUT", enadbl,  10),  
      (1,"OPT.OUT", enadbl,  9),  
      (0,"OPT.OUT", enadbl,  8)],


# RX Channel 7--0 Disable: Writing 1 deactivates the electrical output, Default is 0.
93 : [('\t\t\t', '\t[', ']'),  
      (7,"OPT. OUT", enadbl, 7), 
      (6,"OPT. OUT", enadbl, 6), 
      (5,"OPT. OUT", enadbl, 5), 
      (4,"OPT. OUT", enadbl, 4), 
      (3,"OPT. OUT", enadbl, 3), 
      (2,"OPT. OUT", enadbl, 2), 
      (1,"OPT. OUT", enadbl, 1), 
      (0,"OPT. OUT", enadbl, 0)],

# Squelch Disable Channel 11--8: Writing 1 inhibits squelch for the channel, Default is 0.
94 : [('SQULCH STS \tLPG \t', '\t[', '] \tSQULCH STATUS OF ALL CHS,1 => INHIBITS SQUELCH'),
      (3,"SQUELCH", enadbl, 11),            
      (2,"SQUELCH", enadbl, 10),  
      (1,"SQUELCH", enadbl, 9),  
      (0,"SQUELCH", enadbl, 8)],

# Squelch Disable Channel 7--0: Writing 1 inhibits squelch for the channel, Default is 0.
95 : [('\t\t\t', '\t[', ']'),  
      (7,"SQUELCH", enadbl, 7), 
      (6,"SQUELCH", enadbl, 6), 
      (5,"SQUELCH", enadbl, 5), 
      (4,"SQUELCH", enadbl, 4), 
      (3,"SQUELCH", enadbl, 3), 
      (2,"SQUELCH", enadbl, 2), 
      (1,"SQUELCH", enadbl, 1), 
      (0,"SQUELCH", enadbl, 0)],
    
# Rate Select Channel 11--8: Write 00 for max. BW (QDR 10 Gbps application), 01 for DDR and SDR BW 
# (5 and 2.5 Gbps applications), rest reserved. Default is 00
96 : [('RATE SELECT \tLPG \t', '\t[', '] \tRATE SELECT OF ALL CHS,00 => MAX. BW'),
      (7,"RATE SELECT",maxbw, 11), 
      (5,"RATE SELECT",maxbw, 10), 
      (3,"RATE SELECT",maxbw, 9), 
      (1,"RATE SELECT",maxbw, 8)],
    
# Rate Select Channel 7--4: Write 00 for max. BW (QDR 10 Gbps application), 01 for DDR and SDR BW 
# (5 and 2.5 Gbps applications), rest reserved. Default is 00
97 : [('\t\t\t', '\t[', ']' ),
      (7,"RATE SELECT",maxbw, 7), 
      (5,"RATE SELECT",maxbw, 6), 
      (3,"RATE SELECT",maxbw, 5), 
      (1,"RATE SELECT",maxbw, 4)],
  
# Rate Select Channel 3--0: Write 00 for max. BW (QDR 10 Gbps application), 01 for DDR and SDR BW 
# (5 and 2.5 Gbps applications), rest reserved. Default is 00
98 : [('\t\t\t', '\t[', ']' ),
      (7,"RATE SELECT",maxbw, 3), 
      (5,"RATE SELECT",maxbw, 2), 
      (3,"RATE SELECT",maxbw, 1), 
      (1,"RATE SELECT",maxbw, 0)],
  
# Mask LOS RX Channel 11--8: Writing 1 Prevents IntL generation, Default = 0
112 : [('LOS MASK \tLPG \t', '\t[', '] \tLOS MASK BIT FOR ALL CHS,1 => NO IntL GEN'),
       (3,"LOS MASK BIT", enadbl, 11),            
       (2,"LOS MASK BIT", enadbl, 10),  
       (1,"LOS MASK BIT", enadbl, 9),  
       (0,"LOS MASK BIT", enadbl, 8)],
  
# Mask LOS RX Channel 7--0: Writing 1 Prevents IntL generation, Default = 0
113 : [('\t\t\t', '\t[', ']'),  
       (7,"LOS MASK BIT", enadbl, 7), 
       (6,"LOS MASK BIT", enadbl, 6), 
       (5,"LOS MASK BIT", enadbl, 5), 
       (4,"LOS MASK BIT", enadbl, 4), 
       (3,"LOS MASK BIT", enadbl, 3), 
       (2,"LOS MASK BIT", enadbl, 2), 
       (1,"LOS MASK BIT", enadbl, 1), 
       (0,"LOS MASK BIT", enadbl, 0)],
  

# Mask Internal High/Low Temperature Alarm: Writing 1 Prevents IntL generation, Default = 0
116 : [('TEMP MASK \tLPG \t', '\t[', '] \tTEMP MASK BIT,1 => NO IntL GEN'),
       (7,"HIGH TEMP MASK BIT", enadbl, None),            
       (6,"LOW  TEMP MASK BIT", enadbl, None)],
  

# Mask Internal High/Low 3.3 Vcc/2.5 Vcc Alarm: Writing 1 Prevents IntL generation, Default = 0
117 : [('VOL MASK \tLPG \t', '\t[', '] \tVOL MASK BIT,1 => NO IntL GEN'),
       (7,"HIGH 3.3V MASK BIT", enadbl, 11),            
       (6,"LOW  3.3V MASK BIT", enadbl, 10),  
       (7,"HIGH 2.5V MASK BIT", enadbl, 11),            
       (6,"LOW  2.5V MASK BIT", enadbl, 10)],


# Type Identifier: Coded 00h for unspecified. See SFF-8472 for reference
128 : [('MP IDNTIFIER\tUPG0\t','\t[',']\t\tMINIPOD TYPE IDENTIFIER')],


# Module Description: Coded for < 1.5 W
129 : [('PWR CLASS\tUPG0\t','\t[',']\t\tMINIPOD POWER CLASS' ),
       (7,"POWER CLASS",powerclass, None),    
       (5, "TX CDR    ",noyes, None),  
       (4, "RX CDR    ",noyes, None),  
       (3, "RENone.CLK",noyes, None),
       (2, "PG2       ",noyes, None),            
       (1, "CLT       ",noyes, None)],
            

# Required Power Supplies: Coded for 3.3 V and 2.5 V supplies   
130 : [('PWR SUPPLY \tUPG0 \t','\t[','] \t\tMINIPOD POWER SUPPLY REQUIREMENT'),
       (7, "3.3V    ",noyes, None),  
       (6, "2.5V    ",noyes, None),  
       (5, "1.8V    ",noyes, None),
       (4, "VO      ",noyes, None),            
       (3, "VARIABLE",noyes, None)],  


# Max Short-Term Operating Case Temperature in degC: Coded for 85 degC
131 : [('CASE TEMP\tUPG0\t','\t[',']\t\tMINIPOD CASE TEMPERATURE RECOMENDED')],


#Min Bit Rate in 100 Mb/s units: Coded for 1250 Mb/s
132 : [('MIN SIG@ \tUPG0 \t','\t[','] \t\tMINIMUM SIGNAL RATE PER CHANNEL')],
 

# Max Bit Rate in 100 Mb/s units: Coded for 10312 Mb/s
133 : [('MAX SIG@ \tUPG0 \t','\t[','] \t\tMAXIMUM SIGNAL RATE PER CHANNEL')],


# Nominal Laser Wavelength (Wavelength in nm = value / 20): Coded 00h for RX
134 : [('WAVELENGTH \tUPG0 \t','\t[','] \t\tNOMINAL WAVELENGTH')],
135 : [('\t\t\t','\t[', ']\t\t')],


# Wavelength deviation from nominal (tolerance in nm = +/- value/200):
# Coded 00h for RX
136 : [('WAVELEN_TOL \tUPG0 \t','\t[','] \t\tWAVELENGTH TOLERANCE')],
137 : [('\t\t\t','\t[', ']\t\t')],


# Supported Flags/Actions: Coded for RX LOS, Output Squelch for LOS, Alarm Flags
138 : [('FEA_FLAG\tUPG0\t','\t[',']\t\tFLAG RELATED FEATURES, 0 => NOT SUPPORTED'),
       (7, "FAULT       ", noyes, None),
       (6, "TXLOS       ", noyes, None),
       (5, "RXLOS       ", noyes, None),
       (4, "CDRLOL      ", noyes, None),
       (3, "SQULCH LOS  ", noyes, None),
       (2, "WARNING FLAG", noyes, None)],


# Supported Monitors: Coded for RX Input, Pave, Internal Temp, Elapsed Time
139 : [('FEA_MON1\tUPG0\t','\t[',']\t\tMONITOR RELATED FEATURES, 0 => NOT SUPPORTED'),
       (7, "TXBIAS", noyes, None),
       (6, "TXLOP ", noyes, None),
       (5, "RXPWR ", groupsingle, None),
       (4, "RXPWR ", omapave, None),
       (3, "CTEMP ", noyes, None),
       (2, "ITEMP ", noyes, None),
       (1, "PTEMP ", noyes, None),
       (0, "ETIME ", noyes, None)],

# Supported Monitors: Coded for 3.3 V, 2.5 V
140 : [('FEA_MON2\tUPG0\t','\t[',']\t\tMONITOR RELATED FEATURES, 0 => NOT SUPPORTED'),
       (7, "BER   ", noyes, None),  
       (6, "3.3V  ", noyes, None),  
       (5, "2.5V  ", noyes, None), 
       (4, "1.8V  ", noyes, None),
       (3, "VO/VCC", noyes, None), 
       (2, "TECi  ", noyes, None)],
               
# Supported Controls: Coded for Ch Disable, Squelch Disable, Rate Select
141 : [('FEA_CON1\tUPG0\t','\t[',']\t\tCONTROL RELATED FEATURES SUPPORTED'),
       (7, "CH DISABLE    ", control, None) ,
       (5, "SQULCH DISABLE", control, None), 
       (3, "RATE SELECT   ", control, None), 
       (1, "TXEQU         ", control, None)],
               

# Supported Controls: Coded for RX Amplitude, RX De-emphasis, Ch Polarity Flip,
# Module Addressing
142 : [('FEA_CON2\tUPG0\t','\t[',']\t\tCONTROL RELATED FEATURES SUPPORTED'),
       (7, "RX AMP CONTROL        ", control, None),
       (5, "RX DE_EMPHASIS CONTROL", control, None), 
       (3, "MARGIN MODE      ", noyes, None),  
       (2, "CH RESET         ", noyes, None),  
       (1, "CH POLARITY      ", noyes, None),
       (0, "MODULE ADDRESSING", noyes, None)]          ,  
               
# Supported Functions
143 : [('FEA_CON3\tUPG0\t','\t[',']\t\tCONTROL RELATED FEATURES SUPPORTED'),
       (7, "FEC       ", noyes, None),  
       (6, "PEC       ", noyes, None),  
       (5, "JTAG      ", noyes, None),
       (4, "AC-JTAG   ", noyes, None),            
       (3, "BIST      ", noyes, None),  
       (2, "TEC-TEMP  ", noyes, None),  
       (1, "SLEEP     ", noyes, None),
       (0, "CDR BYPASS", noyes, None)],
}



reg_values_page1 = {
# Internal Temperature High Alarm Threshold MSB: Integer part coded in signed 2s complement
128 : [('TEMP LIMIT\tUPG1\t','\t[', ']\t\tR[28:29]: MINIPOD INTERNAL TEMPERATURE THRESHOLD')],

# Internal Temperature High Alarm Threshold LSB: Fractional part in units of 1deg/256 coded in binary.
129 : [('\t\t\t', '\t[', ']\t\tHIGH = ')],

# Internal Temperature Low Alarm Threshold MSB: Integer part coded in signed 2s complement
130 : [('\t\t\t', '\t[', ']')],

# Internal Temperature Low Alarm Threshold LSB: Fractional part in units of 1deg/256 coded in binary.
131 : [('\t\t\t', '\t[', ']\t\tLOW = ')],

# Registers 144--145
# Internal 3.3 Vcc High Alarm Threshold: Voltage in 100 mV units coded as 16 bit unsigned integer,
# low address is MSB.
144 : [('3.3V LIMIT\tUPG1\t', '\t[',  ']\t\tR[32:33]: MINIPOD INTERNAL 3.3V THRESHOLD')],
145 : [('\t\t\t', '\t[',  ']\t\tHIGH = ')],

# Registers 146--147
# Internal 3.3 Vcc Low Alarm Threshold: Voltage in 100 mV units coded as 16 bit unsigned integer,
# low address is MSB.
146 : [('\t\t\t', '\t[',  ']')],
147 : [('\t\t\t', '\t[',  ']\t\tLOW = ')],

# Registers 152--153
# Internal 2.5 Vcc High Alarm Threshold: Voltage in 100 mV units coded as 16 bit unsigned integer,
# low address is MSB.
152 : [('2.5V LIMIT\tUPG1\t', '\t[',  ']\t\tR[32:33]: MINIPOD INTERNAL 2.5V THRESHOLD')],
153 : [('\t\t\t', '\t[',  ']\t\tHIGH = ')],

# Registers 154--155
# Internal 2.5 Vcc Low Alarm Threshold: Voltage in 100 mV units coded as 16 bit unsigned integer,
# low address is MSB.
154 : [('\t\t\t', '\t[',  ']')],
155 : [('\t\t\t', '\t[',  ']\t\tLOW = ')],

# Registers 184--185
# RX Optical Power All Channels High Alarm Threshold: Optical power in 0.1 mW units coded as
# 16 bit unsigned integer, low address is MSB.
184 : [('PWR LIMIT\tUPG1\t', '\t[',  ']\t\tR[40:63]: MINIPOD OPTICAL POWER THRESHOLD')],
185 : [('\t\t\t', '\t[',  ']\t\tHIGH = ')],

# Registers 186--187
# RX Optical Power All Channels Low Alarm Threshold: Optical power in 0.1 mW units coded as
# 16 bit unsigned integer, low address is MSB.
186 : [('\t\t\t', '\t[',  ']')],
187 : [('\t\t\t', '\t[',  ']\t\tLOW = ')],


# IntL Pulse/Static Option: Writing 1 sets IntL to Static mode, Default is 1 for Static mode
225 : [('INTl MODE \tUPG1 \t', '\t[', '] \tINTL STTAUS, STATIC = 1, PULSE = 0'),
       (0,"INTL MODE",["STATIC","PULSE"],1,None)],


# Output Polarity Flip Channel 11--8: Writing 1 inverts truth of the differential output pair, Default is 0.
226 : [('OUT POLA','\tUPG1','\t', '\t[', ']','\tOUTPUT POLARITY FLIP OF ALL CHS, 1 => ENABLE FLIP MODE'),
       (3,"FLIP MODE", dblena, 11),            
       (2,"FLIP MODE", dblena, 10),  
       (1,"FLIP MODE", dblena, 9),  
       (0,"FLIP MODE", dblena, 8)],


# Output Polarity Flip Channel 7--0: Writing 1 inverts truth of the differential output pair, Default is 0.
227 : [('\t\t\t', '\t[', ']' ),
       (7,"FLIP MODE", dblena, 7), 
       (6,"FLIP MODE", dblena, 6), 
       (5,"FLIP MODE", dblena, 5), 
       (4,"FLIP MODE", dblena, 4), 
       (3,"FLIP MODE", dblena, 3), 
       (2,"FLIP MODE", dblena, 2), 
       (1,"FLIP MODE", dblena, 1), 
       (0,"FLIP MODE", dblena, 0)],

# Registers 228--233
# RX Output Amplitude Control: Channel 11--10. See Code Description on page 50. Default = 0100b
228 : [('OUT AMP \tUPG1 \t', '\t[', '] \tOUTPUT AMPLITUDE CONTROL CODE OF ALL CHS, DEFAULT => 4H')],

229 : [('\t\t\t', '\t[', ']' )],
230 : [('\t\t\t', '\t[', ']' )],
231 : [('\t\t\t', '\t[', ']' )],
232 : [('\t\t\t', '\t[', ']' )],
233 : [('\t\t\t', '\t[', ']' )],


# Registers 234--239
# RX Output De-emphasis Control: Channel 11--0. See Code Description on page 50. Default = 0011b
234 : [('DE-EMPHASIS  \tUPG1 \t', '\t[', '] \tOUTPUT DE-EMPHASIS CONTROL CODE OF ALL CHS, DEFAULT => 3H')],
235 : [('\t\t\t', '\t[', ']')],
236 : [('\t\t\t', '\t[', ']')],
237 : [('\t\t\t', '\t[', ']')],
238 : [('\t\t\t', '\t[', ']')],
239 : [('\t\t\t', '\t[', ']')],


# Registers 250--255
# Mask High/Low RX Power Alarm Channel 11--0: Writing 1 Prevents IntL generation, Default = 0
250 : [('OPTPWR MASK \tLPG \t', '\t[',  ']\tOPT POWER MASK BIT, 1 => NO IntL GEN'),
       (7,"HIGH POWER MASK BIT", enadbl, 11 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 11 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 10 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 10 )],
               
251 : [('\t\t\t', '\t[',  ']'),
       (7,"HIGH POWER MASK BIT", enadbl, 9 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 9 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 8 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 8 )],

252 : [('\t\t\t', '\t[',  ']'),
       (7,"HIGH POWER MASK BIT", enadbl, 7 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 7 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 6 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 6 )],

253 : [('\t\t\t', '\t[',  ']'),
       (7,"HIGH POWER MASK BIT", enadbl, 5 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 5 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 4 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 4 )],
               
254 : [('\t\t\t', '\t[',  ']'),
       (7,"HIGH POWER MASK BIT", enadbl, 3 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 3 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 2 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 2 )],

255 : [('\t\t\t', '\t[',  ']'),
       (7,"HIGH POWER MASK BIT", enadbl, 1 ),            
       (6,"LOW  POWER MASK BIT", enadbl, 1 ),  
       (3,"HIGH POWER MASK BIT", enadbl, 0 ),            
       (2,"LOW  POWER MASK BIT", enadbl, 0 )]
}











vppd =  [
    '| AMP CODE | MIN = 70mVppd  | NORMAL = 100mVppd | MAX = 130mVppd |',
    '| AMP CODE | MIN = 150mVppd | NORMAL = 200mVppd | MAX = 250mVppd |',
    '| AMP CODE | MIN = 240mVppd | NORMAL = 300mVppd | MAX = 360mVppd |',
    '| AMP CODE | MIN = 320mVppd | NORMAL = 400mVppd | MAX = 480mVppd |',
    '| AMP CODE | MIN = 400mVppd | NORMAL = 500mVppd | MAX = 600mVppd |',
    '| AMP CODE | MIN = 480mVppd | NORMAL = 600mVppd | MAX = 720mVppd |',
    '| AMP CODE | MIN = 560mVppd | NORMAL = 700mVppd | MAX = 840mVppd |',
    '| AMP CODE | MIN = 640mVppd | NORMAL = 800mVppd | MAX = 960mVppd |']

vendorDetailsHeader = '--------------------------------------------------------------------------------------------\n'+ \
                      'MINIPOD INFO/VENDOR SPCIFIC DETAILS IN ASCII\n'+\
                      '--------------------------------------------------------------------------------------------\n\n'+\
                      'REGISTER TYPE \t PAGE \t ADD \tASCII\t\tDETAILS\n\n'

vendorDetails = [
        ('\nVENDOR NAME  \t UPG0 \t\t\t\t REG 152-167:VENDOR NAME "AVAGO"',        [152, 168]),  # VENDOR NAME
        ('\nVENDOR ID    \t UPG0 \t\t\t\t VENDOR OUI/IEEE ID      "00H-17H-6AH"',  [168, 171]),  # VENDOR ID
        ('\nVENDOR PART  \t UPG0 \t\t\t\t VENDOR PART NUMBER      "AFBR-821FN3Z"', [171, 187]),  # VENDOR PART
        ('\nVENDOR RVN   \t UPG0 \t\t\t\t VENDOR REVISON NUMBER   "NULL"',         [187, 189]),  # VENDOR RVN
        ('\nVENDOR SN    \t UPG0 \t\t\t\t VENDOR SERIAL NUMBER    "A1632200J"',    [189, 205]),  # VENDOR SN
        ('\nVENDOR DATE  \t UPG0 \t\t\t\t VENDOR MFG DATE         "20160808"',     [205, 213]),  # VENDOR DATE
        ('\nUSER AREA    \t UPG0 \t\t\t\t CUSTOMER SPECIFIC AREA  "NULL"',         [213, 223]),  # USER AREA
        ('\nVENDOR AREA  \t UPG0 \t\t\t\t VENDOR SPECIFIC AREA    "NULL"',         [224, 254])]  # VENDOR AREA

featuresHeader = '--------------------------------------------------------------------------------------------\n'+\
                 'MINIPOD INFO/AVAILABLE FEATURES IN MINIPOD\n'+\
                 '--------------------------------------------------------------------------------------------\n\n'+\
                 'REGISTER TYPE\tPAGE\tADD \tVAL\t\tDETAILS\n'

basicsHeader = '--------------------------------------------------------------------------------------------\n'+\
               'MINIPOD INFO/BASIC DETAILS ABOUT MINIPOD\n'+\
               '--------------------------------------------------------------------------------------------\n\n'+\
               'REGISTER TYPE\tPAGE\tADD \tVAL\t\tDETAILS\n'
    
parametersHeader = '--------------------------------------------------------------------------------------------\n'+\
                   'MINIPOD STATUS/CURRENT VALUES OF DIFFERENT PARAMETERS\n'+\
                   '--------------------------------------------------------------------------------------------\n\n'+\
                   'REGISTER TYPE' +  '\tPAGE' +  '\tADD ' +  '\tVAL' + '\t\tDETAILS\n'

flagsHeader = '--------------------------------------------------------------------------------------------\n'+\
              'MINIPOD STATUS/CURRENT FLAGS OF DIFFERENT PARAMETERS\n'+\
              '--------------------------------------------------------------------------------------------\n\n'+\
              'REGISTER TYPE'+  '\tPAGE'+  '\tADD '+  '\tVAL' + '\t\tDETAILS\n'

flagAlarms = [bcolors.FAIL + " LOS STATUS:LATCHED:CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "TEMP CROSSED LIMIT:CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "VOLTAGES CROSSED LIMIT:CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "PWRo CROSSED LIMIT:CHECK LOG" + bcolors.ENDC ]

thresholdHeader = '--------------------------------------------------------------------------------------------\n'+\
                  'MINIPOD STATUS/THRESHOLD VALUES OF DIFFERENT PARAMETERS\n'+\
                  '--------------------------------------------------------------------------------------------\n\n'+\
                  'REGISTER TYPE'+  '\tPAGE'+  '\tADD '+  '\tVAL' + '\t\tDETAILS\n\n'
     
configHeader = '--------------------------------------------------------------------------------------------\n'+\
               'MINIPOD STATUS/CURRENT STATUS OF CONFIGURATION PARAMETERS\n'+\
               '--------------------------------------------------------------------------------------------\n\n'+\
               'REGISTER TYPE'+  '\tPAGE'+ '\tADD '+  '\tVAL' + '\t\tDETAILS\n\n'

configAlarms = [bcolors.FAIL + "OPTICAL CHANNEL:NOT IN DEFAULT SETTING:CHECK DETAILS" + bcolors.ENDC,
                bcolors.FAIL + "SQUELCH FEATURE:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC,
                bcolors.FAIL + "RATE SELECT:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC,
                bcolors.FAIL + "INTL MODE IS PULSE" + bcolors.ENDC,
                bcolors.FAIL + "FLIP MODE:NOT IN DEFAULT SETTING:CHECK LOG" + bcolors.ENDC,
                bcolors.FAIL + "AMP CODE:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC,
                bcolors.FAIL + "DE-EMPHASIS LVL:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC ]

maskHeader = '--------------------------------------------------------------------------------------------\n'+\
             'MINIPOD CONFIGURATION/CURRENT STATUS OF MASK CONFIGURED\n'+\
             '--------------------------------------------------------------------------------------------\n'+\
             'REGISTER TYPE'+  '\tPAGE'+  '\tADD '+  '\tVAL' + '\t\tANALYSIS\n\n'

maskAlarms = [bcolors.FAIL + "LOS MASK:NOT IN DEFAULT SETTING: CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "VOLTAGE:NOT IN DEAFULT SETTINGS :CHECK LOG" + bcolors.ENDC,
              bcolors.FAIL + "OPTPWR:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC]
