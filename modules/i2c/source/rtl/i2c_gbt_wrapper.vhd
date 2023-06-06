-------------------------------------------------------------------------------
-- Title      : I2C Interface - Wrapper for I2C wishbone master core
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_gbt_wrapper.vhd
-- Author     : J. Schambach
-- Company    : University of Texas at Austin
-- Created    : 2017-06-16
-- Last update: 2019-02-11
-- Platform   : Xilinx Vivado 2016.4
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wrap wishbone slave for I2C to provide full I2C transactions
--              for GBTx ASICs
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;
use work.i2c_pkg.all;

entity i2c_gbt_wrapper is
  port (
    -- Wishbone interface signals
    WB_CLK         : in  std_logic;     -- master clock input
    WB_RST         : in  std_logic;     -- synchronous active high reset
    WB_WBS_I       : in  wbs_i_type;
    WB_WBS_O       : out wbs_o_type;
    -- debug output pulses
    COMPLETED_BYTE : out std_logic;
    AL_ERROR       : out std_logic;
    NOACK_ERROR    : out std_logic;
    -- i2c lines
    SCL_PAD_i      : in  std_logic;     -- i2c clock line input
    SCL_PAD_o      : out std_logic;     -- i2c clock line output
    SCL_PAD_T      : out std_logic;  -- i2c clock line output enable, active low
    SDA_PAD_i      : in  std_logic;     -- i2c data line input
    SDA_PAD_o      : out std_logic;     -- i2c data line output
    SDA_PAD_T      : out std_logic   -- i2c data line output enable, active low
    );
end entity i2c_gbt_wrapper;

architecture structural of i2c_gbt_wrapper is
  constant C_GBTX0_SLAVE_ADDR : std_logic_vector(6 downto 0) := "0000001";
  constant C_GBTX1_SLAVE_ADDR : std_logic_vector(6 downto 0) := "0000011";
  constant C_GBTX2_SLAVE_ADDR : std_logic_vector(6 downto 0) := "0000101";

  type slave_array_t is array (0 to 2) of std_logic_vector(6 downto 0);
  constant C_GBTX_SLAVE_ADDR : slave_array_t :=
    (0 => C_GBTX0_SLAVE_ADDR,
     1 => C_GBTX1_SLAVE_ADDR,
     2 => C_GBTX2_SLAVE_ADDR);


  constant NR_REGISTERS : natural := 4;

  type wb_state_t is (WB_IDLE,
                      WB_ERR,
                      WB_ACK,
                      WAIT_TIP_HI,
                      WAIT_TIP_LO,
                      WR_FIRST_BYTE,
                      WR_SECOND_BYTE,
                      WR_DATA_OR_RD,
                      CHECK_WRITE,
                      READ_BYTE,
                      STORE_BYTE
                      );

  type registers_t is record
    state       : wb_state_t;
    next_state  : wb_state_t;
    gbtxRegAddr : unsigned(15 downto 0);
    slaveAddr   : std_logic_vector(6 downto 0);
    i2cData     : std_logic_vector(7 downto 0);
  end record registers_t;

  signal sRegs, sNextRegs : registers_t;
  constant cDefaultRegs : registers_t := (state       => WB_IDLE,
                                          next_state  => WB_IDLE,
                                          gbtxRegAddr => (others => '0'),
                                          slaveAddr   => (others => '0'),
                                          i2cData     => (others => '0')
                                          );


  signal iWbAddr : natural range 0 to 255;

  signal sCoreEn    : std_logic := '0';
  signal sData_i    : std_logic_vector(7 downto 0);
  signal sWeData    : std_logic;
  signal sCommand   : std_logic_vector(4 downto 0);
  signal sWeCommand : std_logic;
  signal sData_o    : std_logic_vector(7 downto 0);
  signal sStatus    : std_logic_vector(3 downto 0);

  signal sCompletedByte : std_logic;
  signal sAlError       : std_logic;
  signal sNoackError    : std_logic;

  component i2c_frequency_selector is
    generic (FREQ_SELECTION_BIT_WIDTH :     integer);
    port (frequency_setting_o         : out std_logic_vector(FREQ_SELECTION_BIT_WIDTH-1 downto 0));
  end component;
  signal sFreqSetting : std_logic_vector(C_FREQ_SELECTION_BIT_WIDTH-1 downto 0);

