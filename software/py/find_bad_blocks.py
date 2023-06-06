"""A script to extract the bad blocks for the RU"""

import os
import sqlite3
import sys

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

import bad_blocks_io

def get_db(db_file_name):
    """extracts the bad block addresses of board with serial number board_serial"""
    db_file = os.path.realpath(db_file_name)
    if not os.path.isfile(db_file):
        print("file not found")
        exit(-1)
    db_connection = sqlite3.connect(db_file)
    return db_connection


def get_bad_blocks_from_sn(db_connection, board_serial, flash_device_list=(0,), exclusive_name=False):
    """returns the bad_blocks"""
    try:
        bad_blocks = bad_blocks_io.get_bad_blocks_of_board(
            board_serial,
            db_connection,
            exclusive_name,
            verbose=False)
    except LookupError:
        return []
    except:
        raise
    # don't know how to use panda dataframes, so convert the dataframe to a list
    bb_list = bad_blocks.values.tolist()
    # bad blocks are in the second column of this list, flash "device"" in the 3rd
    bad_blocks = []
    for _, address, device, _ in bb_list:
        if device in flash_device_list:
            bad_blocks.append(address)
    bad_bitfile_locations = []
    for block in bad_blocks:
        bad_bitfile_locations.append(block//0x100*0x100)
    bad_bitfile_locations = list(set(bad_bitfile_locations)) # Remove duplicates
    return bad_bitfile_locations

# board_id format in database for bad_blocks table: (from conversation with Marcel)
# board_id = 1,2,3 etc -> RUv2.0
# board_id = 000001,000002,000003 etc -> RUv2.1 (might be duplicated with dna)
# board_id = dna -> RUv2.1
# board_id = proto1, proto2, proto3 etc -> RUv2.0
# board_id = RU1v1SN1, RU1v1SN2, RU1v1SN3 etc -> RUv1.1
# board_id = RU1_1ID1, RU1_1ID2, RU1_1ID3 etc -> RUv1.1
# board_id = 1_again  -> RUv2.0

# board_serial_no mapping in board_id table: (from conversation with Marcel)
# board_serial_no = 000001,000002,000003 etc -> RUv2.1
# board_serial_no = 001,002,003 etc -> RUv2.1
# board_serial_no = 2v01,2v02 etc -> RUv2.0

def get_bad_blocks_from_sn_2_1(db_connection, board_serial, flash_device_list=(0,)):
    return get_bad_blocks_from_sn(db_connection, f"{board_serial:06}", flash_device_list, exclusive_name=False)

def get_bad_blocks_from_sn_2_0(db_connection, board_serial, flash_device_list=(0,)):
    bb_list = get_bad_blocks_from_sn(db_connection, board_serial, flash_device_list, exclusive_name=True)
    bb_list.extend(get_bad_blocks_from_sn(db_connection, f"proto{board_serial}", flash_device_list, exclusive_name=True))
    bb_list.extend(get_bad_blocks_from_sn(db_connection, f"{board_serial}_again", flash_device_list, exclusive_name=True))
    bb_list = list(set(bb_list)) # Remove duplicates
    return bb_list

def get_bad_blocks_from_sn_1_1(db_connection, board_serial, flash_device_list=(0,)):
    bb_list = get_bad_blocks_from_sn(db_connection, f"RU1v1SN{board_serial}", flash_device_list, exclusive_name=True)
    bb_list.extend(get_bad_blocks_from_sn(db_connection, f"RU1_1ID{board_serial}", flash_device_list, exclusive_name=True))
    bb_list = list(set(bb_list)) # Remove duplicates
    return bb_list

if __name__ == "__main__":
    filename = '/home/ALICE/TestSystem/software/py/ITS_WP10_RU_board_badblocks.db'
    max_sn_2_1 = 392
    max_sn_2_0 = 6
    max_sn_1_1 = 13
    dna_not_found = []
    bb_not_found = []
    db = get_db(filename)
    with open('bb_dna', 'w') as f:
        f.write("ru_dna_lut = {\n")
        for sn in range(1, max_sn_2_1+1):
            dna = bad_blocks_io.get_dna_mapping(sn, db)
            if dna != '':
                f.write(f"    0x{int(dna):X} : {sn:3<},\n")
            else:
                dna_not_found.append(sn)
        f.write("}\n")
        print(f"DNA not found for the following SN {dna_not_found}")
        dna_not_found = []
        f.write("ru_2_0_dna_lut = {\n")
        for sn in range(1, max_sn_2_0+1):
            dna = bad_blocks_io.get_dna_mapping(f"2v0{sn}", db)
            if dna != '':
                f.write(f"    0x{int(dna):X} : {sn:3<},\n")
            else:
                dna_not_found.append(sn)
        f.write("}\n")
        print(f"DNA not found for the following RUv2.0 SN {dna_not_found}")
        dna_not_found = []
    with open('bb_lut', 'w') as f:
        f.write("sn2bb_lut_c0 = {\n")
        for sn in range(1, max_sn_2_1+1):
            bb = get_bad_blocks_from_sn_2_1(db, sn, (0,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c0 not found for the following SN {bb_not_found}")
        bb_not_found = []
        f.write("sn2bb_lut_c1 = {\n")
        for sn in range(1, max_sn_2_1+1):
            bb = get_bad_blocks_from_sn_2_1(db, sn, (1,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c1 not found for the following SN {bb_not_found}")
        bb_not_found = []
        f.write("sn2bb_lut_2_0_c0 = {\n")
        for sn in range(1, max_sn_2_0+1):
            bb = get_bad_blocks_from_sn_2_0(db, sn, (0,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c0 not found for the following RUv2.0 SN {bb_not_found}")
        bb_not_found = []
        f.write("sn2bb_lut_2_0_c1 = {\n")
        for sn in range(1, max_sn_2_0+1):
            bb = get_bad_blocks_from_sn_2_0(db, sn, (1,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c1 not found for the following RUv2.0 SN {bb_not_found}")
        bb_not_found = []
        f.write("sn2bb_lut_1_1_c0 = {\n")
        for sn in range(1, max_sn_1_1+1):
            bb = get_bad_blocks_from_sn_1_1(db, sn, (0,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c0 not found for the following RUv1.1 SN {bb_not_found}")
        bb_not_found = []
        f.write("sn2bb_lut_1_1_c1 = {\n")
        for sn in range(1, max_sn_1_1+1):
            bb = get_bad_blocks_from_sn_1_1(db, sn, (1,))
            if bb != []:
                f.write(f"    {sn:3<} : [{', '.join(hex(x) for x in bb)}],\n")
            else:
                bb_not_found.append(sn)
        f.write("}\n")
        print(f"BB c1 not found for the following RUv1.1 SN {bb_not_found}")
