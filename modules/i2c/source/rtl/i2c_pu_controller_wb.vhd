-------------------------------------------------------------------------------
-- Title      : Power Unit Controller
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_controller_wb.vhd
-- Author     : Joachim Schambach  <jschamba@physics.utexas.edu>
-- Company    : University of Texas at Austin
-- Created    : 2019-05-02
-- Last update: 2019-09-25
-- Platform   : Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wishone for the Power Unit controller module
-------------------------------------------------------------------------------
-- Copyright (c) 2019 University of Texas at Austin
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author    Description
-- 2019-05-02  1.0      jschamba  Created
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;


library work;
-- Wishbone interface package
use work.intercon_pkg.all;
use work.i2c_pkg.all;
use work.i2c_pu_controller_pkg.all;

use work.xpm_cdc_components_pkg.all;


entity i2c_pu_controller_wb is
  port (
    -- Wishbone interface signals
    WB_CLK           : in  std_logic;   -- master clock input
    WB_RST           : in  std_logic;   -- synchronous active high reset
    WB_WBS_I         : in  wbs_i_type;  -- Wishbone Inputs
    WB_WBS_O         : out wbs_o_type;  -- Wishbone Outputs
    -- interface data
    LIMIT_TEMP0      : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    LIMIT_TEMP1      : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    LIMIT_TEMP2      : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    LO_LIMIT_TEMP0   : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    LO_LIMIT_TEMP1   : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    LO_LIMIT_TEMP2   : out std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    TEMP0            : in  std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    TEMP1            : in  std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    TEMP2            : in  std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    TRIPPED          : in  std_logic_vector(WB_DATA_WIDTH-1 downto 0);
    ENABLE_PWR       : in  std_logic_vector(C_MODULE_NUMBER*2-1 downto 0);
    ENABLE_BIAS      : in  std_logic_vector(C_MODULE_NUMBER-1 downto 0);
    POWER_MASK       : out std_logic_vector(C_MODULE_NUMBER*2-1 downto 0);
    BIAS_MASK        : out std_logic_vector(C_MODULE_NUMBER-1 downto 0);
    FIFO_RST         : out std_logic_vector(3 downto 0);
    INTERLOCK_ENABLE : out std_logic_vector(3 downto 0);
    ADC_VALS         : in  std_logic_vector(C_MAX_ADC_CHANNELS*16-1 downto 0)
    );
end entity i2c_pu_controller_wb;

architecture structural of i2c_pu_controller_wb is


  signal s_wbs_reg_i : t_wbs_reg_array(NR_REGS-1 downto 0);
  signal s_wbs_reg_o : t_wbs_reg_array(NR_REGS-1 downto 0);

  constant C_DEFAULT_REGS : t_wbs_reg_array(NR_REGS-1 downto 0) :=
    (WB_ADD'pos(A_LIMIT_TEMP0)           => C_TEMP_HI_LIMIT_PB,
     WB_ADD'pos(A_LIMIT_TEMP1)           => C_TEMP_HI_LIMIT,
     WB_ADD'pos(A_LIMIT_TEMP2)           => C_TEMP_HI_LIMIT,
     WB_ADD'pos(A_LO_LIMIT_TEMP0)        => C_TEMP_LO_LIMIT_PB,
     WB_ADD'pos(A_LO_LIMIT_TEMP1)        => C_TEMP_LO_LIMIT,
     WB_ADD'pos(A_LO_LIMIT_TEMP2)        => C_TEMP_LO_LIMIT,
     WB_ADD'pos(A_TEMP_INTERLOCK_ENABLE) => x"0007",
     WB_ADD'pos(A_ENABLE_MASK)           => x"ff00", -- all off
     others                              => x"0000");

  constant c_ack : std_logic_vector(NR_REGS-1 downto 0) := (others => '0');


