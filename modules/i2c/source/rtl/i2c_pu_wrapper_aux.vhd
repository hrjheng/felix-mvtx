-------------------------------------------------------------------------------
-- Title      : I2C Interface - Wrapper for I2C master core
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_pu_wrapper_aux.vhd
-- Author     : J. Schambach
-- Company    : University of Texas at Austin
-- Created    : 2019-04-16
-- Last update: 2019-08-14
-- Platform   : Xilinx Vivado 2018.3
-- Target     : Kintex Ultrascale
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Wrap I2C core to provide full I2C transactions
--              for controlling the power unit AUX I2C bus
--
--              I2C bus frequency is set to 100kHz, based on a wishbone
--              speed of 160MHz
--
--              I2C slave addresses are mapped to addresses
--
--              I2C write transactions bytes are sent as:
--              SL - BYTE_0 - BYTE_1 - BYTE_2 - BYTE_3   or
--              SL - BYTE_1 - BYTE_2 - BYTE_3            or
--              SL - BYTE_2 - BYTE_3                     or
--              SL - BYTE_3
--
--              I2C read transactions bytes are as follows:
--              SL - read[7:0]                  or
--              SL - read[15:8] - read[7:0]     or
--              SL - IGNORED_BYTE - read[15:8] - read[7:0]
--
--              BYTE_x and ADDRESS are latched at IDLE when START goes high
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;
use work.i2c_pkg.all;

