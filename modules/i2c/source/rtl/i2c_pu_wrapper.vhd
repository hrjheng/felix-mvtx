-------------------------------------------------------------------------------
-- Title      : I2C Interface - Wrapper for I2C wishbone master core
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_wrapper.vhd
-- Author     : J. Schambach
-- Company    : University of Texas at Austin
-- Created    : 2017-06-16
-- Last update: 2019-04-10
-- Platform   : Xilinx Vivado 2016.4
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wrap wishbone slave for I2C to provide full I2C transactions
--              for controlling the power unit
--
--              I2C bus frequency is set to 100kHz, based on a wishbone
--              speed of 160MHz
--
--              I2C slave addresses are mapped to wishbone register addresses
--
--              I2C write transactions bytes are sent as:
--              SL - sByte1 - sByte2 - sByte3   or
--              SL - sByte2 - sByte3            or
--              SL - sByte3
--
--              I2C read transactions bytes are as follows:
--              SL - read[7:0]                  or
--              SL - read[15:8] - read[7:0]     or
--              SL - sByte1 - read[15:8] - read[7:0]
--
--              sByte1 is sent to wishbone address 0, while sByte2 and sByte3
--              are sent to the appropriate wishbone write address as
--              data[15:8] and data[7:0], respectively.
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;
use work.i2c_pkg.all;

entity i2c_pu_wrapper is
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
    -- "main" i2c lines
    SCL_PAD_i      : in  std_logic;     -- i2c clock line input
    SCL_PAD_o      : out std_logic;     -- i2c clock line output
    SCL_PAD_T      : out std_logic;  -- i2c clock line output enable, active low
    SDA_PAD_i      : in  std_logic;     -- i2c data line input
    SDA_PAD_o      : out std_logic;     -- i2c data line output
    SDA_PAD_T      : out std_logic;  -- i2c data line output enable, active low
    -- "aux" i2c lines
    AUX_SCL_PAD_i  : in  std_logic;     -- i2c clock line input
    AUX_SCL_PAD_o  : out std_logic;     -- i2c clock line output
    AUX_SCL_PAD_T  : out std_logic;  -- i2c clock line output enable, active low
    AUX_SDA_PAD_i  : in  std_logic;     -- i2c data line input
    AUX_SDA_PAD_o  : out std_logic;     -- i2c data line output
    AUX_SDA_PAD_T  : out std_logic   -- i2c data line output enable, active low
    );
end entity i2c_pu_wrapper;

