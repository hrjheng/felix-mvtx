-------------------------------------------------------------------------------
-- Title      : i2c_gbt_tmr_wrapper
-- Project    : RUv1
-------------------------------------------------------------------------------
-- File       : i2c_gbt_tmr_wrapper.vhd
-- Author     : Matteo Lupi <matteo.lupi@cern.ch>
-- Company    : CERN European Organization for Nuclear Research
-- Company    : Goethe Universitaet Frankfurt am Main
-- Created    : 2017-09-01
-- Last update: 2019-06-07
-- Platform   : Xilinx Vivado 2016.4
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

entity i2c_gbt_tmr_wrapper is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 1
    );
  port (
    WB_CLK           : in  std_logic;
    WB_RST           : in  std_logic;
    WB_WBS_I         : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_O         : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_I : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_I2C_MON_O : out t_wbs_o_array(0 to C_K_TMR-1);
    SCL_PAD_i        : in  std_logic;
    SCL_PAD_o        : out std_logic;
    SCL_PAD_T        : out std_logic;
    SDA_PAD_i        : in  std_logic;
    SDA_PAD_o        : out std_logic;
    SDA_PAD_T        : out std_logic);
end;

architecture str of i2c_gbt_tmr_wrapper is

  -- withbone slave interface
  signal s_wb_wbs_i : wbs_i_type;
  signal s_wb_wbs_o : wbs_o_type;

  signal sCompletedByte : std_logic;
  signal sAlError       : std_logic;
  signal sNoAckError    : std_logic;
  
begin  -- architecture str

  INST_i2c_gbt_wrapper : entity work.i2c_gbt_wrapper
    port map (
      WB_CLK         => WB_CLK,
      WB_RST         => WB_RST,
      WB_WBS_I       => s_wb_wbs_i,
      WB_WBS_O       => s_wb_wbs_o,
      COMPLETED_BYTE => sCompletedByte,
      AL_ERROR       => sAlError,
      NOACK_ERROR    => sNoAckError,
      SCL_PAD_i      => SCL_PAD_i,
      SCL_PAD_o      => SCL_PAD_o,
      SCL_PAD_T      => SCL_PAD_T,
      SDA_PAD_i      => SDA_PAD_i,
      SDA_PAD_o      => SDA_PAD_o,
      SDA_PAD_T      => SDA_PAD_T
      );

  -- I2C monitor module
  INST_i2c_monitor_gbtx : entity work.i2c_monitor_gbtx
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
      )
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_I2C_MON_I,
      WB_WBS_O         => WB_WBS_I2C_MON_O,
      COMPLETED_BYTE_i => sCompletedByte,
      AL_ERROR_i       => sAlError,
      NOACK_ERROR_i    => sNoAckError,
      MISMATCH         => open,
      MISMATCH_2ND     => open
      );

  -- implementation with array of WBS inputs
  INST_majority_voter_wbs_i : entity work.majority_voter_wbs_i
    generic map (
      --MISMATCH_EN           => MISMATCH_EN, -- temporary, remove after slave is protected
      MISMATCH_EN           => 0,
      G_ADDITIONAL_MISMATCH => 0)
    port map (
      ASSERTION_CLK => WB_CLK,
      ASSERTION_RST => WB_RST,
      INPUT         => WB_WBS_I,
      OUTPUT        => s_wb_wbs_i,
      MISMATCH      => open,
      MISMATCH_2ND  => open);

  WB_WBS_O(0) <= s_wb_wbs_o;
  WB_WBS_O(1) <= s_wb_wbs_o;
  WB_WBS_O(2) <= s_wb_wbs_o;

end architecture str;
