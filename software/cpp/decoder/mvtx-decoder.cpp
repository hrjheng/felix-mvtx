/* Compile with:
gcc --std=gnu99 -march=native -lm -O3 -o decoder decoder.c
*/

#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <set>
#include <sstream>
#include <vector>

#include <immintrin.h>
#include <mm_malloc.h>
#include <signal.h>
#include <unistd.h>

#include "progressbar.h"
#include "utils.h"

#include <TBenchmark.h>
#include <TFile.h>
#include <TObject.h>
#include <TTree.h>

using namespace std;

constexpr uint8_t FLX_WORD_SZ = 32;

struct decoder_t
{
    std::ifstream file;

    static constexpr uint8_t nlanes = 3;

    uint32_t filebuf_size;
    uint32_t lanebuf_size;
    uint32_t hitsbuf_size;
    uint32_t nbytesleft;
    size_t nbytesread;
    uint8_t *filebuffer;
    uint8_t *lanebuffer;
    uint32_t *hitsbuffer;

    std::array<uint8_t *, nlanes> lane_ends;
    uint32_t *hits_end;

    uint8_t *ptr;
    uint8_t *prev_packet_ptr;

    std::vector<uint32_t> feeids;
    std::array<uint8_t, nlanes> chipIds = {0xFF, 0xFF, 0xFF};

    trg_t trigger;

    int thscan_nInj;
    int thscan_nChg;
    int feeid = -1;

    bool isThr = false;
    bool isTun = false;

    uint32_t evt_cnts[Trg::BitMap::nBitMap] = {};

    decoder_t(std::string &flName) : filebuf_size(8192 * 1001), lanebuf_size(1024 * 1024), hitsbuf_size(10000), nbytesleft(0), nbytesread(0), thscan_nInj(0), thscan_nChg(0)
    {
        // TODO: check meaningfullness of params...
        file.open(flName, std::ios::binary);
        if (!file.is_open())
        {
            std::cerr << "Error while trying to open file: " << strerror(errno);
            std::cerr << ". Exiting" << std::endl;
            exit(-1);
        }

        assert(!(filebuf_size % 8192));
        // memory allocations
        filebuffer = reinterpret_cast<uint8_t *>(_mm_malloc(filebuf_size * sizeof(uint8_t), 4096));
        lanebuffer = reinterpret_cast<uint8_t *>(_mm_malloc(nlanes * lanebuf_size * sizeof(uint8_t), 4096));
        hitsbuffer = reinterpret_cast<uint32_t *>(_mm_malloc(nlanes * hitsbuf_size * sizeof(uint32_t), 4096));

        if (!filebuffer || !lanebuffer || !hitsbuffer)
        {
            std::cerr << "Error while allocating memory: " << strerror(errno);
            std::cerr << ". Exiting." << std::endl;
            exit(-1);
        }
        ptr = filebuffer;
        trigger = {};
    }

    ~decoder_t()
    {
        _mm_free(filebuffer);
        _mm_free(lanebuffer);
        _mm_free(hitsbuffer);
    }

    inline void packet_init(bool reset_hits = false)
    {
        for (uint8_t i = 0; i < nlanes; ++i)
        {
            lane_ends[i] = lanebuffer + i * lanebuf_size;
        }
        if (reset_hits)
        {
            hits_end = hitsbuffer;
        }
    }

    inline bool has_lane_data()
    {
        uint8_t i = 0;
        for (const auto &lane_end : lane_ends)
        {
            if (lane_end != (lanebuffer + i * lanebuf_size))
            {
                return true;
            }
            ++i;
        }
        return false;
    }

    size_t ptr_pos(uint8_t *_ptr = nullptr) { return (((!_ptr) ? ptr : _ptr) - filebuffer); }
};

uint32_t nHB = 0, nHB_with_data = 0, nTrg_with_data = 0;

void reset_stat()
{
    nHB = 0;
    nHB_with_data = 0;
    nTrg_with_data = 0;
}

inline void updateTrgEvtCnts(const rdh_t &_rdh, decoder_t *&_decoder)
{
    for (const auto &trg : Trg::allBitMap)
    {
        if (((_rdh.trgType >> trg) & 1) == 1)
        {
            _decoder->evt_cnts[trg]++;
        }
    }
}

void printStat(const size_t n_events, const size_t n_evt_with_payload, const size_t nTrg)
{
    std::cout << "Read " << n_events << " events. " << n_evt_with_payload;
    std::cout << " with ALPIDE payload and " << nTrg << " triggers" << std::endl;
    std::cout << std::endl;
}

void printTrgCnts(decoder_t *decoder)
{
    std::cout << "Trigger counts:" << endl;
    for (const auto &trg : Trg::allBitMap)
    {
        std::cout << Trg::BitMapName[trg].c_str() << ": " << decoder->evt_cnts[trg] << std::endl;
    }
    std::cout << std::endl;
}

void save_block(decoder_t *decoder)
{
    ostringstream ss;
    ss << "last_chunk_" << decoder->feeid << ".err";
    ofstream fdump(ss.str().c_str(), ios::trunc);
    fdump.write(reinterpret_cast<char *>(decoder->filebuffer), decoder->ptr - decoder->filebuffer + decoder->nbytesleft);
    fdump.close();
}

