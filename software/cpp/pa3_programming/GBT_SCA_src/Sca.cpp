#include "Sca.h"

#include <stdio.h>
#include <thread>

#include <ctime>

#include "FELIXwrapper/Cru.h"
#include "FELIXwrapper/ChannelFactory.h"

namespace sc_regs = o2::roc::Cru::ScRegisters;

extern int log_mode;
extern int log_log;
extern int log_log_log;
extern int G_length;
extern uint128_t G_tms_data;
extern char id[7];
extern int G_MSB_LSB;

auto getBarChannel()
{
    auto cardId = o2::roc::Parameters::cardIdFromString(id);
    auto params = o2::roc::Parameters::makeParameters(cardId, 2);
    auto bar2 = o2::roc::ChannelFactory().getBar(params);
    return bar2;
}

uint64_t barRead(uint32_t address)
{
    static auto bar2 = getBarChannel();
    return bar2->readRegister(address);
}

void barWrite(uint32_t address, uint64_t data)
{
    static auto bar2 = getBarChannel();
    bar2->writeRegister(address, data);
}

void get_CRU_githash()
{
    std::cout << barRead(0x0060) << "\n";
}

void set_gbt_channel(int gbt_channel)
{
  barWrite(sc_regs::SC_LINK.address, gbt_channel);
}

uint32_t get_gbt_channel()
{
  uint64_t swt_mon = barRead(sc_regs::SWT_MON.address);
  return (swt_mon >> 44) & 0x1F;
}

void waitBusy()
{
  uint32_t busy_cnt = 0;
  volatile uint32_t busy = 0x1;
  while (busy == 0x1)
  {
    busy = barRead(sc_regs::SCA_RD_CTRL.address)>>31;
    busy_cnt = busy_cnt + 1;
    if (busy_cnt == 1e9)
    {
      std::cout << "\nSCA is stuck";
    }
  }
}

void executeCommand()
{
    barWrite(sc_regs::SCA_WR_CTRL.address, 0x4); // address = address / 4
    barWrite(sc_regs::SCA_WR_CTRL.address, 0x0);
    waitBusy();
}

// sca write and read based on sca_o2.py

void wr(uint32_t cmd, uint32_t data)
{// Write 64 bit packet (data + cmd) to the SCA interface and execute the command
  uint64_t data_cmd = data;
  data_cmd = (data_cmd << 32) | cmd;
  barWrite(sc_regs::SCA_WR_CMD_DATA.address, data_cmd);
  executeCommand();
}

void sca_write(uint8_t channel, uint8_t command, uint32_t scadata)
{
  uint8_t trid = 0x12;
  uint32_t cmd = ((channel&0xff)<<24) + (trid<<16) + (command&0xff);
  wr(cmd, scadata);
  std::this_thread::sleep_for(std::chrono::milliseconds(3)); // maybe for the hardware delay, failed with 800 microseconds
}

uint32_t rd()
{
  uint64_t data_cmd = 0x0;
  uint32_t cmd = 0x0;
  uint32_t err_code = 0x40;
  while(err_code != 0)
  {
    data_cmd = barRead(sc_regs::SCA_RD_CMD_DATA.address);
    cmd  = data_cmd & 0xFFFFFFFF;
    err_code = cmd & 0xff;
    if (err_code == 0x40)
    {
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
      std::cout << "sca busy\n";
    } else if (err_code != 0)
    {
      std::cout << "\nsca read error";
    } else
    {
    }
  }
  return (data_cmd >> 32) & 0xFFFFFFFF;
}

uint32_t sca_read()
{
  return rd();
}

void HDLC_reset()
{
  barWrite(sc_regs::SCA_WR_CTRL.address, 0x1);
  waitBusy();
  rd();
  barWrite(sc_regs::SCA_WR_CTRL.address, 0x0);
}

void HDLC_connect()
{
  barWrite(sc_regs::SCA_WR_CTRL.address, 0x2);
  waitBusy();
  rd();
  barWrite(sc_regs::SCA_WR_CTRL.address, 0x0);
}

void sca_init_communication()
{
  HDLC_reset();
  HDLC_connect();
}

// i2c

