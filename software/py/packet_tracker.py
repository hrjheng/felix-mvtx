#!/usr/bin/env python
import decode

parser = decode.argparse.ArgumentParser()
parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
parser.add_argument("-r", "--run_location", required=True, help="Location of run to be analyzed, required for logging")
parser.add_argument("-l", "--link_number", required=True, help="Link number to be analyzed, required for logging")
parser.add_argument("-t", "--scan_type", required=False, help="Type of scan run (Threshold, FakeHitRate, etc)", default="FakeHitRate")
args = parser.parse_args()

run_location = args.run_location
run_number = run_location[len(run_location) - 6 : len(run_location)]
filename = args.filepath
link_number = args.link_number
scan_type = args.scan_type

f = open(filename, 'rb')

current_packet_counter = -1
iblock = 0
packet_id_jumps = []
while True:
    block = f.read(decode.BLOCK_SIZE)
    blen = len(block)
    if blen==0:
        break #EOF
    assert blen==decode.BLOCK_SIZE, '8k block is incomplete'
    memsize = block[decode.rdh_definitions.Rdh4ByteMap.MEMSIZE_MSB] << 8 | block[decode.rdh_definitions.Rdh4ByteMap.MEMSIZE_LSB]
    if memsize == 0:
        continue
    rdh = decode.Decode.decode_rdh(block[0:decode.RDH_SIZE])
    if rdh['packet_counter'] not in [0,current_packet_counter+1]:
        packet_id_jumps.append((iblock, rdh['packet_counter'], current_packet_counter))
    current_packet_counter = rdh['packet_counter']
    iblock += 1

if len(packet_id_jumps):
    log = open("packet_logs/" + scan_type  + "/run" + run_number + "_link" + link_number + ".log", 'w+')
    log.write("ERROR: Packet jumps present: \n")
    for bk, nxt, seq in packet_id_jumps:
        log.write(f"\tblock {bk}\t next {nxt}\t current {seq}\n")
    print(f"Link {link_number} complete... Packet jumps occured, check logs!")

else:
    print(f"Link {link_number} complete... No issues!")
