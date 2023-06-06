for i in 0x00030000 0x00030200 0x00030300 0x00030400 0x00030500 0x00030600 0x00030800 
do
    python i2c_scan.py --id $1 --base-address $i
done
