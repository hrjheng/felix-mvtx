# GBT EC - SCA configuration

## Execute sca\_prg.py

```bash
cd GBTSC/sw
./sca_prg.py -i PCIE_ID -l GBT_CH -b BOARD_NAME
```
Example G-RORC
```
./sca_prg.py -i#0 -l 0 -b G-RORC
```
Example CRU
```
./sca.py -i#0 -l 0 -b CRU
```
Output of the program
```
-------------------------------------------------------
SCA ADD:
BASE ADD = 0x4224000
-------------------------------------------------------
-------------------
1) INIT SCA
20) ENABLE GPIO
21) Push DATA to GPIO
22) GPIO INTENABLE
...
...
...
Else) QUIT
-------------------
Enter a choice :
```

# GBT SWT 

## Execute swt\_prg.py

```bash
cd GBTSC/sw
./swt_prg.py -i PCIE_ID -l GBT_CH -swt SWT_WORD -rd/-wr/-rs
```
RESET CORE
```
./swt_prg.py -i#0 -l 1 -swt 0x01000000 -rs
```

WRITE SWT
```
./swt_prg.py -i#0 -l 1 -swt 0x01000000 -wr
```

READ BACK
```
./swt_prg.py -i#0 -l 1 -swt 0x01000000 -rd

RD - DATA 0x3000ff0000ffff000000L
MON    0x101
```

### MON WORD FORMAT

| BIT   | FIELD |
|-------|-------|
| [7:0] | SWT WR OPERATION   |
| [15:8] | LINK ID  |
| [23:16] | NUMBER OF SWT WROD IN FIFO   |
