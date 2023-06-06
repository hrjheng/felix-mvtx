-------------------------------------------------------------------------------
-- Title      : Power Unit Controller
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_controller.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-04-26
-- Last update: 2019-09-06
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Top Controller for the Power Unit I2C main and aux busses
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-04-26  1.0      jschamba  Created
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;

library work;
use work.intercon_pkg.all;
use work.i2c_pkg.all;
use work.i2c_pu_main_pkg.all;
use work.xpm_cdc_components_pkg.all;
use work.i2c_pu_controller_pkg.all;


entity i2c_pu_controller is
  port (
    -- Wishbone interface signals
    WB_CLK                 : in  std_logic;  -- master clock input
    WB_RST                 : in  std_logic;  -- synchronous active high reset
    WB_WBS_PU_MAIN_I       : in  wbs_i_type;  -- Wishbone Inputs
    WB_WBS_PU_MAIN_O       : out wbs_o_type;  -- Wishbone Outputs
    WB_WBS_PU_AUX_I        : in  wbs_i_type;  -- Wishbone Inputs
    WB_WBS_PU_AUX_O        : out wbs_o_type;  -- Wishbone Outputs
    WB_WBS_PU_CTRL_I       : in  wbs_i_type;  -- Wishbone Inputs
    WB_WBS_PU_CTRL_O       : out wbs_o_type;  -- Wishbone Outputs
    -- controller input
    IS_MIDDLE_BARREL       : in  std_logic;
    -- debug output pulses
    PU_MAIN_COMPLETED_BYTE : out std_logic;  -- Pulse I2C byte completed
    PU_MAIN_AL_ERROR       : out std_logic;  -- Pulse I2C Arbitration Lost Error
    PU_MAIN_NOACK_ERROR    : out std_logic;  -- Pulse I2C NOACK Error
    PU_AUX_COMPLETED_BYTE  : out std_logic;  -- Pulse I2C byte completed
    PU_AUX_AL_ERROR        : out std_logic;  -- Pulse I2C Arbitration Lost Error
    PU_AUX_NOACK_ERROR     : out std_logic;  -- Pulse I2C NOACK Error
    REQ_FIFO_MAIN_OVF      : out std_logic;  -- Request FIFO overflow Main I2C
    RES_FIFO_MAIN_OVF      : out std_logic;  -- Result FIFO overflow Main I2C
    RES_FIFO_MAIN_UFL      : out std_logic;  -- Result FIFO underflow Main I2C
    REQ_FIFO_AUX_OVF       : out std_logic;  -- Request FIFO overflow Aux I2C
    RES_FIFO_AUX_OVF       : out std_logic;  -- Result FIFO overflow Aux I2C
    RES_FIFO_AUX_UFL       : out std_logic;  -- Result FIFO underflow Aux I2C
    -- "main" i2c lines
    SCL_PAD_i              : in  std_logic;  -- i2c clock line input
    SCL_PAD_o              : out std_logic;  -- i2c clock line output
    SCL_PAD_T              : out std_logic;  -- i2c clock line output enable, active low
    SDA_PAD_i              : in  std_logic;  -- i2c data line input
    SDA_PAD_o              : out std_logic;  -- i2c data line output
    SDA_PAD_T              : out std_logic;  -- i2c data line output enable, active low
    -- "aux" i2c lines
    SCL_AUX_PAD_i          : in  std_logic;  -- i2c clock line input
    SCL_AUX_PAD_o          : out std_logic;  -- i2c clock line output
    SCL_AUX_PAD_T          : out std_logic;  -- i2c clock line output enable, active low
    SDA_AUX_PAD_i          : in  std_logic;  -- i2c data line input
    SDA_AUX_PAD_o          : out std_logic;  -- i2c data line output
    SDA_AUX_PAD_T          : out std_logic  -- i2c data line output enable, active low
    );
end entity i2c_pu_controller;