void meanrms(float *m, float *s, float *data, size_t n)
{
    float s1 = 0.;
    float s2 = 0.;
    int nn0 = 0;
    for (size_t i = 0; i < n; ++i)
    {
        if (data[i] > 0)
        {
            float x = data[i];
            s1 += x;
            s2 += x * x;
            ++nn0;
        }
    }
    s1 /= nn0;
    s2 /= nn0;
    *m = s1;
    *s = sqrtf(s2 - s1 * s1);
}

static inline void threshold_next_row(float *thrs, float *rmss, float *sumd, float *sumd2, int nch, int ninj)
{
    for (int x = 0; x < 3 * 1024; ++x)
    {
        float den = sumd[x];
        float m = sumd2[x];
        if (den > 0)
        {
            m /= den;
        }
        float u = den;
        float s = sqrtf(m - u * u);
        thrs[x] = m;
        rmss[x] = s;
    }
}

static inline void threshold_next_charge(float *sumd, float *sumd2, int ch, int *lasthist, int *hist, int ninj)
{
    int ch1 = ch - 1;
    int ch2 = ch;

    float ddV = 1.0 * (ch2 - ch1);
    float V1 = ch1;
    float V2 = ch2;
    float meandV = 0.5 * (V2 + V1);

    for (int x = 0; x < 3 * 1024; ++x)
    {
        float f = 1.f / (1.f * ninj);
        float n2 = hist[x] * f;
        float n1 = lasthist[x] * f;

        float dn = n2 - n1;
        float den = dn / ddV;
        float m = meandV * dn / ddV;
        sumd[x] += den;
        sumd2[x] += m;
    }
}

static inline void fillrowhist(int *hist, uint32_t *hits, int n, int row)
{
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Woverflow"
    const __m128i masky = _mm_set1_epi32(0x000003FE);
    const __m128i mask0 = _mm_set1_epi32(0x00000001);
    const __m128i maska = _mm_set1_epi32(0x0000FFFE);
#pragma GCC diagnostic pop

    const __m128i bad = _mm_set1_epi32(3 * 1024); // bad pixel ID
    __m128i y = _mm_set1_epi32(row << 1);
    while (n > 0)
    {
        __m128i a = _mm_load_si128((__m128i *)hits);
        __m128i yp = _mm_and_si128(a, masky);
        __m128i ok = _mm_cmpeq_epi32(yp, y);

        __m128i t1 = _mm_srli_epi32(a, 1);
        __m128i t2 = _mm_srli_epi32(a, 9);
        __m128i t3 = _mm_and_si128(t2, maska);
        __m128i t4 = _mm_xor_si128(t1, a);
        __m128i t5 = _mm_and_si128(t4, mask0);
        __m128i x = _mm_or_si128(t3, t5);
        __m128i b = _mm_blendv_epi8(bad, x, ok); // epi8 is OK, due to ok

        if (n > 3)
            ++hist[_mm_extract_epi32(b, 3)];
        if (n > 2)
            ++hist[_mm_extract_epi32(b, 2)];
        if (n > 1)
            ++hist[_mm_extract_epi32(b, 1)];

        ++hist[_mm_extract_epi32(b, 0)];

        hits += 4;
        n -= 4;
    }
}

static inline void transformhits(uint32_t *hits, int n)
{
    const __m128i masky = _mm_set1_epi32(0x000001FF);
    const __m128i mask0 = _mm_set1_epi32(0x00000001);
    const __m128i maska = _mm_set1_epi32(0x0000FFFE);
    while (n > 0)
    {
        __m128i a = _mm_load_si128((__m128i *)hits);

        __m128i t1 = _mm_srli_epi32(a, 1); // >> 1 each 4 32'b elements (right shift by 1 = divide by 2)
        // y = row ID
        __m128i y = _mm_and_si128(t1, masky); // & each 4 32'b element with 0x000001FF (address divided by 2 = row)

        __m128i t2 = _mm_srli_epi32(a, 9);
        __m128i t3 = _mm_and_si128(t2, maska);
        __m128i t4 = _mm_xor_si128(t1, a);
        __m128i t5 = _mm_and_si128(t4, mask0);
        __m128i x = _mm_or_si128(t3, t5);

        __m128i t6 = _mm_slli_epi32(y, 16); // last 16 bits as row
        __m128i yx = _mm_or_si128(t6, x);
        // after transformation: yx
        // "0th" counts from the right
        //! row is the last 16 bits of yx, we only need 9 bits for row ID (7 unused bits)
        //! column is the first 10 bits [9th to 0th] of the first 16 bits of yx (6 unused bits)
        //! lane is the next 2 bits [11th and 10th] of the first 16 bits of yx
        //! [15th to 12th] not used
        //! [24th to 16th] for row ID (9 bits)
        //! [31th to 25th] not used
        _mm_store_si128((__m128i *)hits, yx);

        hits += 4;
        n -= 4;
    }
}

static inline void fillhitmap(uint32_t *map, uint32_t *hits, int n)
{
    const __m128i masky __attribute__((unused)) = _mm_set1_epi32(0x01FF0000);
    const __m128i maskx = _mm_set1_epi32(0x00003FFF);
    const __m128i stride = _mm_set1_epi32(3 * 1024);
    while (n > 0)
    {
        __m128i hs = _mm_stream_load_si128((__m128i *)hits);
        __m128i t1 = _mm_srli_epi32(hs, 16);
        __m128i t2 = _mm_mullo_epi32(t1, stride);
        __m128i t3 = _mm_and_si128(hs, maskx);
        __m128i a = _mm_add_epi32(t2, t3);
        if (n > 3)
            ++map[_mm_extract_epi32(a, 3)];
        if (n > 2)
            ++map[_mm_extract_epi32(a, 2)];
        if (n > 1)
            ++map[_mm_extract_epi32(a, 1)];

        ++map[_mm_extract_epi32(a, 0)];

        hits += 4;
        n -= 4;
    }
}

