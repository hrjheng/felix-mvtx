# Compile source for Canola CAN controller

# Set up util_part_path and lib_name
#------------------------------------------------------
quietly set lib_name "work"
quietly set part_name "dcs_canbus"
# path from mpf-file in sim
quietly set util_part_path "../../../../$part_name"
quietly set lib_path "../libs"

vlib $lib_path/$lib_name
vmap $lib_name $lib_path/$lib_name

quietly set compdirectives_vhdl "-quiet -nologo -nostats -O5 -2008 -lint -work $lib_name"

quietly set compdirectives_vlog "-mixedsvvh s -93 -suppress 1346,1236 -quiet -work $lib_name +incdir+$util_part_path/source/rtl/can_controller/"

echo "\n\n\n=== Compiling Canola sources\n"

eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/counters/counter_saturating.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/counters/up_counter.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_time_quanta_gen.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_crc.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_btl.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_bsp.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_frame_rx_fsm.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_frame_tx_fsm.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_eml.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_voters/tmr_voter_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/counter_saturating_tmr_wrapper_triplicated.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/up_counter_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_time_quanta_gen_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_bsp_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_btl_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_eml_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_frame_rx_fsm_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/canola_frame_tx_fsm_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/tmr_wrapper_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/tmr_wrappers/tmr_wrapper_cfg_wp10.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/canola/canola_top_tmr.vhd
