#!/usr/bin/env python3.9

import os, csv
from collections import OrderedDict
import json

PART_TO_RU_ID_IN_LAYER = {
    'L0T':  0,
    'L0B':  6,
    'L1T':  0,
    'L1B':  8,
    'L2TI': 0,
    'L2TO': 5,
    'L2BO': 10,
    'L2BI': 15,
    'L3T':  0,
    'L3B':  12,
    'L4TI': 0,
    'L4TO': 8,
    'L4BO': 15,
    'L4BI': 23,
    'L5TI': 0,
    'L5TO': 10,
    'L5BO': 21,
    'L5BI': 31,
    'L6TI': 0,
    'L6TO': 12,
    'L6BO': 24,
    'L6BI': 36
    }

# columns: HOSTNAME,flp,cru,CRU_SN,pp,part,nstaves

#___________________________________
def gen_tb_yml(crate):
    output = f"# This is automatically generated config file for {crate['part']} by 'config_file_generator.py'.\n"
    with open("template_testbench.yml") as template:
        for line in template:
            if "!!!" in line:
                key = line.split(" :")[0]
                output += line.replace("!!!", crate[key])
            else:
                output += line
    cfgname = f"output/testbench_{crate['part']}_{crate['pp'].replace('-','').replace(';','_')}.yml".lower()
    with open(cfgname, 'w') as f:
        f.write(output)
    print("Generating testbench config YML file:" , cfgname)

def get_feeid(layer, fiber_uplink, stave_number_in_layer):
    feeid = (layer << 12) + (fiber_uplink << 8) + stave_number_in_layer
    return feeid

def get_fiber_uplink(link_number_in_layer, num_swt):
    uplink = link_number_in_layer // num_swt
    return uplink

def get_stave_number_in_layer(link_number_in_layer, start_board_id, num_swt):
    board_num = link_number_in_layer % num_swt
    return board_num + start_board_id

#___________________________________
def gen_roc_cfg(crate):
    swt = sorted(list(crate['links'].keys()))
    ttc = sorted([v for vals in crate['links'].values() for v in vals])
    off = [i for i in range(24) if i not in swt+ttc]

    for ep in [0,1]:
        output = OrderedDict()
        cru = OrderedDict()
        cru['allowRejection'] = "false"
        cru['clock'] = "ttc"
        cru['cruId'] = crate['cruId']
        cru['datapathMode'] = "packet"
        cru['loopback'] = "false"
        cru['gbtMode'] = "GBT"
        cru['downstreamData'] = "CTP"
        cru['ponUpstream'] = "true"
        cru['onuAddress'] = crate['onuAddress']
        cru['dynamicOffset'] = "true"
        cru['triggerWindowSize'] = "1000"
        cru['gbtEnabled'] = "true"
        cru['userLogicEnabled'] = "false"
        cru['runStatsEnabled'] = "false"
        cru['userAndCommonLogicEnabled'] = "false"
        cru['systemId'] = "0x20"
        cru['timeFrameLength'] = "128"


        links_dict_disable = OrderedDict()
        links_dict_disable['enabled'] = "false"
        links_dict_disable['gbtMux'] = "ttc"
        links_dict_disable['feeId'] = "0x0"

        output['cru'] = cru

        output['links'] = links_dict_disable

        for l in swt:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                links_dict = OrderedDict()
                links_dict['enabled'] = "true"
                links_dict['gbtMux'] = "swt"

                fiber_uplink = get_fiber_uplink(l, len(swt))
                stave_number_in_layer = get_stave_number_in_layer(l, crate['start_board_id'], len(swt))
                links_dict['feeId'] = hex(get_feeid(crate['layer'], fiber_uplink, stave_number_in_layer))
                name = f"link{l%12}"
                output[name] = links_dict
        for l in ttc:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                links_dict = OrderedDict()
                links_dict['enabled'] = "true"
                links_dict['gbtMux'] = "ttc"

                fiber_uplink = get_fiber_uplink(l, len(swt))
                stave_number_in_layer = get_stave_number_in_layer(l, crate['start_board_id'], len(swt))
                links_dict['feeId'] = hex(get_feeid(crate['layer'], fiber_uplink, stave_number_in_layer))
                name = f"link{l%12}"
                output[name] = links_dict

        for l in off:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                name = f"link{l%12}"
                output[name] = links_dict_disable

        cfgname = f"output/roc_{crate['HOSTNAME'].replace('.cern.ch','')}_sn{crate['CRU_SN']}_ep{ep}.json".lower()
        with open(cfgname, 'w') as f:
            json.dump(output, f, indent=2)
        print("Generating roc config JSON file:" , cfgname)