static inline void decode(uint8_t *laneptr, uint8_t *laneend, uint32_t *&hitsbuf_end, uint8_t &chipId)
{
    if (laneptr == laneend)
    {
        return;
    }

    size_t nhit = 0;

    uint8_t busy_on = 0;
    uint8_t busy_off = 0;

    //  uint8_t abc = 0;
    uint8_t laneId = 0;
    uint8_t reg = 0;
    uint8_t chip_header_found = 0;
    uint8_t chip_trailer_found = 0;

    while (laneptr < laneend)
    {
        // TODO: check out of bounds problem (better: ensure that the 2 bytes following
        // laneend are readable)
        if (*laneptr == 0xF1)
        { // BUSY ON
            ++busy_on;
            ++laneptr;
        }
        else if (*laneptr == 0xF0)
        { // BUSY OFF
            ++busy_off;
            ++laneptr;
        }
        else if ((*laneptr & 0xF0) == 0xE0)
        { // EMPTY
            chip_header_found = 0;
            chip_trailer_found = 1;
            chipId = laneptr[0] & 0xF;
            laneId = chipId % 3;
            // abc = laneptr[1];
            busy_on = busy_off = 0;
            laneptr += 2;
        }
        else
        {
            if (chip_header_found)
            {
                if ((laneptr[0] & 0xE0) == 0xC0)
                { // REGION HEADER
                    // TODO: move first region header out of loop, asserting its existence
                    reg = laneptr[0] & 0x1F;
                    ++laneptr;
                }
                if ((laneptr[0] & 0xC0) == 0x40)
                { // DATA SHORT
                    int addr = (laneptr[0] & 0x3F) << 8 | laneptr[1];
                    addr |= (laneId << 19) | (reg << 14);
                    hitsbuf_end[nhit++] = addr;
                    laneptr += 2;
                }
                else if ((laneptr[0] & 0xC0) == 0x00)
                { // DATA LONG
                    int addr = (laneptr[0] & 0x3F) << 8 | laneptr[1];
                    addr |= (laneId << 19) | (reg << 14);
                    hitsbuf_end[nhit++] = addr;

                    uint8_t hitmap = laneptr[2]; // TODO: assert that bit 8 is 0?
                    if (hitmap & 0x01)
                        hitsbuf_end[nhit++] = addr + 1;
                    if (hitmap & 0x7E)
                    { // provide early out (mostly 2-pixel clusters...)
                        if (hitmap & 0x02)
                            hitsbuf_end[nhit++] = addr + 2;
                        if (hitmap & 0x04)
                            hitsbuf_end[nhit++] = addr + 3;
                        if (hitmap & 0x08)
                            hitsbuf_end[nhit++] = addr + 4;
                        if (hitmap & 0x10)
                            hitsbuf_end[nhit++] = addr + 5;
                        if (hitmap & 0x20)
                            hitsbuf_end[nhit++] = addr + 6;
                        if (hitmap & 0x40)
                            hitsbuf_end[nhit++] = addr + 7;
                    }
                    laneptr += 3;
                }
                else if ((laneptr[0] & 0xF0) == 0xB0)
                { // CHIP TRAILER
                    chip_trailer_found = 1;
                    busy_on = busy_off = chip_header_found = 0;
                    ++laneptr;
                }
                else
                {
                    // ERROR (IDLES and BUSIES should be stripped)
                    printf("ERROR: invalid byte 0x%02X\n", laneptr[0]);
                    while (laneptr != laneend)
                    {
                        printf(" %02X ", *(uint8_t *)laneptr);
                        ++laneptr;
                    }
                }
            }
            else
            { // chip_header
                if ((laneptr[0] & 0xF0) == 0xA0)
                {
                    chip_header_found = 1;
                    chip_trailer_found = 0;
                    chipId = laneptr[0] & 0xF;
                    laneId = chipId % 3;
                    // abc = laneptr[1];
                    reg = 0;
                    laneptr += 2;
                }
                else if (laneptr[0] == 0x00)
                { // padding
                    ++laneptr;
                }
                else
                { // ERROR (IDLES and BUSIES should be stripped)
                    printf("ERROR: invalid byte 0x%02X\n", laneptr[0]);
                    while (laneptr != laneend)
                    {
                        printf(" %02X ", *(uint8_t *)laneptr);
                        ++laneptr;
                    }
                }
            } // data
        }     // busy_on, busy_off, chip_empty, other
    }         // while
    if (!chip_trailer_found)
    {
        std::cerr << "ERROR: ALPIDE data end without data trailer" << std::endl;
    }
    hitsbuf_end += nhit;
    return;
}

static inline void decoder_decode_lanes_into_hits(decoder_t *decoder)
{
    uint8_t chipId = 0xFF;
    for (int i = 0; i < decoder->nlanes; ++i)
    {
        decode(decoder->lanebuffer + decoder->lanebuf_size * i, decoder->lane_ends[i], decoder->hits_end, chipId);
        assert(chipId != 0xFF);
        decoder->chipIds[i] = chipId;
    }
}

