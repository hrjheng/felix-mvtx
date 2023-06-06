# Compile sources for CAN HLP module

# Set up util_part_path and lib_name
#------------------------------------------------------
quietly set lib_name "work"
quietly set part_name "dcs_canbus"
# path from mpf-file in sim
quietly set util_part_path "../../../../$part_name"
quietly set common_rtl_path "$util_part_path/../common/source/rtl"
quietly set common_tmr_rtl_path "$util_part_path/../common_tmr/source/rtl"
quietly set wishbone_rtl_path "$util_part_path/../wishbone/source/rtl"

quietly set lib_path "../libs"

vlib $lib_path/$lib_name
vmap $lib_name $lib_path/$lib_name

quietly set compdirectives_vhdl "-quiet -nologo -nostats -2008 -lint -work $lib_name"

quietly set compdirectives_vlog "-quiet -suppress 1346,1236 -work $lib_name +incdir+$common_tmr_rtl_path +incdir+$wishbone_rtl_path +define+DISABLE_MAJORITY_VOTER_ASSERTIONS=1"

echo "\n\n\n=== Compiling $lib_name source\n"

eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/can_hlp_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/can_hlp_fsm.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/tmr_wrappers/can_hlp_fsm_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/can_hlp_wishbone_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/can_hlp_wb_slave_regs.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/tmr_wrappers/can_hlp_wb_slave_regs_tmr_wrapper.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/monitor/can_hlp_monitor_pkg.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/monitor/can_hlp_monitor.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_hlp/can_hlp_top.vhd
