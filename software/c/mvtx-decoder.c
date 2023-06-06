/* Compile with:
gcc --std=gnu99 -march=native -lm -O3 -o decoder decoder.c
*/

#include <immintrin.h>
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <strings.h>
#include <math.h>
#include <inttypes.h>
#include <sys/stat.h>

struct decoder_t {
  int        nlanes      ;
  size_t     filebuf_size;
  size_t     lanebuf_size;
  size_t     hitbuf_size ;
  uint8_t*   filebuffer  ;
  uint8_t*   lanebuffer  ;
  uint8_t**  laneend     ;
  uint32_t*  hitbuffer   ;
  uint32_t** hitbuf_end  ;
  uint8_t*   abcs        ;
  uint8_t*   pageptr     ;
  size_t*    nHits       ;
  size_t*    nTotalHits  ;
  int        nbytesleft  ;
  int        file        ;
  size_t     nTrgs       ;
  uint32_t   cdw_counter ;
  uint16_t   cdw_row     ;
  uint16_t   cdw_charge  ;
  int        foundFEEID  ;
};

struct hit_t {
  uint16_t evno;
  uint64_t orbit : 40;
  uint16_t bc    : 12;
  uint8_t  abc;
  uint16_t feeid;
  uint8_t  laneid;
  uint16_t y;
  uint16_t x;
} __attribute__( ( packed ) );

struct trg_t
{
  uint64_t orbit : 40;
  uint16_t bc    : 12;
  uint8_t  isCWD;
  uint8_t  cdw_counter;
  uint16_t cdw_row;
  uint16_t cdw_charge;
} __attribute__( ( packed ) );

struct rdh_t
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
  uint64_t orbit;
  uint16_t bc;
  uint32_t trgType;
  uint16_t packetCounter;
  uint8_t  stopBit;
  int priority;
  uint8_t  pages_count;
  uint16_t rdhGBTcounter; // 10 bits
};

void decode_rdh( uint8_t* rdh_ptr, struct rdh_t* rdh )
{
  // FELIX header
  rdh->flxId         = ( *( uint8_t*  )( rdh_ptr + 23 ) ) & 0xFF;
  rdh->pageSize      = ( *( uint16_t* )( rdh_ptr + 25 ) ) & 0x7FF;
  rdh->gbtLink       = ( *( uint16_t* )( rdh_ptr + 28 ) ) & 0x7FF;
  rdh->flxHdrSize    = ( *( uint16_t* )( rdh_ptr + 29 ) ) & 0x7FF;
  rdh->flxHdrVersion = ( *( uint16_t* )( rdh_ptr + 30 ) ) & 0xFFFF;
  // RU header
  rdh->rdhVersion    = ( *( uint8_t*  )( rdh_ptr + 32 ) ) & 0xFF;
  rdh->rdhSize       = ( *( uint8_t*  )( rdh_ptr + 33 ) ) & 0xFF;
  rdh->feeId         = ( *( uint16_t* )( rdh_ptr + 34 ) ) & 0xFFFF;
  rdh->sourceId      = ( *( uint8_t*  )( rdh_ptr + 36 ) ) & 0xFF;
  rdh->detectorField = ( *( uint32_t* )( rdh_ptr + 37 ) ) & 0xFFFFFFFF;
  rdh->bc            = ( *( uint16_t* )( rdh_ptr + 41 ) ) & 0xFFF;
  rdh->orbit         = ( *( uint64_t* )( rdh_ptr + 43 ) ) & 0xFFFFFFFFFF;
  rdh->trgType       = ( *( uint32_t* )( rdh_ptr + 52 ) ) & 0xFFFFFFFF;
  rdh->packetCounter = ( *( uint16_t* )( rdh_ptr + 56 ) ) & 0xFFFF;
  rdh->stopBit       = ( *( uint8_t*  )( rdh_ptr + 58 ) ) & 0xFF;
  rdh->priority      = ( *( uint8_t*  )( rdh_ptr + 59 ) ) & 0xFF;
  rdh->rdhGBTcounter = ( *( uint16_t* )( rdh_ptr + 62 ) ) & 0xFFFF;
}

struct tdh_t
{
  uint16_t trigger_type    : 12;
  uint8_t internal_trigger : 1;
  uint8_t no_data          : 1;
  uint8_t continuation     : 1;
  uint16_t bc              : 12;
  uint64_t orbit           : 40;
} __attribute__( ( packed ) );

void decode_tdh( uint8_t* tdh_ptr, struct tdh_t* tdh )
{
  tdh->trigger_type     = ( ( tdh_ptr[1] & 0x0F ) << 8 ) | tdh_ptr[0];
  tdh->internal_trigger = ( tdh_ptr[1] >> 4 ) & 0x1;
  tdh->no_data          = ( tdh_ptr[1] >> 5 ) & 0x1;
  tdh->continuation     = ( tdh_ptr[1] >> 6 ) & 0x1;
  tdh->bc               = ( ( tdh_ptr[3] & 0x0F ) << 8 ) | tdh_ptr[2];
  tdh->orbit            = ( *( uint64_t* )&( tdh_ptr[4] ) ) & 0xFFFFFFFFFF;
}

