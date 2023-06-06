-------------------------------------------------------------------------------
-- Title      : Power Unit Controller wishbone package
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_controller_pkg.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-05-02
-- Last update: 2019-08-02
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Package with wishbone definitions for the powerunit controller
--              wishbone module
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-05-02  1.0      jschamba  Created
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;

package i2c_pu_controller_pkg is


  -- number of ADCs to monitor
  constant C_MAX_ADC_CHANNELS : natural := 35;

  type WB_ADD is (
    A_LIMIT_TEMP0,
    A_LIMIT_TEMP1,
    A_LIMIT_TEMP2,
    A_TEMP0,
    A_TEMP1,
    A_TEMP2,
    A_FIFO_RST,
    A_TRIPPED,
    A_ENABLE_PWR,
    A_ENABLE_BIAS,
    A_ENABLE_MASK,
    A_TEMP_INTERLOCK_ENABLE,
    A_PWR_INTERLOCK_ENABLE,
    A_LO_LIMIT_TEMP0,
    A_LO_LIMIT_TEMP1,
    A_LO_LIMIT_TEMP2,
    A_ADC_00
    );

  constant NR_REGS : natural := WB_ADD'pos(WB_ADD'high) + C_MAX_ADC_CHANNELS;

  -- Read/Write enable array
  constant C_WB_ADD_WE : t_wbs_reg_we_array(NR_REGS-1 downto 0) := (
    WB_ADD'pos(A_LIMIT_TEMP0)           => rw,
    WB_ADD'pos(A_LIMIT_TEMP1)           => rw,
    WB_ADD'pos(A_LIMIT_TEMP2)           => rw,
    WB_ADD'pos(A_LO_LIMIT_TEMP0)        => rw,
    WB_ADD'pos(A_LO_LIMIT_TEMP1)        => rw,
    WB_ADD'pos(A_LO_LIMIT_TEMP2)        => rw,
    WB_ADD'pos(A_ENABLE_MASK)           => rw,
    WB_ADD'pos(A_TEMP_INTERLOCK_ENABLE) => rw,
    WB_ADD'pos(A_PWR_INTERLOCK_ENABLE)  => rw,
    WB_ADD'pos(A_FIFO_RST)              => w,
    others                              => r
    );

  constant C_TURNOFF1_4_bit  : integer := 0;
  constant C_TURNOFF5_8_bit  : integer := 1;
  constant C_OVERTEMP_P0_bit : integer := 2;
  constant C_OVERTEMP_P1_bit : integer := 3;
  constant C_OVERTEMP_P2_bit : integer := 4;
  constant C_TRIPPED_bit     : integer := 5;

  -- Mask for one power unit handles 8 modules,
  -- with 8 digital and 8 analog voltages
  constant C_MODULE_NUMBER : integer := 8;

  -- bits for enabling the monitoring
  constant C_INTERLOCK_ENABLE_P0  : integer := 0;
  constant C_INTERLOCK_ENABLE_P1  : integer := 1;
  constant C_INTERLOCK_ENABLE_P2  : integer := 2;
  constant C_INTERLOCK_ENABLE_PWR : integer := 3;

  constant C_TEMP_LO_LIMIT    : std_logic_vector := x"45de";  -- 15deg, 3.4 Ohm
  constant C_TEMP_HI_LIMIT    : std_logic_vector := x"4894";  -- 26deg, 3.4 Ohm
  constant C_TEMP_HI_LIMIT_PB : std_logic_vector := x"4668";  -- 26deg
  constant C_TEMP_LO_LIMIT_PB : std_logic_vector := x"43b2";  -- 15deg
  
end package i2c_pu_controller_pkg;