entity i2c_pu_wrapper_aux is
  port (
    -- Wishbone interface signals
    CLK            : in  std_logic;     -- master clock input
    RST            : in  std_logic;     -- synchronous active high reset
    BYTE_0         : in  std_logic_vector(7 downto 0);
    BYTE_1         : in  std_logic_vector(7 downto 0);
    BYTE_2         : in  std_logic_vector(7 downto 0);
    BYTE_3         : in  std_logic_vector(7 downto 0);
    ADDRESS        : in  std_logic_vector(4 downto 0);
    START          : in  std_logic;
    BUSY           : out std_logic;
    I2C_DATA_o     : out std_logic_vector(15 downto 0);
    DATA_VALID     : out std_logic;
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
end entity i2c_pu_wrapper_aux;

architecture structural of i2c_pu_wrapper_aux is
  -- Aux I2C bus slave addresses
  constant C_EN1_4_SLAVE_ADDR : std_logic_vector(6 downto 0) := "0111000";
  constant C_EN5_8_SLAVE_ADDR : std_logic_vector(6 downto 0) := "0111001";

  component i2c_frequency_selector is
    generic (FREQ_SELECTION_BIT_WIDTH :     integer);
    port (frequency_setting_o         : out std_logic_vector(FREQ_SELECTION_BIT_WIDTH-1 downto 0));
  end component;

  signal sFreqSetting : std_logic_vector(C_FREQ_SELECTION_BIT_WIDTH-1 downto 0);

  type wb_state_t is (WB_IDLE,
                      WAIT_TIP_HI,
                      WAIT_TIP_LO,
                      WR_BYTE3,
                      CHECK_WRITE,
                      RD_BYTE2,
                      STORE_BYTE,
                      WAIT_NOT_BUSY
                      );

  type registers_t is record
    state      : wb_state_t;
    next_state : wb_state_t;
    i2cData    : std_logic_vector(15 downto 0);
  end record registers_t;

  signal sRegs, sNextRegs : registers_t;

  constant cDefaultRegs : registers_t := (state      => WB_IDLE,
                                          next_state => WB_IDLE,
                                          i2cData    => (others => '0')
                                          );


  signal iWbAddr : natural range 0 to 31;

  signal sCoreEn    : std_logic := '0';
  signal sData_i    : std_logic_vector(7 downto 0);
  signal sWeData    : std_logic;
  signal sCommand   : std_logic_vector(4 downto 0);
  signal sWeCommand : std_logic;
  signal sData_o    : std_logic_vector(7 downto 0);
  signal sStatus    : std_logic_vector(3 downto 0);


  signal sByte0         : std_logic_vector(7 downto 0);
  signal sByte1         : std_logic_vector(7 downto 0);
  signal sByte2         : std_logic_vector(7 downto 0);
  signal sByte3         : std_logic_vector(7 downto 0);
  signal sCompletedByte : std_logic;
  signal sAlError       : std_logic;
  signal sNoackError    : std_logic;
  signal sDataValid     : std_logic;

begin

  i2c_frequency_selector_INST : i2c_frequency_selector
    generic map (
      FREQ_SELECTION_BIT_WIDTH => C_FREQ_SELECTION_BIT_WIDTH)
    port map (
      frequency_setting_o => sFreqSetting);


  p_register_outputs : process (CLK) is
  begin
    if rising_edge(CLK) then
      if RST = '1' then
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

  iWbAddr <= to_integer(unsigned(ADDRESS));

  I2C_DATA_o <= sRegs.i2cData;
  DATA_VALID <= sDataValid;

  p_WishboneSlave : process (CLK) is
  begin
    if rising_edge(CLK) then
      if RST = '1' then
        sRegs   <= cDefaultRegs;
        sCoreEn <= '0';
        sByte0  <= (others => '0');
        sByte1  <= (others => '0');
        sByte2  <= (others => '0');
        sByte3  <= (others => '0');
        BUSY    <= '0';
      else
        sCoreEn <= '1';
        sRegs   <= sNextRegs;
        if (sRegs.state = WB_IDLE) and (START = '1') then
          sByte0 <= BYTE_0;
          sByte1 <= BYTE_1;
          sByte2 <= BYTE_2;
          sByte3 <= BYTE_3;
          BUSY   <= '1';
        elsif sRegs.state = WB_IDLE then
          sByte0 <= sByte0;
          sByte1 <= sByte1;
          sByte2 <= sByte2;
          sByte3 <= sByte3;
          BUSY   <= '0';
        else
          sByte0 <= sByte0;
          sByte1 <= sByte1;
          sByte2 <= sByte2;
          sByte3 <= sByte3;
          BUSY   <= '1';
        end if;
      end if;
    end if;
  end process p_WishboneSlave;


  p_nextstate : process (all) is
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
    sDataValid     <= '0';


    case sRegs.state is
      when WB_IDLE =>
        if START = '1' then

          vNextRegs.i2cData := (others => '0');
          case iWbAddr is

            -- *********** write transaction ***********************
--            // AUX bus, write 1 byte
            when 1 =>
              -- data: slave address & write bit; cmd: STA & WR
              vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
              i2c_core_set(C_EN1_4_SLAVE_ADDR & '0', '1', vCmd, '1');
              vNextRegs.state      := WAIT_TIP_HI;
              vNextRegs.next_state := WR_BYTE3;

--            // AUX bus, write 1 byte
            when 2 =>
              -- data: slave address & write bit; cmd: STA & WR
              vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
              i2c_core_set(C_EN5_8_SLAVE_ADDR & '0', '1', vCmd, '1');
              vNextRegs.state      := WAIT_TIP_HI;
              vNextRegs.next_state := WR_BYTE3;

            -- ****************** read transaction ***********************
--            // AUX bus: read 1 byte
            when 3 =>
              -- data: slave address & read bit; cmd: STA & WR
              vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
              i2c_core_set(C_EN1_4_SLAVE_ADDR & '1', '1', vCmd, '1');
              vNextRegs.state      := WAIT_TIP_HI;
              vNextRegs.next_state := RD_BYTE2;

--            // AUX bus: read 1 byte
            when 4 =>
              -- data: slave address & read bit; cmd: STA & WR
              vCmd                 := I2C_CMD_START or I2C_CMD_WRITE;
              i2c_core_set(C_EN5_8_SLAVE_ADDR & '1', '1', vCmd, '1');
              vNextRegs.state      := WAIT_TIP_HI;
              vNextRegs.next_state := RD_BYTE2;


--            // all other addresses are error
            when others =>
              vNextRegs.state := WB_IDLE;
          end case;
        end if;

      when WAIT_TIP_HI =>
        if sStatus(I2C_STAT_AL) = '1' then
          -- Arbitration lost
          sAlError        <= '1';
          vNextRegs.state := WB_IDLE;
        elsif sStatus(I2C_STAT_TIP) = '1' then
          -- transfer started
          vNextRegs.state := WAIT_TIP_LO;
        end if;

      when WAIT_TIP_LO =>
        if sStatus(I2C_STAT_AL) = '1' then
          -- Arbitration lost
          sAlError        <= '1';
          vNextRegs.state := WB_IDLE;
        elsif sStatus(I2C_STAT_TIP) = '0' then
          sCompletedByte                <= '1';
          -- transfer finished
          vNextRegs.state               := sRegs.next_state;
          -- latch received data into i2cData LSB
          vNextRegs.i2cData(7 downto 0) := sData_o;
        end if;

      when WR_BYTE3 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WAIT_NOT_BUSY;
        else
          -- write: data = WB.dat_i; cmd = WR & STO
          vCmd                 := I2C_CMD_WRITE or I2C_CMD_STOP;
          i2c_core_set(sByte3, '1', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := CHECK_WRITE;
          vNextRegs.i2cData    := (others => '1');
        end if;

      when CHECK_WRITE =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError <= '1';
          vNextRegs.state := WAIT_NOT_BUSY;
        else
          vNextRegs.state := WB_IDLE;
        end if;

      when RD_BYTE2 =>
        if sStatus(I2C_STAT_RXACK) = '1' then  -- no ACK from slave
          sNoackError     <= '1';
          -- cmd: STO
          vCmd            := I2C_CMD_STOP;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state := WAIT_NOT_BUSY;
        else
          -- data = 0; cmd = RD & STO & ACK
          vCmd                 := I2C_CMD_READ or I2C_CMD_STOP or I2C_CMD_ACK;
          i2c_core_set(x"00", '0', vCmd, '1');
          vNextRegs.state      := WAIT_TIP_HI;
          vNextRegs.next_state := STORE_BYTE;
        end if;

      when STORE_BYTE =>
        -- data = 0; cmd = 0: clear ACK bit
        i2c_core_set(x"00", '0', "00000", '1');
        sDataValid      <= '1';
        vNextRegs.state := WB_IDLE;

       when WAIT_NOT_BUSY =>
        if sStatus(I2C_STAT_I2C_BUSY) = '0' then
          vNextRegs.state := WB_IDLE;
        end if;

      when others =>
        vNextRegs.state := WB_IDLE;
    end case;

    sNextRegs <= vNextRegs;
  end process p_nextstate;


  -- attach I2C master core for PU "aux" bus
  INST_pu_i2c_master_aux : entity work.i2c_master_top
    port map (
      CLK        => CLK,
      RST        => RST,
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
