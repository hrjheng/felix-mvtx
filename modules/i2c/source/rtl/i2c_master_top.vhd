-------------------------------------------------------------------------------
-- Title      : I2C Interface - Top module
-- Project    : ALICE ITS WP10
-------------------------------------------------------------------------------
-- File       : i2c_master_top.vhd
-- Author     : J. Schambach
-- Company    : University of Texas at Austin
-- Created    : 2015-11-13
-- Last update: 2018-06-15
-- Platform   : Xilinx Vivado 2015.3
-- Target     : Kintex-7
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Code downloaded from opencores. Original header at the end
--              of the code, description below from original code.
--              modified for formatting
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
-- Wishbone interface package
use work.intercon_pkg.all;

entity i2c_master_top is
  port (
    CLK        : in  std_logic;         -- master clock input
    RST        : in  std_logic := '0';  -- synchronous active high reset
    -- core control signals
    CORE_EN    : in  std_logic;
    PRER_i     : in  std_logic_vector(15 downto 0);
    DATA_i     : in  std_logic_vector(7 downto 0);
    WE_DATA    : in  std_logic;
    COMMAND    : in  std_logic_vector(4 downto 0);
    WE_COMMAND : in  std_logic;
    DATA_o     : out std_logic_vector(7 downto 0);
    STATUS     : out std_logic_vector(3 downto 0);
    --
    -- i2c lines
    SCL_PAD_i  : in  std_logic;         -- i2c clock line input
    SCL_PAD_o  : out std_logic;         -- i2c clock line output
    SCL_PAD_T  : out std_logic;  -- i2c clock line output enable, active low
    SDA_PAD_i  : in  std_logic;         -- i2c data line input
    SDA_PAD_o  : out std_logic;         -- i2c data line output
    SDA_PAD_T  : out std_logic   -- i2c data line output enable, active low
    );
end entity i2c_master_top;

architecture structural of i2c_master_top is

  -- registers
  signal prer : unsigned(15 downto 0);         -- clock prescale register
  signal txr  : std_logic_vector(7 downto 0);  -- transmit register
  signal rxr  : std_logic_vector(7 downto 0);  -- receive register
  signal cr   : std_logic_vector(4 downto 0);  -- command register
  signal sr   : std_logic_vector(3 downto 0);  -- status register


  -- done signal: command completed, clear command register
  signal done : std_logic;

  -- command register signals
  signal sta, sto, rd, wr, ack : std_logic;

  -- status register signals
  signal irxack, rxack : std_logic;     -- received aknowledge from slave
  signal tip           : std_logic;     -- transfer in progress
  signal i2c_busy      : std_logic;     -- i2c bus busy (start signal detected)
  signal i2c_al, al    : std_logic;     -- arbitration lost

