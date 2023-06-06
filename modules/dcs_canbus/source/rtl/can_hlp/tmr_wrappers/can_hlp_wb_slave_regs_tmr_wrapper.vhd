-------------------------------------------------------------------------------
-- Title      : CAN HLP Wishbone Slave TMR Wrapper
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : can_hlp_wb_slave_regs_tmr_wrapper.vhd
-- Author     : Simon Voigt Nesbø
-- Company    : Western Norway University of Applied Sciences
-- Created    : 2020-03-04
-- Last update: 2020-10-04
-- Platform   : Xilinx Vivado 2018.3
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: TMR wrapper for wishbone slave for CAN HLP module
-------------------------------------------------------------------------------
-- Copyright (c) 2020
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2020-03-04  1.0      SVN       Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.intercon_pkg.all;
use work.canola_pkg.all;
use work.can_hlp_pkg.all;
use work.can_hlp_wishbone_pkg.all;
use work.tmr_pkg.all;

entity can_hlp_wb_slave_regs_tmr_wrapper is
  generic (
    G_SEE_MITIGATION_TECHNIQUE : integer := 0;
    G_MISMATCH_EN              : integer := 1;
    G_MISMATCH_REGISTERED      : integer := 0;
    G_ADDITIONAL_MISMATCH      : integer := 1
    );
  port (
    WB_CLK                       : in  std_logic;
    WB_RST                       : in  std_logic;
    WB_WBS_I                     : in  t_wbs_i_array(0 to C_K_TMR-1);
    WB_WBS_O                     : out t_wbs_o_array(0 to C_K_TMR-1);

    -- CAN error state
    CAN_ERROR_ACTIVE  : in std_logic;
    CAN_ERROR_PASSIVE : in std_logic;
    CAN_BUS_OFF       : in std_logic;

    -- CAN Transmit Error Count (TEC) and Receive Error Count (REC)
    -- These are special internal counters in the CAN controller,
    -- and can not go in the monitor module.
    CAN_TEC : in std_logic_vector(C_ERROR_COUNT_LENGTH-1 downto 0);
    CAN_REC : in std_logic_vector(C_ERROR_COUNT_LENGTH-1 downto 0);

    -- Wishbone register outputs
    WISHBONE_REGS_O : out t_can_hlp_wb_regs;

    --Mismatch
    MISMATCH     : out std_logic;
    MISMATCH_2ND : out std_logic
    );
  attribute DONT_TOUCH                                      : string;
  attribute DONT_TOUCH of can_hlp_wb_slave_regs_tmr_wrapper : entity is "true";
end entity can_hlp_wb_slave_regs_tmr_wrapper;

architecture structural of can_hlp_wb_slave_regs_tmr_wrapper is

