-------------------------------------------------------------------------------
-- Title      : CAN High Level Protocol (HLP) FSM TMR wrapper
-- Project    : CAN Bus for DCS in the ITS Readout Unit
-------------------------------------------------------------------------------
-- File       : can_hlp_fsm_tmr_wrapper.vhd
-- Author     : Simon Voigt Nesbø
-- Company    :
-- Created    : 2020-03-05
-- Last update: 2020-10-11
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: TMR wrapper for FSM logic for CAN HLP
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2020-03-05  1.0      SVN     Created
-------------------------------------------------------------------------------



library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


library work;
use work.intercon_pkg.all;
use work.canola_pkg.all;
use work.can_hlp_pkg.all;
use work.tmr_pkg.all;

entity can_hlp_fsm_tmr_wrapper is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 1
    );
  port (
    CLK   : in std_logic;
    RESET : in std_logic;

    CAN_NODE_ID : in std_logic_vector(7 downto 0);
    TEST_MODE   : in std_logic;
    SEND_ALERT  : in std_logic;
    SEND_STATUS : in std_logic;

    -- Data for alert and status messages
    -- Alert uses bits 15:0 only, status uses all 32 bits.
    STATUS_ALERT_DATA : in std_logic_vector(31 downto 0);

    -- Interface to CAN controller
    CAN_RX_MSG       : in  can_msg_t;
    CAN_RX_MSG_VALID : in  std_logic;
    CAN_TX_MSG       : out can_msg_t;
    CAN_TX_START     : out std_logic;
    CAN_TX_BUSY      : in  std_logic;
    CAN_TX_DONE      : in  std_logic;
    CAN_TX_FAILED    : in  std_logic;

    -- Counters for CAN HLP module
    HLP_READ_COUNT_UP          : out std_logic;
    HLP_WRITE_COUNT_UP         : out std_logic;
    HLP_STATUS_COUNT_UP        : out std_logic;
    HLP_ALERT_COUNT_UP         : out std_logic;
    HLP_UNKNOWN_COUNT_UP       : out std_logic;
    HLP_LENGTH_ERROR_COUNT_UP  : out std_logic;
    HLP_NODE_ID_ERROR_COUNT_UP : out std_logic;
    HLP_MSG_DROPPED_COUNT_UP   : out std_logic;

    -- Interface to wishbone master via FIFO
    -- CAN HLP initiates WB transactions on DP0
    DP0_DT_O   : out std_logic_vector(31 downto 0);
    DP0_FULL_I : in  std_logic;
    DP0_WR_O   : out std_logic;

    -- Interface to wishbone master via FIFO
    -- CAN HLP receives WB replies on DP1
    DP1_DT_I   : in  std_logic_vector(31 downto 0);
    DP1_EPTY_I : in  std_logic;
    DP1_RD_O   : out std_logic;

    --Mismatch
    MISMATCH     : out std_logic;
    MISMATCH_2ND : out std_logic
    );
  attribute DONT_TOUCH                            : string;
  attribute DONT_TOUCH of can_hlp_fsm_tmr_wrapper : entity is "true";
end entity can_hlp_fsm_tmr_wrapper;


architecture structural of can_hlp_fsm_tmr_wrapper is

