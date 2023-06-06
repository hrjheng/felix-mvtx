#!/usr/bin/env python3.9

"""program to read binary file"""

# import modules
import sys
import argparse


# program
def readFile(file_object, link):
    """Read file and interpret"""
    f_i = file_object
    p_count = 0
    byte_count = 0
    while True:
        try:
            # read 32 bytes (256bits) at a time
            word = f_i.read(32)
            if len(word) < 32:
                break
            byte_count += 32
            # search for FLX data header
            if (word[31] != 0xAB) or ((word[28] & 0x1f) != link):
                continue
            # found FELIX header
            p_count = 0
            packet_cnt = word[25] + ((word[26] << 8) & 0xf00)
            for i in range(packet_cnt):
                word = f_i.read(32)
                if (word[31] & 0xfc) != 0:  # check that the count is formatted correctly
                    print(f"Byte {byte_count}: not a FELIX data word", file=sys.stderr)
                    byte_count += 32
                    continue  # not a valid FELIX data word, ignore and try to continue
                byte_count += 32
                count = word[30] + ((word[31] << 8) & 0x300)
                if count < p_count:
                    p_count = 0
                d_count = count - p_count
                assert (d_count | 0x3 == 0x3), f"Byte {byte_count}: Counter increment must be less than or equal 3. gbt count {count} and previous count {p_count} found.. ({word[30]:02x} {word[31]:02x})"
                p_count = count

                if count == 3:
                    print("".join([f"{word[i]:02x} " for i in range(9,-1,-1)]), f"| HEADER - v: {word[0]}", f"feeid: {word[2]+(word[3]<<8):x}")
                    print("".join([f"{word[i]:02x} " for i in range(19,9,-1)]), f"| HEADER - bc: {word[10]+(word[11]<<8):x}",
                          f"o: {word[14]+(word[15]<<8)+(word[16]<<16)+(word[17]<<24)+(word[18]<<32):x}")
                    msg = f"| HEADER - pg: {word[24]+(word[25]<<8):d} stop: {word[26]} trg: {word[20]+(word[21]<<8)+(word[22]<<16)+(word[23]<<24):x} ("
                    if word[21] & 0x40 == 0x40:
                        msg += "R "
                    if word[21] & 0x20 == 0x20:
                        msg += "C "
                    else:
                        msg += "T "
                    if word[21] & 0x10 == 0x10:
                        msg += "FErst "
                    if word[21] & 0x8 == 0x8:
                        msg += "TF "
                    if word[21] & 0x4 == 0x4:
                        msg += "EOC "
                    if word[21] & 0x2 == 0x2:
                        msg += "SOC "
                    if word[21] & 0x1 == 0x1:
                        msg += "EOT "
                    if word[20] & 0x80 == 0x80:
                        msg += "SOT "
                    if word[20] & 0x10 == 0x10:
                        msg += "PhT "
                    if word[20] & 0x7 == 0x7:
                        msg += "HBr HB ORBIT "
                    elif word[20] & 0x7 == 0x3:
                        msg += "HB ORBIT "
                    msg_final = msg[:-1] + ")"
                    print("".join([f"{word[i]:02x} " for i in range(29,19,-1)]), msg_final)
                else:
                    for i in range(d_count):
                        if word[i*10+9] == 0xe0:
                            msg = "| IHW - Sensor "
                            for j in range(8):
                                if word[i*10+0] & (1<<j) != 0:
                                    msg += f"{j} "
                            for j in range(2):
                                if word[i*10+1] & (1<<j) != 0:
                                    msg += f"{j+8}"
                        elif word[i*10+9] == 0xe8:
                            msg = f"| TDH - o: {word[i*10+4]+(word[i*10+5]<<8)+(word[i*10+6]<<16)+(word[i*10+7]<<24)+(word[i*10+8]<<32):x} "
                            msg += f"bc: {word[i*10+2]+(word[i*10+3]<<8):x}"
                            if word[i*10+1] & 0x10 == 0x10:
                                msg += " IntTrg,"
                            if word[i*10+1] & 0x20 == 0x20:
                                msg += " NoData,"
                            if word[i*10+1] & 0x40 == 0x40:
                                msg += " Cont,"
                            msg += f" Trg: {((word[i*10+1]&0xf)<<8)+word[i*10+0]:03x}"
                        elif word[i*10+9] == 0xf0:
                            msg = "| TDT - "
                            if word[i*10+8] & 0x10 == 0x10:
                                msg += "lane_timeout "
                            if word[i*10+8] & 0x8 == 0x8:
                                msg += "lane_starts_violation "
                            if word[i*10+8] & 0x2 == 0x2:
                                msg += "transmission_timeout "
                            if word[i*10+8] & 0x1 == 0x1:
                                msg += "packet_done "
                            if word[i*10+7] & 0x80 == 0x80:
                                msg += "timeouit_to_start "
                            if word[i*10+7] & 0x40 == 0x40:
                                msg += "timeout_start_stop "
                            if word[i*10+7] & 0x20 == 0x20:
                                msg += "timeout_in_idle"
                        elif word[i*10+9] == 0xe4:
                            msg = "| DDW"
                        elif word[i*10+9] == 0xf8:
                            msg = "| CDW"
                        else:
                            msg = "| DATA"
                        print("".join([f"{word[i]:02x} " for i in range(i*10+9,i*10-1,-1)]), msg)
        except IOError:
            break


# define main
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='?')
    parser.add_argument("-s", "--offset", type=int, required=False,
                        help="Byte offset for the data decoding to seek to. NOTE: not supported without input file (i.e. with input in stdin)",
                        default=0)
    parser.add_argument("-l", "--link", type=int, required=False,
                        help="Link number (1,..,24)",
                        default=1)
    args = parser.parse_args()
    offset = args.offset
    link = args.link
    if args.filename:
        f_i = open(args.filename, 'rb')
        if offset != 0:
            f_i.seek(offset)
    elif not sys.stdin.isatty():
        f_i = sys.stdin.buffer
    else:
        parser.print_help()
        sys.exit(0)

    assert link in range(1,25), "link must be between 1 and 24"
    readFile(f_i, link)
    # close the file
    f_i.close()


if __name__ == '__main__':
    main()
