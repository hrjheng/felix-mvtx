-------------------------------------------------------------------------------
-- Title      : CAN High Level Protocol (HLP)
-- Project    : CAN Bus for DCS in the ITS Readout Unit
-------------------------------------------------------------------------------
-- File       : can_hlp_fsm.vhd
-- Author     : Simon Voigt Nesbø
-- Company    :
-- Created    : 2018-03-30
-- Last update: 2020-09-04
-- Platform   :
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: FSM logic for the CAN bus DCS High Level Protocol (HLP)
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2018-03-30  1.0      simon   Created
-- 2018-03-30  1.1      AV      Sync reset
-- 2020-02-11  1.2      SVN     Update for new CAN controller
-- 2020-11-24           AV      Add reset for CAN_TX_MSG.data, data_length and arb_id_a
-------------------------------------------------------------------------------



library ieee;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;


library work;
use work.intercon_pkg.all;
use work.canola_pkg.all;
use work.can_hlp_pkg.all;

entity can_hlp_fsm is
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

    HLP_FSM_STATE_O : out std_logic_vector(C_HLP_FSM_STATE_BITSIZE-1 downto 0);
    HLP_FSM_STATE_I : in  std_logic_vector(C_HLP_FSM_STATE_BITSIZE-1 downto 0));

end entity can_hlp_fsm;


architecture rtl of can_hlp_fsm is
  constant C_WB_FIFO_RW_BIT_READ_VAL  : std_logic := '0';
  constant C_WB_FIFO_RW_BIT_WRITE_VAL : std_logic := '1';

  signal s_can_rx_msg_available : std_logic;
  signal s_can_rx_msg           : can_msg_t;

  signal s_fsm_state_out   : hlp_fsm_state_t := ST_IDLE;
  signal s_fsm_state_voted : hlp_fsm_state_t;

  attribute fsm_encoding                      : string;
  attribute fsm_encoding of s_fsm_state_out   : signal is "sequential";
  attribute fsm_encoding of s_fsm_state_voted : signal is "sequential";

