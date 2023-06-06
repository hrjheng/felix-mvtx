-------------------------------------------------------------------------------
-- Title      : CAN HLP Wishbone Slave Registers
-- Project    : ITS RU FPGA
-------------------------------------------------------------------------------
-- File       : can_hlp_wb_slave_regs.vhd
-- Author     : Simon Voigt Nesbø
-- Company    : Western Norway University of Applied Sciences
-- Created    : 2018-04-11
-- Last update: 2020-10-04
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wishbone slave for CAN and HLP registers.
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-04-11  1.0      SVN     Created
-- 2019-01-15  1.1      AV      Changed to ws_reg
-- 2020-02-12  2.0      SVN     Updated for new version of CAN HLP
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;

-- Wishbone interface package
use work.intercon_pkg.all;
use work.canola_pkg.all;
use work.can_hlp_pkg.all;
use work.can_hlp_wishbone_pkg.all;

entity can_hlp_wb_slave_regs is
  port (
    -- Wishbone interface
    WB_CLK   : in  std_logic;           -- Wishbone clock
    WB_RST   : in  std_logic;           -- Wishbone reset
    WB_WBS_I : in  wbs_i_type;          -- Wishbone slave input signals
    WB_WBS_O : out wbs_o_type;          -- Wishbone slave output signals

    -- Control register signals
    CTRL_TRIPLE_SAMPLING_EN : out std_logic;
    CTRL_RETRANSMIT_EN      : out std_logic;
    CTRL_TEST_MODE_EN       : out std_logic;

    -- CAN configuration settings for bit timing and baud rate
    CAN_PROP_SEG   : out std_logic_vector(C_CAN_PROP_SEG_range'range);
    CAN_PHASE_SEG1 : out std_logic_vector(C_CAN_PHASE_SEG1_range'range);
    CAN_PHASE_SEG2 : out std_logic_vector(C_CAN_PHASE_SEG2_range'range);
    CAN_SJW        : out std_logic_vector(C_CAN_SJW_range'range);
    CAN_CLK_SCALE  : out std_logic_vector(C_CAN_CLK_SCALE_range'range);

    -- CAN error state
    CAN_ERROR_ACTIVE  : in std_logic;
    CAN_ERROR_PASSIVE : in std_logic;
    CAN_BUS_OFF       : in std_logic;

    -- CAN Transmit Error Count (TEC) and Receive Error Count (REC)
    -- These are special internal counters in the CAN controller,
    -- and can not go in the monitor module.
    CAN_TEC : in std_logic_vector(C_ERROR_COUNT_LENGTH-1 downto 0);
    CAN_REC : in std_logic_vector(C_ERROR_COUNT_LENGTH-1 downto 0);

    -- Wishbone register outputs, and voted input
    WISHBONE_REGS_I : in  t_can_hlp_wb_regs;
    WISHBONE_REGS_O : out t_can_hlp_wb_regs);

end can_hlp_wb_slave_regs;

architecture rtl of can_hlp_wb_slave_regs is

  -- wishbone signal for reading
  signal s_wbs_reg_i    : t_wbs_reg_array(NR_REGS-1 downto 0);  -- Read registers
  signal s_wbs_reg_o    : t_wbs_reg_array(NR_REGS-1 downto 0);  -- Write registers
  signal s_wbs_wr_pulse : std_logic_vector(NR_REGS-1 downto 0);
  constant c_ack        : std_logic_vector(WB_ADD'pos(WB_ADD'high) downto 0) := (others => '0');

begin

  -----------------------------------------------------------------------------
  -- Read and write registers to be passed to the wishbone register module
  -----------------------------------------------------------------------------
  p_wishbone_data : process (all) is
  begin  -- process p_wishbone_data
    s_wbs_reg_i <= (others => x"0000");  -- initialize all bits to 0

    -- Read
    s_wbs_reg_i(WB_ADD'pos(A_STATUS))(C_STATUS_ERROR_ACTIVE_bit)  <= CAN_ERROR_ACTIVE;
    s_wbs_reg_i(WB_ADD'pos(A_STATUS))(C_STATUS_ERROR_PASSIVE_bit) <= CAN_ERROR_PASSIVE;
    s_wbs_reg_i(WB_ADD'pos(A_STATUS))(C_STATUS_BUS_OFF_bit)       <= CAN_BUS_OFF;
    s_wbs_reg_i(WB_ADD'pos(A_CAN_TEC))                            <= wb_resize(CAN_TEC);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_REC))                            <= wb_resize(CAN_REC);

    -- Write
    WISHBONE_REGS_O.CTRL           <= s_wbs_reg_o(WB_ADD'pos(A_CTRL))(C_CTRL_range'range);
    WISHBONE_REGS_O.CAN_PROP_SEG   <= s_wbs_reg_o(WB_ADD'pos(A_CAN_PROP_SEG))(C_CAN_PROP_SEG_range'range);
    WISHBONE_REGS_O.CAN_PHASE_SEG1 <= s_wbs_reg_o(WB_ADD'pos(A_CAN_PHASE_SEG1))(C_CAN_PHASE_SEG1_range'range);
    WISHBONE_REGS_O.CAN_PHASE_SEG2 <= s_wbs_reg_o(WB_ADD'pos(A_CAN_PHASE_SEG2))(C_CAN_PHASE_SEG2_range'range);
    WISHBONE_REGS_O.CAN_SJW        <= s_wbs_reg_o(WB_ADD'pos(A_CAN_SJW))(C_CAN_SJW_range'range);
    WISHBONE_REGS_O.CAN_CLK_SCALE  <= s_wbs_reg_o(WB_ADD'pos(A_CAN_CLK_SCALE))(C_CAN_CLK_SCALE_range'range);
    WISHBONE_REGS_O.TEST_REG       <= s_wbs_reg_o(WB_ADD'pos(A_TEST_REG))(C_TEST_REG_range'range);

    -- Write feedback
    s_wbs_reg_i(WB_ADD'pos(A_CTRL))           <= wb_resize(WISHBONE_REGS_O.CTRL);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_PROP_SEG))   <= wb_resize(WISHBONE_REGS_O.CAN_PROP_SEG);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_PHASE_SEG1)) <= wb_resize(WISHBONE_REGS_O.CAN_PHASE_SEG1);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_PHASE_SEG2)) <= wb_resize(WISHBONE_REGS_O.CAN_PHASE_SEG2);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_SJW))        <= wb_resize(WISHBONE_REGS_O.CAN_SJW);
    s_wbs_reg_i(WB_ADD'pos(A_CAN_CLK_SCALE))  <= wb_resize(WISHBONE_REGS_O.CAN_CLK_SCALE);
    s_wbs_reg_i(WB_ADD'pos(A_TEST_REG))       <= wb_resize(WISHBONE_REGS_O.TEST_REG);

    -- Pulse on write
    -- OUTPUT_NAME <= s_wbs_wr_pulse(WB_ADD'pos(A_REGNAME));
  end process p_wishbone_data;

  -----------------------------------------------------------------------------
  -- Wishbone register handling
  -----------------------------------------------------------------------------
  INST_wishbone_slave_register : entity work.ws_reg
    generic map (
      WB_ADD_WE      => C_WB_ADD_WE,
      WB_ILLEGAL_VAL => x"DEAD",
      WB_REG_INIT    => C_WISHBONE_DEFAULT,
      REG_WB_INPUT   => false,
      WB_EXT_ACK_EN  => c_ack)
    port map(
      WB_CLK    => WB_CLK,
      WB_RST    => WB_RST,
      WB_WBS_I  => WB_WBS_I,
      WB_WBS_O  => WB_WBS_O,
      WBS_REG_I => s_wbs_reg_i,
      WBS_REG_O => s_wbs_reg_o,
      WBS_RD_PULSE_O => open,
      WBS_WR_PULSE_O => s_wbs_wr_pulse,
      WBS_EXT_ACK_I  => c_ack);

end architecture rtl;