size_t pull_data(decoder_t *decoder)
{
    ssize_t nread = 0;
    uint8_t *buf_ptr = decoder->filebuffer; // set buf_ptr to filebuffer init
    decoder->nbytesread += decoder->ptr - buf_ptr;
    memcpy(buf_ptr, decoder->ptr, decoder->nbytesleft); // move byte left to filebuffer start
    decoder->ptr = buf_ptr;
    buf_ptr += decoder->nbytesleft;
    size_t len = (decoder->filebuf_size - decoder->nbytesleft);
    len = (len > 0x1000) ? len & ~0xFFF : len; // in chunks of 256 bytes multiples
    uint64_t n;
    do
    {
        decoder->file.read((char *)buf_ptr, len);
        n = decoder->file.gcount();
        len -= n;
        buf_ptr += n;
        nread += n;
    } while (len > 0 && n > 0);

    return nread;
}

enum EXIT_CODE
{
    NO_FLX_HEADER = -1,
    BAD_READ = -2,
    BAD_END_FILE = -3,
    DONE = 0,
    HB_DATA_DONE = 1,
    HB_NO_DATA_DONE = 2,
    N_EXIT_CODE
};

static inline EXIT_CODE decoder_read_event_into_lanes(decoder_t *decoder)
{
    rdh_t rdh;
    uint32_t nStopBit = 0;
    uint32_t prev_pck_cnt = 0;

    bool header_found = false;
    bool prev_evt_complete = false;
    bool haspayload = false;

    while (true)
    { // loop over pages in files
        if (decoder->nbytesleft > 0)
        {
            bool padding_found = false;
            while ((*(reinterpret_cast<uint16_t *>(decoder->ptr + 30)) == 0xFFFF) && decoder->nbytesleft)
            {
                padding_found = true;
                decoder->ptr += FLX_WORD_SZ;
                decoder->nbytesleft -= FLX_WORD_SZ;
                decoder->nbytesleft += (!decoder->nbytesleft) ? pull_data(decoder) : 0;
            }
            if (padding_found)
            {
                padding_found = false;
                ASSERT(!((decoder->nbytesread + decoder->ptr_pos()) & 0xFF), decoder, "FLX header is not properly aligned in byte %lu of current chunk, previous packet %ld", decoder->ptr_pos(), decoder->ptr_pos(decoder->prev_packet_ptr));
            }
        }

        uint32_t pagesize = 0;
        if (decoder->nbytesleft >= (2 * FLX_WORD_SZ))
        { // at least FLX header and RDH
            if (*(reinterpret_cast<uint16_t *>(decoder->ptr + 30)) == 0xAB01)
            {
                rdh.decode(decoder->ptr);
                pagesize = (rdh.pageSize + 1) * FLX_WORD_SZ;
            }
            else
            {
                return NO_FLX_HEADER;
            }
        }

        if (!pagesize || decoder->nbytesleft < pagesize)
        { // pagesize = 0 read rdh
            // at least the RDH needs to be there...
            if (decoder->nbytesleft < 0)
            {
                printf("ERROR: d_nbytesleft: %d, less than zero \n", decoder->nbytesleft);
                return BAD_READ;
            }

            size_t nread = pull_data(decoder);
            decoder->nbytesleft += nread;
            if (!nread)
                return (decoder->nbytesleft < pagesize) ? BAD_END_FILE : DONE;

            continue;
        }

        decoder->prev_packet_ptr = decoder->ptr;
        uint8_t *flx_ptr = decoder->ptr; // payload: TODO: check header
        decoder->ptr += pagesize;
        decoder->nbytesleft -= pagesize;

        if (!pagesize)
            continue; // TODO...

        if (decoder->feeid < 0)
        {
            if (rdh.stopBit)
            {
                nStopBit++;
            }

            if (std::find(decoder->feeids.cbegin(), decoder->feeids.cend(), rdh.feeId) == decoder->feeids.cend())
            {
                decoder->feeids.push_back(rdh.feeId);
            }
            else if (nStopBit > 10 * decoder->feeids.size())
            {
                return DONE;
            }
            else
            {
                continue;
            }
        }

        if (rdh.feeId != decoder->feeid)
            continue;               // TODO: ...
        flx_ptr += 2 * FLX_WORD_SZ; // skip RDH
        // printf("flx_ptr: %d \n", *(uint8_t*)flx_ptr);

        const size_t nFlxWords = (pagesize - (2 * FLX_WORD_SZ)) / FLX_WORD_SZ;
        // TODO assert pagesize > 2
        ASSERT(((!rdh.packetCounter) || (rdh.packetCounter == prev_pck_cnt + 1)), decoder, "Incorrect pages count %d in byte %ld of current chunk", rdh.packetCounter, decoder->ptr_pos());
        prev_pck_cnt = rdh.packetCounter;

        if (!rdh.packetCounter)
        {
            nHB++;
            // TODO add couter per trigger bit asserted in the event
            // TODO check right protocol for SOC/EOC or SOT/EOT
            decoder->packet_init(true);
            updateTrgEvtCnts(rdh, decoder);
        }
        else
        {
            if (!rdh.stopBit)
            {
                ASSERT(!prev_evt_complete, decoder, "Previous event was already complete, byte %ld of current chuck", decoder->ptr_pos());
            }
        }
        struct tdh_t tdh;
        struct tdt_t tdt;
        struct cdw_t cdw;
        int prev_gbt_cnt = 3;
        for (size_t iflx = 0; iflx < nFlxWords; ++iflx)
        {
            __m256i data = _mm256_stream_load_si256((__m256i *)flx_ptr);
            const uint16_t gbt_cnt = _mm256_extract_epi16(data, 15) & 0x3FF;
            ASSERT((gbt_cnt - prev_gbt_cnt) <= 3, decoder, "Error. Bad gbt counter in the flx packet at byte %ld", decoder->ptr_pos(flx_ptr));
            prev_gbt_cnt = gbt_cnt;
            const uint16_t n_gbt_word = ((gbt_cnt - 1) % 3) + 1;

            uint8_t *gbt_word;
            for (size_t igbt = 0; igbt < n_gbt_word; ++igbt)
            {
                gbt_word = flx_ptr + (igbt * 10);
                uint8_t lane = *(reinterpret_cast<uint8_t *>(gbt_word + 9));

                if (lane == 0xE0)
                {
                    // lane heder: needs to be present: TODO: assert this
                    // TODO assert first word after RDH and active lanes
                    haspayload = false;
                }
                else if (lane == 0xE8)
                { // TRIGGER DATA HEADER (TDH)
                    tdh.decode(gbt_word);
                    header_found = true;
                    if (!tdh.continuation)
                    {
                        // TODO add counter of not continuation triggers
                        decoder->trigger.orbit = tdh.orbit;
                        decoder->trigger.bc = tdh.bc;
                        if (!tdh.no_data)
                        {
                            nTrg_with_data++;
                        }
                        if (tdh.bc)
                        {
                            updateTrgEvtCnts(rdh, decoder);
                        }
                    }
                }
                else if (lane == 0xF8)
                { // CALIBRATION DATA WORD (CDW)
                    cdw.decode(gbt_word);
                    if (decoder->isThr)
                    {
                        uint16_t new_row = cdw.user_field & 0xFFFF;
                        uint16_t new_charge = (cdw.user_field >> 16) & 0xFFFF;
                        if ((!decoder->trigger.thscan_inj) || (decoder->trigger.thscan_inj == decoder->thscan_nInj))
                        {
                            if (!decoder->isTun)
                            {
                                ASSERT(new_row >= decoder->trigger.thscan_row, decoder, "Row not increasing after thscan_injections: previous %d new %d", decoder->trigger.thscan_row, new_row);
                            }
                            if (new_row == decoder->trigger.thscan_row)
                            { // rolling charge at change of row
                                ASSERT(new_charge > decoder->trigger.thscan_chg, decoder, "Charge not increasing after max thscan_injections: previous %d, new %d [previous row %d current row %d]", decoder->trigger.thscan_chg, new_charge, decoder->trigger.thscan_row, new_row);
                            }
                            //       else
                            //       {
                            //         if(thscan_current_charge != -1 and rdh['triggers'] != ['EOT'])
                            //         {
                            //          assert new_charge < thscan_current_charge,
                            //             "Charge not decreasing after row change: previous {thscan_current_charge}
                            //            new {new_charge}\nRDH: {rdh}"
                            //         }
                            //       }
                            decoder->trigger.thscan_inj = 1;
                            decoder->trigger.thscan_row = new_row;
                            decoder->trigger.thscan_chg = new_charge;
                        }
                        else
                        {
                            ASSERT(new_row == decoder->trigger.thscan_row, decoder, "Row not correct before reaching max thscan_injections: expected %d got %d", decoder->trigger.thscan_row, new_row);
                            ASSERT(new_charge == decoder->trigger.thscan_chg, decoder, "Charge not correct before reaching max thscan_injections: expected %d got %d, [previous row %d, current row %d observed injections %d]", decoder->trigger.thscan_chg, new_charge, decoder->trigger.thscan_row, new_row, decoder->trigger.thscan_inj);
                            decoder->trigger.thscan_inj += 1;
                        }
                    }
                }
                else if (lane == 0xF0)
                { // lane trailer
                    tdt.decode(gbt_word);
                    prev_evt_complete = tdt.packet_done;
                    if (tdt.packet_done)
                    {
                        // TODO add counter and check == no continuation counter
                    }
                }
                else if (lane == 0xE4)
                { // DIAGNOSTIC DATA WORD (DDW)
                  //  TODO add diagnostic dataword decoder
                  //  to do assert stop bit = 1
                }
                else if (((lane >> 5) & 0x7) == 0x5)
                { // IB DIAGNOSTIC DATA
                    // decode IB diagnostic word
                    cerr << "WARNING!!! IB diagnostic data word received and skipped." << endl;
                }
                else
                { // lane payload
                    ASSERT(((lane >> 5) & 0x7) == 0x1, decoder, "Wrong GBT Word %x in byte %ld, it is not an IB word", lane, decoder->ptr_pos(flx_ptr));
                    haspayload = true;
                    ASSERT(header_found, decoder, "Trigger header not found before chip data, in byte %ld", decoder->ptr_pos(flx_ptr));
                    lane &= 0x1F; // TODO: assert range + map IDs
                    lane %= 3;
                    memcpy(decoder->lane_ends[lane], gbt_word, 9);
                    decoder->lane_ends[lane] += 9;
                }

                if (prev_evt_complete)
                {
                    if (decoder->has_lane_data())
                    {
                        decoder_decode_lanes_into_hits(decoder);
                        decoder->packet_init();
                    }
                    prev_evt_complete = false;
                    header_found = false;
                }
            } // for igbt
            flx_ptr += FLX_WORD_SZ;
        }
        if (rdh.stopBit)
        {
            return (haspayload) ? HB_DATA_DONE : HB_NO_DATA_DONE;
        }
    } // while(true)
}

