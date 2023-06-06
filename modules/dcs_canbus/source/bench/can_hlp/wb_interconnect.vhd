-------------------------------------------------------------------------------
-- Title      : Wishbone interconnect for testbench
-- Project    : ITS RU FPGA
-------------------------------------------------------------------------------
-- File       : wb_interconnect.vhd
-- Author     : Simon Voigt Nesbo (svn@hvl.no)
-- Company    : Western Norway University of Applied Sciences
-- Created    : 2020-02-14
-- Last update: 2020-03-02
-- Platform   :
-- Standard   : VHDL'08
-------------------------------------------------------------------------------
-- Description: Connects wishbone master interface to correct wishbone
--              slave interface based on which address is being accessed
-------------------------------------------------------------------------------
-- Copyright (c) 2018
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author                  Description
-- 2020-02-14  1.0      svn                     Created
-------------------------------------------------------------------------------
use std.textio.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_misc.all;
use ieee.numeric_std.all;

library work;
use work.intercon_pkg.all;
use work.tmr_pkg.all;

-- test bench entity
entity wb_interconnect is
  generic (
    NUM_WB_MASTERS : natural := 1;
    NUM_WB_SLAVES  : natural := 1);

  port (
    -- Wishbone master interfaces
    wbm_i : out t_wbm_i_array(0 to NUM_WB_MASTERS-1);
    wbm_o : in  t_wbm_o_array(0 to NUM_WB_MASTERS-1);

    -- Wishbone slave interface
    wbs_i      : out t_wbs_i_matrix(0 to NUM_WB_SLAVES-1);
    wbs_o      : in  t_wbs_o_matrix(0 to NUM_WB_SLAVES-1));
end wb_interconnect;

architecture behav of wb_interconnect is

  -- Selected WBM interface
  signal wbm_sel_i : wbm_i_type;
  signal wbm_sel_o : wbm_o_type;

  -- Signals to select and connect master interfaces to a slave
  signal s_master_sel : std_logic_vector(0 to NUM_WB_SLAVES-1) := (others => '0');
  signal s_master_num : natural                                := 0;

  constant C_WBM_I_DISCONNECT : wbm_i_type := (dat_i => (others => '0'),
                                               ack_i => '0',
                                               err_i => '0');

begin

  -- Connect wishbone master interface to slaves
  proc_wb_interconnect : process(all) is
  begin  -- process proc_wb_interconnect

    -- Default assignments (replies) to masters
    for i in 0 to NUM_WB_MASTERS-1 loop
      wbm_i(i) <= C_WBM_I_DISCONNECT;
    end loop;

    wbm_sel_i <= C_WBM_I_DISCONNECT;

    -- Select the first master to toggle cyc_o
    for i in 0 to NUM_WB_MASTERS-1 loop
      if (or_reduce(s_master_sel) = '0' and wbm_o(i).cyc_o = '1') or
         (or_reduce(s_master_sel) = '1' and s_master_num = i)
      then
        s_master_num <= 0;
        s_master_sel <= (others => '0');

        if wbm_o(i).cyc_o = '1' then
          s_master_num    <= i;
          s_master_sel(i) <= '1';
        end if;
      end if;
    end loop;


    -- Connect master input/output to signal for select master interface
    if or_reduce(s_master_sel) = '1' then
      wbm_sel_o           <= wbm_o(s_master_num);
      wbm_i(s_master_num) <= wbm_sel_i;
    else
      wbm_sel_o.addr_o <= (others => '0');
      wbm_sel_o.dat_o  <= (others => '0');
      wbm_sel_o.cyc_o  <= '0';
      wbm_sel_o.stb_o  <= '0';
      wbm_sel_o.we_o   <= '0';
    end if;


    -- Slave assignment
    for i in 0 to NUM_WB_SLAVES-1 loop
      if to_integer(unsigned(wbm_sel_o.addr_o(WB_ADD_WIDTH-1 downto WB_ADD_WIDTH-WB_ADDB_WIDTH))) = i then
        -- Connect signals to this slave if the 7 MSB bits of the address match

        -- Slave input / Master output
        for j in 0 to C_K_TMR-1 loop
          wbs_i(i)(j).addr_i <= wbm_sel_o.addr_o(WB_ADDS_WIDTH-1 downto 0);
          wbs_i(i)(j).dat_i  <= wbm_sel_o.dat_o;
          wbs_i(i)(j).cyc_i  <= wbm_sel_o.cyc_o;
          wbs_i(i)(j).stb_i  <= wbm_sel_o.stb_o;
          wbs_i(i)(j).we_i   <= wbm_sel_o.we_o;
        end loop;  -- j

        -- Master input / Slave output
        wbm_sel_i.dat_i <= wbs_o(i)(0).dat_o;
        wbm_sel_i.ack_i <= wbs_o(i)(0).ack_o;
        wbm_sel_i.err_i <= wbs_o(i)(0).err_o;
      else

        -- Address didn't match, disconnect master interface

        for j in 0 to C_K_TMR-1 loop
          wbs_i(i)(j).addr_i <= (others => '0');
          wbs_i(i)(j).dat_i  <= (others => '0');
          wbs_i(i)(j).cyc_i  <= '0';
          wbs_i(i)(j).stb_i  <= '0';
          wbs_i(i)(j).we_i   <= '0';
        end loop;  -- j

      end if;
    end loop;  -- i

  end process proc_wb_interconnect;

end behav;
