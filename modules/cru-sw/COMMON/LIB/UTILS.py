import sys

class Utils:
    def uns(self, val):
        if val == None:
            print('Error, val is equal to None')
            val = 0
        elif val < 0:
            val = val + 2**32

        return (val)

    def twos_comp(self, val, bits):
        """
        compute the 2's compliment of int value val
        """
        if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)        # compute negative value

        return val

    def two_comp13(self, nb13bits):
        if nb13bits > 8191:
            print("Number is greater than 8191!!!")
            nb13bits = 8191

        if nb13bits <= 4095:
            return nb13bits
        else:
            return nb13bits-8192

    def two_comp15(self, nb15bits):
        """
        All single-ended (V1,V2,V3,V4) or differential (V1-V2, V3-V4) tensions
        are in 15bits complemented to 2.
        So we need this conversion function
        """
        if nb15bits > 32767:
            print("Number is greater than 32767!!!")
            nb15bits = 32767
        if nb15bits <= 16383:
            return nb15bits
        else:
            return nb15bits-32768

    def checkVal(self, add, val1, val2):
        """
        Function to read a value from the register and compare it with the value written
        """
        if val1 != val2 :
            print('ADD ', hex(add), ' ERROR WR [',hex(val1), '] RD [',hex(val2), ']')

    def checkData(self, reg_add, data, val, file_dump, debug = None):
        file_dump.write('WR -> REG : 0x%02X DATA 0x%02X\n' % (reg_add, data))
        if (data & 0xff) != val:
            file_dump.write('RD ->            DATA %02X  !!! ERROR\n' % (data))
            return 1
        else:
            file_dump.write('RD ->            DATA %02X\n' % (data))
            return 0

    def printRes(self, msg, val):
        if val == 1:
            print('%23s  --  !!!  ERROR !!!' %msg)
        else:
            print('%23s  --  OK' %msg)

    def errorMsg(self, string, val, debug = None):
        """
        Print ERROR messages
        """
        print (string, hex(val))
        sys.exit()

    def extractBits(self, val):
        """
        store the single bit in a list
        """
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

    def getDataFromFile(self, reg_list, file_name):
        reg_index = 0
        start = 0
        data_list = []

        with open(file_name) as f:
            for line in f:
                # search the start of the registers
                if 'REGISTER_MAP' in line :
                    start = 1
                    continue
                elif 'END_PROFILE' in line :
                    start = 0

                if start == 1 :
                    # get the register value
                    reg = line[:3]
                    reg = int(reg)

                    if (reg == reg_list[reg_index]) :
                        # get the data
                        data = line[4:6]
                        data = '0x' + data
                        data_int = int(data,0)
                        data_list.append(data_int)
                        reg_index = reg_index + 1
                        if reg_index == len(reg_list):
                            return data_list

    def invertByte(self, data) :
        l = data
        n = 2
        ll = [l[i:i+n] for i in range(0, len(l), n)]

        data = '0x' + ll[4] + ll[3] + ll[2] + ll[1]
        return data

    def checkRet(self, data, ret) :
        if data != ret :
            print('ERROR : DATA WR %s, DATA RD %s' % (hex(data), hex(ret)))