architecture structural of i2c_pu_wrapper is
  -- Main I2C bus
  constant C_T_THR_SLAVE_ADDR      : std_logic_vector(6 downto 0) := "0101000";
  constant C_A_THR01_04_SLAVE_ADDR : std_logic_vector(6 downto 0) := "1010010";
  constant C_A_THR05_08_SLAVE_ADDR : std_logic_vector(6 downto 0) := "1100000";
  constant C_A_THR09_12_SLAVE_ADDR : std_logic_vector(6 downto 0) := "1110000";
  constant C_A_THR13_16_SLAVE_ADDR : std_logic_vector(6 downto 0) := "1110010";
  constant C_V01_04_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0101100";
  constant C_V05_08_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0101101";
  constant C_V09_12_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0101110";
  constant C_V13_16_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0101111";
  constant C_B_V_SLAVE_ADDR        : std_logic_vector(6 downto 0) := "0101001";
  constant C_ADC1_2_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0011101";
  constant C_ADC3_4_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0011111";
  constant C_ADC5_6_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0110101";
  constant C_ADC7_8_SLAVE_ADDR     : std_logic_vector(6 downto 0) := "0110111";
  constant C_ADC_B_SLAVE_ADDR      : std_logic_vector(6 downto 0) := "0011110";
  constant C_EN_B_SLAVE_ADDR       : std_logic_vector(6 downto 0) := "0111000";
  -- Aux I2C bus
  constant C_EN1_4_SLAVE_ADDR      : std_logic_vector(6 downto 0) := "0111000";
  constant C_EN5_8_SLAVE_ADDR      : std_logic_vector(6 downto 0) := "0111001";



  component i2c_frequency_selector is
    generic (FREQ_SELECTION_BIT_WIDTH :     integer);
    port (frequency_setting_o         : out std_logic_vector(FREQ_SELECTION_BIT_WIDTH-1 downto 0));
  end component;
  signal sFreqSetting : std_logic_vector(C_FREQ_SELECTION_BIT_WIDTH-1 downto 0);

  type wb_state_t is (WB_IDLE,
                      WB_ERR,
                      WB_ACK,
                      WAIT_TIP_HI,
                      WAIT_TIP_LO,
                      WR_BYTE0,
                      WR_BYTE1,
                      WR_BYTE2,
                      WR_BYTE3,
                      CHECK_WRITE,
                      RD_RTD0,
                      RD_RTD1,
                      RD_BYTE1,
                      SHIFT_DATA,
                      RD_BYTE2,
                      STORE_BYTE
                      );

  type registers_t is record
    state      : wb_state_t;
    next_state : wb_state_t;
    byte0      : std_logic_vector(7 downto 0);
    byte1      : std_logic_vector(7 downto 0);
    i2cData    : std_logic_vector(15 downto 0);
  end record registers_t;

  signal sRegs, sNextRegs : registers_t;
  constant cDefaultRegs : registers_t := (state      => WB_IDLE,
                                          next_state => WB_IDLE,
                                          byte0      => (others => '0'),
                                          byte1      => (others => '0'),
                                          i2cData    => (others => '0')
                                          );


  signal iWbAddr : natural range 0 to 255;

  signal sCoreEn    : std_logic := '0';
  signal sData_i    : std_logic_vector(7 downto 0);
  signal sWeData    : std_logic;
  signal sCommand   : std_logic_vector(4 downto 0);
  signal sWeCommand : std_logic;
  signal sData_o    : std_logic_vector(7 downto 0);
  signal sStatus    : std_logic_vector(3 downto 0);

  signal sWeData_main : std_logic;
  signal sWeCmd_main  : std_logic;
  signal sWeData_aux  : std_logic;
  signal sWeCmd_aux   : std_logic;
  signal sDataMain_o  : std_logic_vector(7 downto 0);
  signal sDataAux_o   : std_logic_vector(7 downto 0);
  signal sStatus_main : std_logic_vector(3 downto 0);
  signal sStatus_aux  : std_logic_vector(3 downto 0);

  signal sCompletedByte : std_logic;
  signal sAlError       : std_logic;
  signal sNoackError    : std_logic;

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

  iWbAddr <= to_integer(unsigned(WB_WBS_I.addr_i));

  -- wishbone read assignment
  p_WB_data_o_assign : process (iWbAddr, sRegs) is
  begin
    case iWbAddr is
      when 0 =>
        WB_WBS_O.dat_o <= sRegs.byte0 & sRegs.byte1;
      when 16 to 23 =>
        WB_WBS_O.dat_o <= sRegs.i2cData;
      when 32 | 33 =>
        WB_WBS_O.dat_o <= sRegs.i2cData;
      when others =>
        WB_WBS_O.dat_o <= x"DEAD";
    end case;
  end process p_WB_data_o_assign;

  p_WishboneSlave : process (WB_CLK) is
  begin
    if rising_edge(WB_CLK) then
      if WB_RST = '1' then
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

  begin
    -- default: keep state, write nothing to i2c core
    vNextRegs := sRegs;
    i2c_core_set(x"00", '0', "00000", '0');

    sCompletedByte <= '0';
    sAlError       <= '0';
    sNoackError    <= '0';


    case sRegs.state is
      when WB_IDLE =>
        if (WB_WBS_I.cyc_i and WB_WBS_I.stb_i) = '1' then

          if WB_WBS_I.we_i = '0' then
            -- ****************** read transaction ***********************
            vNextRegs.i2cData := (others => '0');
            case iWbAddr is
              when 0 =>
                vNextRegs.state := WB_ACK;
---           // read 2 bytes
              when 16 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC1_2_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 2 bytes
              when 17 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC3_4_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 2 bytes
              when 18 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC5_6_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 2 bytes
              when 19 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC7_8_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 2 bytes
              when 20 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC_B_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 2 bytes
              when 21 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_T_THR_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE1;

---           // read 1 byte
              when 22 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN_B_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE2;

---           // read 3 bytes, store the last 2
              when 23 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_T_THR_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_RTD0;

--            // AUX bus: read 1 byte
              when 32 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN1_4_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE2;

