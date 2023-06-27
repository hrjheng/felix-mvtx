
#ifndef __UTILS__
#define __UTILS__

//utility class to emulate a progress bar
#define clean_errno() (errno == 0 ? "None" : strerror(errno))
#define log_error(M, ...) fprintf(stderr, "[ERROR] (%s:%d: errno: %s) " M "\n", __FILE__, __LINE__, clean_errno(), ##__VA_ARGS__)
#define ASSERT(A, D, M,...) if(!(A)) { save_block(D); log_error(M, ##__VA_ARGS__); assert(A); }

namespace
{
  template <class T>
  void CleanVec(std::vector<T> &v)
  {
    std::vector<T>().swap(v);
    v.shrink_to_fit();
  }
}

namespace Trg
{
  enum BitMap
  {
    ORBIT   = 0,
    HB      = 1,
    HBr     = 2,
    HC      = 3,
    PHYSICS = 4,
    PP      = 5,
    CAL     = 6,
    SOT     = 7,
    EOT     = 8,
    SOC     = 9,
    EOC     = 10,
    TF      = 11,
    FE_RST  = 12,
    RT      = 13,
    RS      = 14,
    nBitMap = 15
  };

  static const BitMap allBitMap[] =
  { ORBIT, HB, HBr, HC, PHYSICS, PP, CAL, SOT, EOT, SOC, EOC, TF, FE_RST, RT, RS };

  std::array<std::string, BitMap::nBitMap> BitMapName =
  {{ {"ORBIT"}, {"HB"}, {"HBr"}, {"HC"}, {"PHYSICS"}, {"PP"}, {"CAL"}, {"SOT"}, {"EOT"}, {"SOC"}, {"EOC"},
     {"TF"}, {"FE_RST"}, {"RT"}, {"RS"} }};
}


struct rdh_t // Raw Data Header
{
  // FLX header
  uint8_t flxId;    // [23]
  uint16_t pageSize; // [25]
  uint8_t gbtLink;
  uint8_t flxHdrSize;
  uint16_t flxHdrVersion;
  // RU header
  uint8_t rdhVersion;
  uint8_t rdhSize;
  uint16_t feeId;
  uint8_t sourceId;
  uint32_t detectorField;
  uint64_t orbit; // -> BCO
  uint16_t bc;
  uint32_t trgType;
  uint16_t packetCounter;
  uint8_t  stopBit;
  int priority;
  uint8_t  pages_count;
  uint16_t rdhGBTcounter; // 10 bits

  std::vector<std::string> trgVector = {};

  rdh_t() = default;
  ~rdh_t() = default;

  void decode(uint8_t* rdh_ptr)
  {
   // FELIX header
    flxId         = *(reinterpret_cast<uint8_t*>(rdh_ptr + 23) ) & 0xFF;
    pageSize      = *(reinterpret_cast<uint16_t*>(rdh_ptr + 25) ) & 0x7FF;
    gbtLink       = *(reinterpret_cast<uint16_t*>(rdh_ptr + 28) ) & 0x7FF;
    flxHdrSize    = *(reinterpret_cast<uint16_t*>(rdh_ptr + 29) ) & 0x7FF;
    flxHdrVersion = *(reinterpret_cast<uint16_t*>(rdh_ptr + 30) ) & 0xFFFF;
    // RU header
    rdhVersion    = *(reinterpret_cast<uint8_t*>(rdh_ptr + 32) ) & 0xFF;
    rdhSize       = *(reinterpret_cast<uint8_t*>(rdh_ptr + 33) ) & 0xFF;
    feeId         = *(reinterpret_cast<uint16_t*>(rdh_ptr + 34) ) & 0xFFFF;
    sourceId      = *(reinterpret_cast<uint8_t*>(rdh_ptr + 36) ) & 0xFF;
    detectorField = *(reinterpret_cast<uint32_t*>(rdh_ptr + 37) ) & 0xFFFFFFFF;
    bc            = *(reinterpret_cast<uint16_t*>(rdh_ptr + 42) ) & 0xFFF;
    orbit         = *(reinterpret_cast<uint64_t*>(rdh_ptr + 46) ) & 0xFFFFFFFFFF;
    trgType       = *(reinterpret_cast<uint32_t*>(rdh_ptr + 52) ) & 0xFFFFFFFF;
    packetCounter = *(reinterpret_cast<uint16_t*>(rdh_ptr + 56) ) & 0xFFFF;
    stopBit       = *(reinterpret_cast<uint8_t*>(rdh_ptr + 58) ) & 0xFF;
    priority      = *(reinterpret_cast<uint8_t*>(rdh_ptr + 59) ) & 0xFF;
    rdhGBTcounter = *(reinterpret_cast<uint16_t*>(rdh_ptr + 62) ) & 0xFFFF;

//    for ( const auto& trg : Trg::allBitMap )
//    {
//      if ( ((trgType >> trg) & 1) == 1 )
//      {
//        trgVector.push_back(Trg::BitMapName[trg]);
//      }
//    }
//    assert(std::find(trgVector.begin(), trgVector.end(), "PP") == trgVector.end() );
//    assert(std::find(trgVector.begin(), trgVector.end(), "CAL") == trgVector.end() );
  }
};