struct cdw_t
{
  uint64_t user_field : 48;
  uint32_t cdw_counter : 16;
  //  uint16_t row_cdw = (user_field & 0xFFFF);
  //          uint16_t charge_cdw = ((user_field >> 16) & 0xFFFF);
};

void decode_cdw( uint8_t* cdw_ptr, struct cdw_t* cdw )
{
   cdw->user_field  = ( *( uint64_t * )( cdw_ptr ) ) & 0xFFFFFFFFFFFF;
   cdw->cdw_counter = ( *( uint32_t * )( cdw_ptr + 48 ) ) & 0xFFFFF;
}


void printStat(const size_t n_events, const size_t n_evt_with_payload, const size_t nTrg)
{
  printf( "Read %ld events. %ld with ALPIDE payload and %ld triggers\n",
           n_events, n_evt_with_payload, nTrg);
}

/* view hit files with:
hexdump hits.dat  -e '1/2 "evno=%d" "  " 1/4 "orbit=%08x" "  " 1/1 "bc=%02x" "  " 1/1 "abc=%02x" "  " 1/2 "fee=%02x" "  " 1/1 "laneid=%02d" "  " 1/2 "y=%5d" "\t" 1/2 "x=%5d""\n"'
*/

void decoder_init( struct decoder_t *decoder,size_t filebuf_size, size_t lanebuf_size, size_t hitbuf_size, int nlanes,const char *fname) {
  // TODO: check meaningfullness of params...
  //assert(filebuf_size%8192==0);
  decoder->nlanes       = nlanes;
  decoder->filebuf_size = filebuf_size;
  decoder->lanebuf_size = lanebuf_size;
  decoder->hitbuf_size  = hitbuf_size ;
  // memory allocations
  decoder->filebuffer  = _mm_malloc(filebuf_size * sizeof( uint8_t ), 4096 );
  decoder->lanebuffer  = _mm_malloc(nlanes * lanebuf_size * sizeof( uint8_t ), 4096 );
  decoder->laneend     = _mm_malloc(nlanes * sizeof( uint8_t* ), 4096 );
  decoder->hitbuffer   = _mm_malloc(nlanes * hitbuf_size * sizeof( uint32_t ), 4096 );
  decoder->hitbuf_end  = _mm_malloc(nlanes * sizeof( uint32_t* ), 4096 );
  decoder->nHits       = _mm_malloc(nlanes * sizeof( size_t ), 4096 );
  decoder->nTotalHits  = _mm_malloc(nlanes * sizeof( size_t ), 4096 );
  decoder->abcs        = _mm_malloc(nlanes * sizeof( uint8_t ), 4096 );
  // pointers
  decoder->nbytesleft  = 0;
  decoder->pageptr     = decoder->filebuffer;
  decoder->file        = open( fname, O_RDONLY );
  decoder->nTrgs       = 0;
  // cdw values
  decoder->cdw_counter = 0;
  decoder->cdw_charge  = 0;
  decoder->cdw_row     = 0;

  // found FEEID
  decoder->foundFEEID  = 0;


  // TODO: die in honor
  if( !decoder->filebuffer || !decoder->lanebuffer || \
      !decoder->laneend    || !decoder->hitbuffer  || \
      !decoder->nHits      || !decoder->nTotalHits )
  {
    fprintf( stderr, "Error while allocating memory: \"%s\". Exiting.\n", strerror( errno ) );
    exit( -1 );
  }

  if( decoder->file < 0 )
  {
    fprintf( stderr, "Error while trying to open file: \"%s\". Exiting.\n", strerror( errno ) );
    exit(-1);
  }
}

static inline int decode( uint8_t* laneptr, uint8_t* laneend, uint32_t* hitbuf_end, uint8_t* abc);

static inline void decoder_decode_lanes_into_hits( struct decoder_t* decoder )
{
  for( int i = 0; i < decoder->nlanes; ++i )
  {
    size_t nhits = decode( decoder->lanebuffer + decoder->lanebuf_size * i,
                           decoder->laneend[i], decoder->hitbuf_end[i],
                           decoder->abcs + i );
    decoder->nHits[i]      += nhits;
    decoder->nTotalHits[i] += nhits;
    decoder->hitbuf_end[i] += nhits;
  }
}

static inline void transformhits( uint32_t*hits, int n );

static inline void decoder_transform_hits( struct decoder_t *decoder )
{
  for( size_t i = 0; i < decoder->nlanes; ++i )
    transformhits( decoder->hitbuffer + decoder->hitbuf_size * i,
                   decoder->nHits[i] );
}

