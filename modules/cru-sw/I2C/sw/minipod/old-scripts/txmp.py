import sys

import time
from time import sleep

import i2c_mod
from i2c_mod import *

import mp_mod
from mp_mod import *

import txmp_mod
from txmp_mod import *

g_bit = [0, 0, 0, 0, 0, 0, 0, 0]

def swmp_vndr_dtls(ch, i2c_add,f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD INFO/VENDOR SPCIFIC DETAILS IN ASCII'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tASCII' , '\t\tDETAILS\n'
    
    print >>f,'VENDOR NAME','\tUPAGE0','\t\t\t\tREG 152-167:VENDOR NAME "AVAGO"'
    for i in range(152,168):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'  

    
    print >>f,'VENDOR ID','\tUPAGE0','\t\t\t\tREG 168-170:VENDOR OUI/IEEE ID "00H-17H-6AH"'
    for i in range(168,171):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',hex(val),']' 
    print >>f,'\n'  

    
    print >>f,'VENDOR PART','\tUPAGE0','\t\t\t\tREG 171-186:VENDOR PART NUMBER "AFBR-811FN3Z"'
    for i in range(171,187):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'  

    print >>f,'VENDOR RVN','\tUPAGE0','\t\t\t\tREG 187-188:VENDOR REVISON NUMBER "NULL"'
    for i in range(187,188+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'
    
    print >>f,'VENDOR SN','\tUPAGE0','\t\t\t\tREG 189-204:VENDOR SERIAL NUMBER "A1632300H"'
    for i in range(189,204+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'

    print >>f,'VENDOR DATE','\tUPAGE0','\t\t\t\tREG 205-212:VENDOR MFG DATE "20160809"'
    for i in range(205,212+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'
    
    print >>f,'USER AREA','\tUPAGE0','\t\t\t\tREG 213-222:CUSTOMER SPECIFIC AREA "NULL"'
    for i in range(213,222+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'
    
    print >>f,'VENDOR AREA','\tUPAGE0','\t\t\t\tREG 224-253:VENDOR SPECIFIC AREA "NULL"'
    for i in range(224,253+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        print >>f,'\t\t\t', hex(i), '\t[',str(unichr(val)),']' 
    print >>f,'\n'   

   
def swmp_features(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD INFO/AVAILABLE FEATURES IN MINIPOD'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'


    #CHECK & PRINT MINIPOD FEATURES SUPPORTED
    for i in range(138,143+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==138):
            print  >>f,'FEA_FLAG','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tFLAG RELATED FEATURES,0=>NOT SUPPORTED'
            generic_print(g_bit[7],12,"FAULT","YES","NO",1,f)  
            generic_print(g_bit[6],12,"TXLOS","YES","NO",1,f) 
            generic_print(g_bit[5],12,"RXLOS","YES","NO",1,f)  
            generic_print(g_bit[4],12,"CDRLOL","YES","NO",1,f)  
            generic_print(g_bit[3],12,"SQULCH LOS","YES","NO",1,f)
            generic_print(g_bit[2],12,"WARNING FLAG","YES","NO",1,f)     
            print >>f,'\n'
        if(i==139):
            print  >>f,'FEA_MON1','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tMONITOR RELATED FEATURES,0=>NOT SUPPORTED'
            generic_print(g_bit[7],12,"TXBIAS","YES","NO",1,f)  
            generic_print(g_bit[6],12,"TXLOP","YES","NO",1,f)  
            generic_print(g_bit[5],12,"RXPWR","SINGLE","GROUP",1,f)  
            generic_print(g_bit[4],12,"RXPWR","PAVE","OMA",1,f) 
            generic_print(g_bit[3],12,"CTEMP","YES","NO",1,f) 
            generic_print(g_bit[2],12,"ITEMP","YES","NO",1,f)
            generic_print(g_bit[1],12,"PTEMP","YES","NO",1,f)            
            generic_print(g_bit[0],12,"ETIME","YES","NO",1,f) 
            print >>f,'\n'
        if(i==140):
            print  >>f,'FEA_MON2','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tMONITOR RELATED FEATURES,0=>NOT SUPPORTED'
            generic_print(g_bit[7],12,"BER","YES","NO",1,f)  
            generic_print(g_bit[6],12,"3.3V","YES","NO",1,f)  
            generic_print(g_bit[5],12,"2.5V","YES","NO",1,f)  
            generic_print(g_bit[4],12,"1.8V","YES","NO",1,f) 
            generic_print(g_bit[3],12,"VO/VCC","YES","NO",1,f) 
            generic_print(g_bit[2],12,"TECi","YES","NO",1,f)
            print >>f,'\n'
        if(i==141):
            print  >>f,'FEA_CON1','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tCONTROL RELATED FEATURES SUPPORTED'
            generic_print2(g_bit[7],g_bit[6],"CH DISABLE","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            generic_print2(g_bit[5],g_bit[4],"SQULCH DISABLE","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            generic_print2(g_bit[3],g_bit[2],"RATE SELECT","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            generic_print2(g_bit[1],g_bit[0],"TXEQU","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            print >>f,'\n'
        if(i==142):
            print  >>f,'FEA_CON2','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tCONTROL RELATED FEATURES SUPPORTED'
            generic_print2(g_bit[7],g_bit[6],"RX AMP CONTROL","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            generic_print2(g_bit[5],g_bit[4],"RX DE_EMPHASIS CONTROL","NOT PROVIDED","GLOBAL CONTROL","SELECTIVE CONTROL","RESERVED",f) 
            generic_print(g_bit[3],12,"MARGIN MODE","YES","NO",1,f)  
            generic_print(g_bit[2],12,"CH RESET","YES","NO",1,f)  
            generic_print(g_bit[1],12,"CH POLARITY","YES","NO",1,f)
            generic_print(g_bit[0],12,"MODULE ADDRESSING","YES","NO",1,f)            
            print >>f,'\n'
        if(i==143):
            print  >>f,'FEA_CON3','\tUPG0','\t',hex(i),'\t[', hex(val),']','\tCONTROL RELATED FEATURES SUPPORTED'
            generic_print(g_bit[7],12,"FEC","YES","NO",1,f)  
            generic_print(g_bit[6],12,"PEC","YES","NO",1,f)  
            generic_print(g_bit[5],12,"JTAG","YES","NO",1,f)
            generic_print(g_bit[4],12,"AC-JTAG","YES","NO",1,f)            
            generic_print(g_bit[3],12,"BIST","YES","NO",1,f)  
            generic_print(g_bit[2],12,"TEC-TEMP","YES","NO",1,f)  
            generic_print(g_bit[1],12,"SLEEP","YES","NO",1,f)
            generic_print(g_bit[0],12,"CDR BYPASS","YES","NO",1,f)  
            print >>f,'\n'

def swmp_basics(ch, i2c_add,f) :
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD INFO/BASIC DETAILS ABOUT MINIPOD'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'

    #CHECK & PRINT MINIPOD BASICS
    for i in range(128,137+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==128):
            print >>f,'MP IDNTIFIER','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMINIPOD TYPE IDENTIFIER'
            print >>f,'\n'
        if(i==129):
            print >>f,'PWR CLASS','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMINIPOD POWER CLASS' 
            generic_print2(g_bit[7],g_bit[6],"POWER CLASS","<1.5W","<2.0W","<2.5W","<3.5W",f)            
            generic_print(g_bit[5],12,"TX CDR","YES","NO",1,f)  
            generic_print(g_bit[4],12,"RX CDR","YES","NO",1,f)  
            generic_print(g_bit[3],12,"REF.CLK","YES","NO",1,f)
            generic_print(g_bit[2],12,"PG2","YES","NO",1,f)            
            generic_print(g_bit[1],12,"CLT","YES","NO",1,f) 
            print >>f,'\n'
        if(i==130):
            print >>f,'PWR SUPPLY','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMINIPOD POWER SUPPLY REQUIREMENT' 
            generic_print(g_bit[7],12,"3.3V","YES","NO",1,f)  
            generic_print(g_bit[6],12,"2.5V","YES","NO",1,f)  
            generic_print(g_bit[5],12,"1.8V","YES","NO",1,f)
            generic_print(g_bit[4],12,"VO","YES","NO",1,f)            
            generic_print(g_bit[3],12,"VARIABLE","YES","NO",1,f)  
            print >>f,'\n'
        if(i==131):
            casetmp=val
            print >>f,'CASE TEMP','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMINIPOD CASE TEMPERATURE RECOMENDED' 
            print >>f,'\t\t\t\t\t\t',val,'degC'
            print >>f,'\n'
        if(i==132):
            minsr=val
            print >>f,'MIN SIG@','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMINIMUM SIGNAL RATE PER CHANNEL' 
            print >>f,'\t\t\t\t\t\t',val*100,'Mb/s'
            print >>f,'\n'
        if(i==133):
            maxsr=val
            print >>f,'MAX SIG@','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tMAXIMUM SIGNAL RATE PER CHANNEL' 
            print  >>f,'\t\t\t\t\t\t',val*100,'Mb/s'
            print >>f,'\n'
        if(i==134):
            val1=val
            print >>f,'WAVELENGTH','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tNOMINAL WAVELENGTH' 
        if(i==135):
            wvlen=(val1<<8) + val
            print >>f,'\t\t\t',hex(i),'\t[', hex(wvlen),']','\t',wvlen/20,'nm'
            print >>f,'\n'
        if(i==136):
            val1=val
            print >>f,'WAVELEN_TOL','\tUPG0','\t',hex(i),'\t[',hex(val),']','\tWAVELENGTH TOLERANCE' 
        if(i==137):
            wvlen_tol=(val1<<8) + val
            print >>f,'\t\t\t',hex(i),'\t[', hex(wvlen_tol),']','\t',wvlen_tol/200,'nm'
            print >>f,'\n'

            #status@console 
            val1=readI2C(ch, i2c_add, 152, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val2=readI2C(ch, i2c_add, 153, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val3=readI2C(ch, i2c_add, 154, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val4=readI2C(ch, i2c_add, 155, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val5=readI2C(ch, i2c_add, 156, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            print 'BASIC\tMAKE[',str(unichr(val1)),str(unichr(val2)),str(unichr(val3)),str(unichr(val4)),str(unichr(val5)),']'
            val1=readI2C(ch, i2c_add, 176, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val2=readI2C(ch, i2c_add, 177, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            val3=readI2C(ch, i2c_add, 178, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
            print          '\tPART[',str(unichr(val1)),str(unichr(val2)),str(unichr(val3)),']'    
            print          '\tCASETMP[',casetmp,']degC'
            print          '\tSIG RATE[',maxsr*100,'~',minsr*100,']Mb/s'
            print          '\tWAVELENGTH[',wvlen/20,']nm'
            print          '\tTOLERANCE[',wvlen_tol/200,']nm'

def monmp_params(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD STATUS/CURRENT VALUES OF DIFFERENT PARAMETRS'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'

    for i in range(28,30):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 28) :
            print >>f,'INRNL TEMP','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[28:29]:MINIPOD INTERNAL TEMPERATURE'
            #int. temp. integer part
            temp_msb=twos_comp(val, 8)
        else : 
            #int. temp. fractional part
            temp_lsb=val*0.00390625
            int_temp=temp_msb + temp_lsb
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tINTERNAL TEMPERATURE=',int_temp,'degC\n'
    
    for i in range(32,33+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 32) :
            print >>f,'INTRNL 3.3V','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[32:33]:MINIPOD INTERNAL 3.3V'
            #internal 3.3v msb 
            val1=val
        else : 
            #internal 3.3v lsb
            int_vol1=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tINTERNAL 3.3V=',int_vol1*.0001,'V\n'  

    for i in range(34,35+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 34) :
            print >>f, 'INTRNL 2.5V','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[34:35]:MINIPOD INTERNAL 2.5V'
            #internal 2.5v msb 
            val1=val
        else : 
            #internal 2.5v lsb
            int_vol2=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tINTERNAL 2.5V=',int_vol2*.0001,'V\n'  

    for i in range(40,63+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 40) :
            print >>f,'TXBIAS CUR','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[40:63]:MINIPOD TX BIAS CURRENT FOR ALL CHS'
            #bias cur msb 
            val1=val
        elif (i == 41) : 
            #bias cur lsb
            bias_cur0=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH11=',bias_cur0*2,'uA'  
        elif (i == 42) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 43) : 
            #bias cur lsb
            bias_cur1=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH10=',bias_cur1*2,'uA'  
        elif (i == 44) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 45) : 
            #bias cur lsb
            bias_cur2=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH9=',bias_cur2*2,'uA'  
        elif (i == 46) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 47) : 
            #bias cur lsb
            bias_cur3=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH8=',bias_cur3*2,'uA'  
        elif (i == 48) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 49) : 
            #bias cur lsb
            bias_cur4=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH7=',bias_cur4*2,'uA'  
        elif (i == 50) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 51) : 
            #bias cur lsb
            bias_cur5=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH6=',bias_cur5*2,'uA'  
        elif (i == 52) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 53) : 
            #bias cur lsb
            bias_cur6=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH5=',bias_cur6*2,'uA'  
        elif (i == 54) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 55) : 
            #bias cur lsb
            bias_cur7=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH4',bias_cur7*2,'uA'  
        elif (i == 56) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 57) : 
            #bias cur lsb
            bias_cur8=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH3=',bias_cur8*2,'uA'  
        elif (i == 58) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 59) : 
            #bias cur lsb
            bias_cur9=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH2=',bias_cur9*2,'uA'  
        elif (i == 60) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 61) : 
            #bias cur lsb
            bias_cur10=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH1=',bias_cur10*2,'uA'  
        elif (i == 62) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        else : 
            #bias cur lsb
            bias_cur11=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH0=',bias_cur11*2,'uA\n'

    for i in range(64,87+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 64) :
            print >>f,'TXOUT PWR','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[64:87]:MINIPOD TX OPTICAL OUTPUT POWER FOR ALL CHS'
            #txopt_pwr_out msb
            val1=val
        elif (i == 65) : 
            #txopt_pwr_out lsb
            pwro0=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH11=',pwro0*0.1,'uW'  
        elif (i == 66) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 67) : 
            #txopt_pwr_out lsb
            pwro1=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH10=',pwro1*0.1,'uW'  
        elif (i == 68) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 69) : 
            #txopt_pwr_out lsb
            pwro2=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH9=',pwro2*0.1,'uW'  
        elif (i == 70) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 71) : 
            #txopt_pwr_out lsb
            pwro3=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH8=',pwro3*0.1,'uW'  
        elif (i == 72) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 73) : 
            #txopt_pwr_out lsb
            pwro4=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH7=',pwro4*0.1,'uW'  
        elif (i == 74) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 75) : 
            #txopt_pwr_out lsb
            pwro5=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH6=',pwro5*0.1,'uW'  
        elif (i == 76) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 77) : 
            #txopt_pwr_out lsb
            pwro6=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH5=',pwro6*0.1,'uW'  
        elif (i == 78) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 79) : 
            #txopt_pwr_out lsb
            pwro7=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH4',pwro7*0.1,'uW'  
        elif (i == 80) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 81) : 
            #txopt_pwr_out lsb
            pwro8=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH3=',pwro8*0.1,'uW'  
        elif (i == 82) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 83) : 
            #txopt_pwr_out lsb
            pwro9=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH2=',pwro9*0.1,'uW'  
        elif (i == 84) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        elif (i == 85) : 
            #txopt_pwr_out lsb
            pwro10=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tCH1=',pwro10*0.1,'uW'  
        elif (i == 86) : 
            #txopt_pwr_out msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        else : 
            #txopt_pwr_out lsb
            pwro11=(val1<<8) + val 
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']','\tCH0=',pwro11*0.1,'uW\n'

    for i in range(88,89+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 88) :
            print >>f, 'ELASPED TIME','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[88:89]:ELASPED/POWER ON TIME'
            #internal time msb
            val1=val
        else : 
            #internal timer lsb
            timer=(val1<<8) + val 
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']','\tELASPED TIME=',timer*2,'Hours\n'  

    #status@console
    print  'CURRENT','TEMP [',int_temp,']degC'
    print            '\tHIVOL[',int_vol1*.0001,']V'
    print            '\tLOVOL[',int_vol2*.0001,']V'
    print            '\tBIASi[',bias_cur0*2,'|',bias_cur1*2,'|',bias_cur2*2,'|',bias_cur3*2,'|',bias_cur4*2,'|',bias_cur5*2,']uA'
    print            '\t     [',bias_cur6*2,'|',bias_cur7*2,'|',bias_cur8*2,'|',bias_cur9*2,'|',bias_cur10*2,'|',bias_cur11*2,']uA'
    print            '\tPWRo [',pwro0*0.1,'|',pwro1*0.1,'|',pwro2*0.1,'|',pwro3*0.1,'|',pwro4*0.1,'|',pwro5*0.1,']uW'
    print            '\t     [',pwro6*0.1,'|',pwro7*0.1,'|',pwro8*0.1,'|',pwro9*0.1,'|',pwro10*0.1,'|',pwro11*0.1,']uW'
    print            '\tETIME[',timer*2,']hrs'
    #print  "\n" 


