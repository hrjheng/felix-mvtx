# Compile source for OpenCores CAN controller

# Set up util_part_path and lib_name
#------------------------------------------------------
quietly set lib_name "work"
quietly set part_name "dcs_canbus"
# path from mpf-file in sim
quietly set util_part_path "../../../../$part_name"
quietly set lib_path "../libs"

# (Re-)Generate library and Compile source files
#--------------------------------------------------
echo "\n\nRe-gen lib and compile $lib_name source"
if {[file exists $lib_path/$lib_name]} {
  file delete -force $lib_path/$lib_name
}

vlib $lib_path/$lib_name
vmap $lib_name $lib_path/$lib_name

quietly set compdirectives_vhdl "-2008 -lint -work $lib_name"

quietly set compdirectives_vlog "-mixedsvvh s -93 -suppress 1346,1236 -quiet -work $lib_name +incdir+$util_part_path/source/rtl/can_controller/"

echo "\n\n\n=== Compiling $lib_name source\n"

eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/timescale.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_defines.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_ibo.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_crc.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_register.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_register_asyn.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_register_asyn_syn.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_register_syn.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_acf.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_bsp.sv
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_btl.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_fifo.v
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_registers.sv
eval vlog  $compdirectives_vlog   $util_part_path/source/rtl/can_controller/can_top.v
eval vcom  $compdirectives_vhdl   $util_part_path/source/rtl/can_controller/can_register_pkg.vhd
