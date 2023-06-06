/* ************ MICROSEMI SOC CORP. DIRECTC LICENSE AGREEMENT ************* */
/* ------------------------------------------------------------------------ 
PLEASE READ: BEFORE INSTALLING THIS SOFTWARE, CAREFULLY READ THE FOLLOWING 
MICROSEMI SOC CORP LICENSE AGREEMENT REGARDING THE USE OF THIS SOFTWARE. 
INSTALLING THIS SOFTWARE INDICATES THAT YOU ACCEPT AND UNDERSTAND THIS AGREEMENT 
AND WILL ABIDE BY IT. 

Note: This license agreement (“License”) only includes the following software: 
DirectC. DirectC is licensed under the following terms and conditions.

Hereinafter, Microsemi SoC Corp. shall be referred to as “Licensor” or “Author,” 
whereas the other party to this License shall be referred to as “Licensee.” Each 
party to this License shall be referred to, singularly, as a “Party,” or, 
collectively, as the “Parties.”

Permission to use, copy, modify, and/or distribute DirectC for any purpose, with
or without fee, is hereby granted by Licensor to Licensee, provided that the 
above Copyright notice and this permission notice appear in all copies, 
modifications and/or distributions of DirectC.

DIRECTC IS PROVIDED "AS IS" AND THE AUTHOR/LICENSOR DISCLAIMS ALL WARRANTIES 
WITH REGARD TO DIRECTC INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND 
FITNESS. IN NO EVENT SHALL AUTHOR/LICENSOR BE LIABLE TO LICENSEE FOR ANY DAMAGES, 
INCLUDING SPECIAL, DIRECT,INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES 
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF 
CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION 
WITH THE USE OR PERFORMANCE OF DIRECTC.

Export Control: Information furnished to Licensee may include United States 
origin technical data. Accordingly, Licensee is responsible for complying with, 
and warrants to Licensor that it will comply with, all U.S. export control laws 
and regulations, including the provisions of the Export Administration Act of 
1979 and the Export Administration Regulations promulgated thereunder, the Arms 
Export Control Act, and the sanctions laws administered by the Office of Foreign 
Assets Control including any other U.S. Government regulation applicable to the 
export, re-export, or disclosure of such controlled technical data (or the 
products thereof) to Foreign Nationals, whether within or without the U.S., 
including those employed by, or otherwise associated with, Licensee. Licensee 
shall obtain Licensor’s written consent prior to submitting any request for 
authority to export any such technical data.

ADR: Any dispute between the Parties arising from or related to this License or 
the subject matter hereof, including its validity, construction or performance 
thereunder, shall be exclusively resolved through arbitration by a mutually 
acceptable impartial and neutral arbitrator appointed by the Judicial 
Arbitration and Mediation Services (JAMS) in accordance with its rules and 
procedures. If the Parties are not able to agree on an arbitrator within 10 days 
of the date of request for mediation is served, then JAMS shall appoint an 
arbitrator. Notice of arbitration shall be served and filed with the JAMS main 
offices in Irvine, California. Each Party shall be responsible for all costs 
associated with the preparation and representation by attorneys, or any other 
persons retained thereby, to assist in connection with any such Arbitration. 
However, all costs charged by the mutually agreed upon Arbitration entity shall 
be equally shared by the Parties. The Party seeking Mediation and/or Arbitration 
as provided herein agrees that the venue for any such Mediation and Arbitration 
shall be selected by the other Party and that such venue must be Los Angeles, 
California; New York, New York; or Chicago, Illinois; whereby the applicable law 
and provisions of the Evidence Code of the State selected thereby shall be 
applicable and shall govern the validity, construction and performance of this 
License.

Governing Law: This license will be governed by the laws of the State of 
California, without regard to its conflict of law provisions.

Entire Agreement: This document constitutes the entire agreement between the 
Parties with respect to the subject matter herein and supersedes all other 
communications whether written or oral.                                     */

