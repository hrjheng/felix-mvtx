-------------------------------------------------------------------------------
-- Title      : CAN High Level Protocol (HLP)
-- Project    : CAN Bus DCS for ITS Readout Unit
-------------------------------------------------------------------------------
-- File       : can_hlp_top.vhd
-- Author     : Simon Voigt Nesbø
-- Company    :
-- Created    : 2018-03-30
-- Last update: 2020-10-16
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: CAN High Level Protocol (HLP) for DCS in ITS Readout Unit
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-03-30  1.0      svn     Created
-- 2019-02-15  1.1      mlupi   std fifo, block ram
-- 2020-02-12  2.0      svn     Updated for new version of CAN HLP
-- 2020-10-11  2.1      svn     Updated to use WP10 voters in CAN controller
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.intercon_pkg.all;
use work.canola_pkg.all;
use work.can_hlp_pkg.all;
use work.can_hlp_monitor_pkg.all;
use work.can_hlp_wishbone_pkg.all;
use work.xpm_cdc_components_pkg.all;
use work.tmr_pkg.all;

entity can_hlp_top is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 0);
  port (
    -- Wishbone slave interface
    WB_CLK           : in  std_logic;
    WB_RST           : in  std_logic;
    WB_WBS_I         : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_O         : out t_wbs_o_array(0 to C_K_TMR-1);
    WB_WBS_MONITOR_I : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_MONITOR_O : out t_wbs_o_array(0 to C_K_TMR-1);

    -- Interface to wishbone master via FIFO
    -- CAN HLP intiates WB transactions on DP0
    DP0_DT_O   : out std_logic_vector(GPIF_WIDTH-1 downto 0);
    DP0_EPTY_O : out std_logic;
    DP0_RD_I   : in  std_logic;

    -- Interface to wishbone master via FIFO
    -- CAN HLP receives WB replies on DP1
    DP1_DT_I     : in  std_logic_vector(GPIF_WIDTH-1 downto 0);
    DP1_FULL_O   : out std_logic;
    DP1_WR_I     : in  std_logic;


    -- Pulse to send alert or status messsage
    SEND_ALERT  : in std_logic;
    SEND_STATUS : in std_logic;

    -- Data for alert and status messages
    -- Alert uses bits 15:0 only, status uses all 32 bits.
    STATUS_ALERT_DATA : in std_logic_vector(31 downto 0);

    CAN_NODE_ID : in std_logic_vector(7 downto 0);

    -- CAN bus signals
    CAN_TX : out std_logic;
    CAN_RX : in  std_logic);

end entity can_hlp_top;

architecture structural of can_hlp_top is

  -- HLP FSM signals
  signal s_hlp_read_count_up          : std_logic;
  signal s_hlp_write_count_up         : std_logic;
  signal s_hlp_status_count_up        : std_logic;
  signal s_hlp_alert_count_up         : std_logic;
  signal s_hlp_unknown_count_up       : std_logic;
  signal s_hlp_length_error_count_up  : std_logic;
  signal s_hlp_node_id_error_count_up : std_logic;
  signal s_hlp_msg_dropped_count_up   : std_logic;
  signal s_hlp_test_mode_en           : std_logic;

  -- Wishbone FIFO signals
  signal s_dp1_dt   : std_logic_vector(GPIF_WIDTH-1 downto 0);
  signal s_dp1_epty : std_logic;
  signal s_dp1_rd   : std_logic;
  signal s_dp0_dt   : std_logic_vector(GPIF_WIDTH-1 downto 0);
  signal s_dp0_full : std_logic;
  signal s_dp0_wr   : std_logic;

  -- Wishbone registers
  signal s_wishbone_regs : t_can_hlp_wb_regs;

  -- CAN controller signals
  signal s_can_rx_msg                  : can_msg_t;
  signal s_can_rx_msg_valid            : std_logic;
  signal s_can_tx_msg                  : can_msg_t;
  signal s_can_tx_start                : std_logic;
  signal s_can_tx_retransmit_en        : std_logic;
  signal s_can_tx_busy                 : std_logic;
  signal s_can_tx_done                 : std_logic;
  signal s_can_tx_failed               : std_logic;
  signal s_can_triple_sampling         : std_logic;
  signal s_can_prop_seg                : std_logic_vector(C_PROP_SEG_WIDTH-1 downto 0);
  signal s_can_phase_seg1              : std_logic_vector(C_PHASE_SEG1_WIDTH-1 downto 0);
  signal s_can_phase_seg2              : std_logic_vector(C_PHASE_SEG2_WIDTH-1 downto 0);
  signal s_can_sync_jump_width         : unsigned(C_SYNC_JUMP_WIDTH_BITSIZE-1 downto 0);
  signal s_can_time_quanta_clock_scale : unsigned(C_TIME_QUANTA_WIDTH-1 downto 0);
  signal s_can_transmit_error_count    : unsigned(C_ERROR_COUNT_LENGTH-1 downto 0);
  signal s_can_receive_error_count     : unsigned(C_ERROR_COUNT_LENGTH-1 downto 0);
  signal s_can_error_state             : can_error_state_t;
  signal s_can_tx_msg_sent_count_up    : std_logic;
  signal s_can_tx_ack_error_count_up   : std_logic;
  signal s_can_tx_arb_lost_count_up    : std_logic;
  signal s_can_tx_bit_error_count_up   : std_logic;
  signal s_can_tx_retransmit_count_up  : std_logic;
  signal s_can_rx_msg_recv_count_up    : std_logic;
  signal s_can_rx_crc_error_count_up   : std_logic;
  signal s_can_rx_form_error_count_up  : std_logic;
  signal s_can_rx_stuff_error_count_up : std_logic;


  -- CAN error state signals
  signal s_can_error_active  : std_logic;
  signal s_can_error_passive : std_logic;
  signal s_can_bus_off       : std_logic;

  -- Mismatch signals
  signal s_mismatch_can_ctrl          : std_logic;
  signal s_mismatch_can_ctrl_2nd      : std_logic;
  signal s_mismatch_wb_slave_regs     : std_logic;
  signal s_mismatch_wb_slave_regs_2nd : std_logic;
  signal s_mismatch_fsm               : std_logic;
  signal s_mismatch_fsm_2nd           : std_logic;
  signal s_mismatch_monitor           : std_logic;
  signal s_mismatch_monitor_2nd       : std_logic;

