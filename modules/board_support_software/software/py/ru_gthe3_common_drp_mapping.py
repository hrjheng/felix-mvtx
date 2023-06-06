"""Memory Mapping for the DRP port of the common auto-generated from
https://www.xilinx.com/support/documentation/user_guides/ug576-ultrascale-gth-transceivers.pdf P352
UG576 (v1.6) August 26, 2019"""

from aenum import Enum, NoAlias
from enum import IntEnum

class Gthe3CommonAddress(Enum):
    """
    Class implementing the address as distinct elements.
    Iteration will run through all addresses.
    """
    _settings_ = NoAlias

    QPLL0_CFG0 = 8
    COMMON_CFG0 = 9
    RSVD_ATTR0 = 11
    QPLL0_CFG1 = 16
    QPLL0_CFG2 = 17
    QPLL0_LOCK_CFG = 18
    QPLL0_INIT_CFG0 = 19
    QPLL0_INIT_CFG1 = 20
    QPLL0_FBDIV = 20
    QPLL0_CFG3 = 21
    QPLL0_CP = 22
    QPLL0_REFCLK_DIV = 24
    QPLL0_LPF = 25
    QPLL0_CFG1_G3 = 26
    QPLL0_CFG2_G3 = 27
    QPLL0_LPF_G3 = 28
    QPLL0_LOCK_CFG_G3 = 29
    RSVD_ATTR1 = 30
    QPLL0_FBDIV_G3 = 31
    RXRECCLKOUT0_SEL = 31
    QPLL0_SDM_CFG0 = 32
    QPLL0_SDM_CFG1 = 33
    SDM0INITSEED0_0 = 34
    SDM0INITSEED0_1 = 35
    QPLL0_SDM_CFG2 = 36
    QPLL0_CP_G3 = 37
    SDM0DATA1_0 = 40
    SDM0_WIDTH_PIN_SEL = 41
    SDM0_DATA_PIN_SEL = 41
    SDM0DATA1_1 = 41
    QPLL0_CFG4 = 48
    BIAS_CFG0 = 129
    BIAS_CFG1 = 130
    BIAS_CFG2 = 131
    BIAS_CFG3 = 132
    BIAS_CFG_RSVD = 133
    BIAS_CFG4 = 134
    QPLL1_CFG0 = 136
    COMMON_CFG1 = 137
    POR_CFG = 139
    QPLL1_CFG1 = 144
    QPLL1_CFG2 = 145
    QPLL1_LOCK_CFG = 146
    QPLL1_INIT_CFG0 = 147
    QPLL1_INIT_CFG1 = 148
    QPLL1_FBDIV = 148
    QPLL1_CFG3 = 149
    QPLL1_CP = 150
    SARC_SEL = 152
    SARC_EN = 152
    QPLL1_REFCLK_DIV = 152
    QPLL1_LPF = 153
    QPLL1_CFG1_G3 = 154
    QPLL1_CFG2_G3 = 155
    QPLL1_LPF_G3 = 156
    QPLL1_LOCK_CFG_G3 = 157
    RSVD_ATTR2 = 158
    QPLL1_FBDIV_G3 = 159
    RXRECCLKOUT1_SEL = 159
    QPLL1_SDM_CFG0 = 160
    QPLL1_SDM_CFG1 = 161
    SDM1INITSEED0_0 = 162
    SDM1INITSEED0_1 = 163
    QPLL1_SDM_CFG2 = 164