def monmp_flags(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD STATUS/CURRENT FLAGS OF DIFFERENT PARAMETRS'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'

    chk1=0

    #CHECK & PRINT LOS STATUS OF ALL CHS
    for i in range(9,10+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==9):
            val1=val
            print >>f,'LOS ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tLATCHED STATUS OF LOL FOR ALL CHS,1 => LATCHED'
            generic_print(g_bit[3],11,"LATCHED LOS","OK","LATCHED",0,f)            
            generic_print(g_bit[2],10,"LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[1],9, "LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[0],8, "LATCHED LOS","OK","LATCHED",0,f)  
        if(i==10):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"LATCHED LOS","OK","LATCHED",0,f)            
            generic_print(g_bit[6],6,"LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[5],5,"LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[4],4,"LATCHED LOS","OK","LATCHED",0,f)
            generic_print(g_bit[3],3,"LATCHED LOS","OK","LATCHED",0,f)            
            generic_print(g_bit[2],2,"LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[1],1,"LATCHED LOS","OK","LATCHED",0,f)  
            generic_print(g_bit[0],0,"LATCHED LOS","OK","LATCHED",0,f)
            print >>f,'\n'
            los_chs=val2 & 0x0FFF
            #status@console
            print 'STATUS',
            if(los_chs==0):
                #print(bcolors.OKGREEN + " LOS STATUS IS OK:WITHIN LIMIT" + bcolors.ENDC)
                chk1=1
            else :
                print(bcolors.FAIL + " LOS STATUS:LATCHED:CHECK LOG" + bcolors.ENDC)
                #print "\n"

    #CHECK & PRINT FAULT STATUS OF ALL CHS
    for i in range(11,12+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==11):
            val1=val
            print >>f,'LOS ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tLATCHED STATUS OF FAULT FOR ALL CHS,1 => LATCHED'
            generic_print(g_bit[3],11,"LATCHED FLT","OK","LATCHED",0,f)            
            generic_print(g_bit[2],10,"LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[1],9, "LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[0],8, "LATCHED FLT","OK","LATCHED",0,f)  
        if(i==12):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"LATCHED FLT","OK","LATCHED",0,f)            
            generic_print(g_bit[6],6,"LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[5],5,"LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[4],4,"LATCHED FLT","OK","LATCHED",0,f)
            generic_print(g_bit[3],3,"LATCHED FLT","OK","LATCHED",0,f)            
            generic_print(g_bit[2],2,"LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[1],1,"LATCHED FLT","OK","LATCHED",0,f)  
            generic_print(g_bit[0],0,"LATCHED FLT","OK","LATCHED",0,f)
            print >>f,'\n'
            flt_chs=val2 & 0x0FFF
            #status@console
            if(flt_chs==0):
                #print '\t',
                #print(bcolors.OKGREEN + "FLT STATUS IS OK:WITHIN LIMIT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "FLT STATUS:LATCHED:CHECK LOG" + bcolors.ENDC)

    #CHECK & PRINT TEMP ALARM OF ALL CHS
    for i in range(13,13+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==13):
            temp_alarm=val & 0xC0
            print >>f,'TEMP ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tALARM STATUS OF TEMP,1 => CROSSED LIMIT' 
            generic_print(g_bit[7],12,"HIGH TEMP ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],12,"LOW TEMP ALARM","WITHIN LIMIT","RAISED",0,f)  
            print >>f,'\n'
            #status@console
            if(temp_alarm==0):
                #print '\t',
                #print(bcolors.OKGREEN + "TEMP IS OK:WITHIN LIMIT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "TEMP CROSSED LIMIT:CHECK LOG" + bcolors.ENDC)


    #CHECK & PRINT VOLTAGE ALARM OF ALL CHS
    for i in range(14,14+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==14):
            vol_alarm=val & 0xCC
            print >>f,'VOL ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tALARM STATUS OF VOLTGAE(3.3V & 2.5V),1 => CROSSED LIMIT' 
            generic_print(g_bit[7],12,"HIGH 3.3V ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],12,"LOW 3.3V ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],12,"HIGH 2.5V ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],12,"LOW 2.5V ALARM","WITHIN LIMIT","RAISED",0,f)   
            print >>f,'\n'
            #status@console
            if(vol_alarm==0):
                #print '\t',
                #print(bcolors.OKGREEN + "VOLTAGES ARE OK:WITHIN LIMIT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "VOLTAGES CROSSED LIMIT:CHECK LOG" + bcolors.ENDC)

    
    #CHECK & PRINT BIASi OF ALL CHS
    for i in range(16,21+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==16):
            val1=val & 0xCC
            print >>f,'BIASi ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tALARM STATUS OF BIASi FOR ALL CH,1 => CROSSED LIMIT' 
            generic_print(g_bit[7],11,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],11,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],10,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],10,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)   
        if(i==17):
            val2=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],9,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],9,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],8,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],8,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==18):
            val3=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],7,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],6,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],6,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==19):
            val4=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],5,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],5,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],4,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],4,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==20):
            val5=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],3,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],3,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],2,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],2,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==21):
            val6=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],1,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],1,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],0,"HIGH BIASi ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],0,"LOW BIASi ALARM","WITHIN LIMIT","RAISED",0,f) 
            biasi_alarm=val1 & val2 & val3 & val4 & val5 & val6
            print >>f,'\n'
            #status@console
            if(biasi_alarm==0):
                #print '\t',
                #print(bcolors.OKGREEN + "BIASi FOR ALL CHS:WITHIN LIMIT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "BIASi CROSSED LIMIT:CHECK LOG" + bcolors.ENDC)
        
    #CHECK & PRINT OPT.PWR OF ALL CHS
    for i in range(22,27+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==22):
            val1=val & 0xCC
            print >>f,'PWR ALARM','\tLPG','\t',hex(i),'\t[',hex(val),']','\tALARM STATUS OF PWRo FOR ALL CH,1 => CROSSED LIMIT' 
            generic_print(g_bit[7],11,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],11,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],10,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],10,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)   
        if(i==23):
            val2=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],9,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],9,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],8,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],8,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==24):
            val3=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],7,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],6,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],6,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==25):
            val4=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],5,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],5,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],4,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],4,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==26):
            val5=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],3,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],3,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],2,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],2,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f) 
        if(i==27):
            val6=val & 0xCC
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],1,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[6],1,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f)
            generic_print(g_bit[3],0,"HIGH PWRo ALARM","WITHIN LIMIT","RAISED",0,f)            
            generic_print(g_bit[2],0,"LOW PWRo ALARM","WITHIN LIMIT","RAISED",0,f) 
            pwro_alarm=val1 & val2 & val3 & val4 & val5 & val6
            print >>f,'\n'
            #status@console
            if(pwro_alarm==0):
                #print '\t',
                #print(bcolors.OKGREEN + "PWRo FOR ALL CHS:WITHIN LIMIT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "PWRo CROSSED LIMIT:CHECK LOG" + bcolors.ENDC)

    if(chk1==6):
        print 'ALL OK'
        
  