static inline int decoder_read_event_into_lanes( struct decoder_t *decoder, uint32_t *trgorbit, uint16_t *trgbc, int feeid )
{
  struct rdh_t rdh;
  int haspayload = 0;
  while( 1 )
  { // loop over pages

    if( decoder->nbytesleft > 0 )
    {
      while( ( *( uint16_t* ) ( &( decoder->pageptr[30] ) ) == 0xFFFF ) &&\
              decoder->nbytesleft )
      {
        decoder->pageptr += 32;
        decoder->nbytesleft -= 32;
      }
    }

    int pagesize = 0;
    if( decoder->nbytesleft >= 64 )
    {
      if( *( uint16_t* ) ( &( decoder->pageptr[30] ) ) == 0xAB01 )
      {
        decode_rdh( decoder->pageptr, &rdh );
        pagesize = ( rdh.pageSize + 1 ) * 32;
      }
      else
      {
        printf("nbytesleft: %d\n", decoder->nbytesleft);
        printf("nbytesread: %ld\n", decoder->pageptr - decoder->filebuffer);
        int fdump = open( "error.dat", O_CREAT | O_WRONLY | O_TRUNC, 0666 );
        write(fdump, decoder->filebuffer, (decoder->pageptr - decoder->filebuffer) + decoder->nbytesleft);
        close(fdump);
        return -3;
      }
    }

    if( pagesize == 0 || ( decoder->nbytesleft < pagesize ) )  //pagesize = 0 read rdh
    { // at least the RDH needs to be there...

      if( decoder->nbytesleft < 0 )
      {
        printf( "ERROR: d_nbytesleft: %d, less than zero \n", decoder->nbytesleft );
        return -2;
      }

      ssize_t nread = 0;
      uint8_t* buf_ptr = decoder->filebuffer; // set buf_ptr to filebuffer init
      memcpy( buf_ptr, decoder->pageptr, decoder->nbytesleft ); // move byte left to filebuffer beginig
      decoder->pageptr = buf_ptr;
      buf_ptr += decoder->nbytesleft;
      size_t len = ( decoder->filebuf_size - decoder->nbytesleft );
      if( len > 0x1000 )
        len &= ~0xFFF; // in chunks of 256 bytes multiples

      ssize_t n;
      do {
        n = read( decoder->file, buf_ptr, len);
        len -= n;
        buf_ptr += n;
        nread += n;
      } while( len > 0 && n > 0 );
      if( n < 0 )
        return n;
      if( nread == 0 )
        return (pagesize) ? -4 : 0;

      decoder->nbytesleft += nread;
      continue;
    }

    uint8_t* flx_ptr = decoder->pageptr; // payload: TODO: check header
    decoder->pageptr    += pagesize;
    decoder->nbytesleft -= pagesize;

    if ( pagesize == 0 ) continue; // TODO...
    if ( rdh.feeId != feeid ) continue;  //TODO: ...
    decoder->foundFEEID = 1;
    flx_ptr += 64; //skip RDH
    // printf( "flx_ptr: %d \n", *( uint8_t* )flx_ptr );

    const size_t nFlxWords = ( pagesize - 64 ) / 32;
    //TOD asser pagesize > 2
    if( ! rdh.packetCounter )
    {
      for( int i = 0; i < decoder->nlanes; ++i )
      {
        decoder->hitbuf_end[i] = decoder->hitbuffer + decoder->hitbuf_size * i;
        decoder->laneend[i] = decoder->lanebuffer + i * decoder->lanebuf_size;
        decoder->nHits[i] = 0;
      }
    }

    struct tdh_t tdh;
    struct cdw_t cdw;
    for( size_t iflx = 0; iflx < nFlxWords; ++iflx )
    {
      __m256i data = _mm256_stream_load_si256( ( __m256i* )flx_ptr );
      const uint16_t flx_header = _mm256_extract_epi16(data, 15) & 0x3FF;
      const uint16_t n_flx_word = ( ! (flx_header % 3) ) ? 3 : ( flx_header % 3 );
      uint8_t* gbt_word;
      for( size_t igbt = 0; igbt < n_flx_word; ++igbt )
      {
        gbt_word = flx_ptr + ( igbt * 10 );
        uint8_t lane = *( uint8_t* ) ( &( gbt_word[9] ) );

        if( lane == 0xE0 )
        { // lane heder: needs to be present: TODO: assert this
          haspayload = 0;
        }
        else if( lane == 0xE8 ) // TRIGGER DATA HEADER (TDH)
        {
          decode_tdh( gbt_word, &tdh );
        }
        else if( lane == 0xF8 ) // CALIBRATION DATA WORD (CDW)
        {
          decode_cdw( gbt_word, &cdw );
          uint64_t user_field = ( (uint64_t)gbt_word[5] << 40 ) | ( (uint64_t)gbt_word[4] << 32 ) | ( (uint64_t)gbt_word[3] << 24 ) | ( (uint64_t)gbt_word[2] << 16 ) | ( (uint64_t)gbt_word[1] << 8 ) | ( (uint64_t)gbt_word[0] );
          uint32_t cdw_counter = ( (uint32_t)gbt_word[8] << 16 ) | ( (uint32_t)gbt_word[7] << 8 ) | ( (uint32_t)gbt_word[6] );
          uint32_t row_cdw = (user_field & 0xFFFFFFFF);
          uint16_t charge_cdw = ((user_field >> 16) & 0xFFFF);

          decoder->cdw_counter = cdw_counter;
          decoder->cdw_charge = charge_cdw;
          decoder->cdw_row = row_cdw;
        }
        else if( lane == 0xF0 )
        { // lane trailer
          if( ! tdh.continuation )
            ++decoder->nTrgs;
        }
        else if( lane == 0xE4 )
        {
          //to do assert stop bit = 1
        }
        else if( ( ( lane >> 5 ) & 0x7 ) == 0x5 ) //IB DIAGNOSTIC DATA
        {
          // decode IB diagnostic word
          printf("WARNING!!! IB diagnostic data word received and skipped. \n");
        }
        else
        { // lane payload
          assert( ( ( lane >> 5 ) & 0x7 ) == 0x1 );
          haspayload = 1;
          lane &= 0x1F; // TODO: assert range + map IDs
          uint8_t *ptr = decoder->laneend[lane];
          memcpy(ptr, gbt_word, 9);
          decoder->laneend[lane] += 9;
        }
      } //for igbt
      flx_ptr += 32;
    }
    if( rdh.stopBit )
    {
      decoder_decode_lanes_into_hits( decoder );
      if( haspayload )
        return 1;
      else
        return 2;
    }
  }// while
}

