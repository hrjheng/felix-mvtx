#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus

typedef __uint128_t uint128_t;

namespace Gbt_Sca_Chs
{
  static constexpr uint8_t CTRL(0x00);  // SCA configuration registers
  static constexpr uint8_t SPI(0x01);  // Serial Peripheral master Interface
  static constexpr uint8_t GPIO(0x02);  // Parallel I/O interface
  static constexpr uint8_t I2C0(0x03);  // I2C Serial interface - master 0 (PA3) ***
  static constexpr uint8_t I2C1(0x04);  // I2C Serial interface - master 1 (VTTx ch1)
  static constexpr uint8_t I2C2(0x05);  // I2C Serial interface - master 2 (VTTx ch2)
  static constexpr uint8_t I2C3(0x06);  // I2C Serial interface - master 3
  static constexpr uint8_t I2C4(0x07);  // I2C Serial interface - master 4 (US)
  static constexpr uint8_t I2C5(0x08);  // I2C Serial interface - master 5 (PA3)
  static constexpr uint8_t I2C6(0x09);  // I2C Serial interface - master 6
  static constexpr uint8_t I2C7(0x0A);  // I2C Serial interface - master 7 (GBTX)
  static constexpr uint8_t I2C8(0x0B);  // I2C Serial interface - master 8
  static constexpr uint8_t I2C9(0x0C);  // I2C Serial interface - master 9
  static constexpr uint8_t I2CA(0x0D);  // I2C Serial interface - master 10
  static constexpr uint8_t I2CB(0x0E);  // I2C Serial interface - master 11
  static constexpr uint8_t I2CC(0x0F);  // I2C Serial interface - master 12
  static constexpr uint8_t I2CD(0x10);  // I2C Serial interface - master 13
  static constexpr uint8_t I2CE(0x11);  // I2C Serial interface - master 14
  static constexpr uint8_t I2CF(0x12);  // I2C Serial interface - master 15
  static constexpr uint8_t JTAG(0x13);  // JTAG serial master interface
  static constexpr uint8_t ADC(0x14);  // Analog to digital converter
  static constexpr uint8_t DAC(0x15);  // Digital to analog converter
} // namespace Gbt Channels

namespace Gbt_Sca_Cmds
{ // COmmands must be 8-bit
  // COMMANDS TO OPERATE ON THE GBT-SCA generic control registers
  // Gbt-Sca manual table 5.7
  static constexpr uint8_t CTRL_R_ID_V1(0x91); // ch = 14, rd the chip ID for SCA V1 (needs to go to channel 0x14)
  static constexpr uint8_t CTRL_R_ID_V2(0xD1); // ch = 14, rd the chip ID for SCA V2 (needs to go to channel 0x14)
  static constexpr uint8_t CTRL_W_CRB(0x02); // ch =  0, wr control register B
  static constexpr uint8_t CTRL_W_CRC(0x04); // ch =  0, wr control register C
  static constexpr uint8_t CTRL_W_CRD(0x06); // ch =  0, wr control register D
  static constexpr uint8_t CTRL_R_CRB(0x03); // ch =  0, rd control register B
  static constexpr uint8_t CTRL_R_CRC(0x05); // ch =  0, rd control register C
  static constexpr uint8_t CTRL_R_CRD(0x07); // ch =  0, rd control register D
  static constexpr uint8_t CTRL_R_SEU(0xF1); // ch = 13, rd SEU counter (needs to go to channel 0x13)
  static constexpr uint8_t CTRL_C_SEU(0xF0); // ch = 13, rs SEU counter (needs to go to channel 0x13)