begin

  i2c_frequency_selector_INST : i2c_frequency_selector
    generic map (
      FREQ_SELECTION_BIT_WIDTH => C_FREQ_SELECTION_BIT_WIDTH)
    port map (
      frequency_setting_o => sFreqSetting);

  p_register_outputs : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
        COMPLETED_BYTE <= '0';
        AL_ERROR       <= '0';
        NOACK_ERROR    <= '0';
      else
        COMPLETED_BYTE <= sCompletedByte;
        AL_ERROR       <= sAlError;
        NOACK_ERROR    <= sNoackError;
      end if;
    end if;
  end process p_register_outputs;

  iWbAddr        <= to_integer(unsigned(WB_WBS_I.addr_i));
  WB_WBS_O.dat_o <= std_logic_vector(sRegs.gbtxRegAddr) when iWbAddr < 3 else
                    wb_resize(sRegs.i2cData) when iWbAddr = 3 else
                    x"DEAD";


  p_WishboneSlave : process (WB_CLK) is
  begin  -- process p_WishboneSlave
    if rising_edge(WB_CLK) then         -- rising clock edge
      if WB_RST = '1' then              -- synchronous reset (active high)
        sRegs   <= cDefaultRegs;
        sCoreEn <= '0';
      else
        sCoreEn <= '1';
        sRegs   <= sNextRegs;
      end if;
    end if;
  end process p_WishboneSlave;

  WB_WBS_O.ack_o <= '1' when sRegs.state = WB_ACK else '0';
  WB_WBS_O.err_o <= '1' when sRegs.state = WB_ERR else '0';

  p_nextstate : process (WB_WBS_I, iWbAddr, sData_o, sRegs, sStatus) is
    variable vNextRegs : registers_t;
    variable vCmd      : std_logic_vector(4 downto 0);

    procedure i2c_core_set (
      constant data    : in std_logic_vector(7 downto 0);
      constant we_data : in std_logic;
      constant cmd     : in std_logic_vector(4 downto 0);
      constant we_cmd  : in std_logic) is
    begin  -- procedure i2_core_set
      sData_i    <= data;
      sWeData    <= we_data;
      sCommand   <= cmd;
      sWeCommand <= we_cmd;
    end procedure i2c_core_set;

  begin  -- process p_nextstate
    -- default: keep state, write nothing to i2c core
    vNextRegs := sRegs;
    i2c_core_set(x"00", '0', "00000", '0');

    sCompletedByte <= '0';
    sAlError       <= '0';
    sNoackError    <= '0';

    case sRegs.state is
      when WB_IDLE =>
        if (WB_WBS_I.cyc_i and WB_WBS_I.stb_i) = '1' then
          -- default: assume single cycle access to register
          vNextRegs.state := WB_ACK;

          if iWbAddr >= NR_REGISTERS then
            vNextRegs.state := WB_ERR;
          elsif iWbAddr = 3 then
            -- data: slave address & write bit; cmd: STA & WR
            vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
            i2c_core_set(sRegs.slaveAddr & '0', '1', vCmd, '1');
            vNextRegs.state      := WAIT_TIP_HI;
            vNextRegs.next_state := WR_FIRST_BYTE;
          else
            if WB_WBS_I.we_i = '1' then
              vNextRegs.gbtxRegAddr := unsigned(WB_WBS_I.dat_i);
              vNextRegs.slaveAddr   := C_GBTX_SLAVE_ADDR(iWbAddr);
            end if;
          end if;
        end if;

      when WB_ACK | WB_ERR =>
        -- finalize WB transfger when strobe is deasserted
        if WB_WBS_I.stb_i = '0' then
          vNextRegs.state := WB_IDLE;
        end if;

      when WAIT_TIP_HI =>
        if sStatus(I2C_STAT_AL) = '1' then
          sAlError        <= '1';
          -- Arbitration lost
          vNextRegs.state := WB_ERR;
        elsif sStatus(I2C_STAT_TIP) = '1' then
          -- transfer started
          vNextRegs.state := WAIT_TIP_LO;
        end if;

      when WAIT_TIP_LO =>
        if sStatus(I2C_STAT_AL) = '1' then
          -- Arbitration lost
          sAlError        <= '1';
          vNextRegs.state := WB_ERR;
        elsif sStatus(I2C_STAT_TIP) = '0' then
          sCompletedByte    <= '1';
          -- transfer finished
          vNextRegs.state   := sRegs.next_state;
          vNextRegs.i2cData := sData_o;
        end if;

      when WR_FIRST_BYTE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data: reg addr LSB; cmd: WR
          vCmd                 := I2C_CMD_WRITE;
          i2c_core_set(std_logic_vector(sRegs.gbtxRegAddr(7 downto 0)), '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := WR_SECOND_BYTE;
        end if;

      when WR_SECOND_BYTE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data: reg addr MSB; cmd: WR
          vCmd                  := I2C_CMD_WRITE;
          i2c_core_set(std_logic_vector(sRegs.gbtxRegAddr(15 downto 8)), '1', vCmd, '1');
          vNextRegs.state       := WAIT_TIP_HI;
          vNextRegs.next_state  := WR_DATA_OR_RD;
          -- increase register address
          vNextRegs.gbtxRegAddr := sRegs.gbtxRegAddr + 1;
        end if;

      when WR_DATA_OR_RD =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          if WB_WBS_I.we_i = '1' then
            -- write: data = WB.dat_i; cmd = WR & STO
            vCmd                 := I2C_CMD_WRITE or I2C_CMD_STOP;
            i2c_core_set(WB_WBS_I.dat_i(7 downto 0), '1', vCmd, '1');
            vNextRegs.state      := WAIT_TIP_HI;
            vNextRegs.next_state := CHECK_WRITE;
            vNextRegs.i2cData    := (others => '1');
          else
            -- read: data = slave address & read bit, cmd = WR & STA
            vCmd                 := I2C_CMD_WRITE or I2C_CMD_START;
            i2c_core_set(sRegs.slaveAddr & '1', '1', vCmd, '1');
            vNextRegs.state      := WAIT_TIP_HI;
            vNextRegs.next_state := READ_BYTE;
          end if;
        end if;

      when CHECK_WRITE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          vNextRegs.state := WB_ERR;
        else
          vNextRegs.state := WB_ACK;
        end if;

      when READ_BYTE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data = 0; cmd = RD & STO & ACK
          vCmd                 := I2C_CMD_READ or I2C_CMD_STOP or I2C_CMD_ACK;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := STORE_BYTE;
        end if;

      when STORE_BYTE =>
        vNextRegs.state := WB_ACK;

      when others => null;
    end case;

    sNextRegs <= vNextRegs;
  end process p_nextstate;

  INST_gbt_i2c_master : entity work.i2c_master_top
    port map (
      CLK        => WB_CLK,
      RST        => WB_RST,
      CORE_EN    => sCoreEn,
      PRER_i     => sFreqSetting,
      DATA_i     => sData_i,
      WE_DATA    => sWeData,
      COMMAND    => sCommand,
      WE_COMMAND => sWeCommand,
      DATA_o     => sData_o,
      STATUS     => sStatus,
      SCL_PAD_i  => SCL_PAD_i,
      SCL_PAD_o  => SCL_PAD_o,
      SCL_PAD_T  => SCL_PAD_T,
      SDA_PAD_i  => SDA_PAD_i,
      SDA_PAD_o  => SDA_PAD_o,
      SDA_PAD_T  => SDA_PAD_T
      );


end architecture structural;