class Gthe3CommonAddressAliases(IntEnum):
    """
    Class implementing the address as distinct elements.
    Iteration will run through each address only once.
    """
    QPLL0_CFG0 = 8
    COMMON_CFG0 = 9
    RSVD_ATTR0 = 11
    QPLL0_CFG1 = 16
    QPLL0_CFG2 = 17
    QPLL0_LOCK_CFG = 18
    QPLL0_INIT_CFG0 = 19
    QPLL0_INIT_CFG1 = 20
    QPLL0_FBDIV = 20
    QPLL0_CFG3 = 21
    QPLL0_CP = 22
    QPLL0_REFCLK_DIV = 24
    QPLL0_LPF = 25
    QPLL0_CFG1_G3 = 26
    QPLL0_CFG2_G3 = 27
    QPLL0_LPF_G3 = 28
    QPLL0_LOCK_CFG_G3 = 29
    RSVD_ATTR1 = 30
    QPLL0_FBDIV_G3 = 31
    RXRECCLKOUT0_SEL = 31
    QPLL0_SDM_CFG0 = 32
    QPLL0_SDM_CFG1 = 33
    SDM0INITSEED0_0 = 34
    SDM0INITSEED0_1 = 35
    QPLL0_SDM_CFG2 = 36
    QPLL0_CP_G3 = 37
    SDM0DATA1_0 = 40
    SDM0_WIDTH_PIN_SEL = 41
    SDM0_DATA_PIN_SEL = 41
    SDM0DATA1_1 = 41
    QPLL0_CFG4 = 48
    BIAS_CFG0 = 129
    BIAS_CFG1 = 130
    BIAS_CFG2 = 131
    BIAS_CFG3 = 132
    BIAS_CFG_RSVD = 133
    BIAS_CFG4 = 134
    QPLL1_CFG0 = 136
    COMMON_CFG1 = 137
    POR_CFG = 139
    QPLL1_CFG1 = 144
    QPLL1_CFG2 = 145
    QPLL1_LOCK_CFG = 146
    QPLL1_INIT_CFG0 = 147
    QPLL1_INIT_CFG1 = 148
    QPLL1_FBDIV = 148
    QPLL1_CFG3 = 149
    QPLL1_CP = 150
    SARC_SEL = 152
    SARC_EN = 152
    QPLL1_REFCLK_DIV = 152
    QPLL1_LPF = 153
    QPLL1_CFG1_G3 = 154
    QPLL1_CFG2_G3 = 155
    QPLL1_LPF_G3 = 156
    QPLL1_LOCK_CFG_G3 = 157
    RSVD_ATTR2 = 158
    QPLL1_FBDIV_G3 = 159
    RXRECCLKOUT1_SEL = 159
    QPLL1_SDM_CFG0 = 160
    QPLL1_SDM_CFG1 = 161
    SDM1INITSEED0_0 = 162
    SDM1INITSEED0_1 = 163
    QPLL1_SDM_CFG2 = 164


class Gthe3CommonLow(Enum):
    """
    Class indicating the lowest significant bit of a field
    Iteration will run through all addresses.
    """
    _settings_ = NoAlias

    QPLL0_CFG0 = 0
    COMMON_CFG0 = 0
    RSVD_ATTR0 = 0
    QPLL0_CFG1 = 0
    QPLL0_CFG2 = 0
    QPLL0_LOCK_CFG = 0
    QPLL0_INIT_CFG0 = 0
    QPLL0_INIT_CFG1 = 8
    QPLL0_FBDIV = 0
    QPLL0_CFG3 = 0
    QPLL0_CP = 0
    QPLL0_REFCLK_DIV = 7
    QPLL0_LPF = 0
    QPLL0_CFG1_G3 = 0
    QPLL0_CFG2_G3 = 0
    QPLL0_LPF_G3 = 0
    QPLL0_LOCK_CFG_G3 = 0
    RSVD_ATTR1 = 0
    QPLL0_FBDIV_G3 = 8
    RXRECCLKOUT0_SEL = 0
    QPLL0_SDM_CFG0 = 0
    QPLL0_SDM_CFG1 = 0
    SDM0INITSEED0_0 = 0
    SDM0INITSEED0_1 = 0
    QPLL0_SDM_CFG2 = 0
    QPLL0_CP_G3 = 0
    SDM0DATA1_0 = 0
    SDM0_WIDTH_PIN_SEL = 10
    SDM0_DATA_PIN_SEL = 9
    SDM0DATA1_1 = 0
    QPLL0_CFG4 = 0
    BIAS_CFG0 = 0
    BIAS_CFG1 = 0
    BIAS_CFG2 = 0
    BIAS_CFG3 = 0
    BIAS_CFG_RSVD = 0
    BIAS_CFG4 = 0
    QPLL1_CFG0 = 0
    COMMON_CFG1 = 0
    POR_CFG = 0
    QPLL1_CFG1 = 0
    QPLL1_CFG2 = 0
    QPLL1_LOCK_CFG = 0
    QPLL1_INIT_CFG0 = 0
    QPLL1_INIT_CFG1 = 8
    QPLL1_FBDIV = 0
    QPLL1_CFG3 = 0
    QPLL1_CP = 0
    SARC_SEL = 13
    SARC_EN = 12
    QPLL1_REFCLK_DIV = 7
    QPLL1_LPF = 0
    QPLL1_CFG1_G3 = 0
    QPLL1_CFG2_G3 = 0
    QPLL1_LPF_G3 = 0
    QPLL1_LOCK_CFG_G3 = 0
    RSVD_ATTR2 = 0
    QPLL1_FBDIV_G3 = 8
    RXRECCLKOUT1_SEL = 0
    QPLL1_SDM_CFG0 = 0
    QPLL1_SDM_CFG1 = 0
    SDM1INITSEED0_0 = 0
    SDM1INITSEED0_1 = 0
    QPLL1_SDM_CFG2 = 0