  // the commands accepted by the I2C channel
  // Gbt-Sca manual table 6.15
  // for pa3 access, use channel I2C0 = 0x03
  static constexpr uint8_t I2C_W_CTRL(0x30); // Write CONTROL register
  static constexpr uint8_t I2C_R_CTRL(0x31); // Read CONTROL register
  static constexpr uint8_t I2C_R_STR(0x11); // Read STATUS register
  static constexpr uint8_t I2C_W_MSK(0x20); // Write MASK register
  static constexpr uint8_t I2C_R_MSK(0x21); // Read MASK register
  static constexpr uint8_t I2C_W_DATA0(0x40); // Write data register bytes 0,1,2,3
  static constexpr uint8_t I2C_R_DATA0(0x41); // Read data register bytes 0,1,2,3
  static constexpr uint8_t I2C_W_DATA1(0x50); // Write data register bytes 4,5,6,7
  static constexpr uint8_t I2C_R_DATA1(0x51); // Write data register bytes 4,5,6,7
  static constexpr uint8_t I2C_W_DATA2(0x60); // Write data register bytes 8,9,10,11
  static constexpr uint8_t I2C_R_DATA2(0x61); // Write data register bytes 8,9,10,11
  static constexpr uint8_t I2C_W_DATA3(0x70); // Write data register bytes 12,13,14,15
  static constexpr uint8_t I2C_R_DATA3(0x71); // Write data register bytes 12,13,14,15
  static constexpr uint8_t I2C_S_7B_W(0x82); // Start I2C single byte write (7-bit addr)
  static constexpr uint8_t I2C_S_7B_R(0x86); // Start I2C single byte read (7-bit addr)
  static constexpr uint8_t I2C_S_10B_W(0x8A); // Start I2C single byte write (10-bit addr)
  static constexpr uint8_t I2C_S_10B_R(0x8E); // Start I2C single byte read (10-bit addr)
  static constexpr uint8_t I2C_M_7B_W(0xDA); // Start I2C multi byte write (7-bit addr)
  static constexpr uint8_t I2C_M_7B_R(0xDE); // Start I2C multi byte read (7-bit addr)
  static constexpr uint8_t I2C_M_10B_W(0xE2); // Start I2C multi byte write (10-bit addr)
  static constexpr uint8_t I2C_M_10B_R(0xE6); // Start I2C multi byte read (10-bit addr)
//static constexpr uint8_t I2C_RMW_AND (=   ); // Address not specified in SCA manual
  static constexpr uint8_t I2C_RMW_OR(0xC6); // Start I2C read-modify-write transaction with OR mask
  static constexpr uint8_t I2C_RMW_XOR(0xCA); // Start I2C read-modify-write transaction with XOR mask

  // the commands accepted by the JTAG channel
  // for operations on its regis-ters and for the start of transmission
  // Gbt-Sca manual table 8.10
  static constexpr uint8_t JTAG_W_CTRL(0x80);
  static constexpr uint8_t JTAG_R_CTRL(0x81);
  static constexpr uint8_t JTAG_W_FREQ(0x90);
  static constexpr uint8_t JTAG_R_FREQ(0x91);
  static constexpr uint8_t JTAG_W_TDO0(0x00);
  static constexpr uint8_t JTAG_R_TDI0(0x01);
  static constexpr uint8_t JTAG_W_TDO1(0x10);
  static constexpr uint8_t JTAG_R_TDI1(0x11);
  static constexpr uint8_t JTAG_W_TDO2(0x20);
  static constexpr uint8_t JTAG_R_TDI2(0x21);
  static constexpr uint8_t JTAG_W_TDO3(0x30);
  static constexpr uint8_t JTAG_R_TDI3(0x31);
  static constexpr uint8_t JTAG_W_TMS0(0x40);
  static constexpr uint8_t JTAG_R_TMS0(0x41);
  static constexpr uint8_t JTAG_W_TMS1(0x50);
  static constexpr uint8_t JTAG_R_TMS1(0x51);
  static constexpr uint8_t JTAG_W_TMS2(0x60);
  static constexpr uint8_t JTAG_R_TMS2(0x61);
  static constexpr uint8_t JTAG_W_TMS3(0x70);
  static constexpr uint8_t JTAG_R_TMS3(0x71);
  static constexpr uint8_t JTAG_ARESET(0xC0);
  static constexpr uint8_t JTAG_GO(0xA2);
  static constexpr uint8_t JTAG_GO_M(0xB0);
} //namespace Gbt_Sca_Cmds