static inline EXIT_CODE check_next_event(decoder_t *decoder)
{
    EXIT_CODE ret = decoder_read_event_into_lanes(decoder);

    switch (ret)
    {
    case NO_FLX_HEADER:
        ASSERT(false, decoder, "Error reading file, wrong felix header position in byte %ld, previous flx header in byte %ld", decoder->ptr_pos(), decoder->ptr_pos(decoder->prev_packet_ptr));
        break;
    case BAD_READ:
        std::cerr << "Error while reading file BAD_READ: " << strerror(errno);
        std::cerr << " Exiting." << std::endl;
        break;
    case BAD_END_FILE:
        std::cerr << "Error while reading file: " << strerror(errno);
        std::cerr << ". Last read was incomplete. Exiting (some events might be ignored).";
        std::cerr << std::endl;
        break;
    default:;
    };
    return ret;
}

void save_file(std::string fname, uint32_t n_row, uint32_t nChipsPerLane, float *&data)
{
    ofstream fileMap(fname.data(), ios_base::trunc);
    fileMap.write(reinterpret_cast<const char *>(data), n_row * nChipsPerLane * 1024 * sizeof(float));
    fileMap.close();
}

void run_thrana(struct decoder_t *decoder, string &prefix, const int &n_vcasn_ithr = 1)
{
    if (!decoder->isTun)
    {
        std::cout << "Runing THR analysis for feeid " << decoder->feeid << "..." << std::endl;
    }
    else
    {
        std::cout << "Runing THR tunning analysis for feeid " << decoder->feeid;
        if (n_vcasn_ithr < 0)
        {
            std::cout << ", expected EOX event!!!" << std::endl;
        }
        else
        {
            std::cout << " and n " << n_vcasn_ithr << "..." << std::endl;
        }
    }

    constexpr uint8_t nChipsPerLane = 3;
    int16_t n_row = decoder->isTun ? 6 : 512;
    float *thrs = reinterpret_cast<float *>(_mm_malloc(nChipsPerLane * n_row * 1024 * sizeof(float), 4096));
    float *rmss = reinterpret_cast<float *>(_mm_malloc(nChipsPerLane * n_row * 1024 * sizeof(float), 4096));
    float *sumd = reinterpret_cast<float *>(_mm_malloc(nChipsPerLane * 1 * 1024 * sizeof(float), 4096));
    float *sumd2 = reinterpret_cast<float *>(_mm_malloc(nChipsPerLane * 1 * 1024 * sizeof(float), 4096));
    int *rowhist = reinterpret_cast<int *>(_mm_malloc((nChipsPerLane * 1024 + 1) * sizeof(int), 4096));
    int *lastrowhist = reinterpret_cast<int *>(_mm_malloc((nChipsPerLane * 1024 + 1) * sizeof(int), 4096));

    int ngood = 0;
    int nbad = 0;
    int iInj = 0;
    int prev_row = -1;

    if (decoder->isTun)
    {
        reset_stat();
    }
    bzero(rowhist, (nChipsPerLane * 1024 + 1) * sizeof(int));
    std::array<int, 6> chipRow = {{1, 2, 254, 255, 509, 510}};
    while (true)
    {
        EXIT_CODE ret = check_next_event(decoder);
        if (ret == DONE)
        {
            break;
        }
        else if (ret == HB_DATA_DONE)
        {
            nHB_with_data++;
            int iRow = decoder->trigger.thscan_row;
            int iChg = decoder->trigger.thscan_chg;
            if (prev_row != iRow)
            {
                printf("Row %4d : ", iRow);
                fflush(stdout);
                ngood = 0;
                nbad = 0;
                bzero(sumd, nChipsPerLane * 1024 * sizeof(float));
                bzero(sumd2, nChipsPerLane * 1024 * sizeof(float));
                prev_row = iRow;
            }
            int nhits = decoder->hits_end - decoder->hitsbuffer;
            fillrowhist(rowhist, decoder->hitsbuffer, nhits, (decoder->isTun) ? chipRow[iRow] : iRow);
            iInj++;
            if (iInj == decoder->thscan_nInj)
            {
                iInj = 0;
                int nhit = 0;
                for (int i = 0; i < nChipsPerLane * 1024; ++i)
                {
                    nhit += rowhist[i];
                }

                ngood += nhit;
                nbad += rowhist[nChipsPerLane * 1024];
                if (iChg)
                {
                    threshold_next_charge(sumd, sumd2, iChg, lastrowhist, rowhist, decoder->thscan_nInj);
                }
                int *tmp = lastrowhist;
                lastrowhist = rowhist;
                rowhist = tmp;
                bzero(rowhist, (nChipsPerLane * 1024 + 1) * sizeof(int));
                iChg++;
            }
            if (iChg == decoder->thscan_nChg)
            {
                printf("thscan_row %4d ", iRow);
                iChg = 0;
                threshold_next_row(thrs + iRow * nChipsPerLane * 1024, rmss + iRow * nChipsPerLane * 1024, sumd, sumd2, decoder->thscan_nChg, decoder->thscan_nInj);
                float m, merr, s, serr;
                meanrms(&m, &merr, thrs + decoder->trigger.thscan_row * nChipsPerLane * 1024, nChipsPerLane * 1024);
                meanrms(&s, &serr, rmss + decoder->trigger.thscan_row * nChipsPerLane * 1024, nChipsPerLane * 1024);
                printf(" (mean: %5.2f +/- %4.2f ; RMS: %5.2f +/- %4.2f ; good/bad hits: %d / %d)\n", m, merr, s, serr, ngood, nbad);
                if (decoder->isTun && iRow == 5)
                {
                    ostringstream fname;
                    fname << prefix << ((prefix != "") ? "_" : "") << "thr_map_" << decoder->feeid;
                    fname << "-" << n_vcasn_ithr << ".dat";
                    save_file(fname.str().data(), n_row, nChipsPerLane, thrs);
                    break;
                }
            }
        }
        else if (ret == HB_NO_DATA_DONE)
        {
            cout << "Event HB " << nHB << "Has not data." << endl;
            continue;
        }
        else
            exit(-1);
    }
    if (!decoder->isTun)
    {
        ostringstream fname;
        fname << prefix << ((prefix != "") ? "_" : "") << "thr_map_" << decoder->feeid << ".dat";
        save_file(fname.str(), n_row, nChipsPerLane, thrs);

        fname.str("");
        fname.clear();
        fname << prefix << ((prefix != "") ? "_" : "") << "rtn_map_" << decoder->feeid << ".dat";
        save_file(fname.str(), n_row, nChipsPerLane, rmss);
    }
    printStat(nHB, nHB_with_data, nTrg_with_data);
    _mm_free(lastrowhist);
    _mm_free(rowhist);
    _mm_free(sumd2);
    _mm_free(sumd);
    _mm_free(rmss);
    _mm_free(thrs);
}