/* ************************************************************************ */
/*                                                                          */
/*  JTAG_DirectC    Copyright (C) Microsemi Corporation                     */
/*  Version 4.1     Release date January 29, 2018                           */
/*                                                                          */
/* ************************************************************************ */
/*                                                                          */
/*  Module:         dpchain.c                                               */
/*                                                                          */
/*  Description:    Contains chain functions                                */
/*                                                                          */
/* ************************************************************************ */
#include "dpuser.h"
#include "dpchain.h"
#include "dpjtag.h"
#include "dpcom.h"

// ITS specific
#include "dpalg.h"
#include <stdio.h>
#include <stdint.h>
#include <math.h>

#include "GBT_SCA_src/Sca.h"

extern int mode_stream_in;
extern int mode_stream_io;
extern int G_length;
// End ITS specific

typedef __uint128_t uint128_t;
#ifdef CHAIN_SUPPORT
/* *****************************************************************************
* Variable that must be intialized with appropriate data depending on the chain
* configuration.  See user guide for more information.
*******************************************************************************/
DPUCHAR dp_preir_data[PREIR_DATA_SIZE]={0xff};
DPUCHAR dp_predr_data[PREDR_DATA_SIZE]={0x0};
DPUCHAR dp_postir_data[POSTIR_DATA_SIZE]={0xff};
DPUCHAR dp_postdr_data[POSTDR_DATA_SIZE]={0x0};

DPUINT dp_preir_length = PREIR_LENGTH_VALUE;
DPUINT dp_predr_length = PREDR_LENGTH_VALUE;
DPUINT dp_postir_length = POSTIR_LENGTH_VALUE;
DPUINT dp_postdr_length = POSTDR_LENGTH_VALUE;

