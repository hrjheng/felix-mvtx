set TARGET_DEVICE_CHAIN xcku060_1
set TARGET_DEVICE_SINGLE xcku060_0

if {$argc > 0} {
set TARGET_FW [lindex $argv 0]
} else {
    error "ERROR: Firmware file not provided as argument"
}

set sysdefPaths [glob -nocomplain -- $TARGET_FW]
switch -exact [llength $sysdefPaths] {
    0 {error "ERROR: No files match $TARGET_FW"}
    1 {set TARGET_FW [lindex $sysdefPaths 0]}
    default {error "ERROR: Multiple files match $TARGET_FW: [list $sysdefPaths]"}
}

open_hw
connect_hw_server
open_hw_target
switch -exact [llength [get_hw_devices]] {
    0 {error "ERROR: No devices in chain, is board on?"}
    1 {if {[llength [get_hw_devices ${TARGET_DEVICE_SINGLE}]] == 1} {
           puts "WARNING: JTAG not in chained mode"
           set TARGET_DEVICE ${TARGET_DEVICE_SINGLE}
       } else {
           error "ERROR: Only PA3 in JTAG chain"
       }
    }
    2 {set TARGET_DEVICE ${TARGET_DEVICE_CHAIN}}
    default {error "ERROR: More than 2 devices in chain ?!?"}
}
set_property PROGRAM.FILE $TARGET_FW [lindex [get_hw_devices ${TARGET_DEVICE}] 0]
program_hw_devices [lindex [get_hw_devices ${TARGET_DEVICE}] 0]
refresh_hw_device [lindex [get_hw_devices ${TARGET_DEVICE}] 0]
exit