void run_fhrana(struct decoder_t *decoder, string &prefix)
{
    TFile *outfile = new TFile("fhrana_test.root", "RECREATE");
    TTree *tree = new TTree("tree_fhrana", "tree_fhrana");
    uint32_t event;
    int Nhits;
    vector<uint32_t> FeeID_hit;
    vector<int> Lane_hit;
    vector<uint8_t> ChipID_hit;
    vector<int> RowID_hit, ColumnID_hit;

    tree->Branch("event", &event);
    tree->Branch("Nhits", &Nhits);
    tree->Branch("Lane_hit", &Lane_hit);
    tree->Branch("FeeID_hit", &FeeID_hit);
    tree->Branch("ChipID_hit", &ChipID_hit);
    tree->Branch("RowID_hit", &RowID_hit);
    tree->Branch("ColumnID_hit", &ColumnID_hit);

    std::cout << "Runing FHR analysis for feeid " << decoder->feeid << "..." << std::endl;
    uint32_t print_hb_cnt = 1000;
    progressbar bar(100);
    ostringstream ss;
    ss << " out of " << (print_hb_cnt * 100) << " events.";
    bar.set_tail_s(ss.str());
    // uint32_t *hitmap = reinterpret_cast<uint32_t *>(_mm_malloc(3 * 1024 * 512 * sizeof(uint32_t), 4096));
    // bzero(hitmap, 3 * 1024 * 512 * sizeof(uint32_t));

    int evtidx = 0;
    int totalNhits = 0;

    std::map<int, unsigned int> unique_row_count;

    while (true)
    {
        EXIT_CODE ret = check_next_event(decoder);

        if (!(nHB % print_hb_cnt))
        {
            bar.update();
        }
        if (nHB && (!(nHB % (100 * print_hb_cnt))))
        {
            std::cout << std::endl;
            bar.reset();
        }

        if (ret == DONE)
        {
            outfile->cd();
            tree->Write("", TObject::kWriteDelete);
            outfile->Close();

            break;
        }
        else if (ret == HB_DATA_DONE)
        {
            evtidx++;
            nHB_with_data++;
            int nhits = decoder->hits_end - decoder->hitsbuffer;
            totalNhits = totalNhits + nhits;
            transformhits(decoder->hitsbuffer, nhits);

            // cout << "nhits = " << nhits << endl;

            for (int i = 0; i < nhits; i++)
            {
                // std::cout << "decoder->hitsbuffer[" << i << "] (yx from the transformhits function output) = " << std::bitset<32>(decoder->hitsbuffer[i]) << std::endl;

                // Alternative way to get specific bit from uint32: https://stackoverflow.com/questions/34849753/get-specific-bit-from-uint32
                // column is the first 10 bits [9th to 0th], counting from the right
                uint32_t column = decoder->hitsbuffer[i] & 0x3FF;
                // lane is the next 2 bits [11th and 10th], counting from the right
                uint32_t lane = (decoder->hitsbuffer[i] >> 10) & 0x3;
                // [15th to 12th] are not used
                // [24th to 16th] for row ID (9 bits), counting from the right
                uint32_t row = (decoder->hitsbuffer[i] >> 16) & 0x1FF;
                // [31th to 25th] are not used

                // std::cout << "column = " << std::bitset<32>(column) << std::endl;
                // std::cout << "lane = " << std::bitset<32>(lane) << std::endl;
                // std::cout << "row = " << std::bitset<32>(row) << std::endl;

                FeeID_hit.push_back(decoder->feeid);
                Lane_hit.push_back(static_cast<int>(lane));
                ChipID_hit.push_back(decoder->chipIds[static_cast<int>(lane)]);
                RowID_hit.push_back(static_cast<int>(row));
                ColumnID_hit.push_back(static_cast<int>(column));

                ++unique_row_count[static_cast<int>(row)];
            }

            event = nHB - 1;
            Nhits = nhits;

            tree->Fill();

            CleanVec(FeeID_hit);
            CleanVec(Lane_hit);
            CleanVec(ChipID_hit);
            CleanVec(RowID_hit);
            CleanVec(ColumnID_hit);
        }
        else if (ret == HB_NO_DATA_DONE)
            continue;
        else
            exit(-1);
    }
    std::cout << std::endl;

    for (auto const &pair : unique_row_count)
    {
        std::cout << pair.first << " : " << pair.second << std::endl;
    }

    std::cout << std::endl;
}

