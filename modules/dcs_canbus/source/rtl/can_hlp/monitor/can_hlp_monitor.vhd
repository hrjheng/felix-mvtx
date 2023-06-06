-------------------------------------------------------------------------------
-- Title      : CAN HLP Monitor
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : can_hlp_monitor.vhd
-- Author     : Simon Voigt Nesbø
-- Company    :
-- Created    : 2020-02-11
-- Last update: 2020-10-04
-- Platform   : Xilinx Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wishbone slave for counters in CAN HLP
-------------------------------------------------------------------------------
-- Copyright (c) 2020
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2020-02-11  1.0      SVN       Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;

library work;

-- Wishbone interface package
use work.intercon_pkg.all;
use work.can_hlp_monitor_pkg.all;
use work.tmr_pkg.all;

entity can_hlp_monitor is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 1);
  port (
    -- Wishbone interface
    WB_CLK         : in  std_logic;
    WB_RST         : in  std_logic;
    WB_WBS_I       : in  t_wbs_i_array(0 to C_K_TMR - 1);
    WB_WBS_O       : out t_wbs_o_array(0 to C_K_TMR - 1);

    -- Count up signals
    HLP_READ_COUNT_UP_I           : in std_logic;
    HLP_WRITE_COUNT_UP_I          : in std_logic;
    HLP_STATUS_COUNT_UP_I         : in std_logic;
    HLP_ALERT_COUNT_UP_I          : in std_logic;
    HLP_UNKNOWN_COUNT_UP_I        : in std_logic;
    HLP_LENGTH_ERROR_COUNT_UP_I   : in std_logic;
    HLP_MSG_DROPPED_COUNT_UP_I    : in std_logic;
    CAN_TX_MSG_SENT_COUNT_UP_I    : in std_logic;
    CAN_TX_ACK_ERROR_COUNT_UP_I   : in std_logic;
    CAN_TX_ARB_LOST_COUNT_UP_I    : in std_logic;
    CAN_TX_BIT_ERROR_COUNT_UP_I   : in std_logic;
    CAN_TX_RETRANSMIT_COUNT_UP_I  : in std_logic;
    CAN_RX_MSG_RECV_COUNT_UP_I    : in std_logic;
    CAN_RX_CRC_ERROR_COUNT_UP_I   : in std_logic;
    CAN_RX_FORM_ERROR_COUNT_UP_I  : in std_logic;
    CAN_RX_STUFF_ERROR_COUNT_UP_I : in std_logic;

    -- Mismatch
    MISMATCH       : out std_logic;
    MISMATCH_2ND   : out std_logic);
  attribute DONT_TOUCH                      : string;
  attribute DONT_TOUCH of can_hlp_monitor : entity is "TRUE";
end can_hlp_monitor;

architecture rtl of can_hlp_monitor is

  signal s_counter_reset    : std_logic_vector(C_NR_REGS-1 downto 0);
  signal s_counter_increase : std_logic_vector(C_NR_COUNTERS-1 downto 0);
  signal s_counter_values   : t_wbs_reg_array(0 to C_NR_REGS-1);

  constant C_MISMATCH_WIDTH : integer := 1 + C_NR_COUNTERS;

  signal mismatch_array          : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
  alias mismatch_counter_monitor : std_ulogic is mismatch_array(0);
  alias mismatch_array_counters  : std_ulogic_vector(C_NR_COUNTERS-1 downto 0) is mismatch_array(C_NR_COUNTERS downto 1);

  signal mismatch_2nd_array          : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
  alias mismatch_2nd_counter_monitor : std_ulogic is mismatch_2nd_array(0);
  alias mismatch_2nd_array_counters  : std_ulogic_vector(C_NR_COUNTERS-1 downto 0) is mismatch_2nd_array(C_NR_COUNTERS downto 1);

  -- for monitor modules concatenation
  constant USE_SLAVE_INPUTS   : boolean := FALSE;
  constant USE_MASTER_OUTPUTS : boolean := FALSE;