/****************************************************************************
* Purpose: clock data stored in tdi_data into the device.
* terminate is a flag needed to determine if shifting to pause state should 
* be done with the last bit shift.
****************************************************************************/
void dp_shift_in(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{
    if (current_jtag_state == JTAG_SHIFT_IR)
    {
        if (dp_preir_length > 0U)
        {
            dp_do_shift_in(0U,dp_preir_length, dp_preir_data,0U);
        }
        if (dp_postir_length > 0U)
        {
            dp_do_shift_in(start_bit,num_bits, tdi_data,0U);
            dp_do_shift_in(0U,dp_postir_length, dp_postir_data, terminate);
        }
        else
        {
            dp_do_shift_in(start_bit,num_bits, tdi_data,terminate);
        }	
    }
    else if (current_jtag_state == JTAG_SHIFT_DR)
    {
        if (dp_predr_length > 0U)
        {
            dp_do_shift_in(0U,dp_predr_length, dp_predr_data,0U);
        }
        if (dp_postdr_length > 0U)
        {
            dp_do_shift_in(start_bit,num_bits, tdi_data,0U);
            dp_do_shift_in(0U,dp_postdr_length, dp_postdr_data, terminate);
        }
        else
        {
            dp_do_shift_in(start_bit,num_bits, tdi_data,terminate);
        }
    }
    else
    {
    }
    return;
}
/****************************************************************************
* Purpose:  clock data stored in tdi_data into the device.
*           capture data coming out of tdo into tdo_data.
* This function will always clock data starting bit postion 0.  
* Jtag state machine will always set the pauseDR or pauseIR state at the 
* end of the shift.
****************************************************************************/
void dp_shift_in_out(DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR tdo_data[])
{
    if (current_jtag_state == JTAG_SHIFT_IR)
    {
        if (dp_preir_length > 0U)
        {
            dp_do_shift_in(0U,dp_preir_length, dp_preir_data,0U);
        }
        if (dp_postir_length > 0U)
        {
            dp_do_shift_in_out(num_bits, tdi_data,tdo_data,0U);
            dp_do_shift_in(0U,dp_postir_length, dp_postir_data, 1U);
        }
        else
        {
            dp_do_shift_in_out(num_bits, tdi_data,tdo_data,1U);
        }	
    }
    else if (current_jtag_state == JTAG_SHIFT_DR)
    {
        if (dp_predr_length > 0U)
        {
            dp_do_shift_in(0U,dp_predr_length, dp_predr_data,0U);
        }
        if (dp_postdr_length > 0U)
        {
            dp_do_shift_in_out(num_bits, tdi_data,tdo_data,0U);
            dp_do_shift_in(0U,dp_postdr_length, dp_postdr_data, 1U);
        }
        else
        {
            dp_do_shift_in_out(num_bits, tdi_data,tdo_data,1U);
        }
    }
    else
    {
    }
    return;
}

void dp_do_shift_in(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{
    if(mode_stream_in) // ITS modification, send 32bit instead of one by one
    {
        if(start_bit==0) // TODO: Document #156
        {
            dp_do_shift_in_32bit_mode(start_bit, num_bits, tdi_data, terminate);
        }
        else
        {
            dp_do_shift_in_32bit_mode_sb(start_bit, num_bits, tdi_data, terminate);   
        }
    }
    else
    {
        dp_do_shift_in_1bit_mode(start_bit, num_bits, tdi_data, terminate);
    }
}

// Original DirectC function dp_do_shift_in
void dp_do_shift_in_1bit_mode(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{
    idx = (DPUCHAR) start_bit >> 3;
    bit_buf = 1U << (DPUCHAR)(start_bit & 0x7U);
    if (tdi_data == (DPUCHAR*)DPNULL)
    {
        data_buf = 0U;
    }
    else
    {
        data_buf = tdi_data[idx] >> ((DPUCHAR)(start_bit & 0x7U));
    }
    if (terminate == 0U)
    {
        num_bits++;
    }
    while (--num_bits)
    {
        dp_jtag_tms_tdi(0U, data_buf&0x1U);
        data_buf >>= 1;
        bit_buf <<= 1;
        if ((bit_buf & 0xffU) == 0U )
        {
            bit_buf = 1U;
            idx++;
            if (tdi_data == (DPUCHAR*)DPNULL)
            {
                data_buf = 0U;
            }
            else 
            {
                data_buf = tdi_data[idx];
            }
        }
    }
    if (terminate)
    {
        dp_jtag_tms_tdi(1U, data_buf & 0x1U);
        if (current_jtag_state == JTAG_SHIFT_IR)
        {
            current_jtag_state = JTAG_EXIT1_IR;
        }
        else if (current_jtag_state == JTAG_SHIFT_DR)
        {
            current_jtag_state = JTAG_EXIT1_DR;
        }
        else
        {
        }
    }
    return;
}

// TODO: Document #156
void dp_do_shift_in_32bit_mode_sb(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{// assuming nb < 32
    int test[num_bits];
    int test_nb = num_bits;
    uint32_t test_tdi_word=0;
    uint32_t test_tms_word=0x02000000;
    idx = (DPUCHAR) start_bit >> 3;
    bit_buf = 1U << (DPUCHAR)(start_bit & 0x7U);
    if (tdi_data == (DPUCHAR*)DPNULL)
    {
        data_buf = 0U;
    }
    else
    {
        data_buf = tdi_data[idx] >> ((DPUCHAR)(start_bit & 0x7U));
    }
    if (terminate == 0U)
    {
        num_bits++;
    }
    while (--num_bits)
    {
        if((data_buf&0x1U) == 0)
        {
            test[num_bits] = 0;
        } else {
            test[num_bits] = 1;
        }
        //dp_jtag_tms_tdi(0U, data_buf&0x1U);
        data_buf >>= 1;
        bit_buf <<= 1;
        if ((bit_buf & 0xffU) == 0U )
        {
            bit_buf = 1U;
            idx++;
            if (tdi_data == (DPUCHAR*)DPNULL)
            {
                data_buf = 0U;
            }
            else 
            {
                data_buf = tdi_data[idx];
            }
        }
    }

    if((data_buf&0x1U) == 0)
    {
        test[num_bits] = 0;
    } else {
        test[num_bits] = 1;
    }
    
    test_tdi_word = 0;

    for(int iii = 0; iii < test_nb; iii++)
    {
        test_tdi_word = (pow(2, test_nb-iii) * test[iii]) + test_tdi_word;
    }

    test_tdi_word /= 2;
    
    if (terminate)
    {
        //dp_jtag_tms_tdi(1U, data_buf & 0x1U); //disable this line for buffer mode
        if (current_jtag_state == JTAG_SHIFT_IR)
        {
            current_jtag_state = JTAG_EXIT1_IR;
        }
        else if (current_jtag_state == JTAG_SHIFT_DR)
        {
            current_jtag_state = JTAG_EXIT1_DR;
        }
        else
        {
        }
    }
    jtag_32_bit_mode(test_nb, test_tdi_word, test_tms_word);
    return;
}

// TODO: Document #156
uint32_t dp_do_shift_in_32bit_mode_sb_return_tdi(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{// assuming nb < 32, nb == 26
    int test[num_bits];
    int test_nb = num_bits;
    uint32_t test_tdi_word=0;
    idx = (DPUCHAR) start_bit >> 3;
    bit_buf = 1U << (DPUCHAR)(start_bit & 0x7U);
    if (tdi_data == (DPUCHAR*)DPNULL)
    {
        data_buf = 0U;
    }
    else
    {
        data_buf = tdi_data[idx] >> ((DPUCHAR)(start_bit & 0x7U));
    }
    if (terminate == 0U)
    {
        num_bits++;
    }
    while (--num_bits)
    {
        if((data_buf&0x1U) == 0)
        {
            test[num_bits] = 0;
        } else {
            test[num_bits] = 1;
        }
        data_buf >>= 1;
        bit_buf <<= 1;
        if ((bit_buf & 0xffU) == 0U )
        {
            bit_buf = 1U;
            idx++;
            if (tdi_data == (DPUCHAR*)DPNULL)
            {
                data_buf = 0U;
            }
            else 
            {
                data_buf = tdi_data[idx];
            }
        }
    }

    if((data_buf&0x1U) == 0)
    {
        test[num_bits] = 0;
    } else {
        test[num_bits] = 1;
    }
    
    test_tdi_word = 0;

    for(int iii = 0; iii < test_nb; iii++)
    {
        test_tdi_word = (pow(2, test_nb-iii) * test[iii]) + test_tdi_word;
    }

    test_tdi_word /= 2;

    return test_tdi_word;
}

// TODO: Document #156
void dp_do_shift_in_32bit_mode(DPULONG start_bit, DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR terminate)
{// a bug: this function has not utilized start_bit as in one-bit mode
    uint32_t jtag_tdi_data = 0;
    int nbytes = ceil(num_bits/8.0);
    int rem_bits_in_word = num_bits%32;
    int total_words = ceil(num_bits/32.0);
    uint32_t words[total_words];

    int b0 = 0;
    // fill word list
    // data_buf = tdi_data[idx] >> ((DPUCHAR)(start_bit & 0x7U));
    for (int w = 0; w < total_words; w++)
    {
        jtag_tdi_data = 0; // always reset the var
        if (tdi_data == NULL) {
            jtag_tdi_data = 0;
        }  else {
            if (nbytes - b0 >= 4) {
                for (int b = 0; b < 4; ++b) {
                    jtag_tdi_data = jtag_tdi_data | ((tdi_data[b + b0] & 0xff) << (b * 8));
                }
                b0 += 4;
            } else { // end case
                for (int b = 0; b < (nbytes - b0); ++b) {
                    jtag_tdi_data = jtag_tdi_data | ((tdi_data[b + b0] & 0xff) << (b * 8));
                }
            }
        }
        words[w] = jtag_tdi_data; // all the words are now in the big word array
    }
    // make last tms word. (only one that might be nonzero)
    uint32_t tms_final_word = 0;
    if (terminate) {
        tms_final_word = (rem_bits_in_word == 0) ? 1 << 31 : 1 << (rem_bits_in_word-1);        
    }
    // write data out!
    for (int w = 0; w < total_words; ++w) { // all BUT final word is written to the jtag.
        if(w == total_words-1)
        {
            int final_word_length = (rem_bits_in_word == 0) ? 32 : rem_bits_in_word; // final word length is 32 if full word, else it is remainder
            jtag_32_bit_mode(final_word_length, words[total_words-1], tms_final_word);
        }else{
            jtag_32_bit_mode(32,words[w],0);
        }
    }
    // glbl state jumping.
    if (terminate)
    {
        if (current_jtag_state == JTAG_SHIFT_IR)
        {
            current_jtag_state = JTAG_EXIT1_IR;
        }
        else if (current_jtag_state == JTAG_SHIFT_DR)
        {
            current_jtag_state = JTAG_EXIT1_DR;
        }
        else
        {
        }
    }
}

void dp_do_shift_in_out(DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR tdo_data[], DPUCHAR terminate)
{
    if(mode_stream_io) { // ITS modification, send 32 bits instead of one by one
        dp_do_shift_in_out_32bit_mode(num_bits, tdi_data, tdo_data, terminate);
    } else {
        dp_do_shift_in_out_1bit_mode(num_bits, tdi_data, tdo_data, terminate);
    }
}

//  Original DirectC function dp_do_shift_in_out
void dp_do_shift_in_out_1bit_mode(DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR tdo_data[], DPUCHAR terminate)
{
    bit_buf = 1U;
    idx = 0U;
    tdo_data[idx] = 0U;
    
    if (tdi_data == (DPUCHAR*)DPNULL)
    {
        data_buf = 0U;
    }
    else 
    {   
        data_buf = tdi_data[idx];
    }
    
    while (--num_bits)
    {
        if ((bit_buf & 0xffU) == 0U )
        {
            bit_buf = 1U;
            idx++;
            tdo_data[idx] = 0U;
            if (tdi_data == (DPUCHAR*)DPNULL)
            {
                data_buf = 0U;
            }
            else 
            {
                data_buf = tdi_data[idx];
            }
        }
        if (dp_jtag_tms_tdi_tdo(0U, data_buf&0x1U))
        {
            tdo_data[idx] |= bit_buf;
        }
        bit_buf <<= 1;
        data_buf>>=1;
    }
    if ((bit_buf & 0xffU) == 0U )
    {
        bit_buf = 1U;
        idx++;
        tdo_data[idx] = 0U;
        if (tdi_data == (DPUCHAR*)DPNULL)
        {
            data_buf = 0U;
        }
        else 
        {
            data_buf = tdi_data[idx];
        }
    }
    if(terminate)
    {
        if (dp_jtag_tms_tdi_tdo(1U, data_buf&0x1U))
        {
            tdo_data[idx] |= bit_buf;
        }
        if (current_jtag_state == JTAG_SHIFT_IR)
        {
            current_jtag_state = JTAG_EXIT1_IR;
        }
        else if (current_jtag_state == JTAG_SHIFT_DR)
        {
            current_jtag_state = JTAG_EXIT1_DR;
        }
        else
        {
        }
    }
    else 
    {
        if (dp_jtag_tms_tdi_tdo(0U, data_buf&0x1U))
        {
            tdo_data[idx] |= bit_buf;
        }
    }
    return;
}

// TODO: Document #156
void dp_do_shift_in_out_32bit_mode(DPUINT num_bits, DPUCHAR tdi_data[], DPUCHAR tdo_data[], DPUCHAR terminate)
{
    uint32_t jtag_tdi_data = 0;
    int nbytes = ceil(num_bits/8.0);
    int rem_bits_in_word = num_bits%32;
    int total_words = ceil(num_bits/32.0);
    uint32_t words[total_words];
    uint32_t tdo_words[total_words];

    int b0 = 0;
    // fill word list
    for (int w = 0; w < total_words; w++)
    {
        jtag_tdi_data = 0; // always reset the var
        if (tdi_data == NULL) {
            jtag_tdi_data = 0;
        }  else {
            if (nbytes - b0 >= 4) {
                for (int b = 0; b < 4; ++b) {
                    jtag_tdi_data = jtag_tdi_data | ((tdi_data[b + b0] & 0xff) << (b * 8));
                }
                b0 += 4;
            } else { // end case
                for (int b = 0; b < (nbytes - b0); ++b) {
                    jtag_tdi_data = jtag_tdi_data | ((tdi_data[b + b0] & 0xff) << (b * 8));
                }
            }
        }
        words[w] = jtag_tdi_data; // all teh words are now in the big word array
    }
    // make last tms word. (only one that might be nonzero)
    uint32_t tms_final_word = 0;
    if (terminate) {
        tms_final_word = (rem_bits_in_word == 0) ? 1 << 31 : 1 << (rem_bits_in_word-1);
    }
    // write data out!
    for (int w = 0; w < total_words; ++w) { // all BUT final word is written to the jtag.
        if(w == total_words-1) // last word
        {
            int final_word_length = (rem_bits_in_word == 0) ? 32 : rem_bits_in_word; // final word length is 32 if full word, else it is remainder
            jtag_32_bit_mode(final_word_length, words[total_words-1], tms_final_word);
        }else{
            jtag_32_bit_mode(32,words[w],0);
        }
        tdo_words[w] = jtag_r_TDI_32bit(); // always
    }
   
    int w_i = 0;
    int b_i = 0;
    for(int b = 0; b < nbytes; b++)
    {
        w_i = b / 4;
        b_i = b % 4;
        tdo_data[b] = tdo_words[w_i] >> (b_i * 8);
    }

    // glbl state jumping.
    if(terminate)
    {
        if (current_jtag_state == JTAG_SHIFT_IR)
        {
            current_jtag_state = JTAG_EXIT1_IR;
        }
        else if (current_jtag_state == JTAG_SHIFT_DR)
        {
            current_jtag_state = JTAG_EXIT1_DR;
        }
        else
        {
        }
    }
}

// TODO: Document #156
uint32_t take_26bit_tdi_out(DPULONG DataIndex_sp_arg)
{
    DPULONG page_start_bit_index = DataIndex_sp_arg & 0x7U;
    page_buffer_ptr_sp = dp_get_data(5u,DataIndex_sp_arg);
    uint32_t tdi_data_out = dp_do_shift_in_32bit_mode_sb_return_tdi(page_start_bit_index, 26u, page_buffer_ptr_sp, 1);
    tdi_data_out = tdi_data_out & 0x3ffffff;
    return tdi_data_out;
}

/****************************************************************************
* Purpose:  Gets the data block specified by Variable_ID from the image dat
* file and clocks it into the device.
****************************************************************************/
void dp_get_and_shift_in(DPUCHAR Variable_ID,DPUINT total_bits_to_shift, DPULONG start_bit_index)
{
    DPULONG page_start_bit_index;
    DPUINT bits_to_shift;
    DPUCHAR terminate;
    page_start_bit_index = start_bit_index & 0x7U;
    requested_bytes = (DPULONG) (page_start_bit_index + total_bits_to_shift + 7U) >> 3U;
    
    if (current_jtag_state == JTAG_SHIFT_IR)
    {
        if (dp_preir_length > 0U)
        {
            dp_do_shift_in(0U,dp_preir_length, dp_preir_data,0U);
        }
    }
    else if (current_jtag_state == JTAG_SHIFT_DR)
    {
        if (dp_predr_length > 0U)
        {
            dp_do_shift_in(0U,dp_predr_length, dp_predr_data,0U);
        }
    }
    else
    {
    }
    
    terminate = 0U;
    while (requested_bytes)
    {
        page_buffer_ptr = dp_get_data(Variable_ID,start_bit_index);
        
        if (return_bytes >= requested_bytes )
        {
            return_bytes = requested_bytes;
            bits_to_shift = total_bits_to_shift;
            terminate = 1U;
            if (((current_jtag_state == JTAG_SHIFT_IR) && dp_postir_length) || ((current_jtag_state == JTAG_SHIFT_DR) && dp_postdr_length))
            {
                terminate =0U;
            }
        }
        else 
        {
            bits_to_shift = (DPUCHAR) (return_bytes * 8U - page_start_bit_index);
        }
        dp_do_shift_in(page_start_bit_index, bits_to_shift, page_buffer_ptr,terminate);
        
        requested_bytes = requested_bytes - return_bytes;
        total_bits_to_shift = total_bits_to_shift - bits_to_shift;
        start_bit_index += bits_to_shift;
        page_start_bit_index = start_bit_index & 0x7U;
    }
    
    if (current_jtag_state == JTAG_SHIFT_IR)
    {
        if (dp_postir_length > 0U)
        {
            dp_do_shift_in(0U,dp_postir_length, dp_postir_data,1U);
        }
    }
    else if (current_jtag_state == JTAG_SHIFT_DR)
    {
        if (dp_postdr_length > 0U)
        {
            dp_do_shift_in(0U,dp_postdr_length, dp_postdr_data,1U);
        }
    }
    else
    {
    }
    return;
}

// TODO: Document #156
void test_sp()
{
    uint128_t tms_data_128 = 0x0;
    uint128_t tdi_data_128 = 0x0;
    uint8_t length;
    // 16 iterations,
    for(int i = 1; i <= 16; i++)
    { // merge 3 iteration into 1, thus 16 iterations
        tms_data_128 = (uint128_t)0;
        tdi_data_128 = (uint128_t)0;
        uint64_t tms_data_64 = 0x0;
        uint64_t tdi_data_64 = 0x0;
        for(int j = 1; j <= 3; j++)
        {
            uint32_t tmp = take_26bit_tdi_out(DataIndex_sp);
            if( (i==1) && (j==1) )
            {
                // tms: b000 b011 b0 x2000000 b0 b00111: 39 bits
                // tdi: b000 b000 b0 xTAKETDI b0 b00000
                tms_data_64 = ((uint64_t) 3 << 33) + ((uint64_t) 0x2000000 << 6) + 7;
                tdi_data_64 = (uint64_t)tmp << 6;
                tms_data_128 = (uint128_t)tms_data_64;
                tdi_data_128 = (uint128_t)tdi_data_64;
            } else { 
                // tms: b000 b011 b0 x2000000 b0 b0010: 38 bits
                tms_data_64 = ((uint64_t)3 << 32) + ((uint64_t)0x2000000 << 5) + 2;
                tdi_data_64 = (uint64_t)tmp << 5;
                tms_data_128 = tms_data_128 + ((uint128_t)tms_data_64 << (39 + 38 * (j-2)));
                tdi_data_128 = tdi_data_128 + ((uint128_t)tdi_data_64 << (39 + 38 * (j-2)));
            }
            DataIndex_sp = DataIndex_sp + 26u; //ARRAY_ROW_LENGTH = 26u
        }
        if(i == 1){length = 39+38*2;}
        else {length = 38*3;}
        jtag_sp(tms_data_128, tdi_data_128, length);
    }
    current_jtag_state = 2;
    return;
}

/****************************************************************************
* Purpose:  Get the data block specified by Variable_ID from the image dat
* file and clocks it into the device.  Capture the data coming out of tdo 
* into tdo_data
****************************************************************************/
void dp_get_and_shift_in_out(DPUCHAR Variable_ID,DPUCHAR total_bits_to_shift, DPULONG start_bit_index,DPUCHAR* tdo_data)
{
    requested_bytes = ((DPULONG)total_bits_to_shift + 7u) >> 3u;
    page_buffer_ptr = dp_get_data(Variable_ID,start_bit_index);
    
    if (return_bytes >= requested_bytes )
    {
        return_bytes = requested_bytes;
        dp_shift_in_out((DPUINT)total_bits_to_shift, page_buffer_ptr,tdo_data);
    }
    else
    {
        #ifdef ENABLE_DISPLAY
        dp_display_text("\r\nError: Page buffer size is not big enough...");
        #endif
    }
    
    return;
}
#endif

/* *************** End of File *************** */

