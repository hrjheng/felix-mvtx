-------------------------------------------------------------------------------
-- Title      : I2C Power Unit Wishbone slave AUX bus
-- Project    : ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_aux_wb.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-04-16
-- Last update: 2019-09-25
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Connect the wishbone slave registers to the PU I2C wrapper
--              for the AUX I2C bus
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-04-16  1.0      jschamba  Created
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;
use work.i2c_pkg.all;
use work.i2c_pu_aux_pkg.all;

entity i2c_pu_aux_wb is
  port (
    -- Wishbone interface signals
    WB_CLK           : in  std_logic;   -- master clock input
    WB_RST           : in  std_logic;   -- synchronous active high reset
    WB_WBS_I         : in  wbs_i_type;  -- Wishbone Inputs
    WB_WBS_O         : out wbs_o_type;  -- Wishbone Outputs
    -- debug output pulses
    -- interface data
    REQ_DATA_o       : out std_logic_vector(36 downto 0);  -- I2C request data
    REQ_WREN_o       : out std_logic;   -- I2C request write enable
    I2C_DATA_i       : in  std_logic_vector(15 downto 0);
    I2C_TXN_ID_i     : in  std_logic_vector(WB_DATA_WIDTH-2 downto 0);
    I2C_DATA_RDEN_o  : out std_logic;
    I2C_DATA_EMPTY_i : in  std_logic
    );
end entity i2c_pu_aux_wb;

architecture structural of i2c_pu_aux_wb is

  signal s_start    : std_logic;
  signal s_byte0    : std_logic_vector(7 downto 0);
  signal s_byte1    : std_logic_vector(7 downto 0);
  signal s_byte2    : std_logic_vector(7 downto 0);
  signal s_byte3    : std_logic_vector(7 downto 0);
  signal s_i2c_data : std_logic_vector(15 downto 0);
  signal s_address  : std_logic_vector(4 downto 0);

  signal s_wbs_reg_i    : t_wbs_reg_array(NR_REGS-1 downto 0);
  signal s_wbs_reg_o    : t_wbs_reg_array(NR_REGS-1 downto 0);
  signal s_wbs_wr_pulse : std_logic_vector(NR_REGS-1 downto 0);
  signal s_wbs_rd_pulse : std_logic_vector(NR_REGS-1 downto 0);

  signal WB_WBS_I_addr_i_int : natural range 0 to 2**WB_WBS_I.addr_i'length-1;  -- WB_WBS_I.addr_i converted to int

  constant C_DEFAULT_REGS : t_wbs_reg_array(NR_REGS-1 downto 0) := (others => x"0000");

  constant c_ack : std_logic_vector(WB_ADD'pos(WB_ADD'high) downto 0) := (others => '0');

begin

  WB_WBS_I_addr_i_int <= to_integer(unsigned(WB_WBS_I.addr_i));

  p_wishbone_data : process (all) is
    variable v_pulse : std_logic := '0';
  begin  -- process p_wishbone_data
    s_wbs_reg_i <= (others => x"0000");  -- initialize to 0

    -- Read
    s_wbs_reg_i(WB_ADD'pos(A_DATA_EMPTY)) <= I2C_DATA_EMPTY_i & I2C_TXN_ID_i;
    s_wbs_reg_i(WB_ADD'pos(A_DATA))       <= I2C_DATA_i;

    -- Write
    REQ_DATA_o(15 downto 0) <= s_wbs_reg_o(WB_ADD'pos(A_BYTE01));  -- Byte0 & Byte1


    -- Write feedback
    s_wbs_reg_i(WB_ADD'pos(A_BYTE01)) <= s_wbs_reg_o(WB_ADD'pos(A_BYTE01));

    -- start pulse on write to I2C transaction registers
    v_pulse    := or_reduce(s_wbs_wr_pulse(WB_ADD'pos(A_DATA_EMPTY)-1 downto WB_ADD'pos(A_TXN_01)));
    REQ_WREN_o <= v_pulse;

    -- Byte2/3 directly from wishbone input write
    if v_pulse = '1' then
      REQ_DATA_o(31 downto 16) <= s_wbs_reg_o(WB_WBS_I_addr_i_int);  -- Byte2 & Byte3
    else
      REQ_DATA_o(31 downto 16) <= (others => '0');
    end if;

    -- I2C wrapper address directly from wishbone input
    REQ_DATA_o(36 downto 32) <= WB_WBS_I.addr_i(4 downto 0);

    I2C_DATA_RDEN_o <= s_wbs_rd_pulse(WB_ADD'pos(A_DATA));

  end process p_wishbone_data;

  INST_ws_reg : entity work.ws_reg
    generic map (
      WB_ADD_WE      => C_WB_ADD_WE,
      WB_ILLEGAL_VAL => x"DEAD",
      WB_REG_INIT    => C_DEFAULT_REGS,
      WB_EXT_ACK_EN  => c_ack
      )
    port map (
      WB_CLK         => WB_CLK,
      WB_RST         => WB_RST,
      WB_WBS_I       => WB_WBS_I,
      WB_WBS_O       => WB_WBS_O,
      WBS_REG_I      => s_wbs_reg_i,
      WBS_REG_O      => s_wbs_reg_o,
      WBS_RD_PULSE_O => s_wbs_rd_pulse,
      WBS_WR_PULSE_O => s_wbs_wr_pulse,
      WBS_EXT_ACK_I  => c_ack
      );

end architecture structural;