def monmp_thresholds(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD STATUS/THRESHOLD VALUES OF DIFFERENT PARAMETRS'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'

    #points to UPG1
    writeI2C(ch, i2c_add, 127, 1, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

    for i in range(128,131+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 128) :
            print >>f,'TEMP LIMIT','\tUPAGE1','\t',hex(i),'\t[', hex(val),']','\tR[28:29]:MINIPOD INTERNAL TEMPERATURE THRESHOLD'
            #int. temp. integer part
            temp_msb=twos_comp(val, 8)
        elif (i == 129) : 
            #int. temp. fractional part
            temp_lsb=val*0.00390625
            int_temph=temp_msb + temp_lsb
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']','\tHIGH=',int_temph,'degC\n'
        elif (i == 130) :
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']'
            #int. temp. integer part
            temp_msb=twos_comp(val, 8)
        else : 
            #int. temp. fractional part
            temp_lsb=val*0.00390625
            int_templ=temp_msb + temp_lsb
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']','\tLOW=',int_templ,'degC\n'


    for i in range(144,147+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 144) :
            print >>f,'3.3V LIMIT','\tUPAGE1','\t',hex(i),'\t[', hex(val),']','\tR[32:33]:MINIPOD INTERNAL 3.3V THRESHOLD'
            #internal 3.3v msb 
            val1=val
        elif (i == 145) : 
            #internal 3.3v lsb
            int_volh1=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tHIGH=',int_volh1*.0001,'V\n'  
        elif (i == 146) :
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'
            #internal 2.5v msb 
            val1=val
        else : 
            #internal 2.5v lsb
            int_voll1=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tLOW=',int_voll1*.0001,'V\n'  


    for i in range(152,155+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 152) :
            print >>f,'2.5V LIMIT','\tUPAGE1','\t',hex(i),'\t[', hex(val),']','\tR[32:33]:MINIPOD INTERNAL 2.5V THRESHOLD'
            #internal 3.3v msb 
            val1=val
        elif (i == 153) : 
            #internal 3.3v lsb
            int_volh2=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tHIGH=',int_volh2*.0001,'V\n'  
        elif (i == 154) :
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'
            #internal 2.5v msb 
            val1=val
        else : 
            #internal 2.5v lsb
            int_voll2=(val1<<8) + val 
            print >>f, '\t\t\t',hex(i),'\t[', hex(val),']','\tLOW=',int_voll2*.0001,'V\n'  


    for i in range(176,179+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 176) :
            print >>f,'BIAS LIMIT','\tUPAGE1','\t',hex(i),'\t[', hex(val),']','\tR[40:63]:MINIPOD BIAS CURRENT THRESHOLD'
            #bias cur msb 
            val1=val
        elif (i == 177) : 
            #bias cur lsb
            bias_curh=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tHIGH=',bias_curh*2,'uA'  
        elif (i == 178) : 
            #bias cur msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        else : 
            #bias cur lsb
            bias_curl=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tLOW=',bias_curl*2,'uA'  

    for i in range(184,187+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
        if (i == 184) :
            print >>f,'PWR LIMIT','\tLPAGE','\t',hex(i),'\t[', hex(val),']','\tR[40:63]:MINIPOD OPTICAL POWER THRESHOLD'
            #opt_pwr msb 
            val1=val
        elif (i == 185) : 
            #opt_pwr lsb
            opt_pwrh=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tHIGH=',opt_pwrh*0.1,'uW'  
        elif (i == 186) : 
            #opt_pw msb
            val1=val
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']'  
        else : 
            #opt_pw lsb
            opt_pwrl=(val1<<8) + val 
            print  >>f,'\t\t\t',hex(i),'\t[', hex(val),']','\tLOW=',opt_pwrl*0.1,'uW'
            print >>f,'\n'

    #status@console
    print  'RANGE','  TEMP[',int_temph,      '~',int_templ,']degC'
    print          '\t3.3V[',int_volh1*.0001,'~',int_voll1*.0001,']V'
    print          '\t2.5V[',int_volh2*.0001,'~',int_voll2*.0001,']V'
    print          '\tBIASi[',bias_curh*2,    '~',bias_curl*2,']uA'
    print          '\tPWR[',opt_pwrh*0.1,   '~',opt_pwrl*0.1,']uW'
    #print  "\n"

    #points to UPG0
    writeI2C(ch, i2c_add, 127, 0, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)
       
def monmp_cfg(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f,'MINIPOD STATUS/CURRENT STATUS OF CONFIGURATION PARAMETERS'
    print >>f,'--------------------------------------------------------------------------------------------\n'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tDETAILS\n'
   
    chk1=0
    
    #CHECK & PRINT STATUS OF ALL CHS
    for i in range(92,93+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==92):
            val1=val
            print >>f,'CHNL STS','\tLPG','\t',hex(i),'\t[',hex(val),']','\tSTATUS OF ALL CHS,1 => DISABLE'
            generic_print(g_bit[3],11,"OPT.OUT","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"OPT.OUT","ENA","DBL",0,f)  
            generic_print(g_bit[1],9, "OPT.OUT","ENA","DBL",0,f)  
            generic_print(g_bit[0],8, "OPT.OUT","ENA","DBL",0,f)  
        if(i==93):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[6],6,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[5],5,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[4],4,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[3],3,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[2],2,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[1],1,"OPT. OUT","ENA","DBL",0,f) 
            generic_print(g_bit[0],0,"OPT. OUT","ENA","DBL",0,f) 
            print >>f,'\n'
            sts_chs=val2 & 0x0FFF
            #status@console
            print 'CHANNEL',
            if(sts_chs==0):
                #print '\t',
                #print(bcolors.OKGREEN + "OPTICAL OUTPUT ENABLE FOR ALL" + bcolors.ENDC)
                chk1=1
            else:
                #print '\t',
                print(bcolors.FAIL + "OPTICAL OUTPUT:NOT IN DEFAULT SETTING:CHECK DETAILS" + bcolors.ENDC)

    #CHECK & PRINT SQUELCH STATUS OF ALL CHS
    for i in range(94,95+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==94):
            val1=val
            print >>f,'SQULCH STS','\tLPG','\t',hex(i),'\t[',hex(val),']','\tSQULCH STATUS OF ALL CHS,1 => INHIBITS SQUELCH'
            generic_print(g_bit[3],11,"SQUELCH","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"SQUELCH","ENA","DBL",0,f)  
            generic_print(g_bit[1],9, "SQUELCH","ENA","DBL",0,f)  
            generic_print(g_bit[0],8, "SQUELCH","ENA","DBL",0,f)  
        if(i==95):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[6],6,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[5],5,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[4],4,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[3],3,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[2],2,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[1],1,"SQUELCH","ENA","DBL",0,f) 
            generic_print(g_bit[0],0,"SQUELCH","ENA","DBL",0,f) 
            print >>f,'\n'
            sql_chs=val2 & 0x0FFF
            #status@console
            if(sql_chs==0):
                #print '\t',
                #print(bcolors.OKGREEN + "SQUELCH FEATURE ENABLE FOR ALL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "SQUELCH FEATURE:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)

  
    #CHECK & PRINT MARGIN MODE OF ALL CHS
    for i in range(99,100+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==99):
            val1=val
            print >>f,'MARGIN MODE','\tLPG','\t',hex(i),'\t[',hex(val),']','\tMARGIN MODE OF ALL CHS,1 => ENABLE MARGIN MODE'
            generic_print(g_bit[3],11,"MARGIN MODE","DBL","ENA",0,f)            
            generic_print(g_bit[2],10,"MARGIN MODE","DBL","ENA",0,f)  
            generic_print(g_bit[1],9, "MARGIN MODE","DBL","ENA",0,f)  
            generic_print(g_bit[0],8, "MARGIN MODE","DBL","ENA",0,f)  
        if(i==100):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[6],6,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[5],5,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[4],4,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[3],3,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[2],2,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[1],1,"MARGIN MODE","DBL","ENA",0,f) 
            generic_print(g_bit[0],0,"MARGIN MODE","DBL","ENA",0,f) 
            print >>f,'\n'
            mm_chs=val2 & 0x0FFF
            #status@console
            if(mm_chs==0):
                #print '\t',
                #print(bcolors.OKGREEN + "MARGIN MODE DISABLE FOR ALL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "MARGIN MODE:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)


    #points to UPG1
    writeI2C(ch, i2c_add, 127, 1, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

    #CHECK & PRINT INTl mode
    for i in range(225,225+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit[0] = (val>> (1-1))&1

        if(i==225):
            val1=val
            print >>f,'INTl MODE','\tUPG','\t',hex(i),'\t[',hex(val),']','\tINTL STTAUS,STATIC=1,PULSE=0'
            generic_print(g_bit[0],12,"INTL MODE","STATIC","PULSE",1,f)   
            print >>f,'\n'
            #status@console
            if(g_bit[0]==1):
                #print '\t',
                #print(bcolors.OKGREEN + "INTL MODE IS STATIC" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "INTL MODE IS PULSE" + bcolors.ENDC)

    #CHECK & PRINT FLIP MODE OF ALL CHS
    for i in range(226,227+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==226):
            val1=val
            print >>f,'INP POLA','\tUPG','\t',hex(i),'\t[',hex(val),']','\tINPUT POLARITY FLIP OF ALL CHS,1 => ENABLE FLIP MODE'
            generic_print(g_bit[3],11,"FLIP MODE","DBL","ENA",0,f)            
            generic_print(g_bit[2],10,"FLIP MODE","DBL","ENA",0,f)  
            generic_print(g_bit[1],9, "FLIP MODE","DBL","ENA",0,f)  
            generic_print(g_bit[0],8, "FLIP MODE","DBL","ENA",0,f)  
        if(i==227):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[6],6,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[5],5,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[4],4,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[3],3,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[2],2,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[1],1,"FLIP MODE","DBL","ENA",0,f) 
            generic_print(g_bit[0],0,"FLIP MODE","DBL","ENA",0,f) 
            print >>f,'\n'
            flip_chs=val2 & 0x0FFF
            #status@console
            if(flip_chs==0):
                #print '\t',
                #print(bcolors.OKGREEN + "FLIP MODE DISABLE FOR ALL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "FLIP MODE:NOT IN DEFAULT SETTING:CHECK LOG" + bcolors.ENDC)
                #print "\n"


    #CHECK & PRINT TX EQU OF ALL CHS
    for i in range(228,233+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==228):
            valu= val >> 4
            vall= val & 0x0F
            val1= val 
            print >>f,'INP EQU','\tUPG','\t',hex(i),'\t[',hex(val),']','\tINPUT EQUALIZATION CODE OF ALL CHS,DEFAULT=>2H'
            generic_print1(valu,11,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,10,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
        if(i==229):
            valu= val >> 4
            vall= val & 0x0F
            val2= val 
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print1(valu,9,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,8,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)    
        if(i==230):
            valu= val >> 4
            vall= val & 0x0f
            val3= val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print1(valu,7,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,6,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)   
        if(i==231):
            valu= val >> 4
            vall= val & 0x0f
            val4= val 
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print1(valu,5,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,4,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)   
        if(i==232):
            valu= val >> 4
            vall= val & 0x0f
            val5= val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print1(valu,3,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,2,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)   
        if(i==233):
            valu= val >> 4
            vall= val & 0x0f
            val6= val 
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print1(valu,1,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)            
            generic_print1(vall,0,"EQU CODE","PEAK","MIDBAND","PEAK VS MIDBAND",2,f)
            print >>f,'\n'
            inp_equ=val1 & val2 & val3 & val4 & val5 & val6
            #status@console
            if(inp_equ==0x22):
                #print '\t',
                #print(bcolors.OKGREEN + "DEFAULT EQU. SETTINGS FOR ALL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "EQU CODE:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)

    if(chk1==6):
        print '\tALL OK'
           
    #points to UPG0/LP
    writeI2C(ch, i2c_add, 127, 0, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

def monmp_mask(ch, i2c_add, f):
    print >>f,'--------------------------------------------------------------------------------------------'
    print >>f, 'MINIPOD CONFIGURATION/CURRENT STATUS OF MASK CONFIGURED'
    print >>f,'--------------------------------------------------------------------------------------------'

    print >>f,'REGISTER TYPE',  '\tPAGE',  '\tADD ',  '\tVAL' , '\t\tANALYSIS\n'
    
    chk1=0

    #CHECK & PRINT LOS MASK BIT FOR ALL CHS
    for i in range(112,113+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==112):
            val1=val
            print >>f,'LOS MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tLOS MASK BIT FOR ALL CHS,1 => NO IntL GEN'
            generic_print(g_bit[3],11,"LOS MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"LOS MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[1],9, "LOS MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[0],8, "LOS MASK BIT","ENA","DBL",0,f)  
        if(i==113):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[6],6,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[5],5,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[4],4,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[3],3,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[2],2,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[1],1,"LOS MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[0],0,"LOS MASK BIT","ENA","DBL",0,f) 
            print >>f,'\n'
            mask_los=val2 & 0x0FFF
            #status@console
            print 'MASK',
            if(mask_los==0):
                #print '\t',
                #print(bcolors.OKGREEN + "LOS MASK BIT IS SET TO GEN INTL" + bcolors.ENDC)
                chk1=1
            else :
                #print '\t',
                print(bcolors.FAIL + "LOS MASK:NOT IN DEFAULT SETTING: CHECK LOG" + bcolors.ENDC)
                #print "\n"

    

    #CHECK & PRINT FAULT MASK BIT FOR ALL CHS
    for i in range(114,115+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==114):
            val1=val
            done=0
            print >>f,'LOS MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tFAULT MASK BIT FOR ALL CHS,1 => NO IntL GEN'
            generic_print(g_bit[3],11,"FLT MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"FLT MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[1],9, "FLT MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[0],8, "FLT MASK BIT","ENA","DBL",0,f)  
        if(i==115):
            val2=(val1<<8) +val
            print >>f,'\t\t\t',hex(i),'\t[',hex(val),']'  
            generic_print(g_bit[7],7,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[6],6,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[5],5,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[4],4,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[3],3,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[2],2,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[1],1,"FLT MASK BIT","ENA","DBL",0,f) 
            generic_print(g_bit[0],0,"FLT MASK BIT","ENA","DBL",0,f) 
            print >>f,'\n'
            #status@console
            mask_fault=val2 & 0x0FFF
            if(mask_fault==0):
                #print '\t',
                #print(bcolors.OKGREEN + "FAULT MASK BIT IS SET TO GEN. INTL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "FAULT MASK:NOt IN DAEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)
                #print "\n"

    
    #CHECK & PRINT TEMP MASK BIT FOR ALL CHS
    for i in range(116,116+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==116):
            print >>f,'TEMP MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tTEMP MASK BIT,1 => NO IntL GEN'
            generic_print(g_bit[7],12,"HIGH TEMP MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],12,"LOW  TEMP MASK BIT","ENA","DBL",0,f)  
            print >>f,'\n'
            mask_temp=val & 0xC0
            #status@console
            if(mask_temp==0):
                #print '\t',
                #print(bcolors.OKGREEN + "HI/LO TEMP MASK BIT IS SET TO GEN. INTL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)
    

    #CHECK & PRINT TEMP MASK BIT FOR ALL CHS
    for i in range(117,117+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==117):
            print >>f,'VOL MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tVOL MASK BIT,1 => NO IntL GEN'
            generic_print(g_bit[7],11,"HIGH 3.3V MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],10,"LOW  3.3V MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[7],11,"HIGH 2.5V MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],10,"LOW  2.5V MASK BIT","ENA","DBL",0,f)
            print >>f,'\n'
            #status@console
            mask_vol=val & 0xCC
            if(mask_vol==0):
                #print '\t',
                #print(bcolors.OKGREEN + "VOLTAGE MASK BIT IS SET TO GEN. INTL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "VOLTAGE:NOT IN DEAFULT SETTINGS :CHECK LOG" + bcolors.ENDC)
                

    #points to UPG1
    writeI2C(ch, i2c_add, 127, 1, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        
    #CHECK & PRINT BIAS CURENT MASK BIT FOR ALL CHS
    for i in range(244,249+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==244):
            val1=val & 0xCC
            print >>f,'BIASi MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tBIASi MASK BIT,1 => NO IntL GEN'
            generic_print(g_bit[7],11,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],11,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],10,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
        if(i==245):
            val2=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],9,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],9,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],8,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],8,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
        if(i==246):
            val3=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],7,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],7,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],6,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],6,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
        if(i==247):
            val4=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],5,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],5,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],4,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],4,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
        if(i==248):
            val5=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],3,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],3,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],2,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],2,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
        if(i==249):
            val6=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],1,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],1,"LOW  BIASi MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],0,"HIGH BIASi MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],0,"LOW  BIASi MASK BIT","ENA","DBL",0,f)
            print >>f,'\n'
            #status@console
            mask_biasi=val1 & val2 & val3 & val4 & val5 & val6
            if(mask_biasi==0):
                #print '\t',
                #print(bcolors.OKGREEN + "BIAS CURRENT MASK BIT IS SET TO GEN. INTL" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "BIASi MASK:NOT IN DAFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)
    

    #CHECK & PRINT TX POWER MASK BIT FOR ALL CHS
    for i in range(250,255+1):
        val=readI2C(ch, i2c_add, i, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        #extract each register bits
        g_bit = extractBits(val)

        if(i==250):
            val1=val & 0xCC
            print >>f,'OPTPWR MASK','\tLPG','\t',hex(i),'\t[',hex(val),']','\tOPT POWER MASK BIT,1 => NO IntL GEN'
            generic_print(g_bit[7],11,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],11,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],10,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],10,"LOW  POWER MASK BIT","ENA","DBL",0,f)
        if(i==251):
            val2=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],9,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],9,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],8,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],8,"LOW  POWER MASK BIT","ENA","DBL",0,f)
        if(i==252):
            val3=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],7,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],7,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],6,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],6,"LOW  POWER MASK BIT","ENA","DBL",0,f)
        if(i==253):
            val4=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],5,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],5,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],4,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],4,"LOW  POWER MASK BIT","ENA","DBL",0,f)
        if(i==254):
            val5=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],3,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],3,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],2,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],2,"LOW  POWER MASK BIT","ENA","DBL",0,f)
        if(i==255):
            val6=val & 0xCC
            print >>f,  '\t\t\t',hex(i),'\t[', hex(val),']' 
            generic_print(g_bit[7],1,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[6],1,"LOW  POWER MASK BIT","ENA","DBL",0,f)  
            generic_print(g_bit[3],0,"HIGH POWER MASK BIT","ENA","DBL",0,f)            
            generic_print(g_bit[2],0,"LOW  POWER MASK BIT","ENA","DBL",0,f)
            print >>f,'\n'
            #status@console
            mask_pwr=val1 & val2 & val3 & val4 & val5 & val6
            if(mask_pwr==0):
                #print '\t',
                #print(bcolors.OKGREEN + "OPTPWR MASK BIT IS SET TO GEN. INT" + bcolors.ENDC)
                chk1=chk1+1
            else :
                #print '\t',
                print(bcolors.FAIL + "OPTPWR:NOT IN DEFAULT SETTINGS:CHECK LOG" + bcolors.ENDC)
                #print "\n"
    if(chk1==6):
        print '\tALL OK'
     
    #points to UPG0
    writeI2C(ch, i2c_add, 127, 0, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)    