struct tdh_t
{
  uint16_t trigger_type    : 12;
  uint8_t internal_trigger : 1;
  uint8_t no_data          : 1;
  uint8_t continuation     : 1;
  uint16_t bc              : 12;
  uint64_t orbit           : 40;

  inline void decode(uint8_t* ptr)
  {
    trigger_type     = ((ptr[1] & 0x0F) << 8) | ptr[0];
    internal_trigger = (ptr[1] >> 4) & 0x1;
    no_data          = (ptr[1] >> 5) & 0x1;
    continuation     = (ptr[1] >> 6) & 0x1;
    bc               = ( (ptr[3] & 0x0F) << 8) | ptr[2];
    orbit            = *(reinterpret_cast<uint64_t*>(ptr + 4) ) & 0xFFFFFFFFFF;
  }
} __attribute__( (packed) );


struct tdt_t
{
  uint64_t lane_status          : 56;
  uint8_t timeout_in_idle       : 1;
  uint8_t timeout_start_stop    : 1;
  uint8_t timeout_to_start      : 1;
  uint8_t packet_done           : 1;
  uint8_t transmission_timeout  : 1;
  uint8_t lane_starts_violation : 1;
  uint8_t lane_timeouts         : 1;

  inline void decode( uint8_t* ptr )
  {
    lane_status           = *(reinterpret_cast<uint64_t*>(ptr) ) & 0xFFFFFFFFFFFFFF;
    timeout_in_idle       = (ptr[7] >> 5) & 0x1;
    timeout_start_stop    = (ptr[7] >> 6) & 0x1;
    timeout_to_start      = (ptr[7] >> 7) & 0x1;
    packet_done           = (ptr[8] >> 0) & 0x1;
    transmission_timeout  = (ptr[8] >> 1) & 0x1;
    lane_starts_violation = (ptr[8] >> 3) & 0x1;
    lane_timeouts         = (ptr[8] >> 4) & 0x1;
  }
} __attribute__( (packed) );


struct cdw_t
{
  uint64_t user_field : 48;
  uint32_t cdw_counter : 16;

  cdw_t() = default;
  ~cdw_t() = default;

  inline void decode(uint8_t* ptr)
  {
    user_field  = *(reinterpret_cast<uint64_t*>(ptr) ) & 0xFFFFFFFFFFFF;
    cdw_counter = *(reinterpret_cast<uint32_t*>(ptr + 48) ) & 0xFFFFF;
  }
};


struct trg_t
{
  uint64_t orbit  : 40;
  uint16_t bc     : 12;

  int thscan_row = 0;
  int thscan_chg = 0;
  int thscan_inj = 0;

  trg_t():
    orbit(0),
    bc(0),
    thscan_row(-1),
    thscan_chg(-1),
    thscan_inj(0)
  {}
} __attribute__( (packed) );

#endif