static inline int decode( uint8_t* laneptr, uint8_t* laneend, uint32_t* hitbuf_end, uint8_t* abc )
{
  if( laneptr == laneend )
    return 0;

  size_t nhit = 0;

  uint8_t busy_on = 0;
  uint8_t busy_off = 0;

  uint8_t chipid = 0;
  uint8_t reg = 0;
  uint8_t chip_header_found = 0;
  uint8_t chip_trailer_found = 0;

  while( laneptr < laneend )
  { // TODO: check out of bounds problem (better: ensure that the 2 bytes following laneend are readable)
    if( *laneptr == 0xF1 ) //BUSY ON
    {
      ++busy_on;
      ++laneptr;
    }
    else if( *laneptr == 0xF0 ) // BUSY OFF
    {
      ++busy_off;
      ++laneptr;
    }
    else if( ( *laneptr & 0xF0 ) == 0xE0 )
    {
      chip_header_found = 0;
      chip_trailer_found = 1;
      chipid = laneptr[0] & 0xF;
      *abc = laneptr[1];
      busy_on = busy_off = 0;
      laneptr += 2;
    }
    else
    {
      if( chip_header_found )
      {
        if( ( laneptr[0] & 0xE0 ) == 0xC0 ) // REGION HEADER
        { // REGION HEADER : TODO: move first region header out of loop, asserting its existence
          reg = laneptr[0] & 0x1F;
          ++laneptr;
        }
        if( ( laneptr[0] & 0xC0 ) == 0x40 ) // DATA SHORT
        {
          int addr = ( laneptr[0] & 0x3F ) << 8 | laneptr[1];
          addr |= ( chipid << 19 ) | ( reg << 14 );
          hitbuf_end[nhit++] = addr;
          laneptr += 2;
        }
        else if( ( laneptr[0] & 0xC0 ) == 0x00 ) // DATA LONG
        {
          int addr = ( laneptr[0] & 0x3F ) << 8 | laneptr[1];
          addr |= ( chipid << 19 ) | ( reg << 14 );
          hitbuf_end[nhit++] = addr;

          uint8_t hitmap = laneptr[2]; // TODO: assert that bit 8 is 0?
          if( hitmap & 0x01 )
            hitbuf_end[nhit++] = addr + 1;
          if( hitmap & 0x7E )
          { // provide early out (mostly 2-pixel clusters...)
            if( hitmap & 0x02 )
              hitbuf_end[nhit++] = addr + 2;
            if( hitmap & 0x04 )
              hitbuf_end[nhit++] = addr + 3;
            if( hitmap & 0x08 )
              hitbuf_end[nhit++] = addr + 4;
            if( hitmap & 0x10 )
              hitbuf_end[nhit++] = addr + 5;
            if( hitmap & 0x20 )
              hitbuf_end[nhit++] = addr + 6;
            if( hitmap & 0x40 )
              hitbuf_end[nhit++] = addr + 7;
          }
          laneptr += 3;
        }
        else if( ( laneptr[0] & 0xF0 ) == 0xB0 ) // CHIP TRAILER
        {
          chip_trailer_found = 1;
          busy_on = busy_off = chip_header_found = 0;
          ++laneptr;
        }
      }
      else
      {
        if( ( laneptr[0] & 0xF0 ) == 0xA0 )
        {
          chip_header_found = 1;
          chip_trailer_found = 0;
          chipid = laneptr[0] & 0xF;
          *abc = laneptr[1];
          reg = 0;
          laneptr += 2;
        }
        else if( laneptr[0] == 0x00 ) // padding
        {
          ++laneptr;
        }
        else
        { // ERROR (IDLES and BUSIES should be stripped)
          printf( "ERROR: invalid byte 0x%02X\n", laneptr[0] );
          while( laneptr != laneend )
          {
            printf(" %02X ", *( uint8_t* )laneptr );
            ++laneptr;
          }
          printf( "\n" );
          printf( "ERROR: invalid byte 0x%02X\n", *laneptr & 0xFF );
          return -1;
        } // chip_header
      }  // data
    } // busy_on, busy_off, chip_empty, other
  }  // while
  assert( chip_trailer_found );
  return nhit;
}