uint32_t read_i2c(uint8_t channel, uint8_t sl_addr)
{
  uint32_t result;
  uint32_t data = (sl_addr & 0x7f)<<24;
  sca_write(channel, Gbt_Sca_Cmds::I2C_S_7B_R, data);
  std::this_thread::sleep_for(std::chrono::milliseconds(1)); // maybe for the hardware delay, failed with 800 microseconds
  result = sca_read();
  return result;
}

void write_i2c(uint32_t channel, int sl_addr, int nbytes, uint32_t data0)
{
  uint32_t data1 = 0;
  uint32_t data2 = 0;
  uint32_t data3 = 0;

  if(nbytes == 1) {
    uint32_t data = ((sl_addr & 0x7f)<<24) | ((data0 & 0xff000000)>>8);
    sca_write(channel, Gbt_Sca_Cmds::I2C_S_7B_W, data);
  } else if (nbytes>12) {
    sca_write(channel, Gbt_Sca_Cmds::I2C_W_DATA3, data3);
  } else if (nbytes>8) {
    sca_write(channel, Gbt_Sca_Cmds::I2C_W_DATA2, data2);
  } else if (nbytes>4) {
    sca_write(channel, Gbt_Sca_Cmds::I2C_W_DATA1, data1);
  } else if (nbytes>0) {
    sca_write(channel, Gbt_Sca_Cmds::I2C_W_DATA0, data0);
  } else {
  }
}

// pa3
uint32_t pa3_read_reg(uint8_t address)
{
  return (read_i2c(Gbt_Sca_Chs::I2C0, address) >> 16) & 0xFF;
}

uint32_t pa3_version()
{
  uint32_t version_msb = pa3_read_reg(1);
  uint32_t version_lsb = pa3_read_reg(0);
  uint32_t version = ((version_msb & 0xFF) << 8) | (version_lsb & 0xFF);
  return version;
}

// jtag

void jtag_power()
{
  sca_write(Gbt_Sca_Chs::CTRL, Gbt_Sca_Cmds::CTRL_W_CRD, (0b00011000 << 24));
  //sca_write(Gbt_Sca_Chs::CTRL, Gbt_Sca_Cmds::CTRL_W_CRD, 0b00011000);
}

void jtag_w_CTRL(uint16_t jtag_config)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_CTRL, jtag_config);
}

uint16_t jtag_r_CTRL()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_CTRL, 0);
  return sca_read();
}

void jtag_reset()
{
  jtag_w_CTRL(0x1000); // from manual, 0b0001000000000000 is reset.
}

void jtag_w_TMS_sp(uint128_t tms_data)
{
  uint32_t data_packet[4];
  for(int i = 0; i < 4; i++){
    data_packet[i] = (uint32_t)(tms_data >> (i*32));
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS1, data_packet[1]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS2, data_packet[2]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS3, data_packet[3]);
}

void jtag_w_TMS_96b_sp(uint128_t tms_data)
{
  uint32_t data_packet[3];
  for(int i = 0; i < 3; i++){
    data_packet[i] = tms_data >> (i*32);
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS1, data_packet[1]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS2, data_packet[2]);
}

void jtag_w_TMS_64b_sp(uint64_t tms_data)
{
  uint32_t data_packet[2];
  for(int i = 0; i < 2; i++){
    data_packet[i] = tms_data >> (i*32);
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS1, data_packet[1]);
}

void jtag_w_TDI_sp(uint128_t tdi_data)
{
  uint32_t data_packet[4];
  for(int i = 0; i < 4; i++){
    data_packet[i] = tdi_data >> (i*32);
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO1, data_packet[1]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO2, data_packet[2]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO3, data_packet[3]);
}

void jtag_w_TDI_96b_sp(uint128_t tdi_data)
{
  uint32_t data_packet[3];
  for(int i = 0; i < 3; i++){
    data_packet[i] = tdi_data >> (i*32);
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO1, data_packet[1]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO2, data_packet[2]);
}

void jtag_w_TDI_64b_sp(uint64_t tdi_data)
{
  uint32_t data_packet[2];
  for(int i = 0; i < 2; i++){
    data_packet[i] = tdi_data >> (i*32);
  }
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, data_packet[0]);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO1, data_packet[1]);
}

