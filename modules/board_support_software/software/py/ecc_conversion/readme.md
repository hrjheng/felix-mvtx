The ECC conversion applies hamming codes to the 
xilinx bitfiles. How the ECC checking is implemented in the PA3 is documented in 
the auxFPGA manual

The script expects a bitfile, generated from Vivado.

The generateScrubbingFile.py scrip

******
how to run:

execute  
```
python ./ecc_conversion/make_all_ECC_files.py bitfile_name_githash.bit
```
the output will be   

* blindscrubbing file 
* parameter file
* ecc bitfile
* ecc blindscrubbing file
* ecc parameter file

in binary format ready for use.
