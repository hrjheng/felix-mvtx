#!/bin/bash
#
# ITS readout scrip for CRU FW v20171115
#



OUTPUT=${1:-/tmp/output.bin}
#SIZE=${2:-4096Mi}
SIZE=${2:-128Mi}
PCISLOT=${3:-81:00.0}





xlog(){
	grep -v "infoLoggerD not available, falling back to stdout logging"
}

xread(){
	o2-roc-reg-read 2>/dev/zero --id=${PCISLOT} --channel=2 --address=$1 | xlog
}

xwrite(){
	o2-roc-reg-write 2>/dev/zero --id=${PCISLOT} --channel=2 --address=$1 --value=$2 | xlog
}





# assert rx_set_locktoref in TTCPON, select recovered clock + CTP emulator
xwrite 0x02200020 1
xwrite 0x02400038 0x10
xwrite 0x02000038 0x03



# waveform player output mux: make sure that downstream GBT payload [79:76] is always 0: map there incoming trigger [47:44]
xwrite 0x0c4e0098 0x002d002c
xwrite 0x0c4e009c 0x002f002e



# enable loopback in the GBT block on GBT link #1 
xwrite 0x0424e038 0x00000010



# set up datapath
xwrite 0x06000020 0xffffffff # keep block in reset while reconfiguring

# link #0 -- GBT packet mode to receive data from ITS FE
#xwrite 0x06400024 0x01ea0010 # rawrec: limit packet size, don't cut at HB boundary
#xwrite 0x06400020 0x10001001 # select raw link recorder mode
xwrite 0x06400020 0x10001002 # select gbt packet mode,
#xwrite 0x06400020 0x10009002 # select gbt packet mode, look for SOP/EOP at other end of GBT DATA
#xwrite 0x06400020 0x10001007 # ch off

# link #1 -- monitor downstream trigger: enable raw link recorder (it's in looback, see above)
#xwrite 0x06410024 0x01ea0010 # rawrec: limit packet size, don't cut at HB boundary
#xwrite 0x06410020 0x10001001 # select raw link recorder mode
#xwrite 0x06410020 0x10001007 # ch off --  comment this out to debug downstream

xwrite 0x06000028 0x10200 # enable prio scheduler, pad short packets to the maximum packet size

xwrite 0x06800020 0x10 # always overwrite link id
#xwrite 0x06800024 0x11 # always overwrite pktlen
xwrite 0x06800028 0x01 # for rawrec overwrite hbid

xwrite 0x06c00020 0 # ignore heartbeat flow control messages (don't drop data on HB reject)

#for val in 0xffffffff 0xfffffff0 0xffffff00 0xfffff000 0xffff0000 0x0000; do xwrite 0x06000020 $val; done # release reset





# start DMA
rm -vf ${OUTPUT}
o2-roc-reg-write --id=${PCISLOT} --channel=0 --address=0x700 --value=0 # select real data instead of internal generator
#o2-roc-bench-dma --verbose   --id=${PCISLOT}   --buffer-size=128Mi --superpage-size=2Mi --links="0-31"  --no-errorche  --reset  --bytes=${SIZE}  --to-file-bin=${OUTPUT} &
o2-roc-bench-dma --verbose   --id=${PCISLOT}   --buffer-size=128Mi --superpage-size=2Mi --links="0-31"  --no-errorche  --bytes=${SIZE}  --to-file-bin=${OUTPUT} &

sleep 3 # wait for DMA to start up

for val in 0xffffffff 0xfffffff0 0xffffff00 0xfffff000 0xffff0000 0x0000; do xwrite 0x06000020 $val; done # release reset

sleep 1



xwrite 0x02880010 1    # enter triggered run mode (generate Start of Triggered)

#xwrite 0x02880014 0x08000000 # generate phys trigger @ 0.3 Hz, but immediately
xwrite 0x02880014 0x0800 # JS: Mazsi suggested using this to increase trigger rate
sleep 10
xwrite 0x02880014 0 # stop generating phys triggers - practically only 1 is generated

xwrite 0x02880010 0    # leave triggered run mode (generate End of Triggered)



#sleep 2

# send INT signal (= CTRL + C) to DMA benchmark (in case it's not finished yet)
kill -INT %1

# wait for DMA benchmark to complete
wait