void jtag_sp(uint128_t tms_data, uint128_t tdi_data, uint32_t length)
{
  if(length != (uint32_t)G_length)
  {
    G_length = length;
    uint32_t command = G_length + (G_MSB_LSB << 11);
    jtag_w_CTRL(command);
  }
  if(tms_data != G_tms_data)
  {
    G_tms_data = tms_data;
    jtag_w_TMS_sp(G_tms_data);
  }
  jtag_w_TDI_sp(tdi_data);
  jtag_start_transmission();
}

void jtag_64b_sp(uint64_t tms_data, uint64_t tdi_data, uint32_t length)
{
  if(length != (uint32_t)G_length)
  {
    G_length = length;
    uint32_t command = G_length + (G_MSB_LSB << 11);
    jtag_w_CTRL(command);
  }
  if(tms_data != G_tms_data)
  {
    G_tms_data = tms_data;
    jtag_w_TMS_64b_sp(G_tms_data);
  }
  jtag_w_TDI_64b_sp(tdi_data);
  jtag_start_transmission();
}

void jtag_96b_sp(uint128_t tms_data, uint128_t tdi_data, uint32_t length)
{
  if(length != (uint32_t)G_length)
  {
    G_length = length;
    uint32_t command = G_length + (G_MSB_LSB << 11);
    jtag_w_CTRL(command);
  }
  if(tms_data != G_tms_data)
  {
    G_tms_data = tms_data;
    jtag_w_TMS_96b_sp(G_tms_data);
  }
  jtag_w_TDI_96b_sp(tdi_data);
  jtag_start_transmission();
}

void jtag_w_TMS(uint32_t TMS3_data,
                uint32_t TMS2_data,
                uint32_t TMS1_data,
                uint32_t TMS0_data)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, TMS0_data);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS1, TMS1_data);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS2, TMS2_data);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS3, TMS3_data);
}

void jtag_w_TMS_32bit(uint32_t TMS0_data)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, TMS0_data);
}

uint32_t jtag_r_TMS_32bit()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TMS0, 0);
  return sca_read();
}

void jtag_w_TMS_1bit(uint32_t TMS0_data)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, TMS0_data);
}

uint32_t jtag_r_TMS(uint32_t pos)
{
  switch (pos) {
    case 0 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TMS0, 0);
    case 1 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TMS1, 0);
    case 2 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TMS2, 0);
    case 3 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TMS3, 0);
  }
  return sca_read();
}

void jtag_w_TDO(uint32_t TDO_3,
                uint32_t TDO_2,
                uint32_t TDO_1,
                uint32_t TDO_0)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO3, TDO_3);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO2, TDO_2);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO1, TDO_1);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, TDO_0);
}

void jtag_w_TDO_32bit(uint32_t TDO_0)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, TDO_0);
}

void jtag_w_TDO_1bit(uint32_t TDO_0)
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TDO0, TDO_0);
}

uint32_t jtag_r_TDI(uint32_t pos)
{
  uint32_t fake_data = 0;
  switch (pos) {
    case 3 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TDI3, fake_data);
    case 2 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TDI2, fake_data);
    case 1 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TDI1, fake_data);
    case 0 : sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TDI0, fake_data);
  }
  return sca_read();
}

uint32_t jtag_r_TDI_32bit()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_TDI0, 0);
  return sca_read();
}

void jtag_start_transmission()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_GO, 0x0); // data is not defined in gbt-sca manual
}

void jtag_reset_pulse()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_ARESET, 0x0); // data is not defined in gbt-sca manual
}

void jtag_set_frequency(uint32_t frequency)
{
  uint32_t DIV;
  if (frequency == 20000000)
  {
    DIV = 0;
  }else {
    DIV = 20000000/frequency - 1;
  }
  printf("JTAG Freq. setting: DIV = %x, freq. = %d Hz\n", DIV, frequency);
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_FREQ, DIV);
}

