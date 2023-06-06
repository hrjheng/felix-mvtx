FLXADD={
    'add_num_channels':0x0090,           # Num of Channels per endpoints
    'add_bsp_info_builddatetime':0x0010, # Board ID date and time in BCD format YYMMDDhhmm
    'add_bsp_info_shorthash':0x0060,     # Short git hash (32bit)
    'add_gbt_rx_data_emu':0x5700,        # 1 EMU, 0 GBT
    'add_gbt_tx_data_emu':0x5710,        # 1 EMU, 0 GBT
    'add_gbt_trg_swt_mux':0x5720,        # 1 TRG, 0 SWT
    'add_gbt_align_done':0x6730,         # GBT_ALIGN_DONE
    'add_bsp_hkeeping_fpgaid':0x9360,    # FPGA_DNA
    'add_gbt_sc_link':0xE100,
    'add_gbt_sc_rst':0xE110,
    'add_gbt_sca_wr_ctr':0xE120,
    'add_gbt_sca_tx_cmd_data':0xE130,
    'add_gbt_sca_rd_ctr_mon':0xE140,
    'add_gbt_sca_rx_cmd_data':0xE150,
    'add_gbt_swt_wr_l':0xE160,
    'add_gbt_swt_wr_h':0xE170,
    'add_gbt_swt_cmd':0xE180,
    'add_gbt_swt_rd_l':0xE190,
    'add_gbt_swt_rd_h':0xE1A0,
    'add_gbt_swt_mon':0xE1B0,
    'add_ttc_gth_reset': 0xE400,
    'add_ttc_emu_reset': 0xE410,
    'add_ttc_emu_bcmax': 0xE420,
    'add_ttc_emu_hbmax': 0xE430,
    'add_ttc_emu_hbkeep': 0xE440,
    'add_ttc_emu_hbdrop': 0xE450,
    'add_ttc_emu_runmode': 0xE460,
    'add_ttc_emu_physdiv': 0xE470,
    'add_ttc_emu_physreq': 0xE480,
    'add_ttc_emu_use_bco': 0xE490,
    'add_ttc_emu_ttc_mon': 0xE4A0,
}
