from ROCEXT import *
from cru_table import *

class Ro_ctrl(RocExt):
        def __init__(self, pcie_opened_roc, pcie_id, verbose=False):
                RocExt.__init__(self,verbose)
                RocExt._roc = pcie_opened_roc

                self.verbose = verbose

        def setCheckingMask(self,mask):
                """ Set Heart-Beat Frame checking mask, one bit per channel.
                - 16 LSB are for DWRAPPER 0, 16 MSB for DWRAPPER 1
                - for each word 12 first bit are for raw links, then 13/14 are for ro_ctrl, last bit is for user logic
                """
                self.rocWr(CRUADD['add_ro_prot_check_mask'], val)

        def getCheckerAllocFail(self):
                """ Counts the number of Heart-beat frame checker allocation fail (should not happen) """
                val=self.rocRd(CRUADD['add_ro_prot_alloc_fail'])
                return val

        def getTTClinkErr(self):
                """ Counts the number of LTU to CRU communication errors """
                val=self.rocRd(CRUADD['add_ro_prot_ttc_linkerr'])
                return val