void get_all_feeids(decoder_t *decoder)
{
    while (true)
    {
        if (check_next_event(decoder) == DONE)
            break;
        else
            exit(-1);
    }

    std::sort(decoder->feeids.begin(), decoder->feeids.end());
    std::cout << decoder->feeids.size() << " feeids founds." << std::endl;
    ostringstream ss;
    ss << "[ ";
    for (auto &_feeid : decoder->feeids)
    {
        ss << _feeid << ((_feeid == decoder->feeids.back()) ? "" : ", ");
    }
    ss << " ]";

    std::cout << ss.str() << std::endl;
}

void signal_callback_handler(int signum)
{
    std::cout << "Signal " << signum << " catched. Exit" << std::endl;
    exit(signum);
}

static void display_help()
{
    printf("Usage: mvtx-decoder [OPTIONS] <file_name>\n");
    printf("Decode MVTX raw data.\n\n");
    printf("If not file_name given using /dev/stdin by default\n");
    printf("General options:\n");
    printf("  -f <feeid>         Default: 0.\n");
    printf("  -h                 Display help.\n");
    printf("  -i <thr_inj>       number of injection for threshold.\n");
    printf("                     default: 25.\n");
    printf("  -n <n_thr>         number of DAC settings used for threshold tuning.\n");
    printf("  -p <prefix>        prefix text add to the output data file.\n");
    printf("  -t <run_test>      test analysis to run: \n");
    printf("                     0 : run fakehitrate analysis.\n");
    printf("                     1 : run threshold scan analysis.\n");
    printf("                     2 : run threshold tuning analysis.\n");
}

