-------------------------------------------------------------------------------
-- Title      : DCS CANbus HLP UVVM Testbench
-- Project    : ITS RU FPGA
-------------------------------------------------------------------------------
-- File       : can_hlp_uvvm_tb.vhd
-- Author     : Simon Voigt Nesbo (svn@hvl.no)
-- Company    : Western Norway University of Applied Sciences
-- Created    : 2018-03-02
-- Last update: 2020-10-18
-- Platform   : Questasim/Modelsim 10.6c
-- Target     : Kintex 7
-- Standard   : VHDL'08
-------------------------------------------------------------------------------
-- Description: Testbench for the CAN High Level Protocol (HLP) module.
--              Parts of Bitvis' irqc_tb.vhd from UVVM 1.4.0 has been reused
--              in this testbench.
-------------------------------------------------------------------------------
-- Copyright (c) 2017
-------------------------------------------------------------------------------
-- Revisions  :
-- Date        Version  Author                  Description
-- 2018-03-02  1.0      svn                     Created
-------------------------------------------------------------------------------
use std.textio.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_wishbone;
use bitvis_vip_wishbone.wb_bfm_pkg.all;

library work;
use work.intercon_pkg.all;
use work.can_bfm_pkg.all;
use work.can_uvvm_bfm_pkg.all;
use work.can_hlp_uvvm_bfm_pkg.all;
use work.can_hlp_wishbone_pkg.all;
use work.can_hlp_monitor_pkg.all;
use work.can_hlp_pkg.all;

-- test bench entity
entity can_hlp_uvvm_tb is
end can_hlp_uvvm_tb;

architecture func of can_hlp_uvvm_tb is
  constant C_NUM_TESTS  : natural := 20;  -- Number of iterations in test loops

  constant C_CLK_PERIOD : time       := 6250 ps; -- 160 Mhz
  constant C_CLK_FREQ   : integer    := 1e9 ns / C_CLK_PERIOD;

  -- Copied from Bitvis IRQC testbench
  procedure clock_gen(
    signal   clock_signal  : inout std_logic;
    signal   clock_ena     : in    boolean;
    constant clock_period  : in    time
    ) is
    variable v_first_half_clk_period : time := C_CLK_PERIOD / 2;
  begin
    loop
      if not clock_ena then
        wait until clock_ena;
      end if;
      wait for v_first_half_clk_period;
      clock_signal <= not clock_signal;
      wait for (clock_period - v_first_half_clk_period);
      clock_signal <= not clock_signal;
    end loop;
  end;

  constant C_NUM_HLP_INSTANCES : natural := 4;

  signal clock_ena : boolean := false;

  signal reset : std_logic_vector(C_NUM_HLP_INSTANCES-1 downto 0) := (others => '0');
  signal clk   : std_logic                                        := '0';

  signal can_bus_signal : std_logic;
  signal can_hlp_rx     : std_logic_vector(C_NUM_HLP_INSTANCES-1 downto 0);
  signal can_hlp_tx     : std_logic_vector(C_NUM_HLP_INSTANCES-1 downto 0);
  signal can_bfm_rx     : std_logic;
  signal can_bfm_tx     : std_logic;

  signal s_send_alert        : std_logic_vector(C_NUM_HLP_INSTANCES-1 downto 0) := (others => '0');
  signal s_send_status       : std_logic_vector(C_NUM_HLP_INSTANCES-1 downto 0) := (others => '0');

  type t_status_alert_data is array (C_NUM_HLP_INSTANCES-1 downto 0) of std_logic_vector(31 downto 0);
  signal s_status_alert_data : t_status_alert_data;

  -- Each HLP instances is a WB master, and the WB BFM is a master
  constant C_NUM_WB_MASTERS : natural := C_NUM_HLP_INSTANCES + 1;

  constant C_NUM_WB_SLAVES  : natural := 8;

  type t_WB_ADDB is record
    CAN_HLP_0         : natural;
    CAN_HLP_1         : natural;
    CAN_HLP_2         : natural;
    CAN_HLP_3         : natural;
    CAN_HLP_MONITOR_0 : natural;
    CAN_HLP_MONITOR_1 : natural;
    CAN_HLP_MONITOR_2 : natural;
    CAN_HLP_MONITOR_3 : natural;
  end record;

  constant WB_ADDB : t_WB_ADDB := (
    CAN_HLP_0         => 00,
    CAN_HLP_1         => 01,
    CAN_HLP_2         => 02,
    CAN_HLP_3         => 03,
    CAN_HLP_MONITOR_0 => 04,
    CAN_HLP_MONITOR_1 => 05,
    CAN_HLP_MONITOR_2 => 06,
    CAN_HLP_MONITOR_3 => 07
    );

  -- Wishbone slave interface
  signal wbs_i : t_wbs_i_matrix(0 to C_NUM_WB_SLAVES-1);
  signal wbs_o : t_wbs_o_matrix(0 to C_NUM_WB_SLAVES-1);

  -- Wishbone master interfaces
  -- Array includes BFM at the last position
  signal wbm_i : t_wbm_i_array(0 to C_NUM_WB_MASTERS-1);
  signal wbm_o : t_wbm_o_array(0 to C_NUM_WB_MASTERS-1);

  -- Wishbone master interface
  -- WB BFM requires t_wbm_if from wishbone_bfm_pkg
  -- Firmware requires wbm_i_type/wbm_o_type from intercon_pkg
  -- These interfaces are all connected together
  signal wbm_uvvm : t_wbm_if (dat_o(WB_DATA_WIDTH-1 downto 0),
                              addr_o(WB_ADD_WIDTH-1 downto 0),
                              dat_i(WB_DATA_WIDTH-1 downto 0)) := init_wbm_if_signals(WB_ADD_WIDTH,
                                                                                      WB_DATA_WIDTH);

  signal wb_addr_fifo_test_if : std_logic_vector(WB_ADD_WIDTH-1 downto 0);

  type t_hlp_node_id is array (0 to C_NUM_HLP_INSTANCES-1) of std_logic_vector(7 downto 0);
  signal can_hlp_node_id : t_hlp_node_id :=  (x"AA",
                                              x"12",
                                              x"34",
                                              x"56");

  -- Interface to wishbone master via FIFO
  -- CAN HLP initiates WB transactions on DP0
  type t_dp_fifo_data is array (0 to C_NUM_HLP_INSTANCES-1) of std_logic_vector(31 downto 0);
  signal dp0_dt   : t_dp_fifo_data;
  signal dp0_epty : std_logic_vector(0 to C_NUM_HLP_INSTANCES-1) := (others => '0');
  signal dp0_rd   : std_logic_vector(0 to C_NUM_HLP_INSTANCES-1) := (others => '0');

  -- Interface to wishbone master via FIFO
  -- CAN HLP receives WB replies on DP1
  signal dp1_dt   : t_dp_fifo_data;
  signal dp1_full : std_logic_vector(0 to C_NUM_HLP_INSTANCES-1) := (others => '0');
  signal dp1_wr   : std_logic_vector(0 to C_NUM_HLP_INSTANCES-1) := (others => '0');


  shared variable seed1     : positive := 32564482;
  shared variable seed2     : positive := 89536898;