begin


  p_wishbone_data : process (all) is
  begin
    s_wbs_reg_i <= (others => x"0000");  -- initialize to 0

    -- Read
    s_wbs_reg_i(WB_ADD'pos(A_TEMP0))       <= TEMP0;
    s_wbs_reg_i(WB_ADD'pos(A_TEMP1))       <= TEMP1;
    s_wbs_reg_i(WB_ADD'pos(A_TEMP2))       <= TEMP2;
    s_wbs_reg_i(WB_ADD'pos(A_TRIPPED))     <= TRIPPED;
    s_wbs_reg_i(WB_ADD'pos(A_ENABLE_PWR))  <= ENABLE_PWR;
    s_wbs_reg_i(WB_ADD'pos(A_ENABLE_BIAS)) <= wb_resize(ENABLE_BIAS);

    for i in 0 to C_MAX_ADC_CHANNELS-1 loop
      s_wbs_reg_i(WB_ADD'pos(A_ADC_00)+i) <= ADC_VALS(i*16+15 downto i*16);
    end loop;  -- i


    -- Write
    LIMIT_TEMP0                  <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP0));
    LIMIT_TEMP1                  <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP1));
    LIMIT_TEMP2                  <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP2));
    LO_LIMIT_TEMP0               <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP0));
    LO_LIMIT_TEMP1               <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP1));
    LO_LIMIT_TEMP2               <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP2));
    FIFO_RST                     <= s_wbs_reg_o(WB_ADD'pos(A_FIFO_RST))(3 downto 0);
    INTERLOCK_ENABLE(2 downto 0) <= s_wbs_reg_o(WB_ADD'pos(A_TEMP_INTERLOCK_ENABLE))(2 downto 0);
    INTERLOCK_ENABLE(3)          <= s_wbs_reg_o(WB_ADD'pos(A_PWR_INTERLOCK_ENABLE))(0);
    BIAS_MASK                    <= s_wbs_reg_o(WB_ADD'pos(A_ENABLE_MASK))(15 downto 8);
    for i in 0 to C_MODULE_NUMBER-1 loop
      -- analog and digital voltage should be the same enable mask
      POWER_MASK(2*i)   <= s_wbs_reg_o(WB_ADD'pos(A_ENABLE_MASK))(i);
      POWER_MASK(2*i+1) <= s_wbs_reg_o(WB_ADD'pos(A_ENABLE_MASK))(i);
    end loop;  -- i

    -- Write feedback
    s_wbs_reg_i(WB_ADD'pos(A_LIMIT_TEMP0))           <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP0));
    s_wbs_reg_i(WB_ADD'pos(A_LIMIT_TEMP1))           <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP1));
    s_wbs_reg_i(WB_ADD'pos(A_LIMIT_TEMP2))           <= s_wbs_reg_o(WB_ADD'pos(A_LIMIT_TEMP2));
    s_wbs_reg_i(WB_ADD'pos(A_LO_LIMIT_TEMP0))        <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP0));
    s_wbs_reg_i(WB_ADD'pos(A_LO_LIMIT_TEMP1))        <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP1));
    s_wbs_reg_i(WB_ADD'pos(A_LO_LIMIT_TEMP2))        <= s_wbs_reg_o(WB_ADD'pos(A_LO_LIMIT_TEMP2));
    s_wbs_reg_i(WB_ADD'pos(A_ENABLE_MASK))           <= s_wbs_reg_o(WB_ADD'pos(A_ENABLE_MASK));
    s_wbs_reg_i(WB_ADD'pos(A_TEMP_INTERLOCK_ENABLE)) <= s_wbs_reg_o(WB_ADD'pos(A_TEMP_INTERLOCK_ENABLE));
    s_wbs_reg_i(WB_ADD'pos(A_PWR_INTERLOCK_ENABLE))  <= s_wbs_reg_o(WB_ADD'pos(A_PWR_INTERLOCK_ENABLE));

  end process p_wishbone_data;

  INST_ws_reg : entity work.ws_reg
    generic map (
      WB_ADD_WE      => C_WB_ADD_WE,
      WB_ILLEGAL_VAL => x"DEAD",
      WB_REG_INIT    => C_DEFAULT_REGS,
      WB_EXT_ACK_EN  => c_ack
      )
    port map (
      WB_CLK         => WB_CLK,
      WB_RST         => WB_RST,
      WB_WBS_I       => WB_WBS_I,
      WB_WBS_O       => WB_WBS_O,
      WBS_REG_I      => s_wbs_reg_i,
      WBS_REG_O      => s_wbs_reg_o,
      WBS_RD_PULSE_O => open,
      WBS_WR_PULSE_O => open,
      WBS_EXT_ACK_I  => c_ack
      );

end architecture structural;
