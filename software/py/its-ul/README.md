# ITS-UL Tools

SW tools for ITS User Logic FW.


## convert_hex_data_from_sim

This script is used to convert a text file with lines of hex data to binary format. The input is generally originating from FW simulation.

```
usage: convert_hex_data_from_sim.py [-h] [-i INPUTFILE] [-o OUTPUTFILE]
```

## data_packer

Used to pack and unpack ITS data from 80-bit to 128-bit and vice versa according to the ITS-UL dataformat specification.

```
usage: data_packer.py [-h] [-i INPUTFILE] [-o OUTPUTFILE] [-u]
```