namespace GBTxAddress
{
  static constexpr uint32_t FineDelay0         = 0x4   ;
  static constexpr uint32_t CoarseDelay0       = 0x8   ;
  static constexpr uint32_t TxSwitchesControlA = 0x1D  ;
  static constexpr uint32_t TxSwitchesControlB = 0x1E  ;
  static constexpr uint32_t TxSwitchesControlC = 0x1F  ;
  static constexpr uint32_t I2cRxSelectI2      = 0x23  ;
  static constexpr uint32_t FecCounter         = 0x1B3 ;
  static constexpr uint32_t TxRxPllLocked      = 0x1AB ;
}

class Sca
{
public:
   Sca();
   ~Sca();

   //struct CommandData {
   //   uint32_t command;
   //   uint32_t data;
   //};
//
   //struct ReadResult {
   //   uint32_t command;
   //   uint32_t data;
   //};

   uint32_t barRead(uint32_t index);
   void barWrite(uint32_t index, uint32_t data);
   void get_CRU_githash();

   void sca_write(uint8_t channel, uint8_t command, uint32_t scadata);
   void wr(uint32_t cmd, uint32_t data);

   uint32_t sca_read();
   uint32_t rd();
   uint32_t pa3_version();

   void waitBusy();

private:
};

#endif

#ifdef __cplusplus
extern "C"
{
#endif

typedef __uint128_t uint128_t;

//bar
uint64_t barRead(uint32_t index);
void barWrite(uint32_t index, uint64_t data);
void get_CRU_githash();

void waitBusy();

//sca
void sca_write(uint8_t channel, uint8_t command, uint32_t scadata);
void wr(uint32_t cmd, uint32_t data);
uint32_t sca_read();
uint32_t rd();

void sca_init_communication();

void HDLC_reset();
void HDLC_connect();

//i2c
uint32_t read_i2c(uint8_t channel, uint8_t sl_addr);

//pa3
uint32_t pa3_read_reg(uint8_t address);
uint32_t pa3_version();

//jtag

void jtag_power();

void jtag_reset_pulse();

void jtag_w_CTRL(uint16_t jtag_config);
void jtag_sp(uint128_t tms_data, uint128_t tdi_data, uint32_t length);
void jtag_64b_sp(uint64_t tms_data, uint64_t tdi_data, uint32_t length);
void jtag_96b_sp(uint128_t tms_data, uint128_t tdi_data, uint32_t length);
uint16_t jtag_r_CTRL();

void jtag_w_TMS(uint32_t TMS3_data,
                uint32_t TMS2_data,
                uint32_t TMS1_data,
                uint32_t TMS0_data);

void jtag_w_TMS_1bit(uint32_t TMS0_data);

uint32_t jtag_r_TMS(uint32_t pos);

void jtag_w_TDO(uint32_t TDO_3,
                uint32_t TDO_2,
                uint32_t TDO_1,
                uint32_t TDO_0);

void jtag_w_TDO_1bit(uint32_t TDO_0);

uint32_t jtag_r_TDI(uint32_t pos);

void jtag_start_transmission();

void jtag_reset();

void jtag_set_frequency(uint32_t frequency);

void jtag_32_bit_mode(int length, uint32_t jtag_tdi_data, uint32_t jtag_tms_data);

void jtag_w_TDO_32bit(uint32_t TDO_0);

uint32_t jtag_r_TDI_32bit();

void jtag_w_TMS_32bit(uint32_t TMS0_data);

uint32_t jtag_r_TMS_32bit();

void jtag_w_TMS_var_mode(int length, uint32_t data);

void jtag_read_busy_flag();

void test();

void Sca_pause();

uint32_t get_gbt_channel();

void set_gbt_channel(int gbt_channel);

void set_phase_detector_charge_pump(uint32_t value);

int read_gbtx_register(uint32_t reg);
void write_gbtx_register(uint32_t reg, uint32_t value);

#ifdef __cplusplus
}
#endif