begin
  -- generate acknowledge output signal

  prer <= unsigned(PRER_i);

  -- generate data register
  gen_data : process (CLK) is
  begin  -- process gen_data
    if rising_edge(CLK) then            -- rising clock edge
      if RST = '1' then                 -- synchronous reset (active high)
        txr <= (others => '0');
      elsif WE_DATA = '1' then
        txr <= DATA_i;
      end if;
    end if;
  end process gen_data;


  gen_cr : process (CLK) is
  begin  -- process gen_cr
    if rising_edge(CLK) then            -- rising clock edge
      if RST = '1' then                 -- synchronous reset (active high)
        cr <= (others => '0');
      elsif WE_COMMAND = '1' then
        cr <= COMMAND;
      elsif (done = '1') or (i2c_al = '1') then
        cr <= (others => '0');
      end if;
    end if;
  end process gen_cr;


  -- decode command register
  sta <= cr(4);
  sto <= cr(3);
  rd  <= cr(2);
  wr  <= cr(1);
  ack <= cr(0);

  -- hookup byte controller block
  byte_ctrl : entity work.i2c_master_byte_ctrl
    port map (
      clk      => CLK,
      rst      => RST,
      aReset   => '0',
      ena      => CORE_EN,
      clk_cnt  => prer,
      start    => sta,
      stop     => sto,
      do_read  => rd,
      do_write => wr,
      ack_in   => ack,
      i2c_busy => i2c_busy,
      i2c_al   => i2c_al,
      din      => txr,
      cmd_ack  => done,
      ack_out  => irxack,
      dout     => rxr,
      scl_i    => SCL_PAD_i,
      scl_o    => SCL_PAD_o,
      scl_oen  => SCL_PAD_T,
      sda_i    => SDA_PAD_i,
      sda_o    => SDA_PAD_o,
      sda_oen  => SDA_PAD_T
      );

  DATA_o <= rxr;

  -- status register block
  st_block : block
  begin
    -- generate status register bits
    gen_sr_bits : process (CLK)
    begin
      if rising_edge(CLK) then
        if (RST = '1') then
          al    <= '0';
          rxack <= '0';
          tip   <= '0';
        else
          rxack <= irxack;
          tip   <= (rd or wr);
          al    <= i2c_al or (al and not sta);
        -- interrupt request flag is always generated
        end if;
      end if;
    end process gen_sr_bits;

    -- assign status register bits
    sr(3) <= rxack;
    sr(2) <= i2c_busy;
    sr(1) <= tip;
    sr(0) <= al;
  end block;
  STATUS <= sr;

end architecture structural;
---------------------------------------------------------------------
----                                                             ----
----  WISHBONE revB2 compl. I2C Master Core; top level           ----
----                                                             ----
----                                                             ----
----  Author: Richard Herveille                                  ----
----          richard@asics.ws                                   ----
----          www.asics.ws                                       ----
----                                                             ----
----  Downloaded from: http://www.opencores.org/projects/i2c/    ----
----                                                             ----
---------------------------------------------------------------------
----                                                             ----
---- Copyright (C) 2000 Richard Herveille                        ----
----                    richard@asics.ws                         ----
----                                                             ----
---- This source file may be used and distributed without        ----
---- restriction provided that this copyright statement is not   ----
---- removed from the file and that any derivative work contains ----
---- the original copyright notice and the associated disclaimer.----
----                                                             ----
----     THIS SOFTWARE IS PROVIDED ``AS IS'' AND WITHOUT ANY     ----
---- EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED   ----
---- TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS   ----
---- FOR A PARTICULAR PURPOSE. IN NO EVENT SHALL THE AUTHOR      ----
---- OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,         ----
---- INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES    ----
---- (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE   ----
---- GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR        ----
---- BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF  ----
---- LIABILITY, WHETHER IN  CONTRACT, STRICT LIABILITY, OR TORT  ----
---- (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT  ----
---- OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         ----
---- POSSIBILITY OF SUCH DAMAGE.                                 ----
----                                                             ----
---------------------------------------------------------------------

--  CVS Log
--
--  $Id: i2c_master_top.vhd,v 1.8 2009-01-20 10:38:45 rherveille Exp $
--
--  $Date: 2009-01-20 10:38:45 $
--  $Revision: 1.8 $
--  $Author: rherveille $
--  $Locker:  $
--  $State: Exp $
--
-- Change History:
--               Revision 1.7  2004/03/14 10:17:03  rherveille
--               Fixed simulation issue when writing to CR register
--
--               Revision 1.6  2003/08/09 07:01:13  rherveille
--               Fixed a bug in the Arbitration Lost generation caused by delay on the (external) sda line.
--               Fixed a potential bug in the byte controller's host-acknowledge generation.
--
--               Revision 1.5  2003/02/01 02:03:06  rherveille
--               Fixed a few 'arbitration lost' bugs. VHDL version only.
--
--               Revision 1.4  2002/12/26 16:05:47  rherveille
--               Core is now a Multimaster I2C controller.
--
--               Revision 1.3  2002/11/30 22:24:37  rherveille
--               Cleaned up code
--
--               Revision 1.2  2001/11/10 10:52:44  rherveille
--               Changed PRER reset value from 0x0000 to 0xffff, conform specs.
--
