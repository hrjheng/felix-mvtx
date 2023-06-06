# Programming the serial flash
 1. Set the MSEL pin to 0-1-0 [ON-OFF-ON] before writing the image into the serial flash.
    The MSEL pins are switch 6,7,8 on the dipswitch between the SMA connectors on the top side of the CRU

 2. Make sure you use Python 3

 3. Load the generated .rpd file (Raw Programming Data file) into the serial flash
    * `--rpd-file PATH/TO/RPDFILE` is the path to the .rpd file generated from the .sof file
    * `--show-progress` will display a progress bar (loading time is ~15 minutes) 
    * `--quiet` will surpress all output
    ```
    $ ./program-serial-flash.py -i#0 --rpd-file PATH/TO/RPDFILE [--show-progress] [--quiet] 
    ```
