-------------------------------------------------------------------------------
-- Title      : Power Unit Aux I2C bus package
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_main_pkg.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-04-23
-- Last update: 2019-05-01
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wishbone definitions for Power Unit Main I2C Bus
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-04-23  1.0      jschamba  Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;

package i2c_pu_main_pkg is

  type WB_ADD is (
    A_BYTE01,
    A_TXN_01,
    A_TXN_02,
    A_TXN_03,
    A_TXN_04,
    A_TXN_05,
    A_TXN_06,
    A_TXN_07,
    A_TXN_08,
    A_TXN_09,
    A_TXN_10,
    A_TXN_11,
    A_TXN_12,
    A_TXN_13,
    A_TXN_14,
    A_TXN_15,
    A_TXN_16,
    A_TXN_17,
    A_TXN_18,
    A_TXN_19,
    A_TXN_20,
    A_TXN_21,
    A_TXN_22,
    A_TXN_23,
    A_TXN_24,
    A_TXN_25,
    A_TXN_26,
    A_TXN_27,
    A_TXN_28,
    A_TXN_29,
    A_TXN_30,
    A_TXN_31,
    A_DATA_EMPTY,
    A_DATA
    );

  constant NR_REGS : natural := WB_ADD'pos(WB_ADD'high)+1;

  -- Read/Write enable array
  constant C_WB_ADD_WE : t_wbs_reg_we_array(NR_REGS-1 downto 0) := (
    WB_ADD'pos(A_BYTE01)     => rw,
    WB_ADD'pos(A_DATA_EMPTY) => r,
    WB_ADD'pos(A_DATA)       => r,
    others                   => w
    );

end package i2c_pu_main_pkg;