static inline void transformhits( uint32_t* hits, int n )
{
  //printf("n=%d\n",n);
  /*
  for (int i=0;i<n;++i) {
    int y=hits[i]>>1&0x1FF;
    int x=hits[i]>>9|(hits[i]^hits[i]>>1)&1;
    hits[i]=y<<16|x;
  }
  return;
  */
  // x = reg << 5 | addr >> 9 & 0x1E | (addr ^ addr >> 1) & 0x1
  // y = addr >> 1 & 0x1FF
  const __m128i masky = _mm_set1_epi32( 0x000001FF );
  const __m128i mask0 = _mm_set1_epi32( 0x00000001 );
  const __m128i maska = _mm_set1_epi32( 0x0000FFFE );
  while( n > 0 )
  {
    __m128i a =_mm_load_si128( ( __m128i* )hits );

    __m128i t1 = _mm_srli_epi32( a, 1 );
    __m128i y  =_mm_and_si128( t1, masky );

    __m128i t2 = _mm_srli_epi32( a, 9 );
    __m128i t3 = _mm_and_si128( t2,maska);
    __m128i t4 = _mm_xor_si128( t1,a );
    __m128i t5 = _mm_and_si128( t4,mask0 );
    __m128i x  = _mm_or_si128( t3, t5 );

    __m128i t6=_mm_slli_epi32( y , 16 );
    __m128i yx=_mm_or_si128  ( t6, x );

    _mm_store_si128( ( __m128i* )hits, yx );

    hits += 4;
    n -= 4;
  }
}

static inline void fillrowhist(int *hist,uint32_t *hits,int n,int row) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Woverflow"
  const __m128i masky=_mm_set_epi8(0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE);
  const __m128i mask0=_mm_set_epi8(0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01);
#pragma GCC diagnostic pop

  const __m128i bad=_mm_set1_epi32(9*1024); // bad pixel ID
  __m128i y=_mm_set1_epi32(row<<1);
  while (n>0) {
    __m128i a =_mm_load_si128((__m128i*)hits);
    __m128i yp=_mm_and_si128 (a,masky);
    __m128i ok=_mm_cmpeq_epi32(yp,y);
    __m128i t2=_mm_and_si128 (a,mask0);
    __m128i t3=_mm_srli_epi32(a,9);
    __m128i t4=_mm_xor_si128 (t3,t2); // FIXME later: yeah... it is unique though
    __m128i b =_mm_blendv_epi8(bad,t4,ok); // epi8 is OK, due to ok

    if (n>3)
      ++hist[_mm_extract_epi32(b,3)];
    if (n>2)
      ++hist[_mm_extract_epi32(b,2)];
    if (n>1)
      ++hist[_mm_extract_epi32(b,1)];

    ++hist[_mm_extract_epi32(b,0)];

    hits+=4;
    n-=4;
  }
}

static inline void threshold_next_charge(float *sumd,float *sumd2,int ch, int *lasthist,int *hist, int ninj) {
  int ch1=ch-1;
  int ch2=ch;
  float ddV = 1.0*(ch2 - ch1);
  float V1 = ch1;
  float V2 = ch2;
  float meandV = 0.5*(V2+V1);

  for (int x=0;x<9*1024;++x) {
    float f=1./(1.*ninj);
    float n2=hist[x]*f;
    float n1=lasthist[x]*f;

    float dn=n2-n1;
    float den =dn/ddV;
    float m =meandV*dn/ddV;
    sumd [x]+= den;
    sumd2[x]+= m;

  }

}

static inline void threshold_next_row(float *thrs,float*rmss,float *sumd,float *sumd2,int nch,int ninj) {
  for (int x=0;x<9*1024;++x) {

    float den =sumd [x];
    float m=sumd2[x];
    if (den > 0) {
        m/=den;
    }
    float u  = den;
    float s  =sqrtf(m-u*u);
    thrs[x]=m;
    rmss[x]=s;
  }
}

