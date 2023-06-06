-- $Id$
-------------------------------------------------------------------------------
-- Title      : I2C Interface - Common definitions
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pkg.vhd
-- Author     : J. Schambach
-- Company    : University of Texas at Austin
-- Created    : 2017-03-03
-- Last update: 2019-02-11
-- Platform   : Xilinx Vivado 2016.4
-- Target     : Kintex-7
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Constants used in I2C module
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;

package i2c_pkg is

  -- number of I2C busses in project
  constant C_NUM_I2C : natural := 2;

  constant C_FREQ_SELECTION_BIT_WIDTH : integer := 16;

  -- status bit indices
  constant I2C_STAT_AL       : natural := 0;  -- arbitration lost
  constant I2C_STAT_TIP      : natural := 1;  -- transfer in progress
  constant I2C_STAT_I2C_BUSY : natural := 2;  -- i2c busy
  constant I2C_STAT_RXACK    : natural := 3;  -- ACK received

  -- command bits
  constant I2C_CMD_START : std_logic_vector := "10000";
  constant I2C_CMD_STOP  : std_logic_vector := "01000";
  constant I2C_CMD_READ  : std_logic_vector := "00100";
  constant I2C_CMD_WRITE : std_logic_vector := "00010";
  constant I2C_CMD_ACK   : std_logic_vector := "00001";

end package i2c_pkg;
