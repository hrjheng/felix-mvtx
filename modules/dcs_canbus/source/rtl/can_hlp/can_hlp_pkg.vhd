-------------------------------------------------------------------------------
-- Title      : CAN High Level Protocol (HLP)
-- Project    : CAN Bus DCS for ITS Readout Unit
-------------------------------------------------------------------------------
-- File       : can_hlp_glue_pkg.vhd
-- Author     : Simon Voigt Nesbø
-- Company    :
-- Created    : 2018-04-03
-- Last update: 2020-10-26
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Package with definitions used in can_hlp.vhd
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-04-03  1.0      simon   Created
-- 2020-10-26  1.1      simon   Update for new CAN controller
-------------------------------------------------------------------------------


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

library work;
use work.canola_pkg.all;

package can_hlp_pkg is

  constant C_CAN_BROADCAST_ID : std_logic_vector(7 downto 0) := x"7F";

  constant C_NODE_ID_range : std_logic_vector(10 downto 3) := (others => '0');
  constant C_CMD_ID_range  : std_logic_vector(2 downto 0)  := (others => '0');

  -- CAN HLP command types
  constant C_ALERT          : std_logic_vector(C_CMD_ID_range'range) := "000";
  constant C_WRITE_COMMAND  : std_logic_vector(C_CMD_ID_range'range) := "010";
  constant C_WRITE_RESPONSE : std_logic_vector(C_CMD_ID_range'range) := "011";
  constant C_READ_COMMAND   : std_logic_vector(C_CMD_ID_range'range) := "100";
  constant C_READ_RESPONSE  : std_logic_vector(C_CMD_ID_range'range) := "101";
  constant C_STATUS         : std_logic_vector(C_CMD_ID_range'range) := "110";
  constant C_TEST           : std_logic_vector(C_CMD_ID_range'range) := "111";

  constant C_ALERT_LEN          : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"2";
  constant C_READ_COMMAND_LEN   : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"2";
  constant C_WRITE_COMMAND_LEN  : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"4";
  constant C_READ_RESPONSE_LEN  : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"4";
  constant C_WRITE_RESPONSE_LEN : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"4";
  constant C_STATUS_LEN         : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"4";
  constant C_TEST_LEN           : std_logic_vector(C_DLC_LENGTH-1 downto 0) := x"8";

  type hlp_fsm_state_t is (ST_IDLE,
                           ST_CAN_MSG_RECEIVED,
                           ST_WB_READ_SETUP,
                           ST_WB_READ_INITIATE,
                           ST_WB_READ_DATA,
                           ST_WB_READ_DATA_WAIT1,
                           ST_WB_READ_DATA_WAIT2,
                           ST_WB_WRITE_SETUP,
                           ST_WB_WRITE_INITIATE,
                           ST_CAN_MSG_SEND,
                           ST_SETUP_HLP_TEST,
                           ST_SETUP_HLP_STATUS,
                           ST_SETUP_HLP_ALERT,
                           ST_HLP_NODE_ID_ERROR,
                           ST_HLP_LENGTH_ERROR,
                           ST_HLP_UNKNOWN);

  constant C_HLP_FSM_STATE_BITSIZE : natural :=
    integer(ceil(log2(1.0+real(hlp_fsm_state_t'pos(hlp_fsm_state_t'high)))));

  -- Defines the width of the counter used to generate time quanta pulses
  -- 8 bits allows for baud rates of 100 kbit and a bit below.
  -- 6 bits allows for baud rate down to exactly 250 kbit.
  constant C_TIME_QUANTA_WIDTH : natural := 8;

  -- Maximum number of times the CAN controller is allowed to attempt
  -- retransmission of a message.
  -- Note: Since we have up to 12 RUs on the same CAN bus line,
  -- the controller may have to retry up to 11 times before it's turn in
  -- case of broadcast, so this constant should be higher than that.
  constant C_CAN_RETRANSMIT_COUNT_MAX : natural := 16;

end can_hlp_pkg;
