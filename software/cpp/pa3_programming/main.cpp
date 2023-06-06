#include <stdlib.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>

#include <chrono>

#include <fstream>
#include <iostream>

#include "dpuser.hh"
#include "dpalg.h"

#include "GBT_SCA_src/Sca.h"

//#define DBG
int log_mode         = 0;
int log_log          = 0;
int log_log_log      = 0;
int mode_stream_in   = 1; // Read 32b of TMS/TDA data instead of 1 bits
int mode_stream_io   = 1; // Write/read 32b of TMS/TDA data instead of 1 bits
int mode_stream_tms  = 1; // Writes stream of TMS instead of individual bits
int speed_up         = 1; // Packs data instad of sending individual bits
char id[7];

int G_MSB_LSB = 0; // the 11th bit in the control register of JTAG channel in GBT-SCA

int G_length = -1;
uint128_t G_tms_data = -1;
// 0       1  2       3   4       5  6       7       8
// pa3jtag -a PROGRAM -id 21:00.0 -f pa3.dat -gbt_ch 12

void show_usage()
{
  printf("Usage:\n");
  printf("./pa3jtag -a action -id CRU_PCIe_address -f path_to_dat_file -gbt_ch gbt_ch_number\n");
  printf("ACTIONs:\n1. DEVICE_INFO\n2. READ_IDCODE\n3. ERASE\n4. PROGRAM\n5. VERIFY\n");
}

int check_file_size(std::string filename) // path to file
{
  FILE *p_file = NULL;
  if((p_file = fopen(filename.c_str(),"rb")))
  {
    fseek(p_file,0,SEEK_END);
    int size = ftell(p_file);
    fclose(p_file);
    if( size != 537694)
    {
      printf("Error: Incorrect size of provided bitfile, expected 537694 bytes, size of file is %d.\n", size);
      return 0;
    }
    return 1;
  }
  else
  {
    printf("Error: File not found %s.\n", filename.c_str());
    return 0;
  }
}

int main(int argc, char *argv[])
{
  if(argc != 9)
  {
    printf("Error: Not all parameters present.\n");
    show_usage();
    return -1;
  }
  if(strcmp(argv[1], "-a") || strcmp(argv[3], "-id") || strcmp(argv[5], "-f") || strcmp(argv[7],"-gbt_ch"))
  {
    printf("Error: Parameters not in the right order or misspelled.\n");
    show_usage();
    return -1;
  }

/*  if(strlen(argv[4]) != strlen("04:00.0"))
  {
    printf("Error: id parameter has incorrect format, expecting 04:00.0\n");
    return -1;
  }
  char *sub = argv[4]+2;
  if(strcmp(sub, ":00.0"))
  {
    printf("Error: id parameter has incorrect format, expecting 04:00.0\n");
    return -1;
  }*/
  strcpy(id, argv[4]);

  if(!check_file_size(argv[6]))
    return -1;

  int action __attribute__((unused)) = 0;

  if(!strcmp(argv[2], "DEVICE_INFO")) {
    action = DP_DEVICE_INFO_ACTION_CODE;
  } else if (!strcmp(argv[2], "READ_IDCODE")) {
    action = DP_READ_IDCODE_ACTION_CODE;
  } else if (!strcmp(argv[2], "ERASE")) {
    action = DP_ERASE_ACTION_CODE;
  } else if (!strcmp(argv[2],"PROGRAM")) {
    action = DP_PROGRAM_ACTION_CODE;
  } else if (!strcmp(argv[2],"VERIFY")) {
    action = DP_VERIFY_ACTION_CODE;
  } else {
    printf("Error: Action argument %s not recognised.\n", argv[2]);
    show_usage();
    return -1;
  }

  char* endptr;
  long int gbt_channel_number = strtol(argv[8], &endptr, 10);
  if (*endptr)
  {
    printf("Error: Cannot convert gbt_ch to number.\n");
    return -1;
  }
  if(gbt_channel_number > 23)
  {
    printf("Error: gbt_ch %ld out of range.\n", gbt_channel_number);
    return -1;
  }

  set_gbt_channel((int)gbt_channel_number);

  uint32_t currently_selected_gbt_channel = get_gbt_channel();
  if((uint32_t)gbt_channel_number != currently_selected_gbt_channel)
  {
    printf("Error: Could not set GBT channel.\n");
    return -1;
  }

  set_phase_detector_charge_pump(12);

  printf("Initializing...\n");

  #ifdef DBG
    printf("sca init...\n");
  #endif

  #ifdef DBG
  printf("jtag power on...\n");
  #endif
  jtag_power();

  #ifdef DBG
  printf("jtag reset..\n");
  #endif
  jtag_reset();

  #ifdef DBG
  printf("reset jtag control.....\n ");
  #endif
  jtag_set_frequency(10000000);

  G_length = 1;
  #ifdef DBG
  printf("set G_length: %x\n", G_length);
  jtag_w_CTRL(G_length);
  printf("readback ctl reg 1st time: %04x\n", jtag_r_CTRL());
  #endif

  DPINT Result = DPE_SUCCESS;

  #ifdef DBG
  printf("Action code: %d\n", action);
  #endif

  std::ifstream is (argv[6], std::ifstream::binary);
  if (!is) {
    printf("[ERROR] Invalid file, exiting...\n");
    return -1;
  }
  is.seekg (0, is.end);
  int main_length = is.tellg();
  is.seekg (0, is.beg);

  char * buffer = new char [main_length];
  #ifdef DBG
  std::cout << "[INFO] Reading " << std::dec << main_length << " bytes. " << std::endl;
  #endif
  is.read (buffer,main_length);

  image_buffer = (DPUCHAR*)buffer; //init direct C buffer, image buffer is a global variable.

  Action_code = action;
  dp_top();
  printf("\n");

  delete[] buffer;
  is.close();
  if(error_code != 0)
  {
      printf("err_code: %d\n", error_code);
  }
  printf("pa3_version: %x\n", pa3_version());

  return (Result);
}
