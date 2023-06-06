-------------------------------------------------------------------------------
-- Title      : Configurations for the TMR wrappers - Modified for WP10
-- Project    : Canola CAN Controller
-------------------------------------------------------------------------------
-- File       : tmr_wrapper_cfg_10.vhd
-- Author     : Simon Voigt Nesbø  <svn@hvl.no>
-- Company    :
-- Created    : 2020-10-10
-- Last update: 2020-10-11
-- Platform   :
-- Standard   : VHDL'08
-------------------------------------------------------------------------------
-- Description: Configuration declarations for the TMR wrappers in the design.
--              The configurations choose the TMR voter entities to be used
--              with the component declarations from tmr_voter_pkg.
--              If you want to use custom TMR voters, you can modify this file
--              to map to the existing voter components.
--
-- Note       : This version of the file is modified to use the majority voters
--              in the WP10 RUmainFPGA firmware.
-------------------------------------------------------------------------------
-- Copyright (c) 2020
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author  Description
-- 2020-10-11  1.0      svn     Created
-------------------------------------------------------------------------------
library work;
use work.tmr_voter_pkg.all;


-------------------------------------------------------------------------------
-- BTL - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_btl_tmr_wrapper_cfg of canola_btl_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_btl_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- BSP - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_bsp_tmr_wrapper_cfg of canola_bsp_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_array
        use entity work.majority_voter_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_bsp_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- EML - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_eml_tmr_wrapper_cfg of canola_eml_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_array
        use entity work.majority_voter_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_eml_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- Frame Rx FSM - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_frame_rx_fsm_tmr_wrapper_cfg of canola_frame_rx_fsm_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_array
        use entity work.majority_voter_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_frame_rx_fsm_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- Frame Tx FSM - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_frame_tx_fsm_tmr_wrapper_cfg of canola_frame_tx_fsm_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_array
        use entity work.majority_voter_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_frame_tx_fsm_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- Time Quanta Generator - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration canola_time_quanta_gen_tmr_wrapper_cfg of canola_time_quanta_gen_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter
        use entity work.majority_voter_wrapper2(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT         => INPUT,
                    OUTPUT        => VOTER_OUT,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration canola_time_quanta_gen_tmr_wrapper_cfg;


-------------------------------------------------------------------------------
-- Saturating counter - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration counter_saturating_tmr_wrapper_triplicated_cfg of counter_saturating_tmr_wrapper_triplicated is

  for structural
    for if_TMR_generate

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for;  -- if_TMR_generate
  end for;  -- structural

end configuration counter_saturating_tmr_wrapper_triplicated_cfg;


-------------------------------------------------------------------------------
-- Up counter - TMR Wrapper Configuration
-------------------------------------------------------------------------------
configuration up_counter_tmr_wrapper_cfg of up_counter_tmr_wrapper is

  for structural
    for if_TMR_generate

      for all : tmr_voter_triplicated_array
        use entity work.majority_voter_triplicated_array_wrapper(rtl)
          generic map (
            G_MISMATCH_EN         => G_MISMATCH_OUTPUT_EN,
            G_ADDITIONAL_MISMATCH => G_MISMATCH_OUTPUT_2ND_EN,
            G_MISMATCH_REGISTERED => G_MISMATCH_OUTPUT_REG,
            C_WIDTH               => G_WIDTH)
          port map (ASSERTION_CLK => CLK,
                    ASSERTION_RST => RST,
                    INPUT_A       => INPUT_A,
                    INPUT_B       => INPUT_B,
                    INPUT_C       => INPUT_C,
                    OUTPUT_A      => VOTER_OUT_A,
                    OUTPUT_B      => VOTER_OUT_B,
                    OUTPUT_C      => VOTER_OUT_C,
                    MISMATCH      => MISMATCH,
                    MISMATCH_2ND  => MISMATCH_2ND);
      end for;

    end for; -- if_TMR_generate
  end for;  -- structural

end configuration up_counter_tmr_wrapper_cfg;
