-------------------------------------------------------------------------------
-- Title      : Powerunit I2C Monitor 
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_monitor_pu.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-05-30
-- Last update: 2019-07-03
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Monitor for I2C transactions of the powerunit 
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-05-30  1.0      jschamba  Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;

-- Wishbone interface package
library work;
use work.intercon_pkg.all;
use work.tmr_pkg.all;


entity i2c_monitor_pu is
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
    -- Counter Inputs
    COMPLETED_BYTE_i : in  std_logic;
    AL_ERROR_i       : in  std_logic;
    NOACK_ERROR_i    : in  std_logic;
    REQ_FIFO_OVF_i   : in  std_logic;
    RES_FIFO_OVF_i   : in  std_logic;
    RES_FIFO_UFL_i   : in  std_logic;
    -- Mismatch
    MISMATCH         : out std_logic;
    MISMATCH_2ND     : out std_logic
    );
  attribute DONT_TOUCH                   : string;
  attribute DONT_TOUCH of i2c_monitor_pu : entity is "TRUE";
end entity i2c_monitor_pu;

architecture triplicate_io of i2c_monitor_pu is

  -- Wishbone Mapping
  constant COUNTER_COMPLETED_BYTE_LOW  : natural := 0;
  constant COUNTER_COMPLETED_BYTE_HIGH : natural := 1;
  constant COUNTER_AL_ERROR_LOW        : natural := 2;
  constant COUNTER_AL_ERROR_HIGH       : natural := 3;
  constant COUNTER_NOACK_ERROR_LOW     : natural := 4;
  constant COUNTER_NOACK_ERROR_HIGH    : natural := 5;
  constant COUNTER_REQ_FIFO_OVF_LOW    : natural := 6;
  constant COUNTER_REQ_FIFO_OVF_HIGH   : natural := 7;
  constant COUNTER_RES_FIFO_OVF_LOW    : natural := 8;
  constant COUNTER_RES_FIFO_OVF_HIGH   : natural := 9;
  constant COUNTER_RES_FIFO_UFL_LOW    : natural := 10;
  constant COUNTER_RES_FIFO_UFL_HIGH   : natural := 11;
  constant NR_REGS                     : natural := 12;

  signal s_counter_reset  : std_logic_vector(NR_REGS-1 downto 0);
  signal s_counter_values : t_wbs_reg_array(0 to NR_REGS-1);

  constant C_MISMATCH_WIDTH : integer := 1 + NR_REGS;

  signal mismatch_array          : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
  alias mismatch_counter_monitor : std_ulogic is mismatch_array(0);
  alias mismatch_array_counters  : std_ulogic_vector(NR_REGS-1 downto 0) is mismatch_array(NR_REGS downto 1);

  signal mismatch_2nd_array          : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
  alias mismatch_2nd_counter_monitor : std_ulogic is mismatch_2nd_array(0);
  alias mismatch_2nd_array_counters  : std_ulogic_vector(NR_REGS-1 downto 0) is mismatch_2nd_array(NR_REGS downto 1);

  signal mismatch_int, mismatch_2nd_int : std_ulogic;

