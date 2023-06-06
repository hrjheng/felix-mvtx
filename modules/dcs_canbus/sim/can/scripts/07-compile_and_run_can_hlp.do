quietly set CI_COMP 0
quietly set CI_SIM 0
if { [info exists 1] } {
  if {[string compare $1 "--ci"] == 0 } {
    quietly set CI_COMP 1
  } elseif {[string compare $1 "--ci_sim"] == 0 } {
    quietly set CI_SIM 1
  }
}

if { $CI_COMP == 1 } {
  onerror { quit -force -code 1 }
  onElabError { quit -force -code 1 }
}

set vivado_libs $::env(SIMLIB_MODELSIM_PATH)
quietly set XILINX_LIBS {
                        unisim
                        xpm
                        }

quietly set LIBS ""
foreach lib $XILINX_LIBS {
    append LIBS " -L " $lib
    vmap $lib $vivado_libs/$lib
    }

if { $CI_SIM == 0 } {
  echo "\n\nCompile bitvis uvvm..."
  do 01-compile_bitvis_uvvm.do
  echo "\n\nCompile common sources..."
  do 03-compile_common_src.do
  echo "\n\nCompile Canola CAN controller sources..."
  do 04-compile_can_ctrl_src.do
  echo "\n\nCompile CAN HLP sources..."
  do 05-compile_can_hlp_src.do
  echo "\n\nCompile CAN HLP test bench..."
  do 06-compile_can_hlp_tb.do
}

if { $CI_SIM == 1 } {
    echo "\n\nRun CAN HLP simulation..."
    eval vsim $LIBS -quiet -no_autoacc -nosyncio -novhdlvariablelogging -nolog -nocvg -t 1ps -batch -do \"do ci_do.tcl\" opt_can_hlp_uvvm_tb
} elseif { $CI_COMP == 1 } {
  eval vopt $LIBS -quiet +noacc +nocover -O5 can_hlp_uvvm_tb -o opt_can_hlp_uvvm_tb
  quit
} else {
  echo "\n\nRun CAN HLP simulation..."
  do 00-sim_can_hlp.do
}
