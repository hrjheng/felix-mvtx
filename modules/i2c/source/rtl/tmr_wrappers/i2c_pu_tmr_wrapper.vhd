-------------------------------------------------------------------------------
-- Title      : i2c_gbt_tmr_wrapper
-- Project    : RUv1
-------------------------------------------------------------------------------
-- File       : i2c_gbt_tmr_wrapper.vhd
-- Author     : Matteo Lupi <matteo.lupi@cern.ch>
-- Company    : CERN European Organization for Nuclear Research
-- Company    : Goethe Universitaet Frankfurt am Main
-- Author     : Joachim Schambach (jschamba@physics.utexas.edu)
-- Company    : University of Texas at Austin
-- Created    : 2017-09-01
-- Last update: 2019-07-03
-- Platform   : Xilinx Vivado 2018.3
-- Target     : Kintex US
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: TMR wrapper for the i2c_gbt_wrapper
--              It handles the triplication of the wishbone bus
-------------------------------------------------------------------------------
-- Copyright (c) 2017 CERN European Organization for Nuclear Research
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Wishbone interface package
library work;
use work.intercon_pkg.all;
use work.i2c_pkg.all;
use work.tmr_pkg.all;

entity i2c_pu_tmr_wrapper is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 1
    );
  port (
    WB_CLK                 : in  std_logic;
    WB_RST                 : in  std_logic;
    WB_WBS_PU_MAIN_I       : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_PU_MAIN_O       : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_PU_AUX_I        : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_PU_AUX_O        : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_PU_CTRL_I       : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_PU_CTRL_O       : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_MAIN_I  : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_MAIN_O  : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_AUX_I   : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_AUX_O   : out t_wbs_o_array(0 to C_K_TMR-1);
    IS_MIDDLE_BARREL       : in  std_logic;
    SCL_PAD_i              : in  std_logic;
    SCL_PAD_o              : out std_logic;
    SCL_PAD_T              : out std_logic;
    SDA_PAD_i              : in  std_logic;
    SDA_PAD_o              : out std_logic;
    SDA_PAD_T              : out std_logic;
    SCL_AUX_PAD_i          : in  std_logic;
    SCL_AUX_PAD_o          : out std_logic;
    SCL_AUX_PAD_T          : out std_logic;
    SDA_AUX_PAD_i          : in  std_logic;
    SDA_AUX_PAD_o          : out std_logic;
    SDA_AUX_PAD_T          : out std_logic
    );
end i2c_pu_tmr_wrapper;

architecture str of i2c_pu_tmr_wrapper is

  -- withbone slave interface
  signal s_wb_wbs_main_i : wbs_i_type;
  signal s_wb_wbs_main_o : wbs_o_type;

  signal s_wb_wbs_aux_i : wbs_i_type;
  signal s_wb_wbs_aux_o : wbs_o_type;

  signal s_wb_wbs_ctrl_i : wbs_i_type;
  signal s_wb_wbs_ctrl_o : wbs_o_type;

  signal sCompletedByte_main : std_logic;
  signal sAlError_main       : std_logic;
  signal sNoAckError_main    : std_logic;

  signal sCompletedByte_aux : std_logic;
  signal sAlError_aux       : std_logic;
  signal sNoAckError_aux    : std_logic;

  signal sReqFifoOvf_main : std_logic;
  signal sResFifoOvf_main : std_logic;
  signal sResFifoUfl_main : std_logic;
  signal sReqFifoOvf_aux  : std_logic;
  signal sResFifoOvf_aux  : std_logic;
  signal sResFifoUfl_aux  : std_logic;