begin  -- architecture triplicate_io

  -- Wishbone monitor
  -----------------------------
  INST_ws_counter_monitor_tmr_wrapper_i2c : entity work.ws_counter_monitor_tmr_wrapper
    generic map (
      NR_COUNTERS                => NR_REGS,
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => 0,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
    port map(
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_I,
      WB_WBS_O         => WB_WBS_O,
      counter_reset_o  => s_counter_reset,
      counter_values_i => s_counter_values,
      MISMATCH         => mismatch_counter_monitor,
      MISMATCH_2ND     => mismatch_2nd_counter_monitor);

  -- Counters
  -----------------------------
  counters : block
    signal sCompletedByteCounter : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);
    signal sAlErrorCounter       : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);
    signal sNoAckErrorCounter    : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);
    signal sReqFifoOvfCounter    : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);
    signal sResFifoOvfCounter    : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);
    signal sResFifoUflCounter    : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0);

  begin
    upcounter_tmr_wrapper_COMPLETED_BYTE : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_COMPLETED_BYTE_LOW),
        CNT_UP       => COMPLETED_BYTE_i,
        CNT_VALUE    => sCompletedByteCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_COMPLETED_BYTE_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_COMPLETED_BYTE_LOW)
        );

    mismatch_array_counters(COUNTER_COMPLETED_BYTE_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_COMPLETED_BYTE_HIGH) <= '0';
    s_counter_values(COUNTER_COMPLETED_BYTE_HIGH)            <= sCompletedByteCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_COMPLETED_BYTE_LOW)             <= sCompletedByteCounter(WB_DATA_WIDTH-1 downto 0);

    upcounter_tmr_wrapper_AL_ERROR : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_AL_ERROR_LOW),
        CNT_UP       => AL_ERROR_i,
        CNT_VALUE    => sAlErrorCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_AL_ERROR_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_AL_ERROR_LOW)
        );

    mismatch_array_counters(COUNTER_AL_ERROR_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_AL_ERROR_HIGH) <= '0';
    s_counter_values(COUNTER_AL_ERROR_HIGH)            <= sAlErrorCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_AL_ERROR_LOW)             <= sAlErrorCounter(WB_DATA_WIDTH-1 downto 0);

    upcounter_tmr_wrapper_NOACK_ERROR : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_NOACK_ERROR_LOW),
        CNT_UP       => NOACK_ERROR_i,
        CNT_VALUE    => sNoAckErrorCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_NOACK_ERROR_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_NOACK_ERROR_LOW)
        );

    mismatch_array_counters(COUNTER_NOACK_ERROR_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_NOACK_ERROR_HIGH) <= '0';
    s_counter_values(COUNTER_NOACK_ERROR_HIGH)            <= sNoAckErrorCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_NOACK_ERROR_LOW)             <= sNoAckErrorCounter(WB_DATA_WIDTH-1 downto 0);

    upcounter_tmr_wrapper_REQ_FIFO_OVF : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_REQ_FIFO_OVF_LOW),
        CNT_UP       => REQ_FIFO_OVF_i,
        CNT_VALUE    => sReqFifoOvfCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_REQ_FIFO_OVF_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_REQ_FIFO_OVF_LOW)
        );

    mismatch_array_counters(COUNTER_REQ_FIFO_OVF_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_REQ_FIFO_OVF_HIGH) <= '0';
    s_counter_values(COUNTER_REQ_FIFO_OVF_HIGH)            <= sReqFifoOvfCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_REQ_FIFO_OVF_LOW)             <= sReqFifoOvfCounter(WB_DATA_WIDTH-1 downto 0);

    upcounter_tmr_wrapper_RES_FIFO_OVF : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_RES_FIFO_OVF_LOW),
        CNT_UP       => RES_FIFO_OVF_i,
        CNT_VALUE    => sResFifoOvfCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_RES_FIFO_OVF_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_RES_FIFO_OVF_LOW)
        );

    mismatch_array_counters(COUNTER_RES_FIFO_OVF_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_RES_FIFO_OVF_HIGH) <= '0';
    s_counter_values(COUNTER_RES_FIFO_OVF_HIGH)            <= sResFifoOvfCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_RES_FIFO_OVF_LOW)             <= sResFifoOvfCounter(WB_DATA_WIDTH-1 downto 0);

    upcounter_tmr_wrapper_RES_FIFO_UFL : entity work.upcounter_tmr_wrapper
      generic map (
        BIT_WIDTH                  => 2 * WB_DATA_WIDTH,
        IS_SATURATING              => 0,
        VERBOSE                    => 0,
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => 0,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH
        )
      port map (
        CLK          => WB_CLK,
        RST          => WB_RST,
        RST_CNT      => s_counter_reset(COUNTER_RES_FIFO_UFL_LOW),
        CNT_UP       => RES_FIFO_UFL_i,
        CNT_VALUE    => sResFifoUflCounter,
        MISMATCH     => mismatch_array_counters(COUNTER_RES_FIFO_UFL_LOW),
        MISMATCH_2ND => mismatch_2nd_array_counters(COUNTER_RES_FIFO_UFL_LOW)
        );

    mismatch_array_counters(COUNTER_RES_FIFO_UFL_HIGH)     <= '0';
    mismatch_2nd_array_counters(COUNTER_RES_FIFO_UFL_HIGH) <= '0';
    s_counter_values(COUNTER_RES_FIFO_UFL_HIGH)            <= sResFifoUflCounter(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH);
    s_counter_values(COUNTER_RES_FIFO_UFL_LOW)             <= sResFifoUflCounter(WB_DATA_WIDTH-1 downto 0);

  end block counters;

  --------------------------------
  -- Generate Mismatch signals
  --------------------------------
  mismatch_int <= or_reduce(mismatch_counter_monitor & mismatch_array_counters) when G_MISMATCH_EN = 1 else
                  '0';
  mismatch_2nd_int <= or_reduce(mismatch_2nd_counter_monitor & mismatch_2nd_array_counters) when G_ADDITIONAL_MISMATCH = 1 and G_MISMATCH_EN = 1
                      else '0';

  registered_mismatch : if G_MISMATCH_REGISTERED = 1 generate
    register_mismatch : process (WB_CLK) is
    begin
      if rising_edge(WB_CLK) then
        if WB_RST = '1' then
          MISMATCH     <= '0';
          MISMATCH_2ND <= '0';
        else
          MISMATCH     <= mismatch_int;
          MISMATCH_2ND <= mismatch_2nd_int;
        end if;
      end if;
    end process register_mismatch;
  end generate registered_mismatch;

  comb_mismatch : if G_MISMATCH_REGISTERED = 0 generate
    MISMATCH     <= mismatch_int;
    MISMATCH_2ND <= mismatch_2nd_int;
  end generate comb_mismatch;
end architecture triplicate_io;