begin  -- architecture rtl

  -- Convert HLP FSM state register output to std_logic_vector
  HLP_FSM_STATE_O <= std_logic_vector(to_unsigned(hlp_fsm_state_t'pos(s_fsm_state_out),
                                                  C_HLP_FSM_STATE_BITSIZE));

  -- Convert voted HLP FSM state register input from std_logic_vector to hlp_fsm_state_t
  s_fsm_state_voted <= hlp_fsm_state_t'val(to_integer(unsigned(HLP_FSM_STATE_I)));

  -- Extended ID and remote requests are not used
  CAN_TX_MSG.arb_id_b       <= (others => '0');
  CAN_TX_MSG.remote_request <= '0';
  CAN_TX_MSG.ext_id         <= '0';


  proc_fsm : process (CLK) is
  begin  -- process proc_fsm
    if rising_edge(CLK) then
      -- Default values
      DP0_WR_O                   <= '0';
      DP1_RD_O                   <= '0';
      CAN_TX_START               <= '0';
      HLP_MSG_DROPPED_COUNT_UP   <= '0';
      HLP_READ_COUNT_UP          <= '0';
      HLP_WRITE_COUNT_UP         <= '0';
      HLP_STATUS_COUNT_UP        <= '0';
      HLP_ALERT_COUNT_UP         <= '0';
      HLP_UNKNOWN_COUNT_UP       <= '0';
      HLP_LENGTH_ERROR_COUNT_UP  <= '0';
      HLP_NODE_ID_ERROR_COUNT_UP <= '0';

      CAN_TX_MSG.arb_id_a(C_NODE_ID_range'range) <= CAN_NODE_ID;

      if RESET = '1' then
        s_fsm_state_out        <= ST_IDLE;
        s_can_rx_msg_available <= '0';
        DP0_DT_O               <= (others => '0');
        CAN_TX_MSG.data        <= (others => (others => '0'));
        CAN_TX_MSG.data_length <= (others => '0');
        CAN_TX_MSG.arb_id_a    <= (others => '0');
      else
        -- The shortest possible CAN message is 44 bauds
        -- (standard 11-bit ID, no payload, including EOF field)
        -- At 1 Mbit this message would take 44 microseconds to transmit.
        -- Although the CAN controller has no FIFO itself, this FSM
        -- should process a message and put it into the DP0 FIFO in a
        -- few 6.25 ns clock cycles, much faster than the CAN controller outputs
        -- the messages.
        if CAN_RX_MSG_VALID = '1' then

          -- In the (unlikely) event that we did not have time to
          -- process the previous CAN message
          -- In theory this can happen if the DP0 FIFO is full and
          -- we have to wait a long time for it, but in practice
          -- it will probably never happen
          if s_can_rx_msg_available = '1' then
            HLP_MSG_DROPPED_COUNT_UP <= '1';
          end if;

          s_can_rx_msg           <= CAN_RX_MSG;
          s_can_rx_msg_available <= '1';
        end if;


        case s_fsm_state_voted is
          when ST_IDLE =>
            if TEST_MODE = '1' then
              s_fsm_state_out <= ST_SETUP_HLP_TEST;

            elsif SEND_ALERT = '1' then
              s_fsm_state_out <= ST_SETUP_HLP_ALERT;

            elsif s_can_rx_msg_available = '1' then
              -- New CAN msg received, addressed to us?
              if s_can_rx_msg.ext_id = '0' and s_can_rx_msg.remote_request = '0' and
                (s_can_rx_msg.arb_id_a(C_NODE_ID_range'range) = CAN_NODE_ID or
                 s_can_rx_msg.arb_id_a(C_NODE_ID_range'range) = C_CAN_BROADCAST_ID)
              then
                s_fsm_state_out <= ST_CAN_MSG_RECEIVED;
              end if;

              s_can_rx_msg_available <= '0';

            -- Data in wishbone transaction result fifo (DP1)?
            elsif DP1_EPTY_I = '0' then
              DP1_RD_O        <= '1';
              s_fsm_state_out <= ST_WB_READ_DATA_WAIT1;

            elsif SEND_STATUS = '1' then
              -- Sending status messages has the lowest priority
              s_fsm_state_out <= ST_SETUP_HLP_STATUS;
            end if;

          when ST_CAN_MSG_RECEIVED =>
            case s_can_rx_msg.arb_id_a(C_CMD_ID_range'range) is
              when C_READ_COMMAND  => s_fsm_state_out <= ST_WB_READ_SETUP;
              when C_WRITE_COMMAND => s_fsm_state_out <= ST_WB_WRITE_SETUP;

              -- Read/write response, status and alert are upstreams messages only.
              -- Since we have already filtered out messages not addressed to us,
              -- we should never receive them. If we do it would indicate that
              -- another RU has been configured with the same node ID as us.
              when C_READ_RESPONSE  => s_fsm_state_out <= ST_HLP_NODE_ID_ERROR;
              when C_WRITE_RESPONSE => s_fsm_state_out <= ST_HLP_NODE_ID_ERROR;
              when C_STATUS         => s_fsm_state_out <= ST_HLP_NODE_ID_ERROR;
              when C_ALERT          => s_fsm_state_out <= ST_HLP_NODE_ID_ERROR;
              when C_TEST           => s_fsm_state_out <= ST_IDLE;  -- Ignore
              when others           => s_fsm_state_out <= ST_HLP_UNKNOWN;
            end case;

          when ST_WB_READ_SETUP =>
            HLP_READ_COUNT_UP <= '1';

            -- Read bit, address MSB, and address LSB
            DP0_DT_O(31)           <= C_WB_FIFO_RW_BIT_READ_VAL;
            DP0_DT_O(30 downto 24) <= s_can_rx_msg.data(0)(6 downto 0);
            DP0_DT_O(23 downto 16) <= s_can_rx_msg.data(1);

            if s_can_rx_msg.data_length /= C_READ_COMMAND_LEN then
              s_fsm_state_out <= ST_HLP_LENGTH_ERROR;
            else
              s_fsm_state_out <= ST_WB_READ_INITIATE;
            end if;

          when ST_WB_READ_INITIATE =>
            -- Push read request on to WB DP FIFO
            if DP0_FULL_I = '0' then
              DP0_WR_O <= '1';

              -- Go back to IDLE after pushing read request onto DP0 FIFO
              -- The response will appear on the DP1 FIFO when the wishbone
              -- transaction has completed
              s_fsm_state_out <= ST_IDLE;
            end if;

          -- Wait two clock cycles for data to arrive from DP FIFO
          when ST_WB_READ_DATA_WAIT1 =>
            s_fsm_state_out <= ST_WB_READ_DATA_WAIT2;

          when ST_WB_READ_DATA_WAIT2 =>
            s_fsm_state_out <= ST_WB_READ_DATA;

          when ST_WB_READ_DATA =>
            -- Note: Assuming here that only wishbone read transactions
            --       generates "replies" on the DP1 FIFO, so that every
            --       CAN message sent from this state should be a READ_RESPONSE
            CAN_TX_MSG.arb_id_a(C_CMD_ID_range'range) <= C_READ_RESPONSE;
            CAN_TX_MSG.data_length                    <= C_READ_RESPONSE_LEN;

            CAN_TX_MSG.data(0) <= DP1_DT_I(31 downto 24);
            CAN_TX_MSG.data(1) <= DP1_DT_I(23 downto 16);
            CAN_TX_MSG.data(2) <= DP1_DT_I(15 downto 8);
            CAN_TX_MSG.data(3) <= DP1_DT_I(7 downto 0);

            s_fsm_state_out <= ST_CAN_MSG_SEND;

          when ST_WB_WRITE_SETUP =>
            HLP_WRITE_COUNT_UP <= '1';

            DP0_DT_O(31)           <= C_WB_FIFO_RW_BIT_WRITE_VAL;
            DP0_DT_O(30 downto 24) <= s_can_rx_msg.data(0)(6 downto 0);
            DP0_DT_O(23 downto 16) <= s_can_rx_msg.data(1);
            DP0_DT_O(15 downto 8)  <= s_can_rx_msg.data(2);
            DP0_DT_O(7 downto 0)   <= s_can_rx_msg.data(3);

            -- Repond with the same data
            CAN_TX_MSG.arb_id_a(C_CMD_ID_range'range) <= C_WRITE_RESPONSE;
            CAN_TX_MSG.data_length                    <= C_WRITE_RESPONSE_LEN;

            CAN_TX_MSG.data(0) <= C_WB_FIFO_RW_BIT_READ_VAL &
                                  s_can_rx_msg.data(0)(6 downto 0);
            CAN_TX_MSG.data(1) <= s_can_rx_msg.data(1);
            CAN_TX_MSG.data(2) <= s_can_rx_msg.data(2);
            CAN_TX_MSG.data(3) <= s_can_rx_msg.data(3);

            if s_can_rx_msg.data_length /= C_WRITE_COMMAND_LEN then
              s_fsm_state_out <= ST_HLP_LENGTH_ERROR;
            else
              s_fsm_state_out <= ST_WB_WRITE_INITIATE;
            end if;

          when ST_WB_WRITE_INITIATE =>
            -- Push write request on to WB DP FIFO
            if DP0_FULL_I = '0' then
              DP0_WR_O <= '1';

              -- Send write response
              s_fsm_state_out <= ST_CAN_MSG_SEND;
            end if;

          when ST_SETUP_HLP_TEST =>
            CAN_TX_MSG.arb_id_a(C_CMD_ID_range'range) <= C_TEST;
            CAN_TX_MSG.data_length <= C_TEST_LEN;

            -- Send 010101... pattern so we have a
            -- lot of edges for eye diagram measurements
            CAN_TX_MSG.data(0) <= x"AA";
            CAN_TX_MSG.data(1) <= x"AA";
            CAN_TX_MSG.data(2) <= x"AA";
            CAN_TX_MSG.data(3) <= x"AA";
            CAN_TX_MSG.data(4) <= x"AA";
            CAN_TX_MSG.data(5) <= x"AA";
            CAN_TX_MSG.data(6) <= x"AA";
            CAN_TX_MSG.data(7) <= x"AA";

            s_fsm_state_out <= ST_CAN_MSG_SEND;

          when ST_SETUP_HLP_STATUS =>
            HLP_STATUS_COUNT_UP <= '1';

            CAN_TX_MSG.arb_id_a(C_CMD_ID_range'range) <= C_STATUS;
            CAN_TX_MSG.data_length <= C_STATUS_LEN;

            CAN_TX_MSG.data(0) <= STATUS_ALERT_DATA(7 downto 0);
            CAN_TX_MSG.data(1) <= STATUS_ALERT_DATA(15 downto 8);
            CAN_TX_MSG.data(2) <= STATUS_ALERT_DATA(23 downto 16);
            CAN_TX_MSG.data(3) <= STATUS_ALERT_DATA(31 downto 24);

            s_fsm_state_out     <= ST_CAN_MSG_SEND;

          when ST_SETUP_HLP_ALERT =>
            HLP_ALERT_COUNT_UP <= '1';

            CAN_TX_MSG.arb_id_a(C_CMD_ID_range'range) <= C_ALERT;
            CAN_TX_MSG.data_length <= C_ALERT_LEN;

            CAN_TX_MSG.data(0) <= STATUS_ALERT_DATA(7 downto 0);
            CAN_TX_MSG.data(1) <= STATUS_ALERT_DATA(15 downto 8);

            s_fsm_state_out <= ST_CAN_MSG_SEND;

          when ST_CAN_MSG_SEND =>
            -- Wait for CAN controller to not be busy
            if CAN_TX_BUSY = '0' then
              CAN_TX_START    <= '1';
              s_fsm_state_out <= ST_IDLE;
            end if;

          when ST_HLP_NODE_ID_ERROR =>
            HLP_NODE_ID_ERROR_COUNT_UP <= '1';
            s_fsm_state_out            <= ST_IDLE;

          when ST_HLP_LENGTH_ERROR =>
            HLP_LENGTH_ERROR_COUNT_UP <= '1';
            s_fsm_state_out           <= ST_IDLE;

          when ST_HLP_UNKNOWN =>
            HLP_UNKNOWN_COUNT_UP <= '1';
            s_fsm_state_out      <= ST_IDLE;

          when others =>
            s_fsm_state_out <= ST_IDLE;

        end case;
      end if;
    end if;
  end process proc_fsm;

end architecture rtl;