begin  -- architecture structural


  -- -----------------------------------------------------------------------
  -- Generate single instance of HLP FSM when TMR is disabled
  -- -----------------------------------------------------------------------
  if_NOMITIGATION_generate : if G_SEE_MITIGATION_TECHNIQUE = 0 generate
    signal s_hlp_fsm_state : std_logic_vector(C_HLP_FSM_STATE_BITSIZE-1 downto 0);
  begin
    INST_can_hlp_fsm : entity work.can_hlp_fsm
      port map (
        CLK                        => CLK,
        RESET                      => RESET,
        CAN_NODE_ID                => CAN_NODE_ID,
        TEST_MODE                  => TEST_MODE,
        SEND_ALERT                 => SEND_ALERT,
        SEND_STATUS                => SEND_STATUS,
        STATUS_ALERT_DATA          => STATUS_ALERT_DATA,
        CAN_RX_MSG                 => CAN_RX_MSG,
        CAN_RX_MSG_VALID           => CAN_RX_MSG_VALID,
        CAN_TX_MSG                 => CAN_TX_MSG,
        CAN_TX_START               => CAN_TX_START,
        CAN_TX_BUSY                => CAN_TX_BUSY,
        CAN_TX_DONE                => CAN_TX_DONE,
        CAN_TX_FAILED              => CAN_TX_FAILED,
        HLP_READ_COUNT_UP          => HLP_READ_COUNT_UP,
        HLP_WRITE_COUNT_UP         => HLP_WRITE_COUNT_UP,
        HLP_STATUS_COUNT_UP        => HLP_STATUS_COUNT_UP,
        HLP_ALERT_COUNT_UP         => HLP_ALERT_COUNT_UP,
        HLP_UNKNOWN_COUNT_UP       => HLP_UNKNOWN_COUNT_UP,
        HLP_LENGTH_ERROR_COUNT_UP  => HLP_LENGTH_ERROR_COUNT_UP,
        HLP_NODE_ID_ERROR_COUNT_UP => HLP_NODE_ID_ERROR_COUNT_UP,
        HLP_MSG_DROPPED_COUNT_UP   => HLP_MSG_DROPPED_COUNT_UP,
        DP0_DT_O                   => DP0_DT_O,
        DP0_FULL_I                 => DP0_FULL_I,
        DP0_WR_O                   => DP0_WR_O,
        DP1_DT_I                   => DP1_DT_I,
        DP1_EPTY_I                 => DP1_EPTY_I,
        DP1_RD_O                   => DP1_RD_O,
        HLP_FSM_STATE_O            => s_hlp_fsm_state,
        HLP_FSM_STATE_I            => s_hlp_fsm_state);

    MISMATCH     <= '0';
    MISMATCH_2ND <= '0';
  end generate if_NOMITIGATION_generate;


  -- -----------------------------------------------------------------------
  -- Generate three instances of HLP FSM when TMR is enabled
  -- -----------------------------------------------------------------------
  if_TMR_generate : if G_SEE_MITIGATION_TECHNIQUE = 1 generate
    type t_can_msg_tmr is array (0 to C_K_TMR-1) of can_msg_t;
    type t_dp_fifo_data_tmr is array (0 to C_K_TMR-1) of std_logic_vector(31 downto 0);
    type t_hlp_fsm_state_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_HLP_FSM_STATE_BITSIZE-1 downto 0);

    signal s_can_tx_msg_tmr                 : t_can_msg_tmr;
    signal s_can_tx_msg_serialized_voted    : std_logic_vector(C_CAN_MSG_LENGTH-1 downto 0);
    signal s_can_tx_start_tmr               : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_read_count_up_tmr          : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_write_count_up_tmr         : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_status_count_up_tmr        : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_alert_count_up_tmr         : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_unknown_count_up_tmr       : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_length_error_count_up_tmr  : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_node_id_error_count_up_tmr : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_msg_dropped_count_up_tmr   : std_logic_vector(0 to C_K_TMR-1);
    signal s_dp0_dt_o_tmr                   : t_dp_fifo_data_tmr;
    signal s_dp0_wr_o_tmr                   : std_logic_vector(0 to C_K_TMR-1);
    signal s_dp1_rd_o_tmr                   : std_logic_vector(0 to C_K_TMR-1);
    signal s_hlp_fsm_state_out_tmr          : t_hlp_fsm_state_tmr;
    signal s_hlp_fsm_state_voted_in_tmr     : t_hlp_fsm_state_tmr;

    attribute DONT_TOUCH                                     : string;
    attribute DONT_TOUCH of s_can_tx_msg_tmr                 : signal is "TRUE";
    attribute DONT_TOUCH of s_can_tx_start_tmr               : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_read_count_up_tmr          : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_write_count_up_tmr         : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_status_count_up_tmr        : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_alert_count_up_tmr         : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_unknown_count_up_tmr       : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_length_error_count_up_tmr  : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_node_id_error_count_up_tmr : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_msg_dropped_count_up_tmr   : signal is "TRUE";
    attribute DONT_TOUCH of s_dp0_dt_o_tmr                   : signal is "TRUE";
    attribute DONT_TOUCH of s_dp0_wr_o_tmr                   : signal is "TRUE";
    attribute DONT_TOUCH of s_dp1_rd_o_tmr                   : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_fsm_state_out_tmr          : signal is "TRUE";
    attribute DONT_TOUCH of s_hlp_fsm_state_voted_in_tmr     : signal is "TRUE";

    constant C_mismatch_can_tx_msg                 : integer := 0;
    constant C_mismatch_can_tx_start               : integer := 1;
    constant C_mismatch_hlp_read_count_up          : integer := 2;
    constant C_mismatch_hlp_write_count_up         : integer := 3;
    constant C_mismatch_hlp_status_count_up        : integer := 4;
    constant C_mismatch_hlp_alert_count_up         : integer := 5;
    constant C_mismatch_hlp_unknown_count_up       : integer := 6;
    constant C_mismatch_hlp_length_error_count_up  : integer := 7;
    constant C_mismatch_hlp_node_id_error_count_up : integer := 8;
    constant C_mismatch_hlp_msg_dropped_count_up   : integer := 9;
    constant C_mismatch_dp0_dt_o                   : integer := 10;
    constant C_mismatch_dp0_wr_o                   : integer := 11;
    constant C_mismatch_dp1_rd_o                   : integer := 12;
    constant C_mismatch_hlp_fsm_state              : integer := 13;
    constant C_MISMATCH_WIDTH                      : integer := 14;

    signal s_mismatch_array     : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
    signal s_mismatch_2nd_array : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);

  begin

    -- Generate C_K_TMR instances of can_hlp_fsm
    for_TMR_generate : for i in 0 to C_K_TMR-1 generate
      INST_can_hlp_fsm : entity work.can_hlp_fsm
        port map (
          CLK                        => CLK,
          RESET                      => RESET,
          CAN_NODE_ID                => CAN_NODE_ID,
          TEST_MODE                  => TEST_MODE,
          SEND_ALERT                 => SEND_ALERT,
          SEND_STATUS                => SEND_STATUS,
          STATUS_ALERT_DATA          => STATUS_ALERT_DATA,
          CAN_RX_MSG                 => CAN_RX_MSG,
          CAN_RX_MSG_VALID           => CAN_RX_MSG_VALID,
          CAN_TX_MSG                 => s_can_tx_msg_tmr(i),
          CAN_TX_START               => s_can_tx_start_tmr(i),
          CAN_TX_BUSY                => CAN_TX_BUSY,
          CAN_TX_DONE                => CAN_TX_DONE,
          CAN_TX_FAILED              => CAN_TX_FAILED,
          HLP_READ_COUNT_UP          => s_hlp_read_count_up_tmr(i),
          HLP_WRITE_COUNT_UP         => s_hlp_write_count_up_tmr(i),
          HLP_STATUS_COUNT_UP        => s_hlp_status_count_up_tmr(i),
          HLP_ALERT_COUNT_UP         => s_hlp_alert_count_up_tmr(i),
          HLP_UNKNOWN_COUNT_UP       => s_hlp_unknown_count_up_tmr(i),
          HLP_LENGTH_ERROR_COUNT_UP  => s_hlp_length_error_count_up_tmr(i),
          HLP_NODE_ID_ERROR_COUNT_UP => s_hlp_node_id_error_count_up_tmr(i),
          HLP_MSG_DROPPED_COUNT_UP   => s_hlp_msg_dropped_count_up_tmr(i),
          DP0_DT_O                   => s_dp0_dt_o_tmr(i),
          DP0_FULL_I                 => DP0_FULL_I,
          DP0_WR_O                   => s_dp0_wr_o_tmr(i),
          DP1_DT_I                   => DP1_DT_I,
          DP1_EPTY_I                 => DP1_EPTY_I,
          DP1_RD_O                   => s_dp1_rd_o_tmr(i),
          HLP_FSM_STATE_O            => s_hlp_fsm_state_out_tmr(i),
          HLP_FSM_STATE_I            => s_hlp_fsm_state_voted_in_tmr(i));
    end generate for_TMR_generate;


    CAN_TX_MSG <= deserialize_can_msg(s_can_tx_msg_serialized_voted);


    -- Voter for CAN_TX_MSG
    INST_majority_voter_array_wrapper_can_tx_msg :
      entity work.majority_voter_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_MSG_LENGTH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT_A       => serialize_can_msg(s_can_tx_msg_tmr(0)),
          INPUT_B       => serialize_can_msg(s_can_tx_msg_tmr(1)),
          INPUT_C       => serialize_can_msg(s_can_tx_msg_tmr(2)),
          OUTPUT        => s_can_tx_msg_serialized_voted,
          MISMATCH      => s_mismatch_array(C_mismatch_can_tx_msg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_can_tx_msg));

    -- Voter for CAN_TX_START
    INST_majority_voter_wrapper2_can_tx_start :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_can_tx_start_tmr,
          OUTPUT        => CAN_TX_START,
          MISMATCH      => s_mismatch_array(C_mismatch_can_tx_start),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_can_tx_start));


    -- Voter for HLP_READ_COUNT_UP
    INST_majority_voter_wrapper2_hlp_read_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_read_count_up_tmr,
          OUTPUT        => HLP_READ_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_read_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_read_count_up));


    -- Voter for HLP_WRITE_COUNT_UP
    INST_majority_voter_wrapper2_hlp_write_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_write_count_up_tmr,
          OUTPUT        => HLP_WRITE_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_write_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_write_count_up));


    -- Voter for HLP_STATUS_COUNT_UP
    INST_majority_voter_wrapper2_hlp_status_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_status_count_up_tmr,
          OUTPUT        => HLP_STATUS_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_status_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_status_count_up));


    -- Voter for HLP_ALERT_COUNT_UP
    INST_majority_voter_wrapper2_hlp_alert_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_alert_count_up_tmr,
          OUTPUT        => HLP_ALERT_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_alert_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_alert_count_up));


    -- Voter for HLP_UNKNOWN_COUNT_UP
    INST_majority_voter_wrapper2_hlp_unknown_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_unknown_count_up_tmr,
          OUTPUT        => HLP_UNKNOWN_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_unknown_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_unknown_count_up));


    -- Voter for HLP_LENGTH_ERROR_COUNT_UP
    INST_majority_voter_wrapper2_hlp_length_error_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_length_error_count_up_tmr,
          OUTPUT        => HLP_LENGTH_ERROR_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_length_error_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_length_error_count_up));


    -- Voter for HLP_NODE_ID_ERROR_COUNT_UP
    INST_majority_voter_wrapper2_hlp_node_id_error_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_node_id_error_count_up_tmr,
          OUTPUT        => HLP_NODE_ID_ERROR_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_node_id_error_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_node_id_error_count_up));


    -- Voter for HLP_MSG_DROPPED_COUNT_UP
    INST_majority_voter_wrapper2_hlp_msg_dropped_count_up :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_hlp_msg_dropped_count_up_tmr,
          OUTPUT        => HLP_MSG_DROPPED_COUNT_UP,
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_msg_dropped_count_up),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_msg_dropped_count_up));


    -- Voter for DP0_DT_O
    INST_majority_voter_array_wrapper_dp0_dt_o :
      entity work.majority_voter_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => 32)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT_A       => s_dp0_dt_o_tmr(0),
          INPUT_B       => s_dp0_dt_o_tmr(1),
          INPUT_C       => s_dp0_dt_o_tmr(2),
          OUTPUT        => DP0_DT_O,
          MISMATCH      => s_mismatch_array(C_mismatch_dp0_dt_o),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_dp0_dt_o));


    -- Voter for DP0_WR_O
    INST_majority_voter_wrapper2_dp0_wr_o :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_dp0_wr_o_tmr,
          OUTPUT        => DP0_WR_O,
          MISMATCH      => s_mismatch_array(C_mismatch_dp0_wr_o),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_dp0_wr_o));


    -- Voter for DP1_RD_O
    INST_majority_voter_wrapper2_dp1_rd_o :
      entity work.majority_voter_wrapper2
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT         => s_dp1_rd_o_tmr,
          OUTPUT        => DP1_RD_O,
          MISMATCH      => s_mismatch_array(C_mismatch_dp1_rd_o),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_dp1_rd_o));



    -------------------------------------------------------------------------
    -- Triplicated array voter for HLP FSM state register
    -------------------------------------------------------------------------

    INST_majority_voter_triplicated_array_wrapper_hlp_fsm_state :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_HLP_FSM_STATE_BITSIZE)
        port map (
          ASSERTION_CLK => CLK,
          ASSERTION_RST => RESET,
          INPUT_A       => s_hlp_fsm_state_out_tmr(0),
          INPUT_B       => s_hlp_fsm_state_out_tmr(1),
          INPUT_C       => s_hlp_fsm_state_out_tmr(2),
          OUTPUT_A      => s_hlp_fsm_state_voted_in_tmr(0),
          OUTPUT_B      => s_hlp_fsm_state_voted_in_tmr(1),
          OUTPUT_C      => s_hlp_fsm_state_voted_in_tmr(2),
          MISMATCH      => s_mismatch_array(C_mismatch_hlp_fsm_state),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_hlp_fsm_state));


    -------------------------------------------------------------------------
    -- Mismatch in voted signals
    -------------------------------------------------------------------------
    INST_mismatch : entity work.mismatch
      generic map(
        G_SEE_MITIGATION_TECHNIQUE => G_SEE_MITIGATION_TECHNIQUE,
        G_MISMATCH_EN              => G_MISMATCH_EN,
        G_MISMATCH_REGISTERED      => G_MISMATCH_REGISTERED,
        G_ADDITIONAL_MISMATCH      => G_ADDITIONAL_MISMATCH)
      port map(
        CLK                  => CLK,
        RST                  => RESET,
        mismatch_array_i     => s_mismatch_array,
        mismatch_2nd_array_i => s_mismatch_2nd_array,
        MISMATCH_O           => MISMATCH,
        MISMATCH_2ND_O       => MISMATCH_2ND);

  end generate if_TMR_generate;


end architecture structural;
