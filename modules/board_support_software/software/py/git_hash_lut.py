"""Dictionary of official FW releases with corresponding githash and scrubbing CRC"""

# RU_mainFPGA releases
# https://gitlab.cern.ch/alice-its-wp10-firmware/RU_mainFPGA/-/releases
ru_githash2ver_lut = {
    0x757F563E : "mvtx_v1.18.0.2",  # 600 Mbps version
    0x43CFB8A6 : "mvtx_v1.18.0.1",  # 600 Mbps version
    0x95A9053F : "mvtx_v1.18.0",
    0x109AC916 : "v1.18.0",
    0x952ABF8E : "mvtx_v1.17.9",
    0xE8AEB92A : "v1.17.9",
    0x808C2BE4 : "v1.17.8",
    0x20B8CBEA : "mvtx_v1.17.7",
    0x8C53C903 : "v1.17.7",
    0x5F12A825 : "v1.17.6",
    0x7827D793 : "v1.17.5",
    0x9388A010 : "mvtx_v1.17.4",
    0xE63065EC : "v1.17.4",
    0x08180B25 : "v1.17.3",
    0xAB1BC57D : "v1.17.2",
    0xF14449D4 : "mvtx_v1.17.1",
    0x83BB49E8 : "v1.17.1",
    0xB3223619 : "v1.17.0",
    0xAD004AC4 : "mvtx_v1.16.0",
    0x9667C5D4 : "v1.16.0",
    0x877D41C8 : "mvtx_v1.15.0",
    0x1F61BB5C : "v1.15.0",
    0x8892A07C : "mvtx_v1.14.0",
    0x75DDFFF3 : "v1.14.0",
    0xA3951B3D : "mvtx_v1.13.0",
    0x66BFA093 : "v1.13.0",
    0x401148A2 : "mvtx_v1.12.0",
    0xEB55FDDE : "v1.12.0",
    0x3C738295 : "mvtx_v1.11.0",
    0x9C89DFD1 : "v1.11.0",
    0xA84548D6 : "mvtx_v1.10.0",
    0xAAB84D42 : "v1.10.0",
    0xC0EE647D : "mvtx_v1.9.0.1",
    0x3413BBFE : "mvtx_v1.9.0",
    0xE57DBCB5 : "v1.9.0",
    0x783D615E : "v1.8.1",
    0x1fe85b23 : "mvtx_v1.8.0",
    0x94367193 : "v1.8.0-loc",
    0xcdd8442b : "v1.8.0-ext",
    0x8931000c : "mvtx_v1.7.0_i2cfix",
    0x0fb1510a : "mvtx_v1.7.0",
    0xAD11C003 : "v1.7.0",
    0xbb2e6526 : "mvtx_v1.6.0",
    0xcb15b258 : "v1.6.0",
    0xef5485c8 : "v1.5.0",
    0xfc194fe2 : "v1.4.0",
    0xdaa3b8d8 : "v1.3.0",
    0xe47c97e3 : "v1.2.2",
    0x3a4aaa2e : "v1.2.1",
    0x1566063c : "v1.2.0",
    0xafb92360 : "v1.1.0",
    0xfc91484a : "v1.0.0",
    0x3690d9e2 : "v0.10.1",
    0x0483228b : "v0.10.0",
    0xecd5a8d4 : "v0.9.0",
    0x63a14f2e : "v0.8.1",
    0x18a94fc9 : "v0.8.0",
    0xd15f3068 : "v0.7.0",
    0x9fb6a6f4 : "v0.6.0",
    0x390621d8 : "v0.5.0",
    0x7f74cf95 : "v0.4.0",
    0xa0f76979 : "v0.3.0",
    0x70f77e1c : "powerunit_interlock_v0.6",
    0xa02791ed : "v0.1.11",
    0xc12e7171 : "v0.1.10",
    0x05f1d470 : "powerunit_interlock_v0.5.1",
    0xdd3b5f9a : "v0.1.9",
    0x5b044cbc : "powerunit_interlock_v0.5",
    0xe1b14746 : "v0.1.8"
}

