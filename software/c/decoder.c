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

struct decoder_t {
  int        nlanes      ;
  size_t     filebuf_size;
  size_t     lanebuf_size;
  size_t     hitbuf_size ;
  char      *filebuffer  ;
  uint8_t   *lanebuffer  ;
  uint8_t  **laneend     ;
  uint32_t  *hitbuffer   ;
  uint8_t   *abcs        ;
  char      *pageptr     ;
  int       *nhits       ;
  int        nbytesleft  ;
  int        file        ;
};

struct hit_t {
  uint16_t evno  :16;
  uint32_t orbit :32;
  uint16_t bc    :16; 
  uint8_t  abc   : 8;
  uint16_t feeid :16;
  uint8_t  laneid: 8;
  uint16_t y     :16;
  uint16_t x     :16;
}__attribute__((packed));


/* view hit files with:
hexdump hits.dat  -e '1/2 "evno=%d" "  " 1/4 "orbit=%08x" "  " 1/1 "bc=%02x" "  " 1/1 "abc=%02x" "  " 1/2 "fee=%02x" "  " 1/1 "laneid=%02d" "  " 1/2 "y=%5d" "\t" 1/2 "x=%5d""\n"'
*/

void decoder_init(struct decoder_t *decoder,size_t filebuf_size,size_t lanebuf_size,size_t hitbuf_size,int nlanes,const char *fname) {
  // TODO: check meaningfullness of params...
  //assert(filebuf_size%8192==0);
  decoder->nlanes      =nlanes      ;
  decoder->filebuf_size=filebuf_size;
  decoder->lanebuf_size=lanebuf_size;
  decoder->hitbuf_size =hitbuf_size ;
  decoder->filebuffer  =_mm_malloc(filebuf_size       *sizeof(uint8_t ),4096);
  decoder->lanebuffer  =_mm_malloc(nlanes*lanebuf_size*sizeof(uint8_t ),4096);
  decoder->laneend     =_mm_malloc(nlanes             *sizeof(uint8_t*),4096);
  decoder->hitbuffer   =_mm_malloc(nlanes*hitbuf_size *sizeof(uint32_t),4096);
  decoder->nhits       =_mm_malloc(nlanes             *sizeof(int     ),4096);
  decoder->abcs        =_mm_malloc(nlanes             *sizeof(uint8_t ),4096);
  decoder->nbytesleft  =0;
  decoder->pageptr     =decoder->filebuffer;
  decoder->file=open(fname,O_RDONLY);
  // TODO: die in honor
  if (!decoder->filebuffer || !decoder->lanebuffer || !decoder->laneend || !decoder->hitbuffer || !decoder->nhits) {
    fprintf(stderr,"Error while allocating memory: \"%s\". Exiting.\n",strerror(errno));
    exit(-1);
  }
  if (decoder->file<0) {
    fprintf(stderr,"Error while trying to open file: \"%s\". Exiting.\n",strerror(errno));
    exit(-1);
  }
}