void meanrms(float *m,float *s,float *data,size_t n) {
  float s1=0.;
  float s2=0.;
  int nn0=0;
  for (size_t i=0;i<n;++i) if (data[i]>0) {float x=data[i];s1+=x;s2+=x*x;++nn0;}
  s1/=nn0;
  s2/=nn0;
  *m=s1;
  *s=sqrtf(s2-s1*s1);
}

void thrana( struct decoder_t* decoder, int nch, int ninj, int feeid, const char *prefix, const char *suffix, int nrows )
{
  printf("In thrana. \n" );

  float *thrs       =_mm_malloc( 9*512*1024   *sizeof(float), 4096);
  float *rmss       =_mm_malloc( 9*512*1024   *sizeof(float), 4096);
  float* sumd  = _mm_malloc( 9 * 1024 * sizeof( float ), 4096);
  float* sumd2 = _mm_malloc( 9 * 1024 * sizeof( float ), 4096);
  int   *rowhist    =_mm_malloc((9    *1024+1)*sizeof(int  ), 4096);
  int   *lastrowhist=_mm_malloc((9    *1024+1)*sizeof(int  ), 4096);

  uint32_t trgorbit;
  uint16_t trgbc;

  char fname[200];
  char rmsfname[300];

  sprintf(fname,"%sthrmap%d%s.dat",prefix,feeid,suffix);
  sprintf(rmsfname, "%srmsmap%d%s.dat", prefix, feeid, suffix);
  int f=open(fname,O_CREAT|O_WRONLY|O_TRUNC,0666);
  int frms = open(rmsfname, O_CREAT | O_WRONLY | O_TRUNC, 0666);

  // decoder->cdw_counter= 0;
  // decoder->cdw_charge = 0;
  // decoder->cdw_row = 0;

  size_t nevt = 0;
  size_t nwithpayload = 0;

  for (int row=0;row<512;++row) {
    if (nrows==6 && !(row==1 || row==2 || row==254 || row==255 || row==509 || row==510)) continue;
    printf("Row %4d : ",row);fflush(stdout);
    int nbad=0;
    int ngood=0;
    bzero(sumd ,9*1024*sizeof(float));
    bzero(sumd2,9*1024*sizeof(float));

    for (int ch=0;ch<nch;++ch) {
      bzero(rowhist,(9*1024+1)*sizeof(int));
      for (int inj=0;inj<ninj;++inj) {

        int ret=decoder_read_event_into_lanes(decoder,&trgorbit,&trgbc,feeid);
        if (ret == 0 ) break; // EOF
        if( ret == 1 ) ++nwithpayload;
        if( ret == -1 ){ fprintf(stderr,"Error while reading file: %s Exiting.\n",strerror(errno)); exit(-1); }
        if (ret==-2) { fprintf(stderr,"Error while reading file: %s Last read was incomplete. Exiting (some events might be ignored).\n",strerror(errno)); exit(-1); }
        if (ret==-3) { fprintf(stderr,"Flx header has wrong align. byte %ld \n", decoder->pageptr - decoder->filebuffer ); exit(-1); }
        ++nevt;
        decoder_decode_lanes_into_hits(decoder);
        for (int i=0;i<decoder->nlanes;++i)  { fillrowhist(rowhist,decoder->hitbuffer+i*decoder->hitbuf_size,decoder->nHits[i],row); }
      }

      int nhit=0;
      for (int i=0;i<9*1024;++i) nhit+=rowhist[i];

      ngood+=nhit;
      nbad+=rowhist[9*1024];
      if (ch) {
        threshold_next_charge(sumd,sumd2,ch,lastrowhist,rowhist,ninj);
      }
      int *tmp=lastrowhist;
      lastrowhist=rowhist;
      rowhist=tmp;
    }
    threshold_next_row(thrs+row*9*1024,rmss+row*9*1024,sumd,sumd2,nch,ninj);
    //printf("thr[row=%d,col=0]=%f, rms=%f\n",row,*(thrs+row*9*1024),*(rmss+row*9*1024));
    write(f,thrs+row*9*1024,9*1024*sizeof(float)); // TODO: do not keep full map in memory?
    write(frms,rmss+row*9*1024,9*1024*sizeof(float));
    float m,merr,s,serr;
    meanrms(&m,&merr,thrs+row*9*1024,9*1024);
    meanrms(&s,&serr,rmss+row*9*1024,9*1024);
    printf(" (mean: %5.2f +/- %4.2f ; RMS: %5.2f +/- %4.2f ; good/bad hits: %d / %d)\n",m,merr,s,serr,ngood,nbad);
   }

  while ( 0 )
  {
    int ret = decoder_read_event_into_lanes(decoder,&trgorbit,&trgbc,feeid);

    if (ret == 0 ) break; // EOF

    if( ret == 1 )
    {
      ++nwithpayload;
    }

    if( ret == -1 )
    {
      fprintf(stderr,"Error while reading file: %s Exiting.\n",strerror(errno));
      exit(-1);
    }
    if (ret==-2) {
      fprintf(stderr,"Error while reading file: %s Last read was incomplete. Exiting (some events might be ignored).\n",strerror(errno));
      exit(-1);
    }
    ++nevt;
  }

  printStat( nevt, nwithpayload, decoder->nTrgs );
  close(f);
  _mm_free(lastrowhist);
  _mm_free(rowhist    );
  _mm_free(sumd2      );
  _mm_free(sumd       );
  _mm_free(rmss       );
  _mm_free(thrs       );
}