# RU main FPGA CRC codes, as produced by PA3 during scrubbing
ru_scrubcrc2ver_lut = {
  0x02e3077f : "v1.18.0",
  0xdbfad02d : "v1.17.9",
  0xefa3a114 : "v1.17.8",
  0xc7b1a050 : "v1.17.7",
  0x91718cab : "v1.17.6",
  0x66d19cca : "v1.17.5",
  0xe079aa3c : "v1.17.4",
  0x47e4baba : "v1.16.0"
}

# RUv0_CRU releases
ruv0_cru_githash2ver_lut = {
    0x0CC2CF23 : "v1.1",
    0x6fc4e1d6 : "v1.1_SG2", # Speed grade 2 boards
    0x52a371bb : "CHARM_v1.0",
    0x57042f33 : "20171017",
    0x1f3f0fff : "20171017_SG2",
    0x0ac12387 : "20190306",
    0x057F453E : "20210503",
}

# CRU releases
# https://gitlab.cern.ch/alice-cru/cru-fw
cru_githash2ver_lut = {
    0x475E043B : "m_v1.02",
    0x5dbf360a : "its-ul-v0.1",
    0x5A5CE64A : "v3.15.0-its_patch",
    0x3C46BEB5 : "m_v1.00",
    0xE64B97B1 : "v3.15.0",
    0x14CCD414 : "v3.14.1",
    0x2058C933 : "v3.14.0",
    0x4A412C71 : "v3.13.0",
    0x96425702 : "rm5.1_1",
    0x825ab51f : "v3.12.0-its_patch",
    0x6a85d30c : "v3.12.0",
    0x7be5aa1c : "v3.11.0",
    0x94873b8e : "felix_ORNL_v2_56",
    0x8469D252 : "mvtx_new_dataformat",
    0xe4a5a46e : "v3.10.0",
    0xf71faa86 : "v3.9.1",
    0xe8e58cff : "v3.8.0",
    0xf8cecade : "v3.7.0",
    0x75b96268 : "v3.6.1",
    0x06955404 : "v3.6.0",
    0xd458317e : "v3.5.2",
    0x6baf11da : "v3.5.1",
    0x5b162edd : "v3.5.0",
    0x51882687 : "v3.4.0",
    0x3f5e11b3 : "v3.3.0",
    0x4c8e6c48 : "v3.2.0",
    0x12a179aa : "v3.1.1",
    0xeb4c92a1 : "v3.1.0",
    0x1a3109d2 : "v3.0.0",
    0xbf16cf58 : "v2.7.2",
    0x920ad515 : "v2.7.1",
    0x5b1c7c87 : "v2.7.0",
    0x9bf047b2 : "v2.6.0",
    0x910ae122 : "v2.5.0",
    0x5168b6b8 : "v2.4.0",
    0x873c9ab1 : "v2.3.0"
}

its_ul_githash2ver_lut = {
    0xf6b2a09f : "v0.1",
}

# RU_auxFPGA release
pa3_githash2ver_lut = {
    0x0171751E : "v2.0D",
    0x0D37965F : "v2.0C",
    0x09467AC3 : "v2.0B",
    0x0C95FA5D : "v2.0A",
    0x0F48061C : "fault_injection_alpha",
    0x0007C2D5 : "v2.09",
    0xfda8473d : "v2.08",
    0xf438cb59 : "v2.07",
    0xf1adfd4a : "v2.06"
}

def get_ru_version(git_hash):
    if git_hash in ru_githash2ver_lut:
        return ru_githash2ver_lut[git_hash]
    else:
        return "unofficial version"

def get_ruv0_cru_version(git_hash):
    if git_hash in ruv0_cru_githash2ver_lut:
        return ruv0_cru_githash2ver_lut[git_hash]
    else:
        return "unofficial version"

def get_cru_version(git_hash):
    if git_hash in cru_githash2ver_lut:
        return cru_githash2ver_lut[git_hash]
    else:
        return "unofficial version"

def get_its_ul_version(git_hash):
    if git_hash in its_ul_githash2ver_lut:
        return its_ul_githash2ver_lut[git_hash]
    else:
        return "unofficial version"

def get_pa3_version(git_hash):
    if git_hash in pa3_githash2ver_lut:
        return pa3_githash2ver_lut[git_hash]
    else:
        return "unofficial version"