def gen_roc_cfg_old(crate):
    swt = sorted(list(crate['links'].keys()))
    ttc = sorted([v for vals in crate['links'].values() for v in vals])
    off = [i for i in range(24) if i not in swt+ttc]
    links = {0: [(l, True) for l in swt if l<12]   +   [(l, False) for l in off if l<12],
             1: [(l-12, True) for l in swt if l>=12] + [(l-12, False) for l in off if l>=12]}
    for ep in [0,1]:
        output = ""
        with open("template_roc.cfg") as template:
            for line in template:
                if "!!!" in line:
                    key = line.split("=")[0]
                    output += line.replace("!!!", crate[key])
                else:
                    output += line

        for l in swt:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                fiber_uplink = get_fiber_uplink(l, len(swt))
                stave_number_in_layer = get_stave_number_in_layer(l, crate['start_board_id'], len(swt))
                feeid = get_feeid(crate['layer'], fiber_uplink, stave_number_in_layer)
                output += \
                f"\n[link{l%12}]\n" + \
                f"enabled=true\n" + \
                f"gbtMux=SWT\n"+ \
                f"feeId={hex(feeid)}\n"
        for l in ttc:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                fiber_uplink = get_fiber_uplink(l, len(swt))
                stave_number_in_layer = get_stave_number_in_layer(l, crate['start_board_id'], len(swt))
                feeid = get_feeid(crate['layer'], fiber_uplink, stave_number_in_layer)
                output += \
                f"\n[link{l%12}]\n" + \
                f"enabled=true\n" + \
                f"gbtMux=TTC\n"+ \
                f"feeId={hex(feeid)}\n"

        for l in off:
            if (ep == 0 and l < 12) or (ep == 1 and l >= 12):
                output += \
                f"\n[link{l%12}]\n" + \
                f"enabled=false\n" + \
                f"gbtMux=TTC\n"+ \
                f"feeId={hex(0)}\n"

        cfgname = f"output/roc_{crate['HOSTNAME'].replace('.cern.ch','')}_sn{crate['CRU_SN']}_ep{ep}.cfg".lower()
        with open(cfgname, 'w') as f:
            f.write(output)
        print("Generating roc config CFG file:" , cfgname)

#___________________________________
def gen_readout_cfg(flp, template):
    output = ""
    cfgname = f"output/{template[9:-4]}_{flp['part']}.cfg".lower()
    with open(template) as template:
        for line in template:
            if "!!!PART!!!" in line:
                output += line.replace("!!!PART!!!", flp['part'].lower())
            elif "!!!ID1!!!" in line:
                output += line.replace("!!!ID1!!!", flp['CRU_SN1'])
            elif "!!!ID2!!!" in line:
                output += line.replace("!!!ID2!!!", flp['CRU_SN2'])
            else:
                output += line

    with open(cfgname, 'w') as f:
        f.write(output)
    print("Generating readout config CFG file:" , cfgname)

#___________________________________
def gen_crate_mapping(data, ru_maps):
    ret = ""
    ret += f"'{data['SUBRACK']}': [\n"
    for i in range(data['nstaves']):
        ru_sn = None
        for ru_map in ru_maps:
            if int(ru_map['layer']) == data['layer'] and int(ru_map['board_id_in_layer']) == PART_TO_RU_ID_IN_LAYER[data['part']]+i:
                ru_sn = ru_map['ru_sn']
        if ru_sn is None:
            print(f"ERROR: Could not find ru_sn for combination of layer: {data['layer']} and board_id_in_layer: {PART_TO_RU_ID_IN_LAYER[data['part']]+1}")
            exit()
        ret += f"    ('{data['HOSTNAME']}', '{data['CRU_SN']}', {data['layer']}, {i:2d},{ru_sn}, {PART_TO_RU_ID_IN_LAYER[data['part']]+i:2d}, 0x109AC916, 0x0C95FA5D),\n"
    ret += "],\n"
    return ret


#___________________________________
if __name__=="__main__":
    crate_mapping = ""
    if not os.path.exists("output"): os.makedirs("output")
    with open ("mapping_ru_P2.csv") as csv_file:
        dict_reader = csv.DictReader(csv_file, delimiter=',')
        ru_map = list(dict_reader)

    crate_list = list()
    with open("mapping_P2.csv") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for row in csv_reader:
            crate_list.append(row.copy())

    for crate in crate_list:
        crate['nstaves'] = int(crate['nstaves'])
        crate['start_board_id'] = int(crate['start_board_id'])
        crate['SUBRACK'] = crate['part']+'-'+crate['pp'].replace(';','-')
        crate['layer'] = int(crate['part'][1])
        crate['cruId'] = hex(int(crate['CRU_SN']))
        crate['onuAddress'] = hex(2*int(crate['flp'])+int(crate['cru']))
        if crate['layer'] < 3: # IB
            crate['LAYER'] = "INNER"
            crate['links'] = {i: [i+crate['nstaves'],i+crate['nstaves']*2] for i in range(crate['nstaves'])}
            crate['LINK_DICT'] = "\n  "+"\n  ".join(f"{k}: {v}" for k,v in crate['links'].items())
        else: # OB
            crate['LAYER'] = "OUTER"
            crate['links'] = {i: [i+crate['nstaves']] for i in range(crate['nstaves'])}
            crate['LINK_DICT'] = "\n  "+"\n  ".join(f"{k}: {v}" for k,v in crate['links'].items())
        gen_tb_yml(crate)
        gen_roc_cfg(crate)
        gen_roc_cfg_old(crate)
        crate_mapping += gen_crate_mapping(crate, ru_map)


    flp_list = list()
    for i, crate in enumerate(crate_list):
        if (i % 2) == 0:
            flp = {"CRU_SN1": crate['CRU_SN'], "part": crate['part'][:-1]}
            flp_list.append(flp)
        else:
            flp_list[int((i-1)/2)].update({'CRU_SN2': crate['CRU_SN']})

    for flp in flp_list:
        gen_readout_cfg(flp, "template_readout.cfg")
        gen_readout_cfg(flp, "template_readout_ecs.cfg")



    with open("output/crate_mapping.txt", 'w') as f:
        f.write(crate_mapping)
        #print(crate_mapping)

    print("Done!")
