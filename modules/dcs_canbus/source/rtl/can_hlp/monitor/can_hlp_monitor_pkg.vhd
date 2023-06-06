-------------------------------------------------------------------------------
-- Title      : CAN HLP Monitor Package
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : can_hlp_monitor_pkg.vhd
-- Author     : Simon Voigt nesbø
-- Company    :
-- Created    : 2020-02-11
-- Last update: 2020-02-14
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93
-------------------------------------------------------------------------------
-- Description: Definitions for the CAN HLP monitor
-------------------------------------------------------------------------------
-- Copyright (c) 2020 CERN
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2020-02-11  1.0      SVN       Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.intercon_pkg.all;
use work.tmr_pkg.all;

package can_hlp_monitor_pkg is

  -- The counter registers start at this address,
  -- because the ws_counter_monitor has two registers
  -- position 0 and 1.
  -- See ws_counter_monitor.vhd
  constant C_CNTR_START_ADDR : integer := 2;

  -----------------------------------------------------------------------------
  -- Numbering of 32b registers
  -----------------------------------------------------------------------------

  -- 32-bit counters
  constant C_CNTR_HLP_READ_LOW         : integer := 0;
  constant C_CNTR_HLP_READ_HIGH        : integer := 1;
  constant C_CNTR_HLP_WRITE_LOW        : integer := 2;
  constant C_CNTR_HLP_WRITE_HIGH       : integer := 3;
  constant C_CNTR_CAN_TX_MSG_SENT_LOW  : integer := 4;
  constant C_CNTR_CAN_TX_MSG_SENT_HIGH : integer := 5;
  constant C_CNTR_CAN_RX_MSG_RECV_LOW  : integer := 6;
  constant C_CNTR_CAN_RX_MSG_RECV_HIGH : integer := 7;

  -- 16-bit counters
  constant C_CNTR_HLP_STATUS         : integer := 8;
  constant C_CNTR_HLP_ALERT          : integer := 9;
  constant C_CNTR_HLP_UNKNOWN        : integer := 10;
  constant C_CNTR_HLP_LENGTH_ERROR   : integer := 11;
  constant C_CNTR_HLP_MSG_DROPPED    : integer := 12;
  constant C_CNTR_CAN_TX_ACK_ERROR   : integer := 13;
  constant C_CNTR_CAN_TX_ARB_LOST    : integer := 14;
  constant C_CNTR_CAN_TX_BIT_ERROR   : integer := 15;
  constant C_CNTR_CAN_TX_RETRANSMIT  : integer := 16;
  constant C_CNTR_CAN_RX_CRC_ERROR   : integer := 17;
  constant C_CNTR_CAN_RX_FORM_ERROR  : integer := 18;
  constant C_CNTR_CAN_RX_STUFF_ERROR : integer := 19;
  constant C_NR_REGS                 : integer := 20;

  -----------------------------------------------------------------------------
  -- Numbering of counters, used for the RESET bit mapping
  -----------------------------------------------------------------------------
  -- 32-bit counters
  constant C_CNTR_bit_HLP_READ        : integer := 0;
  constant C_CNTR_bit_HLP_WRITE       : integer := 1;
  constant C_CNTR_bit_CAN_TX_MSG_SENT : integer := 2;
  constant C_CNTR_bit_CAN_RX_MSG_RECV : integer := 3;
  constant C_NR_32_BIT_COUNTERS       : integer := 4;

  -- 16-bit counters
  constant C_CNTR_bit_HLP_STATUS         : integer := 4;
  constant C_CNTR_bit_HLP_ALERT          : integer := 5;
  constant C_CNTR_bit_HLP_UNKNOWN        : integer := 6;
  constant C_CNTR_bit_HLP_LENGTH_ERROR   : integer := 7;
  constant C_CNTR_bit_HLP_MSG_DROPPED    : integer := 8;
  constant C_CNTR_bit_CAN_TX_ACK_ERROR   : integer := 9;
  constant C_CNTR_bit_CAN_TX_ARB_LOST    : integer := 10;
  constant C_CNTR_bit_CAN_TX_BIT_ERROR   : integer := 11;
  constant C_CNTR_bit_CAN_TX_RETRANSMIT  : integer := 12;
  constant C_CNTR_bit_CAN_RX_CRC_ERROR   : integer := 13;
  constant C_CNTR_bit_CAN_RX_FORM_ERROR  : integer := 14;
  constant C_CNTR_bit_CAN_RX_STUFF_ERROR : integer := 15;
  constant C_NR_COUNTERS                 : integer := C_CNTR_bit_CAN_RX_STUFF_ERROR+1;
  constant C_NR_16_BIT_COUNTERS          : integer := C_NR_COUNTERS-C_NR_32_BIT_COUNTERS;

  -- counters ranges definition
  constant C_CNTR_WIDE_range : std_logic_vector(2*WB_DATA_WIDTH-1 downto 0) := (others => '0');
  constant C_CNTR_STD_range  : std_logic_vector(WB_DATA_WIDTH-1 downto 0)   := (others => '0');

  constant C_CNTR_LSB_range : std_logic_vector(WB_DATA_WIDTH-1 downto 0)               := (others => '0');
  constant C_CNTR_MSB_range : std_logic_vector(2*WB_DATA_WIDTH-1 downto WB_DATA_WIDTH) := (others => '0');

end package can_hlp_monitor_pkg;

package body can_hlp_monitor_pkg is
end package body can_hlp_monitor_pkg;