int main(int argc, char **argv)
{
    TBenchmark *gBenchmark = new TBenchmark();
    gBenchmark->Start("mvtx-decoder");

    enum RUN_TEST
    {
        RUN_FHR,
        RUN_THR,
        RUN_TUNING,
        NO_RUN_TEST
    };
    int opt = -1;
    int _feeid = -1;
    int test = -1;
    int thr_inj = 25;
    int thr_chg = 50;
    int n_thr = 1;
    std::string prefix("");
    std::string filename("/dev/stdin");

    while ((opt = getopt(argc, argv, ":f:hi:n:p:t:")) != -1)
    {
        switch (opt)
        {
        case 'f':
            if (sscanf(optarg, "%d", &_feeid) != 1)
            {
                display_help();
                exit(-1);
            }
            break;

        case 'h':
            display_help();
            exit(0);
            break;

        case 'i':
            if (sscanf(optarg, "%d", &thr_inj) != 1)
            {
                exit(-1);
            }
            break;

        case 'n':
            if (sscanf(optarg, "%d", &n_thr) != 1)
            {
                display_help();
                exit(-1);
            }
            break;

        case 'p':
            prefix = optarg;
            break;

        case 't':
            if (sscanf(optarg, "%d", &test) != 1)
            {
                display_help();
                exit(-1);
            }
            break;

        default:
            display_help();
            exit(-1);
        }
    }

    if (optind != argc) // No file given
    {
        filename = std::string(argv[optind++]);
    }

    if (optind != argc)
    {
        std::cout << "###ERROR!!! Extra arguments given" << std::endl;
        display_help();
        exit(-1);
    }

    signal(SIGINT, signal_callback_handler);

    std::unique_ptr<decoder_t> decoder = std::make_unique<decoder_t>(filename);
    decoder->thscan_nInj = thr_inj;
    decoder->thscan_nChg = thr_chg;
    decoder->feeid = _feeid;
    if (_feeid < 0)
    {
        get_all_feeids(decoder.get());
        exit(0);
    }

    RUN_TEST run_test = NO_RUN_TEST;
    switch (test)
    {
    case 0:
        run_test = RUN_FHR;
        break;

    case 1:
        run_test = RUN_THR;
        break;

    case 2:
        run_test = RUN_TUNING;
        break;

    default:
        run_test = NO_RUN_TEST;
    }

    if (run_test == NO_RUN_TEST)
    {
        std::cout << "### ERROR: no run test provided, doing nothing" << std::endl;
        display_help();
        exit(-1);
    }

    switch (run_test)
    {
    case RUN_FHR:
        decoder.get()->isThr = false;
        run_fhrana(decoder.get(), prefix);
        break;
    case RUN_THR:
        decoder.get()->isThr = true;
        decoder.get()->isTun = false;
        run_thrana(decoder.get(), prefix);
        break;
    case RUN_TUNING:
        decoder.get()->isThr = true;
        decoder.get()->isTun = true;
        for (int i = 0; i < n_thr; ++i)
        {
            run_thrana(decoder.get(), prefix, i);
        }
        run_thrana(decoder.get(), prefix, -1);
        break;
    default:
        std::cout << "### ERROR: no run test provided, doing nothing" << std::endl;
        exit(-1);
    }

    gBenchmark->Show("mvtx-decoder");

    return 0;
}