class Gthe3CommonWidth(Enum):
    """
    Class indicating the width of a field
    Iteration will run through all addresses.
    """
    _settings_ = NoAlias

    QPLL0_CFG0 = 16
    COMMON_CFG0 = 16
    RSVD_ATTR0 = 16
    QPLL0_CFG1 = 16
    QPLL0_CFG2 = 16
    QPLL0_LOCK_CFG = 16
    QPLL0_INIT_CFG0 = 16
    QPLL0_INIT_CFG1 = 8
    QPLL0_FBDIV = 8
    QPLL0_CFG3 = 16
    QPLL0_CP = 10
    QPLL0_REFCLK_DIV = 5
    QPLL0_LPF = 10
    QPLL0_CFG1_G3 = 16
    QPLL0_CFG2_G3 = 16
    QPLL0_LPF_G3 = 10
    QPLL0_LOCK_CFG_G3 = 16
    RSVD_ATTR1 = 16
    QPLL0_FBDIV_G3 = 8
    RXRECCLKOUT0_SEL = 2
    QPLL0_SDM_CFG0 = 16
    QPLL0_SDM_CFG1 = 16
    SDM0INITSEED0_0 = 16
    SDM0INITSEED0_1 = 9
    QPLL0_SDM_CFG2 = 16
    QPLL0_CP_G3 = 10
    SDM0DATA1_0 = 16
    SDM0_WIDTH_PIN_SEL = 1
    SDM0_DATA_PIN_SEL = 1
    SDM0DATA1_1 = 9
    QPLL0_CFG4 = 16
    BIAS_CFG0 = 16
    BIAS_CFG1 = 16
    BIAS_CFG2 = 16
    BIAS_CFG3 = 16
    BIAS_CFG_RSVD = 10
    BIAS_CFG4 = 16
    QPLL1_CFG0 = 16
    COMMON_CFG1 = 16
    POR_CFG = 16
    QPLL1_CFG1 = 16
    QPLL1_CFG2 = 16
    QPLL1_LOCK_CFG = 16
    QPLL1_INIT_CFG0 = 16
    QPLL1_INIT_CFG1 = 8
    QPLL1_FBDIV = 8
    QPLL1_CFG3 = 16
    QPLL1_CP = 10
    SARC_SEL = 1
    SARC_EN = 1
    QPLL1_REFCLK_DIV = 5
    QPLL1_LPF = 10
    QPLL1_CFG1_G3 = 16
    QPLL1_CFG2_G3 = 16
    QPLL1_LPF_G3 = 10
    QPLL1_LOCK_CFG_G3 = 16
    RSVD_ATTR2 = 16
    QPLL1_FBDIV_G3 = 8
    RXRECCLKOUT1_SEL = 2
    QPLL1_SDM_CFG0 = 16
    QPLL1_SDM_CFG1 = 16
    SDM1INITSEED0_0 = 16
    SDM1INITSEED0_1 = 9
    QPLL1_SDM_CFG2 = 16