begin  -- architecture can_hlp_top

  -----------------------------------------------------------------------------
  -- CAN High Level Protocol (HLP) FSM
  -----------------------------------------------------------------------------
  INST_can_hlp_fsm : entity work.can_hlp_fsm_tmr_wrapper
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
    port map (
      CLK               => WB_CLK,
      RESET             => WB_RST,
      CAN_NODE_ID       => CAN_NODE_ID,

      TEST_MODE         => s_wishbone_regs.CTRL(C_CTRL_TEST_MODE_EN_bit),
      SEND_ALERT        => SEND_ALERT,
      SEND_STATUS       => SEND_STATUS,
      STATUS_ALERT_DATA => STATUS_ALERT_DATA,

      CAN_RX_MSG        => s_can_rx_msg,
      CAN_RX_MSG_VALID  => s_can_rx_msg_valid,
      CAN_TX_MSG        => s_can_tx_msg,
      CAN_TX_START      => s_can_tx_start,
      CAN_TX_BUSY       => s_can_tx_busy,
      CAN_TX_DONE       => s_can_tx_done,
      CAN_TX_FAILED     => s_can_tx_failed,

      -- Counters for CAN HLP module
      HLP_READ_COUNT_UP          => s_hlp_read_count_up,
      HLP_WRITE_COUNT_UP         => s_hlp_write_count_up,
      HLP_STATUS_COUNT_UP        => s_hlp_status_count_up,
      HLP_ALERT_COUNT_UP         => s_hlp_alert_count_up,
      HLP_UNKNOWN_COUNT_UP       => s_hlp_unknown_count_up,
      HLP_LENGTH_ERROR_COUNT_UP  => s_hlp_length_error_count_up,
      HLP_NODE_ID_ERROR_COUNT_UP => s_hlp_node_id_error_count_up,
      HLP_MSG_DROPPED_COUNT_UP   => s_hlp_msg_dropped_count_up,

      -- Interface to wishbone FIFO
      -- CAN_HLP receives WB replies on this interface
      DP0_DT_O   => s_dp0_dt,
      DP0_FULL_I => s_dp0_full,
      DP0_WR_O   => s_dp0_wr,

      -- Interface to Wishbone FIFO
      -- CAN_HLP initiates WB transactions on this interface
      DP1_DT_I   => s_dp1_dt,
      DP1_EPTY_I => s_dp1_epty,
      DP1_RD_O   => s_dp1_rd,

      --Mismatch
      MISMATCH     => s_mismatch_fsm,
      MISMATCH_2ND => s_mismatch_fsm_2nd
      );


  -----------------------------------------------------------------------------
  -- CAN Controller
  -----------------------------------------------------------------------------
  INST_canola_top_tmr: entity work.canola_top_tmr
    generic map (
      G_SEE_MITIGATION_EN       => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_OUTPUT_EN      => G_MISMATCH_EN,
      G_MISMATCH_OUTPUT_2ND_EN  => G_ADDITIONAL_MISMATCH,
      G_MISMATCH_OUTPUT_REG     => G_MISMATCH_REGISTERED,
      G_TIME_QUANTA_SCALE_WIDTH => C_TIME_QUANTA_WIDTH,
      G_RETRANSMIT_COUNT_MAX    => C_CAN_RETRANSMIT_COUNT_MAX)
    port map (
      CLK                         => WB_CLK,
      RESET                       => WB_RST,
      CAN_TX                      => CAN_TX,
      CAN_RX                      => CAN_RX,
      RX_MSG                      => s_can_rx_msg,
      RX_MSG_VALID                => s_can_rx_msg_valid,
      TX_MSG                      => s_can_tx_msg,
      TX_START                    => s_can_tx_start,
      TX_RETRANSMIT_EN            => s_wishbone_regs.CTRL(C_CTRL_RETRANSMIT_EN_bit),
      TX_BUSY                     => s_can_tx_busy,
      TX_DONE                     => s_can_tx_done,
      TX_FAILED                   => s_can_tx_failed,
      BTL_TRIPLE_SAMPLING         => s_wishbone_regs.CTRL(C_CTRL_TRIPLE_SAMPLING_EN_bit),
      BTL_PROP_SEG                => s_wishbone_regs.CAN_PROP_SEG,
      BTL_PHASE_SEG1              => s_wishbone_regs.CAN_PHASE_SEG1,
      BTL_PHASE_SEG2              => s_wishbone_regs.CAN_PHASE_SEG2,
      BTL_SYNC_JUMP_WIDTH         => unsigned(s_wishbone_regs.CAN_SJW),
      TIME_QUANTA_CLOCK_SCALE     => unsigned(s_wishbone_regs.CAN_CLK_SCALE),
      TRANSMIT_ERROR_COUNT        => s_can_transmit_error_count,
      RECEIVE_ERROR_COUNT         => s_can_receive_error_count,
      ERROR_STATE                 => s_can_error_state,

      -- Counter signals
      TX_MSG_SENT_COUNT_UP       => s_can_tx_msg_sent_count_up,
      TX_ACK_ERROR_COUNT_UP      => s_can_tx_ack_error_count_up,
      TX_ARB_LOST_COUNT_UP       => s_can_tx_arb_lost_count_up,
      TX_BIT_ERROR_COUNT_UP      => s_can_tx_bit_error_count_up,
      TX_RETRANSMIT_COUNT_UP     => s_can_tx_retransmit_count_up,
      RX_MSG_RECV_COUNT_UP       => s_can_rx_msg_recv_count_up,
      RX_CRC_ERROR_COUNT_UP      => s_can_rx_crc_error_count_up,
      RX_FORM_ERROR_COUNT_UP     => s_can_rx_form_error_count_up,
      RX_STUFF_ERROR_COUNT_UP    => s_can_rx_stuff_error_count_up,

      MISMATCH                   => s_mismatch_can_ctrl,
      MISMATCH_2ND               => s_mismatch_can_ctrl_2nd);

  s_can_error_active  <= '1' when s_can_error_state = ERROR_ACTIVE  else '0';
  s_can_error_passive <= '1' when s_can_error_state = ERROR_PASSIVE else '0';
  s_can_bus_off       <= '1' when s_can_error_state = BUS_OFF       else '0';

  -----------------------------------------------------------------------------
  -- Wishbone slave registers
  -----------------------------------------------------------------------------
  INST_can_hlp_wb_slave_regs: entity work.can_hlp_wb_slave_regs_tmr_wrapper
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
    port map (
      WB_CLK                  => WB_CLK,
      WB_RST                  => WB_RST,
      WB_WBS_I                => WB_WBS_I,
      WB_WBS_O                => WB_WBS_O,

      -- CAN error state
      CAN_ERROR_ACTIVE        => s_can_error_active,
      CAN_ERROR_PASSIVE       => s_can_error_passive,
      CAN_BUS_OFF             => s_can_bus_off,

      -- Transmit/Error Receive Error Counters in CAN controller
      CAN_TEC                 => std_logic_vector(s_can_transmit_error_count),
      CAN_REC                 => std_logic_vector(s_can_receive_error_count),

      WISHBONE_REGS_O         => s_wishbone_regs,

      MISMATCH                => s_mismatch_wb_slave_regs,
      MISMATCH_2ND            => s_mismatch_wb_slave_regs_2nd);

  -----------------------------------------------------------------------------
  -- CAN HLP counter monitor
  -----------------------------------------------------------------------------
  INST_can_hlp_monitor: entity work.can_hlp_monitor
    generic map (
      G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
      G_MISMATCH_EN              => G_MISMATCH_EN,
      G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
      G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
    port map (
      WB_CLK                        => WB_CLK,
      WB_RST                        => WB_RST,
      WB_WBS_I                      => WB_WBS_MONITOR_I,
      WB_WBS_O                      => WB_WBS_MONITOR_O,
      HLP_READ_COUNT_UP_I           => s_hlp_read_count_up,
      HLP_WRITE_COUNT_UP_I          => s_hlp_write_count_up,
      HLP_STATUS_COUNT_UP_I         => s_hlp_status_count_up,
      HLP_ALERT_COUNT_UP_I          => s_hlp_alert_count_up,
      HLP_UNKNOWN_COUNT_UP_I        => s_hlp_unknown_count_up,
      HLP_LENGTH_ERROR_COUNT_UP_I   => s_hlp_length_error_count_up,
      HLP_MSG_DROPPED_COUNT_UP_I    => s_hlp_msg_dropped_count_up,
      CAN_TX_MSG_SENT_COUNT_UP_I    => s_can_tx_msg_sent_count_up,
      CAN_TX_ACK_ERROR_COUNT_UP_I   => s_can_tx_ack_error_count_up,
      CAN_TX_ARB_LOST_COUNT_UP_I    => s_can_tx_arb_lost_count_up,
      CAN_TX_BIT_ERROR_COUNT_UP_I   => s_can_tx_bit_error_count_up,
      CAN_TX_RETRANSMIT_COUNT_UP_I  => s_can_tx_retransmit_count_up,
      CAN_RX_MSG_RECV_COUNT_UP_I    => s_can_rx_msg_recv_count_up,
      CAN_RX_CRC_ERROR_COUNT_UP_I   => s_can_rx_crc_error_count_up,
      CAN_RX_FORM_ERROR_COUNT_UP_I  => s_can_rx_form_error_count_up,
      CAN_RX_STUFF_ERROR_COUNT_UP_I => s_can_rx_stuff_error_count_up,
      MISMATCH                      => s_mismatch_monitor,
      MISMATCH_2ND                  => s_mismatch_monitor_2nd);


  -----------------------------------------------------------------------------
  -- DP0 FIFO for wishbone requests
  -----------------------------------------------------------------------------
  inst_dp0_wb_request_fifo : xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",
      ECC_MODE            => "NO_ECC",
      FIFO_WRITE_DEPTH    => 16,
      WRITE_DATA_WIDTH    => 32,
      WR_DATA_COUNT_WIDTH => 5,
      PROG_FULL_THRESH    => 10,
      FULL_RESET_VALUE    => 0,
      USE_ADV_FEATURES    => "0000", -- Enable [12:8] = data_valid, almost_empty, rd_data_count, prog_empty, underflow,
                                     -- [4:0] = wr_ack, almost_full, wr_data_count, prog_full, overflow
      READ_MODE           => "std",
      FIFO_READ_LATENCY   => 2,
      READ_DATA_WIDTH     => 32,
      RD_DATA_COUNT_WIDTH => 5,
      PROG_EMPTY_THRESH   => 10,
      DOUT_RESET_VALUE    => "0",
      WAKEUP_TIME         => 0)
    port map (
      sleep         => '0',
      rst           => WB_RST,
      wr_clk        => WB_CLK,
      wr_en         => s_dp0_wr,
      din           => s_dp0_dt,
      full          => s_dp0_full,
      prog_full     => open,
      wr_data_count => open,
      overflow      => open,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => DP0_RD_I,
      dout          => DP0_DT_O,
      empty         => DP0_EPTY_O,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => open,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open);


  -----------------------------------------------------------------------------
  -- DP1 FIFO for wishbone results/responses
  -----------------------------------------------------------------------------
  inst_dp1_wb_response_fifo: xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",
      ECC_MODE            => "NO_ECC",
      FIFO_WRITE_DEPTH    => 16,
      WRITE_DATA_WIDTH    => 32,
      WR_DATA_COUNT_WIDTH => 5,
      PROG_FULL_THRESH    => 10,
      FULL_RESET_VALUE    => 0,
      USE_ADV_FEATURES    => "0000", -- Enable [12:8] = data_valid, almost_empty, rd_data_count, prog_empty, underflow,
                                     -- [4:0] = wr_ack, almost_full, wr_data_count, prog_full, overflow
      READ_MODE           => "std",
      FIFO_READ_LATENCY   => 2,
      READ_DATA_WIDTH     => 32,
      RD_DATA_COUNT_WIDTH => 5,
      PROG_EMPTY_THRESH   => 10,
      DOUT_RESET_VALUE    => "0",
      WAKEUP_TIME         => 0)
    port map (
      sleep         => '0',
      rst           => WB_RST,
      wr_clk        => WB_CLK,
      wr_en         => DP1_WR_I,
      din           => DP1_DT_I,
      full          => DP1_FULL_O,
      prog_full     => open,
      wr_data_count => open,
      overflow      => open,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => s_dp1_rd,
      dout          => s_dp1_dt,
      empty         => s_dp1_epty,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => open,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open);

end architecture structural;