# define main
def main() :
    f= open('txmp_log.txt','w+')

    # INIT
    # PCIe card ID
    id_card = sys.argv[1]
    
    print '-------------------------------'
    print 'Hello I2C MINIPOD Python script!'
    print 'PCIe ', sys.argv[1]
    print 'BAR  ', hex(g_i2c_cfg)
    print '-------------------------------'
    print ''

    ch = openRocCh(id_card, g_bar_ch)

    resetI2C(ch, g_i2c_cmd) 

    for i in range(mp_start_add, mp_end_add):
   
        i2c_add=i
  
        #SET PAGE BYTE 0 ALWAYS AT BEGINING
        writeI2C(ch, i2c_add, 127, 0, g_i2c_cfg, g_i2c_cmd, g_i2c_dat)

        print '-------------------------'
        print "TX MINIPOD","ADD=",hex(i2c_add)
        print '-------------------------'

        print >>f,'-------------------------'
        print >>f, "TX MINIPOD","ADD=",hex(i2c_add)
        print >>f,'-------------------------'

        #####MODULE INFO######    

        #show minipod basics
        swmp_basics(ch, i2c_add, f)

        #show minipod features
        swmp_features(ch, i2c_add, f)

        #show mp vendor details
        swmp_vndr_dtls(ch, i2c_add, f)

        #####MODULE PSTATUS######

        #monitor mp module thresholds
        monmp_thresholds(ch, i2c_add, f)

        #monitor mp module parameters
        monmp_params(ch, i2c_add, f)

        #monitor mp module flags
        monmp_flags(ch, i2c_add, f)
    
        #####MODULE CSTATUS######

        #monitor mp module cfg regs
        monmp_cfg(ch, i2c_add, f)

        #monitor mp module mask regs
        monmp_mask(ch, i2c_add, f)

    #close log file
    f.close()
    
        #print(bcolors.WARNING + "Warning" + bcolors.ENDC)

if __name__ == '__main__' : 
    main()