void jtag_32_bit_mode(int length, uint32_t jtag_tdi_data, uint32_t jtag_tms_data)
{
  if(log_mode)
  {
    FILE * tms_log;
    FILE * tdi_log;
    tms_log = fopen("tms.log", "a");
    tdi_log = fopen("tdi.log", "a");
    fprintf(tms_log, "tms: 0x%08x tdi: 0x%08x \nlength = %d\n", jtag_tms_data, jtag_tdi_data, length);
    fprintf(tdi_log, "tms: 0x%08x tdi: 0x%08x \nlength = %d\n", jtag_tms_data, jtag_tdi_data, length);
    fclose(tms_log);
    fclose(tdi_log);
  }

  if(log_log_log)
  {
      FILE * log_log_log;
      log_log_log = fopen("log_log.log", "a");
      fprintf(log_log_log, "tms: 0x%08x tdi: 0x%08x \nlength = %d\n", jtag_tms_data, jtag_tdi_data, length);
      fclose(log_log_log);
  }

  if(length != G_length)
  {
    G_length = length;
    uint32_t command = G_length + (G_MSB_LSB << 11);
    jtag_w_CTRL(command);
  }

  jtag_w_TDO_32bit(jtag_tdi_data);

  jtag_w_TMS_32bit(jtag_tms_data);

  jtag_start_transmission();
}

void jtag_w_TMS_var_mode(int length, uint32_t data)
{
  if(log_mode)
  {
    FILE * tms_log;
    FILE * tdi_log;
    tms_log = fopen("tms.log", "a");
    tdi_log = fopen("tdi.log", "a");
    fprintf(tms_log, "tms: 0x%08x length = %d\n", data, length);
    fprintf(tdi_log, "tms: 0x%08x length = %d\n", data, length);
    fclose(tms_log);
    fclose(tdi_log);
    if (length > 32)
    {
      fprintf(tms_log, "WARNING, length to jtag tms is %d\n", length);
    }
  }

  if(log_log)
  {
      FILE * log_log;
      log_log = fopen("log.log", "a");
      fprintf(log_log, "tms: 0x%08x length = %d\n", data, length);
      fclose(log_log);
  }

  if(log_log_log)
  {
      FILE * log_log_log;
      log_log_log = fopen("log_log.log", "a");
      fprintf(log_log_log, "tms: 0x%08x length = %d\n", data, length);
      fclose(log_log_log);
  }

  if(length != G_length)
  {
    G_length = length;
    uint32_t command = G_length + (G_MSB_LSB << 11);
    jtag_w_CTRL(command);
  }

  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_W_TMS0, data);
  jtag_start_transmission();
  //jtag_read_busy_flag();
}

void jtag_read_busy_flag()
{
  sca_write(Gbt_Sca_Chs::JTAG, Gbt_Sca_Cmds::JTAG_R_CTRL, 0xff);
  int32_t result = sca_read();
  printf("JTAG_R_CTRL = %04x\n", result);
}

void Sca_pause()
{
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
}

void set_phase_detector_charge_pump(uint32_t value)
{
  uint32_t current_val = read_gbtx_register(GBTxAddress::I2cRxSelectI2);
  uint32_t new_val = (current_val & 0x0f) | (value<<4);
  write_gbtx_register(GBTxAddress::I2cRxSelectI2, new_val);
  printf("set_phase_detector_charge_pump done\n");
}

int read_gbtx_register(uint32_t reg)
{
  uint32_t data0 = ((reg&0xff)<<24) | ((reg&0xff00)<<8);
  uint32_t gbtx_address = 0;
  uint32_t sl_addr = gbtx_address*2+1;
  uint32_t result;
  write_i2c(Gbt_Sca_Chs::I2C7, sl_addr, 2, data0);
  result = read_i2c(Gbt_Sca_Chs::I2C7, sl_addr);
  result = (result>>16)&0xff;
  return result;
}

void write_gbtx_register(uint32_t reg, uint32_t value)
{
  uint gbtx_address = 0;
  uint32_t sl_addr = gbtx_address*2+1;
  uint32_t data0 = ((reg&0xff)<<24) | ((reg&0xff00)<<8) | ((value&0xff)<<8);
  write_i2c(Gbt_Sca_Chs::I2C7, sl_addr, 3, data0);
}



