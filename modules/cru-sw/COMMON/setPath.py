import sys
import os

thisFilePath=os.path.dirname(os.path.realpath(__file__))

sys.path.append(thisFilePath)
sys.path.append(thisFilePath+'/LIB')
sys.path.append(thisFilePath+'/../I2C/sw')
sys.path.append(thisFilePath+'/../I2C/sw/minipod')

