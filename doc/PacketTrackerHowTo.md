# Running the Packet Tracker script

NOTE: The packet tracker script will only search through the rdh of each packet to look for packet number jumps, do not use it as a real test for data integrity. 

Enter the software directory (from root of CRU_ITS):

``` shell
cd software/py/
```

and call the script "packet_wrapper.py" with the following arguments:

``` shell
python packet_wrapper.py -t [ScanType (e.g. Threshold or FakeHitRate)] -r [RunLocation (absolute path to run directory without '/' at the end)] -l [Links (separated by spaces) ]
```

For example, the following would check for packet jumps on run 001340 (FakeHitRate), links 2 and 5:

``` shell
python packet_wrapper.py -t FakeHitRate -r /data/L0_shifts/run001340 -l 2 5 
```

If you forget/don't want to pull this up everytime, just run:

``` shell
python packet_wrapper.py --help
```

The logs will be stored under packet_logs/[Threshold or FakeHitRate]/runN_linkM.log
If there were no errors, a log file will not be generated!