static inline int decoder_read_event_into_lanes(struct decoder_t *decoder,uint32_t *trgorbit,uint16_t *trgbc,int feeid) {
  for (int i=0;i<decoder->nlanes;++i) {
    decoder->laneend[i]=decoder->lanebuffer+decoder->lanebuf_size*i;
  }
  while (1) { // loop over pages
    int pagesize;
    if (decoder->nbytesleft>=64) 
       pagesize=*(uint16_t*)(decoder->pageptr+8);
    else
       pagesize=0;
    if (pagesize==0||decoder->nbytesleft<pagesize) { // at least the RDH needs to be there...
      ssize_t nread=0; 
      char *ptr=decoder->filebuffer;
      memcpy(ptr,decoder->pageptr,decoder->nbytesleft);
      decoder->pageptr=ptr;
      ptr+=decoder->nbytesleft;
      size_t len=(decoder->filebuf_size-decoder->nbytesleft);
      if (len>0x1000)len&=~0xFFF; // in chunks of 4k multiples
      ssize_t n;
      do {
        n=read(decoder->file,ptr,len);
        len-=n;
        ptr+=n;
        nread+=n;
      } while (len>0 && n>0);
      if (n<0) return n;
      if (nread==0) return 0;
      decoder->nbytesleft+=nread;
      if (decoder->nbytesleft<64) return -2;
      pagesize=*(uint16_t*)(decoder->pageptr+8);
    }
    char *ptr=decoder->pageptr+64; // payload: TODO: check header
    int packetfeeid=*(decoder->pageptr+5)<<8|*(decoder->pageptr+4);
    *trgorbit=*(uint32_t*)(decoder->pageptr+16);
    *trgbc   =*(uint16_t*)(decoder->pageptr+32);
    decoder->nbytesleft-=pagesize;
    decoder->pageptr+=pagesize;
    if (pagesize==0) continue; // TODO...
    if (packetfeeid!=feeid) continue;  //TODO: ...
    int iword=4;
    int haspayload=0;
    do { // loop over 128 bit words in page
      int lane=ptr[9];
      if (lane==(char)0xE0) { // lane heder: needs to be present: TODO: assert this
      }
      else if (lane==(char)0xF0) { // lane trailer
        if (ptr[8]&0x01==0x01) { // event done
           if (haspayload)
             return 1;
           else
             return 2;
        }
        break; // no futher payload in this page
      }
      else { // lane payload
        haspayload=1;
        lane&=0x1F; // TODO: assert range + map IDs
        __m128i data=_mm_stream_load_si128((__m128i*)ptr);
        uint8_t *ptr=decoder->laneend[lane];
        decoder->laneend[lane]+=9;
        // Is not fully correct, as j needs to be a constant...: for (int j=0;j<9;++j) ptr[j]=_mm_extract_epi8(data,j);
        ptr[0]=_mm_extract_epi8(data,0);
        ptr[1]=_mm_extract_epi8(data,1);
        ptr[2]=_mm_extract_epi8(data,2);
        ptr[3]=_mm_extract_epi8(data,3);
        ptr[4]=_mm_extract_epi8(data,4);
        ptr[5]=_mm_extract_epi8(data,5);
        ptr[6]=_mm_extract_epi8(data,6);
        ptr[7]=_mm_extract_epi8(data,7);
        ptr[8]=_mm_extract_epi8(data,8);
      }
      ptr+=16;
      ++iword;
    } while (iword!=512);
  } 
}

static inline int decode(uint8_t *laneptr,uint8_t *laneend,uint32_t *hitbuf,uint8_t *abc);
static inline void decoder_decode_lanes_into_hits(struct decoder_t *decoder) {
  for (int i=0;i<decoder->nlanes;++i)
     decoder->nhits[i]=decode(decoder->lanebuffer+decoder->lanebuf_size*i,decoder->laneend[i],decoder->hitbuffer+decoder->hitbuf_size*i,decoder->abcs+i);
}

static inline void transformhits(uint32_t *hits,int n);
static inline void decoder_transform_hits(struct decoder_t *decoder) {
  for (int i=0;i<decoder->nlanes;++i)
    transformhits(decoder->hitbuffer+decoder->hitbuf_size*i,decoder->nhits[i]);
}