architecture structural of i2c_pu_controller is

  signal iAdcChannel   : natural range 0 to C_MAX_ADC_CHANNELS;
  signal sAdcVals      : std_logic_vector(C_MAX_ADC_CHANNELS*16-1 downto 0);
  signal bLatchAdc     : boolean;
  signal bLatchAdc_fsm : boolean;
  
  type t_i2c_pu_state_main is (IDLE,
                               RESET_WB_CTR,
                               START_WB_REQ,
                               DO_WB_REQ,
                               START_TEMP0_WR,
                               DO_TEMP0_WR,
                               ERROR_TEMP0_WR,
                               START_TEMP0_RD,
                               DO_TEMP0_RD,
                               START_TEMP1_WR,
                               DO_TEMP1_WR,
                               ERROR_TEMP1_WR,
                               START_TEMP1_RD,
                               DO_TEMP1_RD,
                               START_TEMP2_WR,
                               DO_TEMP2_WR,
                               ERROR_TEMP2_WR,
                               START_TEMP2_RD,
                               DO_TEMP2_RD,
                               START_READ_BIAS_MASK,
                               READ_BIAS_MASK,
                               START_ADC_WR,
                               DO_ADC_WR,
                               ERROR_ADC_WR,
                               START_ADC_RD,
                               DO_ADC_RD,
                               COMPARE_TEMPS,
                               START_TURN_OFF_BIAS,
                               TURN_OFF_BIAS
                               );

  -- Main I2C bus signals
  signal sState_main : t_i2c_pu_state_main;

  signal s_start_main    : std_logic;
  signal s_i2c_data_main : std_logic_vector(15 downto 0);
  signal s_busy_main     : std_logic;
  signal sMainNoackError : std_logic;
  signal sMainAlError    : std_logic;

  signal s_main_wb_req_wr    : std_logic;
  signal s_main_wb_req_rd    : std_logic;
  signal s_main_wb_req_empty : std_logic;
  signal s_main_wb_req_dout  : std_logic_vector(36 downto 0);
  signal s_main_wb_req_din   : std_logic_vector(36 downto 0);

  signal s_main_wb_res_wr    : std_logic;
  signal s_main_wb_res_rd    : std_logic;
  signal s_main_wb_res_empty : std_logic;
  signal s_main_wb_res_dout  : std_logic_vector(30 downto 0);
  signal s_main_wb_res_din   : std_logic_vector(30 downto 0);
  signal s_txn_id_main       : std_logic_vector(14 downto 0);

  signal s_data_valid_main : std_logic;
  signal s_latch_data      : std_logic_vector(15 downto 0);

  signal s_byte0_main   : std_logic_vector(7 downto 0);
  signal s_byte1_main   : std_logic_vector(7 downto 0);
  signal s_byte2_main   : std_logic_vector(7 downto 0);
  signal s_byte3_main   : std_logic_vector(7 downto 0);
  signal s_address_main : std_logic_vector(4 downto 0);

  signal s_byte0_main_fsm   : std_logic_vector(7 downto 0);
  signal s_byte1_main_fsm   : std_logic_vector(7 downto 0);
  signal s_byte2_main_fsm   : std_logic_vector(7 downto 0);
  signal s_byte3_main_fsm   : std_logic_vector(7 downto 0);
  signal s_address_main_fsm : std_logic_vector(4 downto 0);

  signal iCountWbreqMain : natural;
  signal bCountMain      : boolean;
  signal bCountRstMain   : boolean;
  signal bFsm_main       : boolean;
  signal bLatchResMain   : boolean;
  signal bTurnOff        : boolean;
  signal bEnPwrValid     : boolean;
  signal bEnBiasValid    : boolean;
  

  -- Aux I2C bus signals
  type t_i2c_pu_state_aux is (IDLE,
                              RESET_WB_CTR,
                              START_WB_REQ,
                              DO_WB_REQ,
                              START_TURN_OFF_1_4,
                              TURN_OFF_1_4,
                              START_TURN_OFF_5_8,
                              TURN_OFF_5_8,
                              START_READ_ENABLE_1_4,
                              READ_ENABLE_1_4,
                              START_READ_ENABLE_5_8,
                              READ_ENABLE_5_8,
                              COMPARE_MASK
                              );

  signal sState_aux, sNextState_aux : t_i2c_pu_state_aux;

  signal s_start_aux    : std_logic;
  signal s_i2c_data_aux : std_logic_vector(15 downto 0);
  signal s_busy_aux     : std_logic;

  signal s_aux_wb_req_wr    : std_logic;
  signal s_aux_wb_req_rd    : std_logic;
  signal s_aux_wb_req_empty : std_logic;
  signal s_aux_wb_req_dout  : std_logic_vector(36 downto 0);
  signal s_aux_wb_req_din   : std_logic_vector(36 downto 0);

  signal s_aux_wb_res_wr    : std_logic;
  signal s_aux_wb_res_rd    : std_logic;
  signal s_aux_wb_res_empty : std_logic;
  signal s_aux_wb_res_dout  : std_logic_vector(30 downto 0);
  signal s_aux_wb_res_din   : std_logic_vector(30 downto 0);
  signal s_txn_id_aux       : std_logic_vector(14 downto 0);

  signal s_data_valid_aux : std_logic;

  signal s_byte3_aux   : std_logic_vector(7 downto 0);
  signal s_address_aux : std_logic_vector(4 downto 0);

  signal sTurnoffPwr1_4Mask : std_logic_vector(7 downto 0);
  signal sTurnoffPwr5_8Mask : std_logic_vector(7 downto 0);
  signal s_address_aux_fsm  : std_logic_vector(4 downto 0);

  signal iCountWbreqAux : natural;
  signal bCountAux      : boolean;
  signal bCountRstAux   : boolean;
  signal bFsm_aux       : boolean;
  signal bTurnoff1_4    : boolean;
  signal bTurnoff5_8    : boolean;

  -- Controller signals
  signal s_limit_temp0    : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_limit_temp1    : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_limit_temp2    : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_lo_limit_temp0 : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_lo_limit_temp1 : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_lo_limit_temp2 : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp0          : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp1          : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp2          : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp0_prev     : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp1_prev     : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_temp2_prev     : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_tripped        : std_logic_vector(WB_DATA_WIDTH-1 downto 0);
  signal s_enable_pwr     : std_logic_vector(C_MODULE_NUMBER*2-1 downto 0);
  signal s_bias           : std_logic_vector(C_MODULE_NUMBER-1 downto 0);
  signal s_enable_1_4     : std_logic_vector(7 downto 0);
  signal s_enable_5_8     : std_logic_vector(7 downto 0);
  signal s_power_mask     : std_logic_vector(C_MODULE_NUMBER*2-1 downto 0);
  signal s_bias_mask      : std_logic_vector(C_MODULE_NUMBER-1 downto 0);

  signal bLatchTemp0 : boolean;
  signal bLatchTemp1 : boolean;
  signal bLatchTemp2 : boolean;
  signal bLatchBias  : boolean;

  signal bLatchTemp0_fsm  : boolean;
  signal bLatchTemp1_fsm  : boolean;
  signal bLatchTemp2_fsm  : boolean;
  signal bLatchEnable_1_4 : boolean;
  signal bLatchEnable_5_8 : boolean;

  signal sTurnOff1_4 : std_logic;
  signal sTurnOff5_8 : std_logic;

  signal sFifoRst    : std_logic_vector(3 downto 0);
  signal sFifoRst_wb : std_logic_vector(3 downto 0);
  signal sMonEnabled : std_logic_vector(3 downto 0);

  signal sTempMonitoringEnabled : std_logic;

  signal sTurnoffBiasMask : std_logic_vector(7 downto 0);

  signal s_bias_wb : std_logic_vector(s_bias'range);

  signal bNokTemp0, bNokTemp0_prev : boolean;
  signal bNokTemp1, bNokTemp1_prev : boolean;
  signal bNokTemp2, bNokTemp2_prev : boolean;
  
begin

  s_enable_pwr <= s_enable_5_8 & s_enable_1_4;


  -----------------------------------------------------------------------------
  -- Determine the over temperature conditions and power masks mismatches
  -- and what to turn off
  -----------------------------------------------------------------------------
  p_check_trip_conditions : process (all) is
    variable vOverTempP0     : std_logic;
    variable vOverTempP1     : std_logic;
    variable vOverTempP2     : std_logic;
    variable vIsTripped      : std_logic;
    variable vConcatenate    : std_logic_vector(3 downto 0);
  begin


    if (sMonEnabled(C_INTERLOCK_ENABLE_P0) = '1') and bNokTemp0 and bNokTemp0_prev
    then
      vOverTempP0 := '1';
    else
      vOverTempP0 := '0';
    end if;

    if (sMonEnabled(C_INTERLOCK_ENABLE_P1) = '1') and bNokTemp1 and bNokTemp1_prev
    then
      vOverTempP1 := '1';
    else
      vOverTempP1 := '0';
    end if;

    if (sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1') and bNokTemp2 and bNokTemp2_prev
    then
      vOverTempP2 := '1';
    else
      vOverTempP2 := '0';
    end if;

    -- set initial value of turn off bit masks to expected values
    sTurnoffBiasMask   <= s_bias_mask;
    sTurnoffPwr1_4Mask <= s_power_mask(7 downto 0);
    sTurnoffPwr5_8Mask <= s_power_mask(15 downto 8);

    -- first check over temperature conditions
    vConcatenate := IS_MIDDLE_BARREL & vOverTempP0 & vOverTempP1 & vOverTempP2;
    case vConcatenate is
--    Middle Barrel
      when "1000" =>
        sTurnOff1_4 <= '0';
        sTurnOff5_8 <= '0';
      when "1010" =>
        sTurnOff1_4                  <= '1';
        sTurnOff5_8                  <= '0';
        sTurnoffBiasMask(1 downto 0) <= "11";
        sTurnoffPwr1_4Mask           <= x"00";
      when "1001" =>
        sTurnOff1_4                  <= '0';
        sTurnOff5_8                  <= '1';
        sTurnoffBiasMask(3 downto 2) <= "11";
        sTurnoffPwr5_8Mask           <= x"00";

--    Outer/Inner Barrel
      when "0000" =>
        sTurnOff1_4 <= '0';
        sTurnOff5_8 <= '0';
      when "0001" =>                  -- don't care P2
        sTurnOff1_4 <= '0';
        sTurnOff5_8 <= '0';

--    all other cases, turn everthing off
      when others =>
        sTurnOff1_4        <= '1';
        sTurnOff5_8        <= '1';
        sTurnOffBiasMask   <= x"FF";
        sTurnoffPwr1_4Mask <= x"00";
        sTurnoffPwr5_8Mask <= x"00";
    end case;

    -- then compare power/bias enables and masks,
    -- and modify the appropriate turnoff bits
    vIsTripped := '0';
    if sMonEnabled(C_INTERLOCK_ENABLE_PWR) = '1' then
      if s_bias_mask = x"FF" then
        -- no BIAS channels turned on: individual module linking only
        for i in 0 to 3 loop
          if bEnPwrValid and (s_enable_pwr(i*2+1 downto i*2) /= s_power_mask(i*2+1 downto i*2))
          then
            vIsTripped                           := '1';
            sTurnOff1_4                          <= '1';
            sTurnoffPwr1_4Mask(i*2+1 downto i*2) <= "00";
          end if;

          if bEnPwrValid and (s_enable_pwr(i*2+9 downto i*2+8) /= s_power_mask(i*2+9 downto i*2+8))
          then
            vIsTripped                           := '1';
            sTurnOff5_8                          <= '1';
            sTurnoffPwr5_8Mask(i*2+1 downto i*2) <= "00";
          end if;
        end loop;  -- i

      else
        -- BIAS turned on, do group linking:
        if IS_MIDDLE_BARREL = '1' then  -- middle barrel:
          -- link: B1 - xVDD1,xVDD2
          if (bEnPwrValid and (s_enable_pwr(3 downto 0) /= s_power_mask(3 downto 0))) or
            (bEnBiasValid and (s_bias(0) /= s_bias_mask(0)))
          then
            vIsTripped                     := '1';
            sTurnOff1_4                    <= '1';
            sTurnoffBiasMask(0)            <= '1';
            sTurnoffPwr1_4Mask(3 downto 0) <= "0000";
          end if;

          -- link: B2 - xVDD3,xVDD4
          if (bEnPwrValid and (s_enable_pwr(7 downto 4) /= s_power_mask(7 downto 4))) or
            (bEnBiasValid and (s_bias(1) /= s_bias_mask(1)))
          then
            vIsTripped                     := '1';
            sTurnOff1_4                    <= '1';
            sTurnoffBiasMask(1)            <= '1';
            sTurnoffPwr1_4Mask(7 downto 4) <= "0000";
          end if;

          -- link: B3 - xVDD5,xVDD6
          if (bEnPwrValid and (s_enable_pwr(11 downto 8) /= s_power_mask(11 downto 8))) or
            (bEnBiasValid and (s_bias(2) /= s_bias_mask(2)))
          then
            vIsTripped                     := '1';
            sTurnOff5_8                    <= '1';
            sTurnoffBiasMask(2)            <= '1';
            sTurnoffPwr5_8Mask(3 downto 0) <= "0000";
          end if;

          -- link: B4 - xVDD7,xVDD8
          if (bEnPwrValid and (s_enable_pwr(15 downto 12) /= s_power_mask(15 downto 12))) or
            (bEnBiasValid and (s_bias(3) /= s_bias_mask(3)))
          then
            vIsTripped                     := '1';
            sTurnOff5_8                    <= '1';
            sTurnoffBiasMask(3)            <= '1';
            sTurnoffPwr5_8Mask(7 downto 4) <= "0000";
          end if;

        else                            -- outer/inner barrel
          -- link: B1 - xVDD1,xVDD2
          if (bEnPwrValid and (s_enable_pwr(3 downto 0) /= s_power_mask(3 downto 0))) or
            (bEnBiasValid and (s_bias(0) /= s_bias_mask(0)))
          then
            vIsTripped                     := '1';
            sTurnOff1_4                    <= '1';
            sTurnoffBiasMask(0)            <= '1';
            sTurnoffPwr1_4Mask(3 downto 0) <= "0000";
          end if;

          -- link: B2 - xVDD3,xVDD4,xVDD5
          if (bEnPwrValid and (s_enable_pwr(9 downto 4) /= s_power_mask(9 downto 4))) or
            (bEnBiasValid and (s_bias(1) /= s_bias_mask(1)))
          then
            vIsTripped                     := '1';
            sTurnOff1_4                    <= '1';
            sTurnOff5_8                    <= '1';
            sTurnoffBiasMask(1)            <= '1';
            sTurnoffPwr1_4Mask(7 downto 4) <= "0000";
            sTurnoffPwr5_8Mask(1 downto 0) <= "00";
          end if;

          -- link B3 - xVDD6,xVDD7
          if (bEnPwrValid and (s_enable_pwr(13 downto 10) /= s_power_mask(13 downto 10))) or
            (bEnBiasValid and (s_bias(2) /= s_bias_mask(2)))
          then
            vIsTripped                     := '1';
            sTurnOff5_8                    <= '1';
            sTurnoffBiasMask(2)            <= '1';
            sTurnoffPwr5_8Mask(5 downto 2) <= "0000";
          end if;

        end if;                         -- if MIDDLE_BARREL
      end if;                           -- if s_bias_mask = x"FF"
    end if;                             -- if sMonEnabled

    
    -- log status of all the different trip conditions for wishbone
    s_tripped <= (C_TURNOFF1_4_bit  => sTurnOff1_4,
                  C_TURNOFF5_8_bit  => sTurnOff5_8,
                  C_OVERTEMP_P0_bit => vOverTempP0,
                  C_OVERTEMP_P1_bit => vOverTempP1,
                  C_OVERTEMP_P2_bit => vOverTempP2,
                  C_TRIPPED_bit     => vIsTripped,
                  others            => '0');
  end process p_check_trip_conditions;

  -----------------------------------------------------------------------------
  -- Controller wishbone
  -----------------------------------------------------------------------------
  sTempMonitoringEnabled <= sMonEnabled(C_INTERLOCK_ENABLE_P0) or sMonEnabled(C_INTERLOCK_ENABLE_P1) or sMonEnabled(C_INTERLOCK_ENABLE_P2);

  s_bias_wb <= (others => '1') when (sTempMonitoringEnabled = '0') else s_bias;
  
   INST_i2c_pu_controller_wb : entity work.i2c_pu_controller_wb
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_PU_CTRL_I,
      WB_WBS_O         => WB_WBS_PU_CTRL_O,
      LIMIT_TEMP0      => s_limit_temp0,
      LIMIT_TEMP1      => s_limit_temp1,
      LIMIT_TEMP2      => s_limit_temp2,
      LO_LIMIT_TEMP0   => s_lo_limit_temp0,
      LO_LIMIT_TEMP1   => s_lo_limit_temp1,
      LO_LIMIT_TEMP2   => s_lo_limit_temp2,
      TEMP0            => (s_temp0 and (s_temp0'range => sMonEnabled(C_INTERLOCK_ENABLE_P0))),
      TEMP1            => (s_temp1 and (s_temp1'range => sMonEnabled(C_INTERLOCK_ENABLE_P1))),
      TEMP2            => (s_temp2 and (s_temp2'range => sMonEnabled(C_INTERLOCK_ENABLE_P2))),
      TRIPPED          => s_tripped,
      ENABLE_PWR       => (s_enable_pwr and (s_enable_pwr'range => or_reduce(sMonEnabled))),
      ENABLE_BIAS      => s_bias_wb,
      POWER_MASK       => s_power_mask,
      BIAS_MASK        => s_bias_mask,
      FIFO_RST         => sFifoRst_wb,
      INTERLOCK_ENABLE => sMonEnabled,
      ADC_VALS         => sAdcVals
      );

  gen_reset : for i in 0 to sFifoRst'high generate
    sFifoRst(i) <= sFifoRst_wb(i) or WB_RST;
  end generate gen_reset;

  -----------------------------------------------------------------------------
  -- Main I2C
  -----------------------------------------------------------------------------
  -- wishbone interface for wrapper
  INST_i2c_pu_main_wb : entity work.i2c_pu_main_wb
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_PU_MAIN_I,
      WB_WBS_O         => WB_WBS_PU_MAIN_O,
      REQ_DATA_o       => s_main_wb_req_din,
      REQ_WREN_o       => s_main_wb_req_wr,
      I2C_DATA_i       => s_main_wb_res_dout(15 downto 0),
      I2C_TXN_ID_i     => s_main_wb_res_dout(30 downto 16),
      I2C_DATA_RDEN_o  => s_main_wb_res_rd,
      I2C_DATA_EMPTY_i => s_main_wb_res_empty
      );

  -- wishbone request FIFO
  INST_wb_request_fifo_main : xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",   --string; "auto", "block", or "distributed";
      ECC_MODE            => "no_ecc",  --string; "no_ecc" or "en_ecc";
      FIFO_WRITE_DEPTH    => 256,       --positive integer
      WRITE_DATA_WIDTH    => 37,        --positive integer
      WR_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_FULL_THRESH    => 250,       --positive integer
      FULL_RESET_VALUE    => 0,         --positive integer; 0 or 1;
      USE_ADV_FEATURES    => "0001",    --Enable [12:8] = data_valid, almost_empty, rd_data_count,
                                        --prog_empty, underflow, [4:0] = wr_ack, almost_full,
                                        --wr_data_count, prog_full, overflow
      READ_MODE           => "fwft",    --string; "std" or "fwft";
      FIFO_READ_LATENCY   => 0,         --positive integer;
      READ_DATA_WIDTH     => 37,        --positive integer
      RD_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_EMPTY_THRESH   => 5,         --positive integer
      DOUT_RESET_VALUE    => "0",       --string
      WAKEUP_TIME         => 0          --positive integer; 0 or 2;
      )
    port map (
      sleep         => '0',
      rst           => sFifoRst(0),
      wr_clk        => WB_CLK,
      wr_en         => s_main_wb_req_wr,
      din           => s_main_wb_req_din,
      full          => open,
      prog_full     => open,
      wr_data_count => open,
      overflow      => REQ_FIFO_MAIN_OVF,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => s_main_wb_req_rd,
      dout          => s_main_wb_req_dout,
      empty         => s_main_wb_req_empty,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => open,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open
      );

  -- latch bytes 2 and 3 (upper 15 bits) from req FIFO as transaction ID
  p_latch_txn_id_main : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        s_txn_id_main <= (others => '0');
      elsif s_start_main = '1' then
        s_txn_id_main <= s_main_wb_req_dout(30 downto 16);
      else
        s_txn_id_main <= s_txn_id_main;
      end if;
    end if;
  end process p_latch_txn_id_main;

  s_main_wb_res_din <= s_txn_id_main & s_i2c_data_main;

  -- wishbone results FIFO
  INST_wb_result_fifo_main : xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",   --string; "auto", "block", or "distributed";
      ECC_MODE            => "no_ecc",  --string; "no_ecc" or "en_ecc";
      FIFO_WRITE_DEPTH    => 256,       --positive integer
      WRITE_DATA_WIDTH    => 31,        --positive integer
      WR_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_FULL_THRESH    => 250,       --positive integer
      FULL_RESET_VALUE    => 0,         --positive integer; 0 or 1;
      USE_ADV_FEATURES    => "0101",    --Enable [12:8] = data_valid, almost_empty, rd_data_count,
                                        --prog_empty, underflow, [4:0] = wr_ack, almost_full,
                                        --wr_data_count, prog_full, overflow
      READ_MODE           => "fwft",    --string; "std" or "fwft";
      FIFO_READ_LATENCY   => 0,         --positive integer;
      READ_DATA_WIDTH     => 31,        --positive integer
      RD_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_EMPTY_THRESH   => 5,         --positive integer
      DOUT_RESET_VALUE    => "0",       --string
      WAKEUP_TIME         => 0          --positive integer; 0 or 2;
      )
    port map (
      sleep         => '0',
      rst           => sFifoRst(1),
      wr_clk        => WB_CLK,
      wr_en         => s_main_wb_res_wr,
      din           => s_main_wb_res_din,
      full          => open,
      prog_full     => open,
      wr_data_count => open,
      overflow      => RES_FIFO_MAIN_OVF,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => s_main_wb_res_rd,
      dout          => s_main_wb_res_dout,
      empty         => s_main_wb_res_empty,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => RES_FIFO_MAIN_UFL,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open
      );


  -- I2C wrapper
  INST_i2c_pu_wrapper_main : entity work.i2c_pu_wrapper_main
    port map (
      CLK            => WB_CLK,
      RST            => WB_RST,
      BYTE_0         => s_byte0_main,
      BYTE_1         => s_byte1_main,
      BYTE_2         => s_byte2_main,
      BYTE_3         => s_byte3_main,
      ADDRESS        => s_address_main,
      START          => s_start_main,
      BUSY           => s_busy_main,
      I2C_DATA_o     => s_i2c_data_main,
      DATA_VALID     => s_data_valid_main,
      COMPLETED_BYTE => PU_MAIN_COMPLETED_BYTE,
      AL_ERROR       => sMainAlError,
      NOACK_ERROR    => sMainNoackError,
      SCL_PAD_i      => SCL_PAD_i,
      SCL_PAD_o      => SCL_PAD_o,
      SCL_PAD_T      => SCL_PAD_T,
      SDA_PAD_i      => SDA_PAD_i,
      SDA_PAD_o      => SDA_PAD_o,
      SDA_PAD_T      => SDA_PAD_T
      );

  PU_MAIN_NOACK_ERROR <= sMainNoackError;
  PU_MAIN_AL_ERROR    <= sMainAlError;

  -- use a counter to cycle through the ADC channels
  p_ADC_counter: process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
       iAdcChannel <= 0; 
      else
        if sState_main = COMPARE_TEMPS then
          iAdcChannel <= (iAdcChannel + 1) mod C_MAX_ADC_CHANNELS;
        else
          iAdcChannel <= iAdcChannel;
        end if;
      end if;
    end if;
  end process p_ADC_counter;
  
  -- interface signals from FSM to I2C wrapper and control registers
  s_address_main <= s_address_main_fsm when bFsm_main else s_main_wb_req_dout(36 downto 32);
  s_byte0_main   <= s_byte0_main_fsm   when bFsm_main else s_main_wb_req_dout(15 downto 8);
  s_byte1_main   <= s_byte1_main_fsm   when bFsm_main else s_main_wb_req_dout(7 downto 0);
  s_byte2_main   <= s_byte2_main_fsm   when bFsm_main else s_main_wb_req_dout(31 downto 24);
  s_byte3_main   <= sTurnoffBiasMask   when bTurnOff else
                  s_byte3_main_fsm when bFsm_main else
                  s_main_wb_req_dout(23 downto 16);

  s_main_wb_res_wr <= s_data_valid_main when bLatchResMain else '0';

  bLatchTemp0 <= bLatchTemp0_fsm when bFsm_main else (s_data_valid_main = '1') and bLatchTemp0_fsm;
  bLatchTemp1 <= bLatchTemp1_fsm when bFsm_main else (s_data_valid_main = '1') and bLatchTemp1_fsm;
  bLatchTemp2 <= bLatchTemp2_fsm when bFsm_main else (s_data_valid_main = '1') and bLatchTemp2_fsm;

  bLatchAdc <= bLatchAdc_fsm when bFsm_main else (s_data_valid_main = '1') and bLatchAdc_fsm;
  
  s_latch_data <= x"FFFF" when bFsm_main else s_i2c_data_main;

  -- Count number of wishbone requests if loop is active;
  -- reset controlled by FSM
  -- used to limit the number of WB requests to execute before going
  -- through the temperature read loop again
  p_count_wbreq_main : process (WB_CLK) is
    variable doLoop : boolean;
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        iCountWbreqMain <= 0;
        doLoop          := false;
      else
        doLoop := sMonEnabled(C_INTERLOCK_ENABLE_P2 downto 0) /= "000";
        if bCountMain and doLoop then
          iCountWbReqMain <= iCountWbReqMain + 1;
        elsif bCountRstMain then
          iCountWbreqMain <= 0;
        else
          iCountWbReqMain <= iCountWbreqMain;
        end if;
      end if;
    end if;
  end process p_count_wbreq_main;

  -- Controller FSM synchronous state update for I2C main bus
  p_state_update : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        sState_main <= IDLE;

      else
        case sState_main is
          when IDLE =>
            if (s_main_wb_req_empty = '0') and (iCountWbreqMain < 2) then
              -- wishbone request FIFO has data, start I2C transaction
              sState_main <= START_WB_REQ;
            elsif sMonEnabled(C_INTERLOCK_ENABLE_P0) = '1' then
              sState_main <= START_TEMP0_WR;
            elsif sMonEnabled(C_INTERLOCK_ENABLE_P1) = '1' then
              sState_main <= START_TEMP1_WR;
            elsif sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1' then
              sState_main <= START_TEMP2_WR;
            elsif sMonEnabled(C_INTERLOCK_ENABLE_PWR) = '1' then
              sState_main <= START_READ_BIAS_MASK; 
            else
              sState_main <= RESET_WB_CTR;
            end if;

          when RESET_WB_CTR =>
            sState_main <= IDLE;

          when START_WB_REQ =>
            sState_main <= DO_WB_REQ;

          when DO_WB_REQ =>
            if s_busy_main = '0' then
              sState_main <= IDLE;
            end if;

          when START_TEMP0_WR =>
            sState_main <= DO_TEMP0_WR;

          when DO_TEMP0_WR =>
            if (sMainAlError = '1') or (sMainNoackError = '1') then
              sState_main <= ERROR_TEMP0_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_TEMP0_RD;
            end if;

          when ERROR_TEMP0_WR =>
            if (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P1) = '1') then
              sState_main <= START_TEMP1_WR;
            elsif (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1') then
              sState_main <= START_TEMP2_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_TEMP0_RD =>
            sState_main <= DO_TEMP0_RD;

          when DO_TEMP0_RD =>
            if (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P1) = '1') then
              sState_main <= START_TEMP1_WR;
            elsif (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1') then
              sState_main <= START_TEMP2_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_TEMP1_WR =>
            sState_main <= DO_TEMP1_WR;

          when DO_TEMP1_WR =>
            if (sMainAlError = '1') or (sMainNoackError = '1') then
              sState_main <= ERROR_TEMP1_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_TEMP1_RD;
            end if;

          when ERROR_TEMP1_WR =>
            if (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1') then
              sState_main <= START_TEMP2_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_TEMP1_RD =>
            sState_main <= DO_TEMP1_RD;

          when DO_TEMP1_RD =>
            if (s_busy_main = '0') and (sMonEnabled(C_INTERLOCK_ENABLE_P2) = '1') then
              sState_main <= START_TEMP2_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_TEMP2_WR =>
            sState_main <= DO_TEMP2_WR;

          when DO_TEMP2_WR =>
            if (sMainAlError = '1') or (sMainNoackError = '1') then
              sState_main <= ERROR_TEMP2_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_TEMP2_RD;
            end if;

          when ERROR_TEMP2_WR =>
            if s_busy_main = '0' then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_TEMP2_RD =>
            sState_main <= DO_TEMP2_RD;

          when DO_TEMP2_RD =>
            if (s_busy_main = '0') then
              sState_main <= START_READ_BIAS_MASK;
            end if;

          when START_READ_BIAS_MASK =>
            sState_main <= READ_BIAS_MASK;

          when READ_BIAS_MASK =>
            if s_busy_main = '0' then
              sState_main <= START_ADC_WR;
            end if;

          when START_ADC_WR =>
            sState_main <= DO_ADC_WR;

          when DO_ADC_WR =>
            if (sMainAlError = '1') or (sMainNoackError = '1') then
              sState_main <= ERROR_ADC_WR;
            elsif s_busy_main = '0' then
              sState_main <= START_ADC_RD;
            end if;

          when ERROR_ADC_WR =>
            if (s_busy_main = '0') then
              sState_main <= COMPARE_TEMPS;
            end if;

          when START_ADC_RD =>
            sState_main <= DO_ADC_RD;

          when DO_ADC_RD =>
            if (s_busy_main = '0') then
              sState_main <= COMPARE_TEMPS;
            end if;

          when COMPARE_TEMPS =>
            -- if any bias channels need to be turned off,
            -- and are not already turned off
            if ((sTurnOff1_4 = '1') or (sTurnOff5_8 = '1')) and (s_bias /= x"FF") then
              sState_main <= START_TURN_OFF_BIAS;
            else
              sState_main <= IDLE;
            end if;

          when START_TURN_OFF_BIAS =>
            sState_main <= TURN_OFF_BIAS;

          when TURN_OFF_BIAS =>
            if s_busy_main = '0' then
              sState_main <= IDLE;
            end if;

          when others =>
            sState_main <= IDLE;
        end case;

      end if;
    end if;
  end process p_state_update;

  -- Controller FSM outputs for I2C main bus
  p_output_logic_main : process (all) is
    variable vAdcChannel : std_logic_vector(5 downto 0);
  begin
    vAdcChannel := std_logic_vector(to_unsigned(iAdcChannel, 6));

    -- defaults:
    s_start_main       <= '0';
    s_main_wb_req_rd   <= '0';
    s_byte0_main_fsm   <= x"00";
    s_byte1_main_fsm   <= x"00";
    s_byte2_main_fsm   <= x"00";
    s_byte3_main_fsm   <= x"00";
    s_address_main_fsm <= "00000";
    bLatchTemp0_fsm    <= false;
    bLatchTemp1_fsm    <= false;
    bLatchTemp2_fsm    <= false;
    bLatchBias         <= false;
    bCountMain         <= false;
    bCountRstMain      <= false;
    bFsm_main          <= false;
    bTurnOff           <= false;
    bLatchResMain      <= false;
    bLatchAdc_fsm      <= false;

    case sState_main is
      when RESET_WB_CTR =>
        bCountRstMain      <= true;

      when START_WB_REQ =>
        s_start_main       <= '1';
        s_main_wb_req_rd   <= '1';
        bCountMain         <= true;

      when DO_WB_REQ =>
        bLatchResMain      <= true;

      when START_TEMP0_WR =>
        s_start_main       <= '1';
        s_byte0_main_fsm   <= x"01";
        s_byte1_main_fsm   <= x"01";
        s_byte2_main_fsm   <= x"ff";
        s_byte3_main_fsm   <= x"ff";
        s_address_main_fsm <= "10111";  -- 0x17
        bCountRstMain      <= true;
        bFsm_main          <= true;

      when START_TEMP1_WR =>
        s_start_main       <= '1';
        s_byte0_main_fsm   <= x"02";
        s_byte1_main_fsm   <= x"01";
        s_byte2_main_fsm   <= x"ff";
        s_byte3_main_fsm   <= x"ff";
        s_address_main_fsm <= "10111";  -- 0x17
        bCountRstMain      <= true;
        bFsm_main          <= true;

      when START_TEMP2_WR =>
        s_start_main       <= '1';
        s_byte0_main_fsm   <= x"04";
        s_byte1_main_fsm   <= x"01";
        s_byte2_main_fsm   <= x"ff";
        s_byte3_main_fsm   <= x"ff";
        s_address_main_fsm <= "10111";  -- 0x17
        bCountRstMain      <= true;
        bFsm_main          <= true;

      when START_TEMP0_RD | START_TEMP1_RD | START_TEMP2_RD =>
        s_start_main       <= '1';
        s_address_main_fsm <= "11111";  -- 0x1f
        bFsm_main          <= true;

      when ERROR_TEMP0_WR =>
        bLatchTemp0_fsm    <= true;
        bFsm_main          <= true;

      when ERROR_TEMP1_WR =>
        bLatchTemp1_fsm    <= true;
        bFsm_main          <= true;

      when ERROR_TEMP2_WR =>
        bLatchTemp2_fsm    <= true;
        bFsm_main          <= true;

      when DO_TEMP0_RD =>
        bLatchTemp0_fsm    <= true;

      when DO_TEMP1_RD =>
        bLatchTemp1_fsm    <= true;

      when DO_TEMP2_RD =>
        bLatchTemp2_fsm    <= true;

      when START_READ_BIAS_MASK =>
        s_start_main       <= '1';
        s_address_main_fsm <= "11110";  -- 0x1e
        bFsm_main          <= true;

      when READ_BIAS_MASK =>
        bLatchBias         <= true;

      when START_ADC_WR =>
        s_start_main       <= '1';
        s_byte3_main_fsm   <= "00100" & vAdcChannel(2 downto 0);
        s_address_main_fsm <= "10" & vAdcChannel(5 downto 3);
        bFsm_main          <= true;

      when ERROR_ADC_WR =>
        bLatchAdc_fsm <= true;
        bFsm_main     <= true;
        
      when START_ADC_RD =>
        s_start_main       <= '1';
        s_address_main_fsm <= "11" & vAdcChannel(5 downto 3);
        bFsm_main          <= true;

      when DO_ADC_RD =>
        bLatchAdc_fsm <= true;

      when START_TURN_OFF_BIAS =>
        s_start_main       <= '1';
        s_address_main_fsm <= "10110";  -- 0x16
        bFsm_main <= true;
        bTurnOff  <= true;

      when others =>
        null;
        
    end case;
  end process p_output_logic_main;

  -- Latch Temperature, Bias/Power enable, ADC registers
  p_latch_regs : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        s_temp0        <= x"0000";
        s_temp1        <= x"0000";
        s_temp2        <= x"0000";
        s_bias         <= x"FF";
        sAdcVals       <= (others => '0');
        bEnPwrValid    <= false;
        bEnBiasValid   <= false;
        bNokTemp0_prev <= false;
        bNokTemp1_prev <= false;
        bNokTemp1_prev <= false;
        bNokTemp0      <= false;
        bNokTemp1      <= false;
        bNokTemp1      <= false;

      else
        -- default: keep current
        s_temp0        <= s_temp0;
        s_temp1        <= s_temp1;
        s_temp2        <= s_temp2;
        s_bias         <= s_bias;
        sAdcVals       <= sAdcVals;
        bNokTemp0_prev <= bNokTemp0_prev;
        bNokTemp1_prev <= bNokTemp1_prev;
        bNokTemp2_prev <= bNokTemp2_prev;
        bNokTemp0      <= bNokTemp0;
        bNokTemp1      <= bNokTemp1;
        bNokTemp2      <= bNokTemp2;

        -- latch
        if bLatchTemp0 then
          s_temp0        <= s_latch_data;
          bNokTemp0_prev <= bNokTemp0;
          bNokTemp0      <= (unsigned(s_latch_data) >= unsigned(s_limit_temp0)) or (unsigned(s_latch_data) <= unsigned(s_lo_limit_temp0));
        end if;

        if bLatchTemp1 then
          s_temp1        <= s_latch_data;
          bNokTemp1_prev <= bNokTemp1;
          bNokTemp1      <= (unsigned(s_latch_data) >= unsigned(s_limit_temp1)) or (unsigned(s_latch_data) <= unsigned(s_lo_limit_temp1));
        end if;

        if bLatchTemp2 then
          s_temp2        <= s_latch_data;
          bNokTemp2_prev <= bNokTemp2;
          bNokTemp2      <= (unsigned(s_latch_data) >= unsigned(s_limit_temp2)) or (unsigned(s_latch_data) <= unsigned(s_lo_limit_temp2));
        end if;

        if sMonEnabled(C_INTERLOCK_ENABLE_PWR) = '0' then
          bEnPwrValid  <= false;
          bEnBiasValid <= false;
        end if;

        if bLatchBias and (s_data_valid_main = '1')then
          s_bias       <= s_latch_data(7 downto 0);
          bEnBiasValid <= true;
        end if;

        if bLatchEnable_1_4 and (s_data_valid_aux = '1') then
          s_enable_1_4 <= s_i2c_data_aux(7 downto 0);
        end if;

        if bLatchEnable_5_8 and (s_data_valid_aux = '1') then
          s_enable_5_8 <= s_i2c_data_aux(7 downto 0);
          bEnPwrValid  <= true;
        end if;

        if bLatchAdc then
          sAdcVals(iAdcChannel*16+15 downto iAdcChannel*16) <= s_latch_data;
        end if;

      end if;
    end if;
  end process p_latch_regs;

  -----------------------------------------------------------------------------
  -- Aux I2C
  -----------------------------------------------------------------------------
  -- wishbone interface for wrapper
  INST_i2c_pu_aux_wb : entity work.i2c_pu_aux_wb
    port map (
      WB_CLK           => WB_CLK,
      WB_RST           => WB_RST,
      WB_WBS_I         => WB_WBS_PU_AUX_I,
      WB_WBS_O         => WB_WBS_PU_AUX_O,
      REQ_DATA_o       => s_aux_wb_req_din,
      REQ_WREN_o       => s_aux_wb_req_wr,
      I2C_DATA_i       => s_aux_wb_res_dout(15 downto 0),
      I2C_TXN_ID_i     => s_aux_wb_res_dout(30 downto 16),
      I2C_DATA_RDEN_o  => s_aux_wb_res_rd,
      I2C_DATA_EMPTY_i => s_aux_wb_res_empty
      );

  -- wishbone request FIFO
  INST_wb_request_fifo_aux : xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",   --string; "auto", "block", or "distributed";
      ECC_MODE            => "no_ecc",  --string; "no_ecc" or "en_ecc";
      FIFO_WRITE_DEPTH    => 256,       --positive integer
      WRITE_DATA_WIDTH    => 37,        --positive integer
      WR_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_FULL_THRESH    => 250,       --positive integer
      FULL_RESET_VALUE    => 0,         --positive integer; 0 or 1;
      USE_ADV_FEATURES    => "0001",    --Enable [12:8] = data_valid, almost_empty, rd_data_count,
                                        --prog_empty, underflow, [4:0] = wr_ack,
                                        --almost_full, wr_data_count, prog_full, overflow
      READ_MODE           => "fwft",    --string; "std" or "fwft";
      FIFO_READ_LATENCY   => 0,         --positive integer;
      READ_DATA_WIDTH     => 37,        --positive integer
      RD_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_EMPTY_THRESH   => 5,         --positive integer
      DOUT_RESET_VALUE    => "0",       --string
      WAKEUP_TIME         => 0          --positive integer; 0 or 2;
      )
    port map (
      sleep         => '0',
      rst           => sFifoRst(2),
      wr_clk        => WB_CLK,
      wr_en         => s_aux_wb_req_wr,
      din           => s_aux_wb_req_din,
      full          => open,
      prog_full     => open,
      wr_data_count => open,
      overflow      => REQ_FIFO_AUX_OVF,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => s_aux_wb_req_rd,
      dout          => s_aux_wb_req_dout,
      empty         => s_aux_wb_req_empty,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => open,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open
      );

  -- latch bytes 2 and 3 (upper 15 bits) from req FIFO as transaction ID
  p_latch_txn_id_aux : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        s_txn_id_aux <= (others => '0');
      elsif s_start_aux = '1' then
        s_txn_id_aux <= s_aux_wb_req_dout(30 downto 16);
      else
        s_txn_id_aux <= s_txn_id_aux;
      end if;
    end if;
  end process p_latch_txn_id_aux;

  s_aux_wb_res_din <= s_txn_id_aux & s_i2c_data_aux;

  -- wishbone results FIFO
  INST_wb_result_fifo_aux : xpm_fifo_sync
    generic map (
      FIFO_MEMORY_TYPE    => "block",   --string; "auto", "block", or "distributed";
      ECC_MODE            => "no_ecc",  --string; "no_ecc" or "en_ecc";
      FIFO_WRITE_DEPTH    => 256,       --positive integer
      WRITE_DATA_WIDTH    => 31,        --positive integer
      WR_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_FULL_THRESH    => 250,       --positive integer
      FULL_RESET_VALUE    => 0,         --positive integer; 0 or 1;
      USE_ADV_FEATURES    => "0101",    --Enable [12:8] = data_valid, almost_empty, rd_data_count,
                                        --prog_empty, underflow, [4:0] = wr_ack, almost_full,
                                        --wr_data_count, prog_full, overflow
      READ_MODE           => "fwft",    --string; "std" or "fwft";
      FIFO_READ_LATENCY   => 0,         --positive integer;
      READ_DATA_WIDTH     => 31,        --positive integer
      RD_DATA_COUNT_WIDTH => 8,         --positive integer
      PROG_EMPTY_THRESH   => 5,         --positive integer
      DOUT_RESET_VALUE    => "0",       --string
      WAKEUP_TIME         => 0          --positive integer; 0 or 2;
      )
    port map (
      sleep         => '0',
      rst           => sFifoRst(3),
      wr_clk        => WB_CLK,
      wr_en         => s_aux_wb_res_wr,
      din           => s_aux_wb_res_din,
      full          => open,
      prog_full     => open,
      wr_data_count => open,
      overflow      => RES_FIFO_AUX_OVF,
      wr_rst_busy   => open,
      almost_full   => open,
      wr_ack        => open,
      rd_en         => s_aux_wb_res_rd,
      dout          => s_aux_wb_res_dout,
      empty         => s_aux_wb_res_empty,
      prog_empty    => open,
      rd_data_count => open,
      underflow     => RES_FIFO_AUX_UFL,
      rd_rst_busy   => open,
      almost_empty  => open,
      data_valid    => open,
      injectsbiterr => '0',
      injectdbiterr => '0',
      sbiterr       => open,
      dbiterr       => open
      );


  -- I2C wrapper
  INST_i2c_pu_wrapper_aux : entity work.i2c_pu_wrapper_aux
    port map (
      CLK            => WB_CLK,
      RST            => WB_RST,
      BYTE_0         => x"00",          -- not used in this wrapper
      BYTE_1         => x"00",          -- not used in this wrapper
      BYTE_2         => x"00",          -- not used in this wrapper
      BYTE_3         => s_byte3_aux,
      ADDRESS        => s_address_aux,
      START          => s_start_aux,
      BUSY           => s_busy_aux,
      I2C_DATA_o     => s_i2c_data_aux,
      DATA_VALID     => s_data_valid_aux,
      COMPLETED_BYTE => PU_AUX_COMPLETED_BYTE,
      AL_ERROR       => PU_AUX_AL_ERROR,
      NOACK_ERROR    => PU_AUX_NOACK_ERROR,
      SCL_PAD_i      => SCL_AUX_PAD_i,
      SCL_PAD_o      => SCL_AUX_PAD_o,
      SCL_PAD_T      => SCL_AUX_PAD_T,
      SDA_PAD_i      => SDA_AUX_PAD_i,
      SDA_PAD_o      => SDA_AUX_PAD_o,
      SDA_PAD_T      => SDA_AUX_PAD_T
      );

  -- Count number of wishbone requests if loop is active;
  -- reset controlled by FSM
  -- used to limit the number of WB requests to execute before going
  -- through the turn-off loop again
  p_count_wbreq_aux : process (WB_CLK) is
    variable doLoop : boolean;
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        iCountWbreqAux <= 0;
        doLoop         := false;
      else
        doLoop := (sTurnOff1_4 = '1') or (sTurnOff5_8 = '1');
        if bCountAux and doLoop then
          iCountWbReqAux <= iCountWbReqAux + 1;
        elsif bCountRstAux then
          iCountWbreqAux <= 0;
        else
          iCountWbReqAux <= iCountWbreqAux;
        end if;
      end if;
    end if;
  end process p_count_wbreq_aux;


  -- output selection from FSM
  s_byte3_aux     <= sTurnoffPwr1_4Mask when bTurnoff1_4 else
                     sTurnoffPwr5_8Mask when bTurnoff5_8 else
                     s_aux_wb_req_dout(23 downto 16);
  s_address_aux   <= s_address_aux_fsm when bFsm_aux else s_aux_wb_req_dout(36 downto 32);
  s_aux_wb_res_wr <= s_data_valid_aux  when bFsm_aux else '0';


  -- Controller FSM synchronous state update for I2C aux bus
  p_update_state_aux : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        sState_aux   <= IDLE;

      else
        case sState_aux is
          when IDLE =>
            if (s_aux_wb_req_empty = '0') and (iCountWbreqAux < 2) then
              sState_aux <= START_WB_REQ;
            elsif (sTurnOff1_4 = '1') then
              sState_aux <= START_TURN_OFF_1_4;
            elsif (sTurnOff5_8 = '1') then
              sState_aux <= START_TURN_OFF_5_8;
            elsif sMonEnabled /= "0000" then
              sState_aux <= START_READ_ENABLE_1_4;
            else
              sState_aux <= RESET_WB_CTR;
            end if;

          when START_WB_REQ =>
            sState_aux <= DO_WB_REQ;

          when DO_WB_REQ =>
            if s_busy_aux = '0' then
              sState_aux <= IDLE;
            end if;

          when START_TURN_OFF_1_4 =>
            sState_aux <= TURN_OFF_1_4;

          when TURN_OFF_1_4 =>
            if (s_busy_aux = '0') and (sTurnOff5_8 = '1') then
              sState_aux <= START_TURN_OFF_5_8;
            elsif (s_busy_aux = '0') and (sMonEnabled /= "0000") then
              sState_aux <= START_READ_ENABLE_1_4;
            elsif (s_busy_aux = '0') then
              sState_aux <= IDLE;
            end if;

          when START_TURN_OFF_5_8 =>
            sState_aux <= TURN_OFF_5_8;

          when TURN_OFF_5_8 =>
            if (s_busy_aux = '0') and (sMonEnabled /= "0000") then
              sState_aux <= START_READ_ENABLE_1_4;
            elsif s_busy_aux = '0' then
              sState_aux <= IDLE;
            end if;

          when START_READ_ENABLE_1_4 =>
            sState_aux <= READ_ENABLE_1_4;

          when READ_ENABLE_1_4 =>
            if s_busy_aux = '0' then
              sState_aux <= START_READ_ENABLE_5_8;
            end if;

          when START_READ_ENABLE_5_8 =>
            sState_aux <= READ_ENABLE_5_8;

          when READ_ENABLE_5_8 =>
            if s_busy_aux = '0' then
              sState_aux <= COMPARE_MASK;
            end if;

          when others =>
            sState_aux <= IDLE;
        end case;

      end if;
    end if;
  end process p_update_state_aux;

  -- Controller FSM outputs for I2C aux bus
  p_output_logic_aux : process (sState_aux) is
  begin
    -- defaults:
    s_start_aux       <= '0';
    s_aux_wb_req_rd   <= '0';
    s_address_aux_fsm <= "00000";
    bCountAux         <= false;
    bCountRstAux      <= false;
    bFsm_aux          <= false;
    bLatchEnable_1_4  <= false;
    bLatchEnable_5_8  <= false;
    bTurnoff1_4       <= false;
    bTurnoff5_8       <= false;
    
    case sState_aux is
      when RESET_WB_CTR =>
        bCountRstAux      <= true;

      when START_WB_REQ =>
        s_start_aux       <= '1';
        s_aux_wb_req_rd   <= '1';
        bCountAux         <= true;

      when DO_WB_REQ =>
        bFsm_aux          <= true;

      when START_TURN_OFF_1_4 =>
        s_start_aux       <= '1';
        s_address_aux_fsm <= "00001";   -- 0x01
        bCountRstAux      <= true;
        bFsm_aux          <= true;
        bTurnoff1_4       <= true;

      when START_TURN_OFF_5_8 =>
        s_start_aux       <= '1';
        s_address_aux_fsm <= "00010";   -- 0x02
        bCountRstAux      <= true;
        bFsm_aux          <= true;
        bTurnoff5_8       <= true;

      when START_READ_ENABLE_1_4 =>
        s_start_aux       <= '1';
        s_address_aux_fsm <= "00011";   -- 0x03
        bCountRstAux      <= true;
        bFsm_aux          <= true;

      when READ_ENABLE_1_4 =>
        bLatchEnable_1_4  <= true;

      when START_READ_ENABLE_5_8 =>
        s_start_aux       <= '1';
        s_address_aux_fsm <= "00100";   -- 0x04
        bFsm_aux          <= true;

      when READ_ENABLE_5_8 =>
        bLatchEnable_5_8  <= true;

      when others =>
        null;
    end case;
  end process p_output_logic_aux;

end architecture structural;