begin  -- architecture str

  INST_i2c_pu_controller : entity work.i2c_pu_controller
    port map (
      WB_CLK                 => WB_CLK,
      WB_RST                 => WB_RST,
      WB_WBS_PU_MAIN_I       => s_wb_wbs_main_i,
      WB_WBS_PU_MAIN_O       => s_wb_wbs_main_o,
      WB_WBS_PU_AUX_I        => s_wb_wbs_aux_i,
      WB_WBS_PU_AUX_O        => s_wb_wbs_aux_o,
      WB_WBS_PU_CTRL_I       => s_wb_wbs_ctrl_i,
      WB_WBS_PU_CTRL_O       => s_wb_wbs_ctrl_o,
      IS_MIDDLE_BARREL       => IS_MIDDLE_BARREL,
      PU_MAIN_COMPLETED_BYTE => sCompletedByte_main,
      PU_MAIN_AL_ERROR       => sAlError_main,
      PU_MAIN_NOACK_ERROR    => sNoAckError_main,
      PU_AUX_COMPLETED_BYTE  => sCompletedByte_aux,
      PU_AUX_AL_ERROR        => sAlError_aux,
      PU_AUX_NOACK_ERROR     => sNoAckError_aux,
      REQ_FIFO_MAIN_OVF      => sReqFifoOvf_main,
      RES_FIFO_MAIN_OVF      => sResFifoOvf_main,
      RES_FIFO_MAIN_UFL      => sResFifoUfl_main,
      REQ_FIFO_AUX_OVF       => sReqFifoOvf_aux,
      RES_FIFO_AUX_OVF       => sResFifoOvf_aux,
      RES_FIFO_AUX_UFL       => sResFifoUfl_aux,
      SCL_PAD_i              => SCL_PAD_i,
      SCL_PAD_o              => SCL_PAD_o,
      SCL_PAD_T              => SCL_PAD_T,
      SDA_PAD_i              => SDA_PAD_i,
      SDA_PAD_o              => SDA_PAD_o,
      SDA_PAD_T              => SDA_PAD_T,
      SCL_AUX_PAD_i          => SCL_AUX_PAD_i,
      SCL_AUX_PAD_o          => SCL_AUX_PAD_o,
      SCL_AUX_PAD_T          => SCL_AUX_PAD_T,
      SDA_AUX_PAD_i          => SDA_AUX_PAD_i,
      SDA_AUX_PAD_o          => SDA_AUX_PAD_o,
      SDA_AUX_PAD_T          => SDA_AUX_PAD_T
      );

  -- Error Monitors:
  INST_i2c_monitor_pu_main : entity work.i2c_monitor_pu
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
      )
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_I2C_MON_MAIN_I,
      WB_WBS_O         => WB_WBS_I2C_MON_MAIN_O,
      COMPLETED_BYTE_i => sCompletedByte_main,
      AL_ERROR_i       => sAlError_main,
      NOACK_ERROR_i    => sNoAckError_main,
      REQ_FIFO_OVF_i   => sReqFifoOvf_main,
      RES_FIFO_OVF_i   => sResFifoOvf_main,
      RES_FIFO_UFL_i   => sResFifoUfl_main,
      MISMATCH         => open,
      MISMATCH_2ND     => open
      );

  INST_i2c_monitor_pu_aux : entity work.i2c_monitor_pu
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
      )
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_I2C_MON_AUX_I,
      WB_WBS_O         => WB_WBS_I2C_MON_AUX_O,
      COMPLETED_BYTE_i => sCompletedByte_aux,
      AL_ERROR_i       => sAlError_aux,
      NOACK_ERROR_i    => sNoAckError_aux,
      REQ_FIFO_OVF_i   => sReqFifoOvf_aux,
      RES_FIFO_OVF_i   => sResFifoOvf_aux,
      RES_FIFO_UFL_i   => sResFifoUfl_aux,
      MISMATCH         => open,
      MISMATCH_2ND     => open
      );

  -- implementation with array of WBS inputs
  INST_majority_voter_wbs_main_i : entity work.majority_voter_wbs_i
    generic map (
      --MISMATCH_EN           => MISMATCH_EN, -- temporary, remove after slave is protected
      MISMATCH_EN           => 0,
      G_ADDITIONAL_MISMATCH => 0)
    port map (
      ASSERTION_CLK => WB_CLK,
      ASSERTION_RST => WB_RST,
      INPUT         => WB_WBS_PU_MAIN_I,
      OUTPUT        => s_wb_wbs_main_i,
      MISMATCH      => open,
      MISMATCH_2ND  => open);

  WB_WBS_PU_MAIN_O(0) <= s_wb_wbs_main_o;
  WB_WBS_PU_MAIN_O(1) <= s_wb_wbs_main_o;
  WB_WBS_PU_MAIN_O(2) <= s_wb_wbs_main_o;

  INST_majority_voter_wbs_aux_i : entity work.majority_voter_wbs_i
    generic map (
      --MISMATCH_EN           => MISMATCH_EN, -- temporary, remove after slave is protected
      MISMATCH_EN           => 0,
      G_ADDITIONAL_MISMATCH => 0)
    port map (
      ASSERTION_CLK => WB_CLK,
      ASSERTION_RST => WB_RST,
      INPUT         => WB_WBS_PU_AUX_I,
      OUTPUT        => s_wb_wbs_aux_i,
      MISMATCH      => open,
      MISMATCH_2ND  => open);

  WB_WBS_PU_AUX_O(0) <= s_wb_wbs_aux_o;
  WB_WBS_PU_AUX_O(1) <= s_wb_wbs_aux_o;
  WB_WBS_PU_AUX_O(2) <= s_wb_wbs_aux_o;

  INST_majority_voter_wbs_ctrl_i : entity work.majority_voter_wbs_i
    generic map (
      --MISMATCH_EN           => MISMATCH_EN, -- temporary, remove after slave is protected
      MISMATCH_EN           => 0,
      G_ADDITIONAL_MISMATCH => 0)
    port map (
      ASSERTION_CLK => WB_CLK,
      ASSERTION_RST => WB_RST,
      INPUT         => WB_WBS_PU_CTRL_I,
      OUTPUT        => s_wb_wbs_ctrl_i,
      MISMATCH      => open,
      MISMATCH_2ND  => open);

  WB_WBS_PU_CTRL_O(0) <= s_wb_wbs_ctrl_o;
  WB_WBS_PU_CTRL_O(1) <= s_wb_wbs_ctrl_o;
  WB_WBS_PU_CTRL_O(2) <= s_wb_wbs_ctrl_o;

end architecture str;