begin

  -- Connect CAN signals
  can_bus_signal <= 'H';

  FOR_GEN_CAN_TX: for i in 0 to C_NUM_HLP_INSTANCES-1 generate
    can_bus_signal <= '0' when can_hlp_tx(i) = '0' else 'Z';
  end generate FOR_GEN_CAN_TX;

  can_bus_signal <= '0' when can_bfm_tx = '0' else 'Z';

  FOR_GEN_CAN_RX: for i in 0 to C_NUM_HLP_INSTANCES-1 generate
    can_hlp_rx(i) <= '1' ?= can_bus_signal;
  end generate FOR_GEN_CAN_RX;

  can_bfm_rx <= '1' ?= can_bus_signal;

  -- Set upt clock generator
  clock_gen(clk, clock_ena, C_CLK_PERIOD);

  -- Connect WB BFM signals to WB interface type used in RU
  wbm_o(C_NUM_WB_MASTERS-1).dat_o    <= wbm_uvvm.dat_o;
  wbm_o(C_NUM_WB_MASTERS-1).addr_o   <= wbm_uvvm.addr_o;
  wbm_o(C_NUM_WB_MASTERS-1).cyc_o    <= wbm_uvvm.cyc_o;
  wbm_o(C_NUM_WB_MASTERS-1).stb_o    <= wbm_uvvm.stb_o;
  wbm_o(C_NUM_WB_MASTERS-1).we_o     <= wbm_uvvm.we_o;
  wbm_uvvm.dat_i <= wbm_i(C_NUM_WB_MASTERS-1).dat_i;
  wbm_uvvm.ack_i <= wbm_i(C_NUM_WB_MASTERS-1).ack_i;


  FOR_GEN_HLP_INST: for i in 0 to C_NUM_HLP_INSTANCES-1 generate
    IF_GEN_HLP_TMR_INST: if i = 0 generate
      -- Generate first HLP instance with triplication
      INST_can_hlp_top : entity work.can_hlp_top
        generic map (
          G_SEE_MITIGATION_TECHNIQUE => 1,
          G_MISMATCH_EN              => 1,
          G_MISMATCH_REGISTERED      => 0,
          G_ADDITIONAL_MISMATCH      => 1)
        port map (
          WB_CLK => clk,
          WB_RST => reset(i),

          -- WB interface for CAN HLP
          WB_WBS_I => wbs_i(WB_ADDB.CAN_HLP_0+i),
          WB_WBS_O => wbs_o(WB_ADDB.CAN_HLP_0+i),

          -- WB interface for CAN HLP monitor
          WB_WBS_MONITOR_I => wbs_i(WB_ADDB.CAN_HLP_MONITOR_0+i),
          WB_WBS_MONITOR_O => wbs_o(WB_ADDB.CAN_HLP_MONITOR_0+i),

          -- Interface to wishbone FIFO
          -- WB master receives WB replies on this interface
          DP0_DT_O   => dp0_dt(i),
          DP0_EPTY_O => dp0_epty(i),
          DP0_RD_I   => dp0_rd(i),

          -- Interface to Wishbone FIFO
          -- WB master initiates WB transactions on this interface
          DP1_DT_I   => dp1_dt(i),
          DP1_FULL_O => dp1_full(i),
          DP1_WR_I   => dp1_wr(i),


          SEND_ALERT        => s_send_alert(i),
          SEND_STATUS       => s_send_status(i),
          STATUS_ALERT_DATA => s_status_alert_data(i),
          CAN_NODE_ID       => can_hlp_node_id(i),
          CAN_TX            => can_hlp_tx(i),
          CAN_RX            => can_hlp_rx(i));
    end generate IF_GEN_HLP_TMR_INST;

    IF_GEN_HLP_NO_TMR_INST: if i > 0 generate
      -- Generate the other HLP instances without triplication
      INST_can_hlp_top : entity work.can_hlp_top
        generic map (
          G_SEE_MITIGATION_TECHNIQUE => 0,
          G_MISMATCH_EN              => 0,
          G_MISMATCH_REGISTERED      => 0,
          G_ADDITIONAL_MISMATCH      => 0)
        port map (
          WB_CLK => clk,
          WB_RST => reset(i),

          -- WB interface for CAN HLP
          WB_WBS_I => wbs_i(WB_ADDB.CAN_HLP_0+i),
          WB_WBS_O => wbs_o(WB_ADDB.CAN_HLP_0+i),

          -- WB interface for CAN HLP monitor
          WB_WBS_MONITOR_I => wbs_i(WB_ADDB.CAN_HLP_MONITOR_0+i),
          WB_WBS_MONITOR_O => wbs_o(WB_ADDB.CAN_HLP_MONITOR_0+i),

          -- Interface to wishbone FIFO
          -- WB master receives WB replies on this interface
          DP0_DT_O   => dp0_dt(i),
          DP0_EPTY_O => dp0_epty(i),
          DP0_RD_I   => dp0_rd(i),

          -- Interface to Wishbone FIFO
          -- WB master initiates WB transactions on this interface
          DP1_DT_I   => dp1_dt(i),
          DP1_FULL_O => dp1_full(i),
          DP1_WR_I   => dp1_wr(i),


          SEND_ALERT        => s_send_alert(i),
          SEND_STATUS       => s_send_status(i),
          STATUS_ALERT_DATA => s_status_alert_data(i),
          CAN_NODE_ID       => can_hlp_node_id(i),
          CAN_TX            => can_hlp_tx(i),
          CAN_RX            => can_hlp_rx(i));
    end generate IF_GEN_HLP_NO_TMR_INST;


    INST_wb_fifo_test_if : entity work.wb_fifo_test_if
      port map
      (
        WB_CLK => clk,
        WB_RST => reset(i),

        WB_WBM_O => wbm_o(i),
        WB_WBM_I => wbm_i(i),

        -- Interface to wishbone FIFO
        -- WB master receives WB replies on this interface
        DP0_DT_I   => dp0_dt(i),
        DP0_EPTY_I => dp0_epty(i),
        DP0_RD_O   => dp0_rd(i),

        -- Interface to Wishbone FIFO
        -- WB master initiates WB transactions on this interface
        DP1_DT_O   => dp1_dt(i),
        DP1_FULL_I => dp1_full(i),
        DP1_WR_O   => dp1_wr(i)
        );
  end generate FOR_GEN_HLP_INST;


  INST_wb_interconnect : entity work.wb_interconnect
    generic map (
      NUM_WB_MASTERS => C_NUM_WB_MASTERS,
      NUM_WB_SLAVES  => C_NUM_WB_SLAVES)
    port map (
      wbm_i  => wbm_i,
      wbm_o  => wbm_o,
      wbs_i  => wbs_i,
      wbs_o  => wbs_o);


  p_main: process
    constant C_SCOPE          : string                := C_TB_SCOPE_DEFAULT;
    variable can_uvvm_bfm_cfg : t_can_uvvm_bfm_config := C_CAN_UVVM_BFM_CONFIG_DEFAULT;
    variable wb_bfm_cfg       : t_wb_bfm_config       := C_WB_BFM_CONFIG_DEFAULT;
    variable data_read        : std_logic_vector(15 downto 0);
    variable data_write       : std_logic_vector(15 downto 0);
    variable rand_data        : std_logic_vector(15 downto 0);
    constant C_STATUS_LEN_i   : integer := to_integer(unsigned(C_STATUS_LEN));
    constant C_ALERT_LEN_i    : integer := to_integer(unsigned(C_ALERT_LEN));
    variable rand_status_data : std_logic_vector(C_STATUS_LEN_i*8-1 downto 0);
    variable rand_alert_data  : std_logic_vector(C_ALERT_LEN_i*8-1 downto 0);
    variable hlp_read_count   : unsigned(31 downto 0); -- 32-bit counter
    variable hlp_write_count  : unsigned(31 downto 0); -- 32-bit counter
    variable hlp_alert_count  : unsigned(15 downto 0); -- 16-bit counter
    variable hlp_status_count : unsigned(15 downto 0); -- 16-bit counter
    variable can_rx_msg_count : unsigned(31 downto 0); -- 32-bit counter
    variable can_tx_msg_count : unsigned(31 downto 0); -- 32-bit counter

    variable arb_id_a : std_logic_vector(C_ARB_ID_A_SIZE-1 downto 0);
    variable arb_id_b : std_logic_vector(C_ARB_ID_B_SIZE-1 downto 0);

    variable can_data : can_payload_t;

    -- Pulse a signal for a number of clock cycles.
    -- Source: irqc_tb.vhd from Bitvis UVVM 1.4.0
    procedure pulse(
      signal   target          : inout std_logic;
      signal   clock_signal    : in    std_logic;
      constant num_periods     : in    natural;
      constant msg             : in    string
    ) is
    begin
      if num_periods > 0 then
        wait until falling_edge(clock_signal);
        target  <= '1';
        for i in 1 to num_periods loop
          wait until falling_edge(clock_signal);
        end loop;
      else
        target  <= '1';
        wait for 0 ns;  -- Delta cycle only
      end if;
      target  <= '0';
      log(ID_SEQUENCER_SUB, msg, C_SCOPE);
    end;

    -- Pulse a signal for a number of clock cycles.
    -- Source: irqc_tb.vhd from Bitvis UVVM 1.4.0
    procedure pulse(
      signal   target        : inout  std_logic_vector;
      constant pulse_value   : in     std_logic_vector;
      signal   clock_signal  : in     std_logic;
      constant num_periods   : in     natural;
      constant msg           : in     string) is
    begin
      if num_periods > 0 then
        wait until falling_edge(clock_signal);
        target <= pulse_value;
        for i in 1 to num_periods loop
          wait until falling_edge(clock_signal);
        end loop;
      else
        target <= pulse_value;
        wait for 0 ns;  -- Delta cycle only
      end if;
      target(target'range) <= (others => '0');
      log(ID_SEQUENCER_SUB, "Pulsed to " & to_string(pulse_value, HEX, AS_IS, INCL_RADIX) & ". " & msg, C_SCOPE);
    end;


    -- Log overloads for simplification
    procedure log(
      msg : string) is
    begin
      log(ID_SEQUENCER, msg, C_SCOPE);
    end;

    procedure wb_write (
      constant slave_num  : in natural;
      constant addr       : in natural;
      constant data_value : in std_logic_vector;
      constant msg        : in string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      wb_write(wb_addr,
               data_value,
               msg,
               clk,
               wbm_uvvm,
               C_SCOPE,
               shared_msg_id_panel,
               wb_bfm_cfg);
      wait until falling_edge(clk);
    end;

    procedure wb_read (
      constant slave_num  : in natural;
      constant addr       : in natural;
      variable data_value : out std_logic_vector;
      constant msg        : in  string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      wb_read(wb_addr,
              data_value,
              msg,
              clk,
              wbm_uvvm,
              C_SCOPE,
              shared_msg_id_panel,
              wb_bfm_cfg);
      wait until falling_edge(clk);
    end;

    procedure wb_check (
      constant slave_num   : in natural;
      constant addr        : in natural;
      constant data_exp    : in std_logic_vector;
      constant alert_level : in t_alert_level := error;
      constant msg         : in string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      wb_check(wb_addr,
               data_exp,
               alert_level,
               msg,
               clk,
               wbm_uvvm,
               C_SCOPE,
               shared_msg_id_panel,
               wb_bfm_cfg);
      wait until falling_edge(clk);
    end;

    -- Wrapper for can_hlp_write
    procedure can_hlp_write (
      constant node_id   : in std_logic_vector(7 downto 0);
      constant slave_num : in natural;
      constant addr      : in natural;
      constant data      : in std_logic_vector(15 downto 0);
      constant msg       : in string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      can_hlp_write(node_id, wb_addr, data, msg,
                    clk, can_bfm_tx, can_bfm_rx, can_uvvm_bfm_cfg);
    end procedure can_hlp_write;

    -- Wrapper for can_hlp_read
    procedure can_hlp_read (
      constant node_id   : in  std_logic_vector(7 downto 0);
      constant slave_num : in  natural;
      constant addr      : in  natural;
      variable data      : out std_logic_vector(15 downto 0);
      constant msg       : in  string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      can_hlp_read(node_id, wb_addr, data, msg,
                   clk, can_bfm_tx, can_bfm_rx, can_uvvm_bfm_cfg);
    end procedure can_hlp_read;

    -- Wrapper for can_hlp_check
    procedure can_hlp_check (
      constant node_id     : in std_logic_vector(7 downto 0);
      constant slave_num   : in natural;
      constant addr        : in natural;
      constant data_exp    : in std_logic_vector(15 downto 0);
      constant alert_level : in t_alert_level := error;
      constant msg         : in string
      ) is
      variable wb_addr : std_logic_vector(14 downto 0);
    begin
      wb_addr(14 downto 8) := std_logic_vector(to_unsigned(slave_num, 7));
      wb_addr(7 downto 0)  := std_logic_vector(to_unsigned(addr, 8));

      can_hlp_check(node_id, wb_addr, data_exp, alert_level, msg,
                    clk, can_bfm_tx, can_bfm_rx, can_uvvm_bfm_cfg);
    end procedure can_hlp_check;

    procedure latch_counters_0 is
    begin
      wb_write(WB_ADDB.CAN_HLP_MONITOR_0, 0, x"0001", "Latch counters in monitor module 0");
    end;

    procedure latch_counters_1 is
    begin
      wb_write(WB_ADDB.CAN_HLP_MONITOR_1, 0, x"0001", "Latch counters in monitor module 1");
    end;

    procedure latch_counters_2 is
    begin
      wb_write(WB_ADDB.CAN_HLP_MONITOR_2, 0, x"0001", "Latch counters in monitor module 2");
    end;

    procedure latch_counters_3 is
    begin
      wb_write(WB_ADDB.CAN_HLP_MONITOR_3, 0, x"0001", "Latch counters in monitor module 3");
    end;

    procedure set_can_hlp_bitrate_1mbit (
      constant can_hlp_module_addr : in natural) is
    begin
      -- Reconfigure for 10 time quantas
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PROP_SEG),
               x"0007", "Update propagation segment for 4 Mbit");
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PHASE_SEG1),
               x"0007", "Update phase segment 1 for 4 Mbit");
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PHASE_SEG2),
               x"0007", "Update phase segment 2 for 4 Mbit");

      -- Set clock prescale to 16
      wb_write(WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_CAN_CLK_SCALE),
               x"000F", "Update clock scale for 1 Mbit");
    end procedure set_can_hlp_bitrate_1mbit;

    procedure set_can_hlp_bitrate_4mbit (
      constant can_hlp_module_addr : in natural) is
    begin
      -- Reconfigure for 10 time quantas
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PROP_SEG),
               x"0007", "Update propagation segment for 4 Mbit");
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PHASE_SEG1),
               x"0007", "Update phase segment 1 for 4 Mbit");
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_PHASE_SEG2),
               x"0007", "Update phase segment 2 for 4 Mbit");

      -- Set clock prescale to 4
      wb_write(can_hlp_module_addr, WB_ADD'pos(A_CAN_CLK_SCALE),
               x"0003", "Update clock scale for 4 Mbit");
    end procedure set_can_hlp_bitrate_4mbit;


    procedure generate_random_data (
      variable data        : out std_logic_vector;
      constant data_length : in  natural)
    is
      variable rand_real : real;
      variable rand_int  : integer;
      variable rand_data : std_logic_vector(0 to data'length-1) := (others => '0');
    begin
      assert data_length <= data'length
                            report "Desired data length larger than data vector size"
                            severity error;

      -- Because the integer type is 32 bits in VHDL,
      -- this procedure fails if the data length is larger than 31 bits
      assert data_length < 32
        report "Data length larger than 31 bits not supported"
        severity error;

      uniform(seed1, seed2, rand_real);

      rand_int := integer(rand_real*real(2**data_length-1));

      data := std_logic_vector(to_unsigned(rand_int, data_length));
    end procedure generate_random_data;

  -- p_main process
  begin
    wb_bfm_cfg.clock_period                  := C_CLK_PERIOD;
    can_uvvm_bfm_cfg.can_config.clock_period := C_CLK_PERIOD;
    can_uvvm_bfm_cfg.can_config.bit_rate     := 250000;

    -- Print the configuration to the log
    report_global_ctrl(VOID);
    report_msg_id_panel(VOID);

    enable_log_msg(ALL_MESSAGES);
    --disable_log_msg(ALL_MESSAGES);
    --enable_log_msg(ID_LOG_HDR);

    -- Only using HLP instances 0 at first,
    -- keep the other instances in reset
    reset(1) <= '1';
    reset(2) <= '1';
    reset(3) <= '1';


    log(ID_LOG_HDR, "Start CAN controller testbench at 250 kbit (default)", C_SCOPE);
    ------------------------------------------------------------

    --set_inputs_passive(VOID);
    clock_ena <= true;   -- to start clock generator
    pulse(reset(0), clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_hlp_write(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG),
                  x"ABCD", "Test write to HLP_TEST_REG");

    can_hlp_check(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG),
                  x"ABCD", ERROR, "Test read back from HLP_TEST_REG");

    latch_counters_0;

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_LOW,
                 data_read, "Read CNTR_CAN_RX_MSG_RECV_COUNT");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_LOW,
                 data_read, "Read CNTR_CAN_TX_MSG_SENT_COUNT");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_LOW,
                 data_read, "Read CNTR_HLP_READ_LOW");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_LOW,
                 data_read, "Read CNTR_HLP_WRITE_LOW");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_STATUS,
                 data_read, "Read CNTR_HLP_STATUS");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_ALERT,
                 data_read, "Read CNTR_HLP_ALERT");

    can_hlp_read(can_hlp_node_id(0),
                 WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_UNKNOWN,
                 data_read, "Read CNTR_HLP_UNKNOWN");

    wait for 10 us;

    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Change bitrate to 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    can_hlp_write(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), x"1234",
                  "Test write to HLP_TEST_REG");

    can_hlp_check(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), x"1234",
                  ERROR, "Test read back from HLP_TEST_REG");


    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Change bitrate to 1 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------

    can_uvvm_bfm_cfg.can_config.bit_rate := 1000000;

    set_can_hlp_bitrate_1mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    can_hlp_write(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), x"5678",
                  "Test write to HLP_TEST_REG");

    can_hlp_check(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), x"5678",
                  ERROR, "Test read back from HLP_TEST_REG");


    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Test HLP read and write @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    pulse(reset(0), clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    hlp_read_count   := to_unsigned(0, hlp_read_count'length);
    hlp_write_count  := to_unsigned(0, hlp_write_count'length);
    hlp_alert_count  := to_unsigned(0, hlp_alert_count'length);
    hlp_status_count := to_unsigned(0, hlp_status_count'length);
    can_rx_msg_count := to_unsigned(0, can_rx_msg_count'length);
    can_tx_msg_count := to_unsigned(0, can_tx_msg_count'length);

    for i in 0 to C_NUM_TESTS loop
      generate_random_data(rand_data, rand_data'length);

      can_hlp_write(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), rand_data,
                    "Test write to HLP_TEST_REG");

      hlp_write_count  := hlp_write_count + 1;

      -- Each HLP transaction has a received and transmitted CAN message
      can_rx_msg_count := can_rx_msg_count + 1;
      can_tx_msg_count := can_tx_msg_count + 1;


      can_hlp_check(can_hlp_node_id(0), WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_TEST_REG), rand_data,
                    ERROR, "Test read back from HLP_TEST_REG");

      -- can_hlp_check performs one HLP read transaction
      hlp_read_count   := hlp_read_count + 1;

      -- Each HLP transaction has a received and transmitted CAN message
      can_rx_msg_count := can_rx_msg_count + 1;
      can_tx_msg_count := can_tx_msg_count + 1;

      -- Wait for one bit period before latching counters,
      -- otherwise the last transmitted message from the CAN controller
      -- will not have been counted
      wait for 0.25 us;

      latch_counters_0;

      -- Use HLP to read the counters as well
      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_LOW,
                    std_logic_vector(hlp_read_count(15 downto 0)),
                    ERROR,
                    "Check HLP read transaction count (LSB)");
      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_HIGH,
                    std_logic_vector(hlp_read_count(31 downto 16)),
                    ERROR,
                    "Check HLP read transaction count (MSB)");

      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_LOW,
                    std_logic_vector(hlp_write_count(15 downto 0)),
                    ERROR,
                    "Check HLP write transaction count (LSB)");
      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_HIGH,
                    std_logic_vector(hlp_write_count(31 downto 16)),
                    ERROR,
                    "Check HLP write transaction count (MSB)");

      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_LOW,
                    std_logic_vector(can_rx_msg_count(15 downto 0)),
                    error,
                    "Check CAN messages received (LSB)");
      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_HIGH,
                    std_logic_vector(can_rx_msg_count(31 downto 16)),
                    error,
                    "Check CAN messages received (MSB)");

      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_LOW,
                    std_logic_vector(can_tx_msg_count(15 downto 0)),
                    error,
                    "Check CAN messages transmitted (LSB)");
      can_hlp_check(can_hlp_node_id(0),
                    WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_HIGH,
                    std_logic_vector(can_tx_msg_count(31 downto 16)),
                    error,
                    "Check CAN messages transmitted (MSB)");

      -- can_hlp_check performs one HLP read transaction
      hlp_read_count   := hlp_read_count + 8;

      -- Each HLP transaction has a received and transmitted CAN message
      can_rx_msg_count := can_rx_msg_count + 8;
      can_tx_msg_count := can_tx_msg_count + 8;

    end loop;  -- i



    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Enable HLP test mode @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    pulse(reset(0), clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    data_write                          := (others => '0');
    data_write(C_CTRL_TEST_MODE_EN_bit) := '1';

    -- Enable HLP test mode.
    -- In this mode the controller continuously spits out
    -- messages with payload of 8 bytes
    wb_write(WB_ADDB.CAN_HLP_0, WB_ADD'pos(A_CTRL),
             data_write, "Enable HLP test mode");

    arb_id_a(C_NODE_ID_range'range) := can_hlp_node_id(0);
    arb_id_a(C_CMD_ID_range'range)  := C_TEST;
    arb_id_b                        := (others => '0');

    -- 0xAA is the expected value for all of the 8 bytes
    for i in 0 to to_integer(unsigned(C_TEST_LEN))-1 loop
      can_data(i) := x"AA";
    end loop;

    for i in 0 to C_NUM_TESTS loop
      -- Verify received HLP TEST data
      can_uvvm_check(arb_id_a, arb_id_b,
                     '0', -- no ext id
                     '0', -- don't expect remote request
                     '0', -- don't send remote frame request
                     can_data,
                     to_integer(unsigned(C_TEST_LEN)),
                     "Verify HLP_TEST data",
                     clk,
                     can_bfm_tx,
                     can_bfm_rx,
                     error,
                     can_uvvm_bfm_cfg);
    end loop;


    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Test HLP status messages @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    pulse(reset(0), clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    hlp_read_count   := to_unsigned(0, hlp_read_count'length);
    hlp_write_count  := to_unsigned(0, hlp_write_count'length);
    hlp_alert_count  := to_unsigned(0, hlp_alert_count'length);
    hlp_status_count := to_unsigned(0, hlp_status_count'length);
    can_rx_msg_count := to_unsigned(0, can_rx_msg_count'length);
    can_tx_msg_count := to_unsigned(0, can_tx_msg_count'length);

    -- Set up expected arbitration ID for HLP STATUS message for this node
    arb_id_a(C_NODE_ID_range'range) := can_hlp_node_id(0);
    arb_id_a(C_CMD_ID_range'range)  := C_STATUS;
    arb_id_b                        := (others => '0');

    for i in 0 to 7 loop
      can_data(i) := (others => '0');
    end loop;

    for i in 0 to C_NUM_TESTS loop
      -- generate_random_data doesn't support 32-bit length
      generate_random_data(rand_status_data(15 downto 0), 16);
      generate_random_data(rand_status_data(31 downto 16), 16);

      s_status_alert_data(0)                         <= (others => '0');
      s_status_alert_data(0)(rand_status_data'range) <= rand_status_data;

      for i in 0 to to_integer(unsigned(C_STATUS_LEN))-1 loop
        can_data(i) := rand_status_data(8*(i+1)-1 downto 8*i);
      end loop;

      wait for 1 us;
      wait until rising_edge(clk);

      -- Send status message from CAN HLP instance
      s_send_status(0) <= '1';
      wait until rising_edge(clk);
      s_send_status(0) <= '0';

      -- Verify received HLP STATUS data with BFM
      can_uvvm_check(arb_id_a, arb_id_b,
                     '0', -- no ext id
                     '0', -- don't expect remote request
                     '0', -- don't send remote frame request
                     can_data,
                     to_integer(unsigned(C_STATUS_LEN)),
                     "Verify HLP_STATUS data",
                     clk,
                     can_bfm_tx,
                     can_bfm_rx,
                     error,
                     can_uvvm_bfm_cfg);

      wait for 1 us;

      can_tx_msg_count := can_tx_msg_count + 1;
      hlp_status_count := hlp_status_count + 1;

      latch_counters_0;

      wait for 1 us;

      -- Check counter values
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_STATUS,
               std_logic_vector(hlp_status_count),
               error,
               "Check HLP status messages");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_ALERT,
               std_logic_vector(hlp_alert_count),
               error,
               "Check HLP alert messages");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_LOW,
               std_logic_vector(hlp_read_count(15 downto 0)),
               error,
               "Check HLP read transaction count (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_HIGH,
               std_logic_vector(hlp_read_count(31 downto 16)),
               error,
               "Check HLP read transaction count (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_LOW,
               std_logic_vector(hlp_write_count(15 downto 0)),
               error,
               "Check HLP write transaction count (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_HIGH,
               std_logic_vector(hlp_write_count(31 downto 16)),
               error,
               "Check HLP write transaction count (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_LOW,
               std_logic_vector(can_rx_msg_count(15 downto 0)),
               error,
               "Check CAN messages received (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_HIGH,
               std_logic_vector(can_rx_msg_count(31 downto 16)),
               error,
               "Check CAN messages received (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_LOW,
               std_logic_vector(can_tx_msg_count(15 downto 0)),
               error,
               "Check CAN messages transmitted (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_HIGH,
               std_logic_vector(can_tx_msg_count(31 downto 16)),
               error,
               "Check CAN messages transmitted (MSB)");
    end loop;




    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Test HLP alert messages @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    pulse(reset(0), clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    hlp_read_count   := to_unsigned(0, hlp_read_count'length);
    hlp_write_count  := to_unsigned(0, hlp_write_count'length);
    hlp_alert_count  := to_unsigned(0, hlp_alert_count'length);
    hlp_status_count := to_unsigned(0, hlp_status_count'length);
    can_rx_msg_count := to_unsigned(0, can_rx_msg_count'length);
    can_tx_msg_count := to_unsigned(0, can_tx_msg_count'length);

    -- Set up expected arbitration ID for HLP ALERT message for this node
    arb_id_a(C_NODE_ID_range'range) := can_hlp_node_id(0);
    arb_id_a(C_CMD_ID_range'range)  := C_ALERT;
    arb_id_b                        := (others => '0');

    for i in 0 to 7 loop
      can_data(i) := (others => '0');
    end loop;

    for i in 0 to C_NUM_TESTS loop
      generate_random_data(rand_alert_data, rand_alert_data'length);

      s_status_alert_data(0)                        <= (others => '0');
      s_status_alert_data(0)(rand_alert_data'range) <= rand_alert_data;

      for i in 0 to to_integer(unsigned(C_ALERT_LEN))-1 loop
        can_data(i) := rand_alert_data(8*(i+1)-1 downto 8*i);
      end loop;

      wait for 1 us;
      wait until rising_edge(clk);

      -- Send alert message from CAN HLP instance
      s_send_alert(0) <= '1';
      wait until rising_edge(clk);
      s_send_alert(0) <= '0';

      -- Verify received HLP ALERT data with BFM
      can_uvvm_check(arb_id_a, arb_id_b,
                     '0', -- no ext id
                     '0', -- don't expect remote request
                     '0', -- don't send remote frame request
                     can_data,
                     to_integer(unsigned(C_ALERT_LEN)),
                     "Verify HLP_ALERT data",
                     clk,
                     can_bfm_tx,
                     can_bfm_rx,
                     error,
                     can_uvvm_bfm_cfg);

      wait for 1 us;

      can_tx_msg_count := can_tx_msg_count + 1;
      hlp_alert_count  := hlp_alert_count + 1;

      latch_counters_0;

      wait for 1 us;

      -- Check counter values
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_STATUS,
               std_logic_vector(hlp_status_count),
               error,
               "Check HLP status messages");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_ALERT,
               std_logic_vector(hlp_alert_count),
               error,
               "Check HLP alert messages");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_LOW,
               std_logic_vector(hlp_read_count(15 downto 0)),
               error,
               "Check HLP read transaction count (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_READ_HIGH,
               std_logic_vector(hlp_read_count(31 downto 16)),
               error,
               "Check HLP read transaction count (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_LOW,
               std_logic_vector(hlp_write_count(15 downto 0)),
               error,
               "Check HLP write transaction count (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_HLP_WRITE_HIGH,
               std_logic_vector(hlp_write_count(31 downto 16)),
               error,
               "Check HLP write transaction count (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_LOW,
               std_logic_vector(can_rx_msg_count(15 downto 0)),
               error,
               "Check CAN messages received (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_RX_MSG_RECV_HIGH,
               std_logic_vector(can_rx_msg_count(31 downto 16)),
               error,
               "Check CAN messages received (MSB)");

      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_LOW,
               std_logic_vector(can_tx_msg_count(15 downto 0)),
               error,
               "Check CAN messages transmitted (LSB)");
      wb_check(WB_ADDB.CAN_HLP_MONITOR_0, C_CNTR_START_ADDR+C_CNTR_CAN_TX_MSG_SENT_HIGH,
               std_logic_vector(can_tx_msg_count(31 downto 16)),
               error,
               "Check CAN messages transmitted (MSB)");
    end loop;

    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Test addressing of multiple HLP nodes @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    pulse(reset, "1111", clk, 10, "Pulsed reset-signal - active for 62.5 ns");

    can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;

    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0);
    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_1);
    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_2);
    set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_3);

    -- Allow the time quanta generator in the controller
    -- some time to adjust to new baud rate
    wait for 5 us;

    for i in 0 to C_NUM_TESTS loop
      for j in 0 to C_NUM_HLP_INSTANCES-1 loop
        generate_random_data(rand_data, rand_data'length);

        can_hlp_write(can_hlp_node_id(j), WB_ADDB.CAN_HLP_0+j, WB_ADD'pos(A_TEST_REG), rand_data,
                      "Write to HLP_TEST_REG");

        can_hlp_check(can_hlp_node_id(j), WB_ADDB.CAN_HLP_0+j, WB_ADD'pos(A_TEST_REG),
                      rand_data, ERROR, "Read back HLP_TEST_REG");

      end loop;
    end loop;


    ---------------------------------------------------------------------------
    log(ID_LOG_HDR, "Test broadcast with multiple HLP nodes @ 4 Mbit", C_SCOPE);
    ---------------------------------------------------------------------------
    for i in 0 to C_NUM_TESTS loop
      for j in 0 to C_NUM_HLP_INSTANCES-1 loop
        -- Keep the other controllers in reset, so we
        -- only get one response for the broadcast commands
        -- Todo: Test broadcast with ALL controllers active simultaneously
        reset    <= (others => '1');
        wait for 1 us;
        reset(j) <= '0';
        wait for 1 us;

        can_uvvm_bfm_cfg.can_config.bit_rate := 4000000;
        set_can_hlp_bitrate_4mbit(WB_ADDB.CAN_HLP_0+j);

        -- Allow the time quanta generator in the controller
        -- some time to adjust to new baud rate
        wait for 5 us;

        generate_random_data(rand_data, rand_data'length);

        can_hlp_write(C_CAN_BROADCAST_ID, WB_ADDB.CAN_HLP_0+j, WB_ADD'pos(A_TEST_REG), rand_data,
                    "Write to HLP_TEST_REG");

        can_hlp_check(C_CAN_BROADCAST_ID, WB_ADDB.CAN_HLP_0+j, WB_ADD'pos(A_TEST_REG),
                      rand_data, ERROR, "Read back HLP_TEST_REG");

      end loop;
    end loop;


    wait for 100 us;             -- to allow some time for completion

    report_alert_counters(FINAL); -- Report final counters and print conclusion for simulation (Success/Fail)
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);

    -- Finish the simulation
    std.env.finish;
    wait;  -- to stop completely

  end process p_main;

end func;