begin

  -- Wishbone monitor
  -----------------------------
  INST_ws_counter_monitor_tmr_wrapper : entity work.ws_counter_monitor_tmr_wrapper
    generic map (
      NR_COUNTERS                => C_NR_REGS,
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH,
      USE_MASTER_OUTPUTS         => USE_MASTER_OUTPUTS,
      USE_SLAVE_INPUTS           => USE_SLAVE_INPUTS)
    port map(
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_I,
      WB_WBS_O         => WB_WBS_O,
      counter_reset_o  => s_counter_reset,
      counter_values_i => s_counter_values,
      counter_master_reset_o => open,
      counter_master_latch_o => open,
      counter_slave_reset_i  => (others => '0'),
      counter_slave_latch_i  => (others => '0'),
      MISMATCH         => mismatch_counter_monitor,
      MISMATCH_2ND     => mismatch_2nd_counter_monitor);

  -- Mapping
  -----------------------------

  s_counter_increase(C_CNTR_bit_HLP_READ)           <= HLP_READ_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_WRITE)          <= HLP_WRITE_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_TX_MSG_SENT)    <= CAN_TX_MSG_SENT_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_RX_MSG_RECV)    <= CAN_RX_MSG_RECV_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_STATUS)         <= HLP_STATUS_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_ALERT)          <= HLP_ALERT_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_UNKNOWN)        <= HLP_UNKNOWN_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_LENGTH_ERROR)   <= HLP_LENGTH_ERROR_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_HLP_MSG_DROPPED)    <= HLP_MSG_DROPPED_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_TX_ACK_ERROR)   <= CAN_TX_ACK_ERROR_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_TX_ARB_LOST)    <= CAN_TX_ARB_LOST_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_TX_BIT_ERROR)   <= CAN_TX_BIT_ERROR_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_TX_RETRANSMIT)  <= CAN_TX_RETRANSMIT_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_RX_CRC_ERROR)   <= CAN_RX_CRC_ERROR_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_RX_FORM_ERROR)  <= CAN_RX_FORM_ERROR_COUNT_UP_I;
  s_counter_increase(C_CNTR_bit_CAN_RX_STUFF_ERROR) <= CAN_RX_STUFF_ERROR_COUNT_UP_I;

  -- Counters
  -----------------------------
  for_upcounter_32_generate : for i in 0 to C_NR_32_BIT_COUNTERS-1 generate
    INST_upcounter_WR_OPERATIONS : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => C_CNTR_WIDE_range'length,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
      port map (
        CLK                               => WB_CLK,
        RST                               => WB_RST,
        RST_CNT                           => s_counter_reset(2*i),
        CNT_UP                            => s_counter_increase(i),
        CNT_VALUE(C_CNTR_LSB_range'range) => s_counter_values(2*i),
        CNT_VALUE(C_CNTR_MSB_range'range) => s_counter_values(2*i+1),
        MISMATCH                          => mismatch_array_counters(i),
        MISMATCH_2ND                      => mismatch_2nd_array_counters(i));
  end generate for_upcounter_32_generate;

  for_upcounter_16_generate : for i in 0 to C_NR_16_BIT_COUNTERS-1 generate
    INST_upcounter_WR_OPERATIONS : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => C_CNTR_STD_range'length,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(i+(2*C_NR_32_BIT_COUNTERS)),
        CNT_UP       => s_counter_increase(i+C_NR_32_BIT_COUNTERS),
        CNT_VALUE    => s_counter_values(i+(2*C_NR_32_BIT_COUNTERS)),
        MISMATCH     => mismatch_array_counters(i+C_NR_32_BIT_COUNTERS),
        MISMATCH_2ND => mismatch_2nd_array_counters(i+C_NR_32_BIT_COUNTERS));
  end generate for_upcounter_16_generate;

  -- Mismatch
  INST_mismatch : entity work.mismatch
    generic map(
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
    port map(
      CLK                  => WB_CLK,
      RST                  => WB_RST,
      mismatch_array_i     => mismatch_array,
      mismatch_2nd_array_i => mismatch_2nd_array,
      MISMATCH_O           => MISMATCH,
      MISMATCH_2ND_O       => MISMATCH_2ND);

end architecture rtl;