--            // AUX bus: read 1 byte
              when 33 =>
                -- data: slave address & read bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN5_8_SLAVE_ADDR & '1', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := RD_BYTE2;

--            // all other addresses are error
              when others =>
                vNextRegs.state := WB_ERR;
            end case;

          else
            -- *********** write transaction ***********************
            case iWbAddr is
              when 0 =>
                vNextRegs.byte0 := WB_WBS_I.dat_i(15 downto 8);
                vNextRegs.byte1 := WB_WBS_I.dat_i(7 downto 0);
                vNextRegs.state := WB_ACK;

--            // write 3 bytes
              when 1 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_T_THR_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 3 bytes
              when 2 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_A_THR01_04_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 3 bytes
              when 3 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_A_THR05_08_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 3 bytes
              when 4 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_A_THR09_12_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 3 bytes
              when 5 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_A_THR13_16_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 2 bytes
              when 6 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_V01_04_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 7 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_V05_08_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 8 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_V09_12_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 9 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_V13_16_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 10 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_B_V_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 11 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC1_2_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 12 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC3_4_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 13 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC5_6_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 14 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC7_8_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 2 bytes
              when 15 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC_B_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE2;

--            // write 1 byte
              when 16 =>
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                -- data: slave address & write bit; cmd: STA & WR
                i2c_core_set(C_ADC1_2_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 1 byte
              when 17 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC3_4_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 1 byte
              when 18 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC5_6_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 1 byte
              when 19 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC7_8_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 1 byte
              when 20 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_ADC_B_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 3 bytes
              when 21 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_T_THR_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE1;

--            // write 1 byte
              when 22 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN_B_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // write 4 bytes
              when 23 =>
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_T_THR_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE0;



--            // AUX bus, write 1 byte
              when 32 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN1_4_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // AUX bus, write 1 byte
              when 33 =>
                -- data: slave address & write bit; cmd: STA & WR
                vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
                i2c_core_set(C_EN5_8_SLAVE_ADDR & '0', '1', vCmd, '1');
                vNextRegs.state      := WAIT_TIP_HI;
                vNextRegs.next_state := WR_BYTE3;

--            // all other addresses are error
              when others =>
                vNextRegs.state := WB_ERR;
            end case;
          end if;
        end if;

      when WB_ACK | WB_ERR =>
        -- finalize WB transfer when strobe is deasserted
        if WB_WBS_I.stb_i = '0' then
          vNextRegs.state := WB_IDLE;
        end if;

      when WAIT_TIP_HI =>
        if sStatus(I2C_STAT_AL) = '1' then
          -- Arbitration lost
          sAlError        <= '1';
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
          sCompletedByte                <= '1';
          -- transfer finished
          vNextRegs.state               := sRegs.next_state;
          -- latch received data into i2cData LSB
          vNextRegs.i2cData(7 downto 0) := sData_o;
        end if;

      when WR_BYTE0 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          vNextRegs.next_state := WR_BYTE1;
          -- data: reg addr LSB; cmd: WR
          vCmd                 := I2C_CMD_WRITE;
          i2c_core_set(sRegs.byte0, '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
        end if;

      when WR_BYTE1 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data: reg addr LSB; cmd: WR
          vCmd                 := I2C_CMD_WRITE;
          i2c_core_set(sRegs.byte1, '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := WR_BYTE2;
        end if;

      when WR_BYTE2 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data: reg addr LSB; cmd: WR
          vCmd                 := I2C_CMD_WRITE;
          i2c_core_set(WB_WBS_I.dat_i(15 downto 8), '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := WR_BYTE3;
        end if;

      when WR_BYTE3 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- write: data = WB.dat_i; cmd = WR & STO
          vCmd                 := I2C_CMD_WRITE or I2C_CMD_STOP;
          i2c_core_set(WB_WBS_I.dat_i(7 downto 0), '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := CHECK_WRITE;
          vNextRegs.i2cData    := (others => '1');
        end if;

      when CHECK_WRITE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          vNextRegs.state := WB_ERR;
        else
          vNextRegs.state := WB_ACK;
        end if;

      when RD_RTD0 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data = 0; cmd = RD
          vCmd                 := I2C_CMD_READ;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := RD_RTD1;
        end if;

      when RD_RTD1 =>
        -- data = 0; cmd = RD
        vCmd                 := I2C_CMD_READ;
        i2c_core_set(x"00", '0', vCmd, '1');
        vNextRegs.state      := WAIT_TIP_HI;
        vNextRegs.next_state := SHIFT_DATA;

      when RD_BYTE1 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WB_ERR;
        else
          -- data = 0; cmd = RD
          vCmd                 := I2C_CMD_READ;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := SHIFT_DATA;
        end if;

      when SHIFT_DATA =>
        vNextRegs.i2cData(15 downto 8) := vNextRegs.i2cData(7 downto 0);
        vNextRegs.state                := RD_BYTE2;

      when RD_BYTE2 =>
        -- data = 0; cmd = RD & STO & ACK
        vCmd                 := I2C_CMD_READ or I2C_CMD_STOP or I2C_CMD_ACK;
        i2c_core_set(x"00", '0', vCmd, '1');
        vNextRegs.state      := WAIT_TIP_HI;
        vNextRegs.next_state := STORE_BYTE;

      when STORE_BYTE =>
        -- data = 0; cmd = 0: clear ACK bit
        i2c_core_set(x"00", '0', "00000", '1');
        vNextRegs.state := WB_ACK;

      when others => null;
    end case;

    sNextRegs <= vNextRegs;
  end process p_nextstate;

  -- select the correct I2C bus (Main or AUX) depending on wishbone address
  p_i2cbus_select : process (iWbAddr, sDataAux_o, sDataMain_o, sStatus_aux,
                             sStatus_main, sWeCommand, sWeData) is
  begin
    case iWbAddr is
      when 0 to 31 =>
        -- address 0 to 0x1f goes to main I2C
        sWeData_main <= sWeData;
        sWeData_aux  <= '0';
        sWeCmd_main  <= sWeCommand;
        sWeCmd_aux   <= '0';
        sData_o      <= sDataMain_o;
        sStatus      <= sStatus_main;
      when 32 to 47 =>
        -- address 0x20 - 0x2f goes to aux I2C
        sWeData_aux  <= sWeData;
        sWeData_main <= '0';
        sWeCmd_aux   <= sWeCommand;
        sWeCmd_main  <= '0';
        sData_o      <= sDataAux_o;
        sStatus      <= sStatus_aux;
      when others =>
        sWeData_aux  <= '0';
        sWeData_main <= '0';
        sWeCmd_aux   <= '0';
        sWeCmd_main  <= '0';
        sData_o      <= (others => '0');
        sStatus      <= "0001";         -- Bad status "Arbitration Lost"
    end case;
  end process p_i2cbus_select;

  -- attach I2C master core for PU "main" bus
  INST_pu_i2c_master : entity work.i2c_master_top
    port map (
      CLK        => WB_CLK,
      RST        => WB_RST,
      CORE_EN    => sCoreEn,
      PRER_i     => sFreqSetting,
      DATA_i     => sData_i,
      WE_DATA    => sWeData_main,
      COMMAND    => sCommand,
      WE_COMMAND => sWeCmd_main,
      DATA_o     => sDataMain_o,
      STATUS     => sStatus_main,
      SCL_PAD_i  => SCL_PAD_i,
      SCL_PAD_o  => SCL_PAD_o,
      SCL_PAD_T  => SCL_PAD_T,
      SDA_PAD_i  => SDA_PAD_i,
      SDA_PAD_o  => SDA_PAD_o,
      SDA_PAD_T  => SDA_PAD_T
      );

  -- attach I2C master core for PU "AUX" bus
  INST_pu_aux_i2c_master : entity work.i2c_master_top
    port map (
      CLK        => WB_CLK,
      RST        => WB_RST,
      CORE_EN    => sCoreEn,
      PRER_i     => sFreqSetting,
      DATA_i     => sData_i,
      WE_DATA    => sWeData_aux,
      COMMAND    => sCommand,
      WE_COMMAND => sWeCmd_aux,
      DATA_o     => sDataAux_o,
      STATUS     => sStatus_aux,
      SCL_PAD_i  => AUX_SCL_PAD_i,
      SCL_PAD_o  => AUX_SCL_PAD_o,
      SCL_PAD_T  => AUX_SCL_PAD_T,
      SDA_PAD_i  => AUX_SDA_PAD_i,
      SDA_PAD_o  => AUX_SDA_PAD_o,
      SDA_PAD_T  => AUX_SDA_PAD_T
      );

end architecture structural;
