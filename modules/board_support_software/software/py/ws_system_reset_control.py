"""file implementing the control for the ws_identity wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule

class WsSystemResetControlAddress(IntEnum):
    """memory mapping for the ws_system_reset_control got from system_reset_control_wishbone_pkg.vhd"""
    RESET_SWT_WB                      = 0x00
    RESET_CAN_WB                      = 0x01
    RESET_WB_INTERCON                 = 0x02
    RESET_WB_SLAVES                   = 0x03
    RESET_PU_1                        = 0x04
    RESET_PU_2                        = 0x05
    RESET_I2C_GBT                     = 0x06
    RESET_DATAPATH                    = 0x07
    RESET_READOUT_MASTER              = 0x08
    RESET_GBT_PACKER                  = 0x09
    RESET_TRIGGER_HANDLER             = 0x0A
    RESET_GBTX_CONTROLLER             = 0x0B
    RESET_GBTX_CONTROLLER_INPUT_STAGE = 0x0C
    RESET_PA3_FIFO                    = 0x0D
    RESET_ALPIDE_CONTROL              = 0x0E
    RESET_ALL_EXCEPT_STAVE_POWER      = 0x0F

class WsSystemResetControl(WishboneModule):
    """wishbone slave used to identify the firmware and the FPGA"""

    def __init__(self, moduleid, board_obj):
        """init"""
        super(WsSystemResetControl, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                       name="Wishbone System Reset")

    def reset_swt_wb(self, commitTransaction=True):
        """Reset SWT WB modules
        
        - SWT Wishbone master
        - SWT FIFOs"""
        self.write(WsSystemResetControlAddress.RESET_SWT_WB, 0x1, commitTransaction=commitTransaction)

    def reset_can_wb(self, commitTransaction=True):
        """Reset CAN WB modules
        
        - CAN Wishbone master
        - CAN HLP"""
        self.write(WsSystemResetControlAddress.RESET_CAN_WB, 0x1, commitTransaction=commitTransaction)

    def reset_wb_intercon(self, commitTransaction=True):
        """Reset WB intercon"""
        self.write(WsSystemResetControlAddress.RESET_WB_INTERCON, 0x1, commitTransaction=commitTransaction)

    def reset_wb_slaves(self, commitTransaction=True):
        """Reset WB base modules modules
        
        - Wishbone wait
        - Radiation Monitor
        - SYSMON
        - Identity
        - Clock health status
        - USB WB blocks"""
        self.write(WsSystemResetControlAddress.RESET_WB_SLAVES, 0x1, commitTransaction=commitTransaction)

    def reset_pu_1(self, commitTransaction=True):
        """Resets PU Controller 1"""
        self.write(WsSystemResetControlAddress.RESET_PU_1, 0x1, commitTransaction=commitTransaction)

    def reset_pu_2(self, commitTransaction=True):
        """Resets PU Controller 2"""
        self.write(WsSystemResetControlAddress.RESET_PU_2, 0x1, commitTransaction=commitTransaction)

    def reset_i2c_gbt_wrapper(self, commitTransaction=True):
        """Resets I2C-GBT wrapper"""
        self.write(WsSystemResetControlAddress.RESET_I2C_GBT, 0x1, commitTransaction=commitTransaction)

    def reset_datapath(self, commitTransaction=True):
        """Resets all datapath modules. 
        
        - datapath_ib
        - datapath_ib_mon
        - datapath_ob
        - datapath_ob_mon
        - calibration_lane
        - ib_lanes
        - ob_lanes
        - datapath_ob_idelay"""
        self.write(WsSystemResetControlAddress.RESET_DATAPATH, 0x1, commitTransaction=commitTransaction)

    def reset_readout_master(self, commitTransaction=True):
        """Resets the Readout Master"""
        self.write(WsSystemResetControlAddress.RESET_READOUT_MASTER, 0x1, commitTransaction=commitTransaction)

    def reset_gbt_packers(self, commitTransaction=True):
        """Resets the GBT Packers"""
        self.write(WsSystemResetControlAddress.RESET_GBT_PACKER, 0x1, commitTransaction=commitTransaction)

    def reset_trigger_handler(self, commitTransaction=True):
        """Resets the Trigger Handler"""
        self.write(WsSystemResetControlAddress.RESET_TRIGGER_HANDLER, 0x1, commitTransaction=commitTransaction)

    def reset_gbtx_controller(self, commitTransaction=True):
        """Resets the GBTx controller, except the input stage macros"""
        self.write(WsSystemResetControlAddress.RESET_GBTX_CONTROLLER, 0x1, commitTransaction=commitTransaction)

    def reset_gbtx_controller_input_stage(self, commitTransaction=True):
        """Resets the GBTx controller input stage macros"""
        self.write(WsSystemResetControlAddress.RESET_GBTX_CONTROLLER_INPUT_STAGE, 0x1, commitTransaction=commitTransaction)

    def reset_pa3_fifo(self, commitTransaction=True):
        """Resets the PA3 FIFO"""
        self.write(WsSystemResetControlAddress.RESET_PA3_FIFO, 0x1, commitTransaction=commitTransaction)

    def reset_alpide_control(self, commitTransaction=True):
        """Resets the ALPIDE Control"""
        self.write(WsSystemResetControlAddress.RESET_ALPIDE_CONTROL, 0x1, commitTransaction=commitTransaction)

    def reset_all_except_stave_power(self, commitTransaction=True):
        """Resets all modules except the PowerUnit Controller and the ALPIDE Control
        
        Function to safely reset all parts of XCKU without affecting stave power.
        """
        self.write(WsSystemResetControlAddress.RESET_ALL_EXCEPT_STAVE_POWER, 0x1, commitTransaction=commitTransaction)