#!/bin/bash



# PCI slot ID + channel number from command line (with default values)

PCISLOT=${1:-3b:00.0}
CH=${2:-0}





# register addresses

SWTBASE=0x0f000000
SWTCTRL=$(( $SWTBASE + 0x20 ))

CHBASE=$(( $SWTBASE + 0x80000 + CH * 32 ))

TXSTAT=$(( $CHBASE + 0x0c ))
TXHDR=$((  $CHBASE + 0x08 ))
TXADDR=$(( $CHBASE + 0x04 ))
TXVAL=$((  $CHBASE + 0x00 ))

RXSTAT=$(( $CHBASE + 0x1c ))
RXHDR=$((  $CHBASE + 0x18 ))
RXADDR=$(( $CHBASE + 0x14 ))
RXVAL=$((  $CHBASE + 0x10 ))





# wrappers around register read / write commands: pre / post process address and value

xlog(){
	grep -v "infoLoggerD not available, falling back to stdout logging"
}

xread(){
	ADDR=$(printf "0x%x" $1)

	VALOUT=$(o2-roc-reg-read 2>/dev/zero --id=$PCISLOT --channel=2 --address=$ADDR | xlog)

	printf "0x%08x\n" $VALOUT
}

xwrite(){
	ADDR=$(printf "0x%x" $1)
	VALIN=$(printf "0x%x" $2)

	VALOUT=$(o2-roc-reg-write 2>/dev/zero --id=$PCISLOT --channel=2 --address=$ADDR --value=$VALIN | xlog)

	printf "0x%08x\n" $VALOUT
}








# reset the full SWT - clear FIFOs
xwrite $SWTCTRL 1
xwrite $SWTCTRL 0


# read TX and RX status
TXS=$(xread $TXSTAT)
RXS=$(xread $RXSTAT)


# check that TX and RX link are up (bit 28)
if [[ $TXS =~ ^0x0....... || $RXS =~ ^0x0....... ]]; then
	echo "TX or RX link is not ready" > /dev/stderr
	exit 1
fi


# check that FIFOs are not full (bit 27)
if [[ $TXS =~ ^0x.[89]...... || $RXS =~ ^0x.[89]...... ]]; then
	echo "TX or RX FIFO is full" > /dev/stderr
	exit 1
fi


# send message -- order is important: first write HDR, then ADDR, then VALUE
xwrite $TXHDR  0x3000			# 4 bit CTRL (0x3 for SWT), 1 bit WnR, 1 bit ACK, 12 bit SEQID
xwrite $TXADDR 0x01010000		# 32 bit address
xwrite $TXVAL  0x01010000	        # 32 bit value


# read TX and RX status
TXS=$(xread $TXSTAT)
RXS=$(xread $RXSTAT)


# check that RX FIFO is not empty (bit 24)
if [[ $RXS =~ ^0x.[19]...... ]]; then
	echo "no response" > /dev/stderr
	exit 1
fi


# fetch message -- order is important: first read HDR, then ADDR, then VALUE
echo $(xread $RXHDR) $(xread $RXADDR) $(xread $RXVAL)


