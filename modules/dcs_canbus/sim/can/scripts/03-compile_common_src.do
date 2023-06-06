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

# (Re-)Generate library and Compile source files
#--------------------------------------------------
echo "\n\nRe-gen lib and compile $lib_name source"
if {[file exists $lib_path/$lib_name]} {
    file delete -force $lib_path/$lib_name
}

vlib $lib_path/$lib_name
vmap $lib_name $lib_path/$lib_name

quietly set compdirectives_vhdl "-quiet -nologo -nostats -2008 -lint -work $lib_name"

quietly set compdirectives_vlog "-quiet -suppress 1346,1236 -work $lib_name +incdir+$common_tmr_rtl_path +incdir+$wishbone_rtl_path +define+DISABLE_MAJORITY_VOTER_ASSERTIONS=1"

echo "\n\n\n=== Compiling $lib_name source\n"

eval vcom  $compdirectives_vhdl   $common_rtl_path/xpm_cdc_components_pkg.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/tmr_pkg.vhd
eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/intercon_pkg.vhd
eval vlog  $compdirectives_vlog   $wishbone_rtl_path/assertions/wishbone_slave_checker_sv.sv
eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/assertions/wishbone_slave_checker.vhd
eval vcom  $compdirectives_vhdl   $common_rtl_path/upcounter/upcounter_core.vhd
eval vlog  $compdirectives_vlog   $common_rtl_path/common/assertions/common_assertions.sv
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mismatch/mismatch.vhd
eval vlog  $compdirectives_vlog   $common_tmr_rtl_path/mmr_registers/assertions/mmr_general_assertions.sv
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mmr_registers/majority_voter_wrapper.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mmr_registers/majority_voter_wrapper2.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mmr_registers/majority_voter_array_wrapper.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mmr_registers/majority_voter_triplicated_array_wrapper.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/mmr_registers/majority_voter_triplicated_wrapper.vhd
eval vlog  $compdirectives_vlog   $common_tmr_rtl_path/mmr_registers/majority_voter_packed.sv
eval vlog  $compdirectives_vlog   $common_tmr_rtl_path/mmr_registers/majority_voter.sv
eval vlog  $compdirectives_vlog   $common_tmr_rtl_path/mmr_registers/majority_voter_triplicated.sv

eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/upcounter/upcounter_tmr_wrapper_tripleoutput.vhd
eval vcom  $compdirectives_vhdl   $common_tmr_rtl_path/upcounter/upcounter_tmr_wrapper.vhd

eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/tmr/majority_voter_wbs_i.vhd
eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/tmr/majority_voter_triplicated_wbs_o.vhd
eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/tmr/majority_voter_triplicated_wbs_i.vhd

eval vcom  $compdirectives_vhdl   $wishbone_rtl_path/slaves/ws_reg.vhd

eval vcom  $compdirectives_vhdl   $util_part_path/../wishbone/source/rtl/slaves/counter_monitor/ws_counter_monitor.vhd
eval vcom  $compdirectives_vhdl   $util_part_path/../wishbone/source/rtl/slaves/counter_monitor/tmr_wrappers/ws_counter_monitor_tmr_wrapper.vhd
