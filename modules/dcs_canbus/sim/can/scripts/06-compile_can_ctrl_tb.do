# Compile sources for CAN HLP module

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

quietly set compdirectives_vlog "-quiet -nologo -nostats -O5 -mixedsvvh s -93 -suppress 1346,1236 -work $lib_name +incdir+$util_part_path/source/bench/can_controller/ +incdir+$util_part_path/source/rtl/can_controller/"

echo "\n\n\n=== Compiling $lib_name source\n"

eval vcom  $compdirectives_vhdl   $util_part_path/source/bench/can_controller/can_wb_uvvm_tb.vhd