static inline void fillhitmap( uint32_t* map, uint32_t* hits, int n )
{
  /*
    for (int i=0;i<n;++i) {
      int x=hits[i]&0xFFFF;
      int y=hits[i]>>16;
      ++map[y*1024*9+x];
    }
  */

  const __m128i masky __attribute__((unused)) = _mm_set1_epi32(0x01FF0000);
  const __m128i maskx=_mm_set1_epi32(0x00003FFF);
  const __m128i stride=_mm_set1_epi32(9*1024);
  while (n>0) {
    __m128i hs=_mm_stream_load_si128((__m128i*)hits);
    //__m128i hs=_mm_load_si128((__m128i*)hits);
    __m128i t1=_mm_srli_epi32(hs,16);
    __m128i t2=_mm_mullo_epi32(t1,stride);
    __m128i t3=_mm_and_si128 (hs,maskx);
    __m128i  a=_mm_add_epi32 (t2,t3   );
    if (n>3)
      ++map[_mm_extract_epi32(a,3)];
    if (n>2)
      ++map[_mm_extract_epi32(a,2)];
    if (n>1)
      ++map[_mm_extract_epi32(a,1)];

    ++map[_mm_extract_epi32(a,0)];

    hits+=4;
    n-=4;
  }
}

#define HITBUFSIZE 1024
void fhrana( struct decoder_t *decoder, int feeid, const char *prefix, int nmax )
{
  printf("In fhrana. \n" );
  struct hit_t hit;
  struct hit_t* hitbuf = NULL;
  int nhitbuf = 0;
  if( nmax )
    hit.feeid = feeid;
  uint32_t trgorbit;
  uint16_t trgbc;
  size_t nevt = 0;
  size_t nwithpayload = 0;
  uint32_t* hitmap = _mm_malloc( 9 * 1024 * 512 * sizeof( uint32_t ), 4096);
  bzero( hitmap, 9 * 1024 * 512 * sizeof( uint32_t) );
  char fname[200];
  int fdump = 0;
  if( nmax )
  {
    sprintf( fname, "%shits%d.dat", prefix, feeid );
    fdump = open( fname, O_CREAT | O_WRONLY | O_TRUNC, 0666 );
    hitbuf = malloc( HITBUFSIZE * sizeof( struct hit_t ) );
    nhitbuf = 0;
  }

  while( 1 )
  {
    int ret = decoder_read_event_into_lanes( decoder, &trgorbit, &trgbc, feeid );
    if( ret == 0 )
      break;
    if( ret == -1 )
    {
      fprintf(stderr,"Error while reading file: %s Exiting.\n",strerror(errno));
      exit(-1);
    }
    if (ret==-2) {
      fprintf(stderr,"Error while reading file: %s Last read was incomplete. Exiting (some events might be ignored).\n",strerror(errno));
      exit(-1);
    }
    if (nmax)
    {
      // hit.orbit = trgorbit;
      // hit.bc = trgbc;
      hit.evno = nwithpayload;
    }

    if( ret == 1 )
    {
      ++nwithpayload;
    }
    decoder_transform_hits( decoder );

    for( int i=0; i<decoder->nlanes;++i )
    {
      // for (int j=0;j<decoder->nhits[i];++j) {
      //   printf("[%d,%d]: %08X\n",i,j,*decoder->hitbuffer+i*decoder->hitbuf_size+j);
      // }
      int nhits = decoder->nHits[i];
      if( nhits < 0 )
      {
        printf( "ERROR IN EVENT %ld LANE: %d\n", nevt, i );
        printf( "POS: %ld\n", lseek( decoder->file, 0, SEEK_CUR ) );
        for( int j = 0; j < decoder->nlanes; ++j )
          printf( "[%d] = %zu\n ", j, decoder->nHits[j] );
      }
      else
      {
        fillhitmap( hitmap, decoder->hitbuffer + i*decoder->hitbuf_size, nhits);
        if (nmax) {
          hit.abc=decoder->abcs[i];
          hit.laneid=i;
          for (int j=0;j<decoder->nHits[i];++j) {
            uint32_t yx=*(decoder->hitbuffer+i*decoder->hitbuf_size+j);
            hit.y=yx>>16;
            hit.x=yx&0xFFFF;
            if (nmax<0 || hitmap[hit.y*9*1024+hit.x]<=nmax) {
              hitbuf[nhitbuf++] = hit;
              if( nhitbuf == HITBUFSIZE )
              {
                 write( fdump, hitbuf, HITBUFSIZE * sizeof( struct hit_t ) );
                 nhitbuf = 0;
              }
            }
          }
        }
      }
    }
    ++nevt;
  }

  if( fdump )
  {
    if( nhitbuf ) write(fdump,hitbuf,nhitbuf*sizeof(struct hit_t));
    close(fdump);
  }
  if(!decoder->foundFEEID){
    printf("FEEID %d not found in file. Exiting.\n",feeid);

  }
  printStat( nevt, nwithpayload, decoder->nTrgs );

  sprintf( fname, "%shitmap%d.dat", prefix, feeid );
  int fhitmap = open( fname, O_CREAT | O_WRONLY | O_TRUNC, 0666 );
  write( fhitmap, hitmap, 9 * 1024 * 512 * sizeof( uint32_t ) );
  close( fhitmap );

  int ntot=0;
  for( int y = 0; y < 512; ++y )
  {
    for( int x = 0; x < 9 * 1024; ++x )
    {
      //if (hitmap[y*9*1024+x]>0) printf("hitmap[y=%3d,x=%4d]=%6d\n",y,x,hitmap[y*9*1024+x]);
      ntot += hitmap[ y * 9 * 1024 + x ];
    }
  }
  printf( "Total number of hits: %d. \n", ntot );
  for( int ilane = 0; ilane < decoder->nlanes; ++ilane )
  {
    printf( "[%d] %zu hits \n", ilane, decoder->nTotalHits[ilane] );
  }
  //for (int x=0;x<9*1024+1;++x) {
  //  if (rowhist[x]>0) printf("rowhistx=%4d]=%6d\n",x,rowhist[x]);
  //}
}