static inline int decode(uint8_t *laneptr,uint8_t *laneend,uint32_t *hitbuf,uint8_t *abc) {
  if (laneptr==laneend) return 0;
  int addrprefix;
  long int nhit=0;
  *abc=laneptr[1];
  if ((*laneptr&0xF0)==0xE0) return 0;
  uint32_t chipid=(laneptr[0]&0x0F)<<19;
  laneptr+=2; // TOOD: check EVENT HEADER/EMPTY EVENT
  while (laneptr<laneend) { // TODO: check out of bounds problem (better: ensure that the 2 bytes following laneend are readable)
    unsigned short w16=*(unsigned short*)laneptr; // TOOD: check alising problems
    if      ((w16&0xC0)==0x40) { // DATA SHORT
      w16=w16>>8|w16<<8;
      int addr=addrprefix|w16&0x3FFF;
      hitbuf[nhit++]=addr;
      laneptr+=2;
    }
    else if ((w16&0xC0)==0x00) { // DATA LONG
      w16=w16>>8|w16<<8;
      int addr=addrprefix|w16;
      hitbuf[nhit++]=addr;
      unsigned char hitmap=*(laneptr+2); // TODO: assert that bit 8 is 0?
      if (hitmap&0x01) hitbuf[nhit++]=addr+1;
      if (hitmap&0x7E) { // provide early out (mostly 2-pixel clusters...)
        if (hitmap&0x02) hitbuf[nhit++]=addr+2;
        if (hitmap&0x04) hitbuf[nhit++]=addr+3;
        if (hitmap&0x08) hitbuf[nhit++]=addr+4;
        if (hitmap&0x10) hitbuf[nhit++]=addr+5;
        if (hitmap&0x20) hitbuf[nhit++]=addr+6;
        if (hitmap&0x40) hitbuf[nhit++]=addr+7;
      }
      laneptr+=3;
    }
    else if ((w16&0xE0)==0xC0) { // REGION HEADER : TODO: move first region header out of loop, asserting its existence
      addrprefix=chipid|(w16&0x1F)<<14;
      ++laneptr;
    }
    else if ((w16&0xF0)==0xB0) { // EVENT TRAILER : TODO: check existance, log flags, move out of loop
      break;
    }
    else { // ERROR (IDLES and BUSIES should be stripped)
      printf("ERROR: invalid byte 0x%02X\n",*laneptr&0xFF);
      while (laneptr!=laneend) {printf(" %02X ",*(unsigned char*)laneptr);laneptr+=1;}
      printf("\n");
      printf("ERROR: invalid byte 0x%02X\n",*laneptr&0xFF);
      return -1;
    }
  }
  return nhit;
}

static inline void transformhits(uint32_t *hits,int n) {
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
  const __m128i masky=_mm_set1_epi32(0x000001FF);
  const __m128i mask0=_mm_set1_epi32(0x00000001);
  const __m128i maska=_mm_set1_epi32(0x0000FFFE);
  while (n>0) {
    __m128i a =_mm_load_si128((__m128i*)hits);

    __m128i t1=_mm_srli_epi32(a , 1   );
    __m128i y =_mm_and_si128 (t1,masky);

    __m128i t2=_mm_srli_epi32(a , 9   );
    __m128i t3=_mm_and_si128 (t2,maska);
    __m128i t4=_mm_xor_si128 (t1,a    );
    __m128i t5=_mm_and_si128 (t4,mask0);
    __m128i x =_mm_or_si128  (t3,t5   );

    __m128i t6=_mm_slli_epi32(y ,16   );
    __m128i yx=_mm_or_si128  (t6,x    );

    _mm_store_si128((__m128i*)hits,yx);

    hits+=4;
    n-=4;
  }
}

static inline void fillrowhist(int *hist,uint32_t *hits,int n,int row) {
  const __m128i masky=_mm_set_epi8(0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE,
                                   0x00,0x00,0x03,0xFE);
  const __m128i mask0=_mm_set_epi8(0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01,
                                   0x00,0x00,0x00,0x01);
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
    if (n>3) ++hist[_mm_extract_epi32(b,3)];
    if (n>2) ++hist[_mm_extract_epi32(b,2)];
    if (n>1) ++hist[_mm_extract_epi32(b,1)];
             ++hist[_mm_extract_epi32(b,0)];
    hits+=4;
    n-=4;
  }
}

static inline void threshold_next_charge(int *sumd,int *sumd2,int ch,int *lasthist,int *hist) {
  for (int x=0;x<9*1024;++x) {
    int d=(hist[x]-lasthist[x]);
    int dch=d*ch;
//    if (d<-0) printf("<-5 %d %d %d\n",x,hist[x],lasthist[x]);
    sumd [x]+=dch;
    sumd2[x]+=dch*ch;
  }
}