begin  -- architecture structural

  -- -----------------------------------------------------------------------
  -- Generate single instance of wishbone slave regs when TMR is disabled
  -- -----------------------------------------------------------------------
  if_NOMITIGATION_generate : if G_SEE_MITIGATION_TECHNIQUE = 0 generate
    signal s_wishbone_regs : t_can_hlp_wb_regs;
    signal s_wb_wbs_o      : wbs_o_type;
    signal s_wb_regs       : t_wbs_reg_array(NR_REGS-1 downto 0);
  begin
    INST_can_hlp_wb_slave_regs : entity work.can_hlp_wb_slave_regs
      port map (
        WB_CLK                  => WB_CLK,
        WB_RST                  => WB_RST,
        WB_WBS_I                => WB_WBS_I(0),
        WB_WBS_O                => s_wb_wbs_o,
        CAN_ERROR_ACTIVE        => CAN_ERROR_ACTIVE,
        CAN_ERROR_PASSIVE       => CAN_ERROR_PASSIVE,
        CAN_BUS_OFF             => CAN_BUS_OFF,
        CAN_TEC                 => CAN_TEC,
        CAN_REC                 => CAN_REC,
        WISHBONE_REGS_I         => s_wishbone_regs,
        WISHBONE_REGS_O         => s_wishbone_regs);

    WISHBONE_REGS_O <= s_wishbone_regs;
    WB_WBS_O(0)     <= s_wb_wbs_o;
    WB_WBS_O(1)     <= s_wb_wbs_o;
    WB_WBS_O(2)     <= s_wb_wbs_o;
    MISMATCH        <= '0';
    MISMATCH_2ND    <= '0';
  end generate if_NOMITIGATION_generate;


  -- -----------------------------------------------------------------------
  -- Generate three instances of wishbone slave regs when TMR is enabled
  -- -----------------------------------------------------------------------
  if_TMR_generate : if G_SEE_MITIGATION_TECHNIQUE = 1 generate
    signal s_wb_wbs_o : t_wbs_o_array(0 to C_K_TMR-1);

    type t_can_hlp_wb_regs_tmr is array (0 to C_K_TMR-1) of t_can_hlp_wb_regs;
    type t_can_prop_seg_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_CAN_PROP_SEG_range'range);
    type t_can_phase_seg1_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_CAN_PHASE_SEG1_range'range);
    type t_can_phase_seg2_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_CAN_PHASE_SEG2_range'range);
    type t_can_sjw_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_CAN_SJW_range'range);
    type t_can_clk_scale_tmr is array (0 to C_K_TMR-1) of std_logic_vector(C_CAN_CLK_SCALE_range'range);

    signal s_wishbone_regs_voted_in_tmr : t_can_hlp_wb_regs_tmr;
    signal s_wishbone_regs_out_tmr      : t_can_hlp_wb_regs_tmr;

    attribute DONT_TOUCH                                 : string;
    attribute DONT_TOUCH of s_wishbone_regs_voted_in_tmr : signal is "TRUE";
    attribute DONT_TOUCH of s_wishbone_regs_out_tmr      : signal is "TRUE";

    constant C_mismatch_wbs_o                  : integer := 0;
    constant C_mismatch_wbs_ctrl_reg           : integer := 1;
    constant C_mismatch_wbs_can_prop_seg_reg   : integer := 2;
    constant C_mismatch_wbs_can_phase_seg1_reg : integer := 3;
    constant C_mismatch_wbs_can_phase_seg2_reg : integer := 4;
    constant C_mismatch_wbs_can_sjw_reg        : integer := 5;
    constant C_mismatch_wbs_can_clk_scale_reg  : integer := 6;
    constant C_mismatch_wbs_can_test_reg       : integer := 7;
    constant C_MISMATCH_WIDTH                  : integer := 8;

    signal s_mismatch_array     : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);
    signal s_mismatch_2nd_array : std_ulogic_vector(C_MISMATCH_WIDTH-1 downto 0);

  begin
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
        mismatch_array_i     => s_mismatch_array,
        mismatch_2nd_array_i => s_mismatch_2nd_array,
        MISMATCH_O           => MISMATCH,
        MISMATCH_2ND_O       => MISMATCH_2ND);

    -- for generate
    for_TMR_generate : for i in 0 to C_K_TMR-1 generate

      INST_can_hlp_wb_slave_regs : entity work.can_hlp_wb_slave_regs
        port map (
          WB_CLK            => WB_CLK,
          WB_RST            => WB_RST,
          WB_WBS_I          => WB_WBS_I(0),
          WB_WBS_O          => s_wb_wbs_o(i),
          CAN_ERROR_ACTIVE  => CAN_ERROR_ACTIVE,
          CAN_ERROR_PASSIVE => CAN_ERROR_PASSIVE,
          CAN_BUS_OFF       => CAN_BUS_OFF,
          CAN_TEC           => CAN_TEC,
          CAN_REC           => CAN_REC,
          WISHBONE_REGS_I   => s_wishbone_regs_voted_in_tmr(i),
          WISHBONE_REGS_O   => s_wishbone_regs_out_tmr(i));

    end generate for_TMR_generate;

    WISHBONE_REGS_O <= s_wishbone_regs_voted_in_tmr(0);

    -------------------------------------------------------------------------
    -- Voter for triplicated wishbone bus signals
    -------------------------------------------------------------------------

    INST_majority_voter_triplicated_wbs_o :
      entity work.majority_voter_triplicated_wbs_o
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT         => s_wb_wbs_o,
          OUTPUT        => WB_WBS_O,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_o),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_o));


    -------------------------------------------------------------------------
    -- Voters for triplicated wishbone registers with write access
    -------------------------------------------------------------------------

    INST_majority_voter_triplicated_array_wrapper_ctrl_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CTRL_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CTRL,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CTRL,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CTRL,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CTRL,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CTRL,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CTRL,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_ctrl_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_ctrl_reg));

    INST_majority_voter_triplicated_array_wrapper_can_prop_seg_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_PROP_SEG_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CAN_PROP_SEG,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CAN_PROP_SEG,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CAN_PROP_SEG,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CAN_PROP_SEG,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CAN_PROP_SEG,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CAN_PROP_SEG,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_prop_seg_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_prop_seg_reg));

    INST_majority_voter_triplicated_array_wrapper_can_phase_seg1_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_PHASE_SEG1_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CAN_PHASE_SEG1,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CAN_PHASE_SEG1,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CAN_PHASE_SEG1,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CAN_PHASE_SEG1,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CAN_PHASE_SEG1,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CAN_PHASE_SEG1,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_phase_seg1_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_phase_seg1_reg));

    INST_majority_voter_triplicated_array_wrapper_can_phase_seg2_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_PHASE_SEG2_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CAN_PHASE_SEG2,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CAN_PHASE_SEG2,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CAN_PHASE_SEG2,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CAN_PHASE_SEG2,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CAN_PHASE_SEG2,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CAN_PHASE_SEG2,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_phase_seg2_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_phase_seg2_reg));

    INST_majority_voter_triplicated_array_wrapper_can_sjw_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_SJW_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CAN_SJW,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CAN_SJW,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CAN_SJW,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CAN_SJW,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CAN_SJW,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CAN_SJW,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_sjw_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_sjw_reg));

    INST_majority_voter_triplicated_array_wrapper_can_clk_scale_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => C_CAN_CLK_SCALE_range'length)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).CAN_CLK_SCALE,
          INPUT_B       => s_wishbone_regs_out_tmr(1).CAN_CLK_SCALE,
          INPUT_C       => s_wishbone_regs_out_tmr(2).CAN_CLK_SCALE,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).CAN_CLK_SCALE,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).CAN_CLK_SCALE,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).CAN_CLK_SCALE,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_clk_scale_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_clk_scale_reg));

    INST_majority_voter_triplicated_array_wrapper_test_reg :
      entity work.majority_voter_triplicated_array_wrapper
        generic map (
          G_MISMATCH_EN         => G_MISMATCH_EN,
          G_ADDITIONAL_MISMATCH => G_ADDITIONAL_MISMATCH,
          G_MISMATCH_REGISTERED => G_MISMATCH_REGISTERED,
          C_WIDTH               => WB_DATA_WIDTH)
        port map (
          ASSERTION_CLK => WB_CLK,
          ASSERTION_RST => WB_RST,
          INPUT_A       => s_wishbone_regs_out_tmr(0).TEST_REG,
          INPUT_B       => s_wishbone_regs_out_tmr(1).TEST_REG,
          INPUT_C       => s_wishbone_regs_out_tmr(2).TEST_REG,
          OUTPUT_A      => s_wishbone_regs_voted_in_tmr(0).TEST_REG,
          OUTPUT_B      => s_wishbone_regs_voted_in_tmr(1).TEST_REG,
          OUTPUT_C      => s_wishbone_regs_voted_in_tmr(2).TEST_REG,
          MISMATCH      => s_mismatch_array(C_mismatch_wbs_can_test_reg),
          MISMATCH_2ND  => s_mismatch_2nd_array(C_mismatch_wbs_can_test_reg));

  end generate if_TMR_generate;

end architecture structural;