void usage(const char *a0) {
  fprintf(stderr,
    "usages:\n"
    " *) %s: thrmap  filename feeid [prefix]\n"
    "   ... produces [prefix]thramp[feeid].dat with 9x1024x512 float32 with thresholds of an IB stave\n"
    " *) %s: thrmap6 filename feeid [prefix] [nsettings]\n"
    "   ... produces [prefix]thramp[feeid][-setting].dat with 9x1024x6   float32 with thresholds of an IB stave (rows 1,2,254,255,509,510)\n"
    " *) %s: hitmap  filename feeid [prefix]\n"
    "   ... produces [prefix]hitamp[feeid].dat with 9x1024x512 int32 with hitmaps of an IB stave\n"
    "   ... if nmax>0 produces also [prefix]hits[feeid].dat with 128 bit records of format:\n"
    "         envno:32;orbit:32;BC:8;FEEID:16;CHIPID:8;y:16;x:16\n"
    "         for the first up to nmax hits for each pixel\n"
    "         (NB: not super-fast... writes hit by hit)\n"
    "examples:\n"
  //  " $ lz4cat thrdata-fee264.lz4 | %s thrmap6 /dev/stdin 264 test # produces: testthrmap264.dat\n"
      " $ ddump -s -g -n 0 -p 2001 test_00000000-0000.prdf | %s hitmap /dev/stdin 264 test # produces: testhitmap256.dat \n"
    ,a0,a0,a0,a0);
}

int main(int argc,char *argv[]) {
  printf("WARNING!!! This decoder is OBSOLETE. Please use <felix-mvtx>/sofware/cpp/decoder/mvtx-decoder\n");
  exit(0);
  if (argc!=4 && argc!=5 && argc!=6) {
    usage(argv[0]);
    exit(-1);
  }
  const char *fname =           argv[2] ;
  int         feeid =      atoi(argv[3]);
  const char *prefix=argc<=4?"":argv[4] ;
  int         nmax  =argc<=5?0 :atoi(argv[5]);
  printf("fname: %s feeid: %d prefix: %s nmax: %d \n",fname, feeid, prefix, nmax);
  // TODO: use and check better defaults:
  struct decoder_t decoder;
  // decoder_init(&decoder,8192*1001,1024*1024,10000,16,fname);
  decoder_init( &decoder, 8192*1001, 1024*1024, 10000, 9, fname);

  if( strcmp( argv[1], "thrmap" ) == 0 )
  {
    thrana( &decoder, 50, 25, feeid, prefix, "", 512 );
  //  decoder_read_event_into_lanes(&decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping EOT
  }
  else if (strcmp(argv[1],"thrmap6")==0) {
    uint32_t trgorbit;
    uint16_t trgbc;
    decoder_read_event_into_lanes(&decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping SOT
    if (nmax==0) nmax=1;
    for (int i=0;i<nmax;++i) {
      char suffix[100]={0};
      if (nmax>1) sprintf(suffix,"-%d",i);
      thrana(&decoder,50,25,feeid,prefix,suffix,6);
    }
    decoder_read_event_into_lanes(&decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping EOT
  }
  else if ( strcmp(argv[1], "hitmap" ) == 0 )
  {
    fhrana( &decoder, feeid, prefix, nmax );
  }
  else {
    usage(argv[0]);
    exit(-1);
  }
}

