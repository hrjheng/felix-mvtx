def extractBits(val):
    bit = [0, 0, 0, 0, 0, 0, 0, 0]

    bit[7] = (val>> (8-1))&1
    bit[6] = (val>> (7-1))&1
    bit[5] = (val>> (6-1))&1 
    bit[4] = (val>> (5-1))&1
    bit[3] = (val>> (4-1))&1 
    bit[2] = (val>> (3-1))&1
    bit[1] = (val>> (2-1))&1 
    bit[0] = (val>> (1-1))&1

    return bit

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val      

def generic_print(bit, ch, msg, ps, ns, dflt, f):

    if(ch == 12):
         if(bit == dflt): 
             print >>f,'\t\t\t\t\t\t',msg,'|',ps,'|',bit
         else:
             print >>f,'\t\t\t\t\t\t',msg,'|',ns,'|',bit
    else :
        if(bit == dflt): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',ps,'|',bit
        else:
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',ns,'|',bit 

def generic_print1(val, ch, msg, p1, p2, p3, dflt, f):

        if(val == dflt): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=2.1db|',p2,'=-1.8db|',p3,'=3.9db','|',bin(val)
        elif(val == 0): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=0.3db|',p2,'=-0.1db|',p3,'=0.4db','|',bin(val)
        elif(val == 1): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=1.3db|',p2,'=-0.9db|',p3,'=2.2db','|',bin(val)
        elif(val == 3): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=3.05db|',p2,'=-3.05db|',p3,'=6.1db','|',bin(val)
        elif(val == 4): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=4.1db|',p2,'=-4.7db|',p3,'=8.8db','|',bin(val)
        elif(val == 5): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=5db|',p2,'=-6.6db|',p3,'=11.6db','|',bin(val)
        elif(val == 6): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=5.6db|',p2,'=-8.3db|',p3,'=13.9db','|',bin(val)
        elif(val == 7): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=6.1db|',p2,'=-10.6db|',p3,'=16.7db','|',bin(val)

def generic_print2(bit1, bit2, msg, out1, out2, out3, out4, f): 
   
         if(bit1 == 0 and bit2 == 0): 
             print >>f,'\t\t\t\t\t\t',msg,'|',out1,'|',bit1,bit2
         elif(bit1 == 0 and bit2 == 1): 
             print >>f,'\t\t\t\t\t\t',msg,'|',out2,'|',bit1,bit2
         elif(bit1 == 1 and bit2 == 0): 
             print >>f,'\t\t\t\t\t\t',msg,'|',out3,'|',bit1,bit2
         else :
             print >>f,'\t\t\t\t\t\t',msg,'|',out4,'|',bit1,bit2

def generic_print3(bit1, bit2, ch, msg, out1, out2, out3, out4, f): 
   
         if(bit1 == 0 and bit2 == 0): 
             print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',out1,'|',bit1,bit2
         elif(bit1 == 0 and bit2 == 1): 
             print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',out2,'|',bit1,bit2
         elif(bit1 == 1 and bit2 == 0): 
             print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',out3,'|',bit1,bit2
         else :
             print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',out4,'|',bit1,bit2

def generic_print4(val, ch, msg, p1, p2, p3, dflt, f):

        if(val == dflt): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=400mVppd|',p2,'=500mVppd|',p3,'=600mVppd','|',bin(val)
        elif(val == 0): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=70mVppd|',p2,'=100mVppd|',p3,'=130mVppd','|',bin(val)
        elif(val == 1): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=150mVppd|',p2,'=200mVppd|',p3,'=250mVppd','|',bin(val)
        elif(val == 2): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=240mVppd|',p2,'=300mVppd|',p3,'=360mVppd','|',bin(val)
        elif(val == 3): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=320mVppd|',p2,'=400mVppd|',p3,'=480mVppd','|',bin(val)
        elif(val == 5): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=480mVppd|',p2,'=600mVppd|',p3,'=720mVppd','|',bin(val)
        elif(val == 6): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=560mVppd|',p2,'=700mVppd|',p3,'=840mVppd','|',bin(val)
        elif(val == 7): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',p1,'=640mVppd|',p2,'=800mVppd|',p3,'=960mVppd','|',bin(val)

def generic_print5(val, ch, msg, dflt, f):

        lvld=3*0.85714285714285714285714285714286
        lvl=(val*0.85714285714285714285714285714286)

        if(val == dflt): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvld,'db|',bin(val)
        elif(val == 0): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 1): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 2): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 3): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 5): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 6): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
        elif(val == 7): 
            print >>f,'\t\t\t\t\t\tCH',ch,'|',msg,'|',lvl,'db|',bin(val)