static inline void threshold_next_row(float *thrs,float*rmss,int *sumd,int *sumd2,int nch,int ninj) {
  float f=1./(1.*ninj);
  for (int x=0;x<9*1024;++x) {
    float sd =sumd [x];
    float sd2=sumd2[x];
    float u  =f*sd;
    //float s  =sqrtf(f*sd2-u*u);
    float s  =sqrtf(f*sd2-u*u);
    //if (isnan(s)) {
    //  printf("NAN: %d %f %f %d %d\n",x,sd,sd2,sumd[x],sumd2[x]);
    //}

    thrs[x]=u;
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

void thrana(struct decoder_t *decoder,int nch,int ninj,int feeid,const char *prefix,const char *suffix,int nrows) {
  float *thrs       =_mm_malloc( 9*512*1024   *sizeof(float),4096);
  float *rmss       =_mm_malloc( 9*512*1024   *sizeof(float),4096);
  int   *sumd       =_mm_malloc( 9    *1024   *sizeof(int  ),4096);
  int   *sumd2      =_mm_malloc( 9    *1024   *sizeof(int  ),4096);
  int   *rowhist    =_mm_malloc((9    *1024+1)*sizeof(int  ),4096);
  int   *lastrowhist=_mm_malloc((9    *1024+1)*sizeof(int  ),4096);
  //for (int row=250;row<260;++row) {
  uint32_t trgorbit;
  uint16_t trgbc;
  //decoder_read_event_into_lanes(decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping SOT
  char fname[200];
  sprintf(fname,"%sthrmap%d%s.dat",prefix,feeid,suffix);
  int f=open(fname,O_CREAT|O_WRONLY|O_TRUNC,0666);
  for (int row=0;row<512;++row) {
    if (nrows==6 && !(row==1 || row==2 || row==254 || row==255 || row==509 || row==510)) continue;
    printf("Row %4d : ",row);fflush(stdout);
    int nbad=0;
    int ngood=0;
    bzero(sumd ,9*1024*sizeof(int));
    bzero(sumd2,9*1024*sizeof(int));
    for (int ch=0;ch<nch;++ch) {
    //  printf(".");fflush(stdout);
      bzero(rowhist,(9*1024+1)*sizeof(int));
      for (int inj=0;inj<ninj;++inj) {
        int ret=decoder_read_event_into_lanes(decoder,&trgorbit,&trgbc,feeid);
        if (!ret) {printf("Error while reading events... %d\n",ret);exit(-1);}
        decoder_decode_lanes_into_hits(decoder);
        for (int i=0;i<decoder->nlanes;++i)  {
          fillrowhist(rowhist,decoder->hitbuffer+i*decoder->hitbuf_size,decoder->nhits[i],row);
        }
      }
      int nhit=0;
      for (int i=0;i<9*1024;++i) nhit+=rowhist[i];
      //printf("ch=%d: nhit=%d\n",ch,nhit);
      ngood+=nhit;
      nbad+=rowhist[9*1024];
      // Row  32:  ________xxxx------------ (12.32 +/- 0.12)
      //if      (nhit<  1024*ninj/4) {printf("\b_");fflush(stdout);}
      //else if (nhit>3*1024*ninj/4) {printf("\b-");fflush(stdout);}
      //else                         {printf("\bx");fflush(stdout);}
      if (ch) {
        threshold_next_charge(sumd,sumd2,ch,lastrowhist,rowhist);
    //    printf("ch=%d : sumd[0]=%d, sumd2[0]=%d, rowhist[0]=%d, lastrowhist[0]=%d\n",ch,sumd[0],sumd2[0],rowhist[0],lastrowhist[0]);
      }
//      printf("ch=%d : sumd[621]=%d, sumd2[621]=%d, rowhist[621]=%d, lastrowhist[621]=%d\n",ch,sumd[621],sumd2[621],rowhist[621],lastrowhist[621]);
      int *tmp=lastrowhist;
      lastrowhist=rowhist;
      rowhist=tmp;
    }
    threshold_next_row(thrs+row*9*1024,rmss+row*9*1024,sumd,sumd2,nch,ninj);
    //printf("thr[row=%d,col=0]=%f, rms=%f\n",row,*(thrs+row*9*1024),*(rmss+row*9*1024));
    write(f,thrs+row*9*1024,9*1024*sizeof(float)); // TODO: do not keep full map in memory?
    float m,merr,s,serr;
    meanrms(&m,&merr,thrs+row*9*1024,9*1024);
    meanrms(&s,&serr,rmss+row*9*1024,9*1024);
    printf(" (mean: %5.2f +/- %4.2f ; RMS: %5.2f +/- %4.2f ; good/bad hits: %d / %d)\n",m,merr,s,serr,ngood,nbad);
  }
  close(f);
  _mm_free(lastrowhist);
  _mm_free(rowhist    );
  _mm_free(sumd2      );
  _mm_free(sumd       );
  _mm_free(rmss       );
  _mm_free(thrs       );
}

static inline void fillhitmap(int *map,uint32_t *hits,int n) {
/*
  for (int i=0;i<n;++i) {
    int x=hits[i]&0xFFFF;
    int y=hits[i]>>16;
    ++map[y*1024*9+x];
  }
*/

  const __m128i masky=_mm_set1_epi32(0x01FF0000);
  const __m128i maskx=_mm_set1_epi32(0x00003FFF);
  const __m128i stride=_mm_set1_epi32(9*1024);
  while (n>0) {
    __m128i hs=_mm_stream_load_si128((__m128i*)hits);
    //__m128i hs=_mm_load_si128((__m128i*)hits);
    __m128i t1=_mm_srli_epi32(hs,16);
    __m128i t2=_mm_mullo_epi32(t1,stride);
    __m128i t3=_mm_and_si128 (hs,maskx);
    __m128i  a=_mm_add_epi32 (t2,t3   );
    if (n>3) ++map[_mm_extract_epi32(a,3)];
    if (n>2) ++map[_mm_extract_epi32(a,2)];
    if (n>1) ++map[_mm_extract_epi32(a,1)];
             ++map[_mm_extract_epi32(a,0)];
    hits+=4;
    n-=4;
  }
}

#define HITBUFSIZE 1024
void fhrana(struct decoder_t *decoder,int feeid,const char *prefix,int nmax) {
  struct hit_t hit;
  struct hit_t *hitbuf;
  int nhitbuf;
  if (nmax) hit.feeid=feeid;
  uint32_t trgorbit;
  uint16_t trgbc;
  long nev=0;
  long nwithpayload=0;
  int *hitmap=_mm_malloc(9*1024*512*sizeof(int),4096);
  bzero(hitmap,9*1024*512*sizeof(int));
  char fname[200];
  int fdump=0;
  if (nmax) {
    sprintf(fname,"%shits%d.dat",prefix,feeid);
    fdump=open(fname,O_CREAT|O_WRONLY|O_TRUNC,0666);
    hitbuf=malloc(HITBUFSIZE*sizeof(struct hit_t));
    nhitbuf=0;
  }
  while (1) {
    int ret=decoder_read_event_into_lanes(decoder,&trgorbit,&trgbc,feeid);
    //printf("fhrana: %d\n",ret);
    if (ret==0) break;
    if (ret==-1) {
      fprintf(stderr,"Error while reading file: %s Exiting.\n",strerror(errno));
      exit(-1);
    }
    if (ret==-2) {
      fprintf(stderr,"Error while reading file: %s Last read was incomplete. Exiting (some events might be ignored).\n",strerror(errno));
      exit(-1);
    }
    if (nmax) {
      hit.orbit=trgorbit;
      hit.bc=trgbc;
      hit.evno=nwithpayload;
    }
    if (ret==1) ++nwithpayload;
    decoder_decode_lanes_into_hits(decoder);
    decoder_transform_hits(decoder);
    for (int i=0;i<decoder->nlanes;++i)  {
//      for (int j=0;j<decoder->nhits[i];++j) {
//        printf("[%d,%d]: %08X\n",i,j,*decoder->hitbuffer+i*decoder->hitbuf_size+j);
//      }
      if (decoder->nhits[i]<0) {
        printf("ERROR IN EVENT %ld LANE: %d\n",nev,i);
        printf("POS: %lld\n",lseek(decoder->file,0,SEEK_CUR));
        for (int j=0;j<decoder->nlanes;++j)  printf("[%d]=%d\n",j,decoder->nhits[j]);
      }
      else {
        fillhitmap(hitmap,decoder->hitbuffer+i*decoder->hitbuf_size,decoder->nhits[i]);
        if (nmax) {
          hit.abc=decoder->abcs[i];
          hit.laneid=i;
          for (int j=0;j<decoder->nhits[i];++j) {
            uint32_t yx=*(decoder->hitbuffer+i*decoder->hitbuf_size+j);
            hit.y=yx>>16;
            hit.x=yx&0xFFFF;
            if (nmax<0 || hitmap[hit.y*9*1024+hit.x]<=nmax) {
              hitbuf[nhitbuf++]=hit;
              if (nhitbuf==HITBUFSIZE) {
                 write(fdump,hitbuf,HITBUFSIZE*sizeof(struct hit_t));
                 nhitbuf=0;
              }
            }
          }
        }
      }
    }
    ++nev;
//    if (nev>0) break;
  }
  if (fdump) {
    if (nhitbuf) write(fdump,hitbuf,nhitbuf*sizeof(struct hit_t));
    close(fdump);
  }
  printf("Read %ld events. %ld with ALPIDE payload\n",nev,nwithpayload); 

  sprintf(fname,"%shitmap%d.dat",prefix,feeid);
  int fhitmap=open(fname,O_CREAT|O_WRONLY|O_TRUNC,0666);
  write(fhitmap,hitmap,9*1024*512*sizeof(int));
  close(fhitmap);
  int ntot=0;
  for (int y=0;y<512;++y) {
    for (int x=0;x<9*1024;++x) {
      //if (hitmap[y*9*1024+x]>0) printf("hitmap[y=%3d,x=%4d]=%6d\n",y,x,hitmap[y*9*1024+x]);
      ntot+=hitmap[y*9*1024+x];
    }
  }
  printf("Total number of hits: %d\n",ntot);
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
    " $ lz4cat thrdata-fee264.lz4 | %s thrmap6 /dev/stdin 264 test # produces: testthrmap264.dat\n"
    ,a0,a0,a0,a0);
}

int main(int argc,char *argv[]) {
  if (argc!=4 && argc!=5 && argc!=6) {
    usage(argv[0]);
    exit(-1);
  }
  const char *fname =           argv[2] ;
  int         feeid =      atoi(argv[3]);
  const char *prefix=argc<=4?"":argv[4] ;
  int         nmax  =argc<=5?0 :atoi(argv[5]);

  // TODO: use and check better defaults:
  struct decoder_t decoder;
  decoder_init(&decoder,8192*1001,1024*1024,10000,16,fname);

  if      (strcmp(argv[1],"thrmap")==0) {
    uint32_t trgorbit;
    uint16_t trgbc;
    decoder_read_event_into_lanes(&decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping SOT
    thrana(&decoder,50,25,feeid,prefix,"",512);
    decoder_read_event_into_lanes(&decoder,&trgorbit,&trgbc,feeid); // TODO: this is skipping EOT
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
  else if (strcmp(argv[1],"hitmap")==0) {
    fhrana(&decoder,feeid,prefix,nmax);
  }
  else {
    usage(argv[0]);
    exit(-1);
  }
}

