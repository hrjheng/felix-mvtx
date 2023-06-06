-------------------------------------------------------------------------------
-- Title      : CAN DCS HLP Wishbone Slave Registers
-- Project    : ITS RU FPGA
-------------------------------------------------------------------------------
-- File       : can_hlp_wishbone_pkg.vhd
-- Author     : Simon Voigt Nesbø
-- Company    : Western Norway University of Applied Sciences
-- Created    : 2018-04-11
-- Last update: 2020-10-26
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wishbone slave for CAN bus DCS HLP registers. Based on
--              implementation in ws_usb_if.vhd by Matteo Lupi
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-04-11  1.0      simon   Created
-- 2019-01-15  1.1      AV      Changed to ws_reg version
-- 2020-10-26  1.2      simon   Update for new CAN controller
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.can_hlp_pkg.all;
use work.canola_pkg.all;
use work.intercon_pkg.all;


package can_hlp_wishbone_pkg is

  -----------------------------------------------------------------------------
  -- Wishbone registers - bit field indexes
  -----------------------------------------------------------------------------

  -- Control register
  constant C_CTRL_range                  : std_logic_vector(2 downto 0) := (others => '0');
  constant C_CTRL_TRIPLE_SAMPLING_EN_bit : natural                      := 0;
  constant C_CTRL_RETRANSMIT_EN_bit      : natural                      := 1;
  constant C_CTRL_TEST_MODE_EN_bit       : natural                      := 2;

  -- Status register
  constant C_STATUS_range             : std_logic_vector(2 downto 0) := (others => '0');
  constant C_STATUS_ERROR_ACTIVE_bit  : natural                      := 0;
  constant C_STATUS_ERROR_PASSIVE_bit : natural                      := 1;
  constant C_STATUS_BUS_OFF_bit       : natural                      := 2;

  constant C_TEST_REG_range       : std_logic_vector(15 downto 0)                          := (others => '0');
  constant C_CAN_PROP_SEG_range   : std_logic_vector(C_PROP_SEG_WIDTH-1 downto 0)          := (others => '0');
  constant C_CAN_PHASE_SEG1_range : std_logic_vector(C_PHASE_SEG1_WIDTH-1 downto 0)        := (others => '0');
  constant C_CAN_PHASE_SEG2_range : std_logic_vector(C_PHASE_SEG2_WIDTH-1 downto 0)        := (others => '0');
  constant C_CAN_SJW_range        : std_logic_vector(C_SYNC_JUMP_WIDTH_BITSIZE-1 downto 0) := (others => '0');
  constant C_CAN_CLK_SCALE_range  : std_logic_vector(C_TIME_QUANTA_WIDTH-1 downto 0)       := (others => '0');

  -- Registers with write access that are accessed by CAN/HLP logic
  type t_can_hlp_wb_regs is record
    CTRL           : std_logic_vector(C_CTRL_range'range);
    TEST_REG       : std_logic_vector(C_TEST_REG_range'range);
    CAN_PROP_SEG   : std_logic_vector(C_CAN_PROP_SEG_range'range);
    CAN_PHASE_SEG1 : std_logic_vector(C_CAN_PHASE_SEG1_range'range);
    CAN_PHASE_SEG2 : std_logic_vector(C_CAN_PHASE_SEG2_range'range);
    CAN_SJW        : std_logic_vector(C_CAN_SJW_range'range);
    CAN_CLK_SCALE  : std_logic_vector(C_CAN_CLK_SCALE_range'range);
  end record t_can_hlp_wb_regs;

  -----------------------------------------------------------------------------
  -- Wishbone registers and fields - default/reset values
  -----------------------------------------------------------------------------
  constant C_CTRL_TRIPLE_SAMPLING_EN_RESET_VAL : std_logic := '0';
  constant C_CTRL_RETRANSMIT_EN_RESET_VAL      : std_logic := '1';
  constant C_CTRL_TEST_MODE_EN_RESET_VAL       : std_logic := '0';

  constant C_CTRL_RESET_VAL : std_logic_vector(C_CTRL_range'range) :=
    (C_CTRL_TRIPLE_SAMPLING_EN_bit => C_CTRL_TRIPLE_SAMPLING_EN_RESET_VAL,
     C_CTRL_RETRANSMIT_EN_bit      => C_CTRL_RETRANSMIT_EN_RESET_VAL,
     C_CTRL_TEST_MODE_EN_bit       => C_CTRL_TEST_MODE_EN_RESET_VAL);

  -- One baud consists of one time quanta for the sync segment (not configurable),
  -- and the time quantas for the prop and phase segments (configurable).
  -- Note that the number of time quantas for the segments is NOT given by the
  -- numeric value of PROP_SEG and PHASE_SEG1/2, but by the length of the sequence
  -- of '1' bits, starting from LSB.
  constant C_CAN_PROP_SEG_RESET_VAL   : std_logic_vector(C_CAN_PROP_SEG_range'range)   := "111111";
  constant C_CAN_PHASE_SEG1_RESET_VAL : std_logic_vector(C_CAN_PHASE_SEG1_range'range) := "011111";
  constant C_CAN_PHASE_SEG2_RESET_VAL : std_logic_vector(C_CAN_PHASE_SEG2_range'range) := "001111";

  constant C_CAN_SJW_RESET_VAL : std_logic_vector(C_CAN_SJW_range'range)
    := std_logic_vector(to_unsigned(2, C_SYNC_JUMP_WIDTH_BITSIZE));

  -- C_CAN_CLOCK_SCALE_RESET_VAL configures clock scale to generate time quantas
  -- The actual baud rate depends on CAN_CLOCK_SCALE, CAN_PROP_SEG,
  -- CAN_PHASE_SEG1, and CAN_PHASE_SEG2.
  --
  -- Baud rate = 1 / (number of time quantas per baud * time quanta period)
  --           = 1 / ((1 + prop_seg + phase_seg1 + phase_seg2) * (Tclk x (1 + clock_scale)))
  -- Clock scale = 1 / (Baud rate * num time quantas * Tclk) - 1
  --
  -- With PROP_SEG = 111111, PHASE_SEG1 = 11111, PHASE_SEG2 = 1111,
  -- the number of time quantas (including sync seg) = 1 + 6 + 5 + 4 = 16

  -- Clock scale = 39 (0x27): 250 kbit baud rate with 16 time quantas
  constant C_CAN_CLK_SCALE_RESET_VAL : std_logic_vector(C_TIME_QUANTA_WIDTH-1 downto 0) := x"27";

  constant C_TEST_REG_RESET_VAL : std_logic_vector(C_TEST_REG_range'range) := (others => '0');


  -----------------------------------------------------------------------------
  -- Mapping of WB Registers
  -----------------------------------------------------------------------------
  type WB_ADD is (
    A_CTRL,
    A_STATUS,
    A_CAN_PROP_SEG,
    A_CAN_PHASE_SEG1,
    A_CAN_PHASE_SEG2,
    A_CAN_SJW,
    A_CAN_CLK_SCALE,
    A_CAN_TEC,
    A_CAN_REC,
    A_TEST_REG
    );

  constant NR_REGS : natural := WB_ADD'pos(WB_ADD'high) + 1;

  -----------------------------------------------------------------------------
  -- Register write enable
  -----------------------------------------------------------------------------
  constant C_WB_ADD_WE : t_wbs_reg_we_array(NR_REGS-1 downto 0) := (
    WB_ADD'pos(A_CTRL)           => rw,
    WB_ADD'pos(A_STATUS)         => r,
    WB_ADD'pos(A_CAN_PROP_SEG)   => rw,
    WB_ADD'pos(A_CAN_PHASE_SEG1) => rw,
    WB_ADD'pos(A_CAN_PHASE_SEG2) => rw,
    WB_ADD'pos(A_CAN_SJW)        => rw,
    WB_ADD'pos(A_CAN_CLK_SCALE)  => rw,
    WB_ADD'pos(A_CAN_TEC)        => r,
    WB_ADD'pos(A_CAN_REC)        => r,
    WB_ADD'pos(A_TEST_REG)       => rw);

  -----------------------------------------------------------------------------
  -- Reset value for writable registers
  -----------------------------------------------------------------------------
  constant C_WISHBONE_DEFAULT : t_wbs_reg_array(NR_REGS-1 downto 0) := (
    WB_ADD'pos(A_CTRL)           => wb_resize(C_CTRL_RESET_VAL(C_CTRL_range'range)),
    WB_ADD'pos(A_CAN_PROP_SEG)   => wb_resize(C_CAN_PROP_SEG_RESET_VAL(C_CAN_PROP_SEG_range'range)),
    WB_ADD'pos(A_CAN_PHASE_SEG1) => wb_resize(C_CAN_PHASE_SEG1_RESET_VAL(C_CAN_PHASE_SEG1_range'range)),
    WB_ADD'pos(A_CAN_PHASE_SEG2) => wb_resize(C_CAN_PHASE_SEG2_RESET_VAL(C_CAN_PHASE_SEG2_range'range)),
    WB_ADD'pos(A_CAN_SJW)        => wb_resize(C_CAN_SJW_RESET_VAL(C_CAN_SJW_range'range)),
    WB_ADD'pos(A_CAN_CLK_SCALE)  => wb_resize(C_CAN_CLK_SCALE_RESET_VAL(C_CAN_CLK_SCALE_range'range)),
    WB_ADD'pos(A_TEST_REG)       => wb_resize(C_TEST_REG_RESET_VAL(C_TEST_REG_range'range)),
    others                       => x"0000"
    );

end package can_hlp_wishbone_pkg;
