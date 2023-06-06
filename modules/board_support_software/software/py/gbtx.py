from enum import IntEnum, unique

import logging
from xml.dom import minidom
import os
import time

from ws_i2c_gbtx import WsI2cGbtx


@unique
class Controller(IntEnum):
    """Class to decide how to control the GBTX"""
    RDO = 0
    SCA = 1


@unique
class GBTxAddress(IntEnum):
    """GBTx addrees (WIP)"""
    ckCtr0             = 0
    ckCtr1             = 1
    ckCtr2             = 2
    ckCtr3             = 3
    ckCtr4             = 273
    ckCtr5             = 274
    ckCtr6             = 275
    ckCtr7             = 276
    ckCtr8             = 277
    ckCtr9             = 278
    ckCtr10            = 279
    ckCtr11            = 280
    ckCtr12            = 281
    ckCtr13            = 282
    ckCtr14            = 283
    ckCtr15            = 284
    ckCtr16            = 285
    ckCtr17            = 286
    ckCtr18            = 287
    ckCtr19            = 288
    ckCtr20            = 289
    ckCtr21            = 290
    ckCtr22            = 291
    ckCtr23            = 292
    ckCtr24            = 293
    ckCtr25            = 294
    ckCtr26            = 295
    ckCtr27            = 296
    ckCtr28            = 297
    ckCtr29            = 298
    ckCtr30            = 299
    ckCtr31            = 300
    ckCtr32            = 301
    ckCtr33            = 302
    ckCtr34            = 303
    ckCtr35            = 304
    ckCtr36            = 305
    ckCtr37            = 306
    ckCtr38            = 307
    ckCtr39            = 308
    ckCtr40            = 309
    ckCtr41            = 310
    ckCtr42            = 311
    ckCtr43            = 312
    ckCtr44            = 313
    ckCtr45            = 314
    ckCtr46            = 315
    ckCtr47            = 316
    ckCtr48            = 317
    ckCtr49            = 318
    ckCtr50            = 319

    ttcCtr0            = 4
    ttcCtr1            = 5
    ttcCtr2            = 6
    ttcCtr3            = 7
    ttcCtr4            = 8
    ttcCtr5            = 9
    ttcCtr6            = 10
    ttcCtr7            = 11
    ttcCtr8            = 12
    ttcCtr9            = 13
    ttcCtr10           = 14
    ttcCtr11           = 15
    ttcCtr12           = 16
    ttcCtr13           = 17
    ttcCtr14           = 18
    ttcCtr15           = 19
    ttcCtr16           = 20
    ttcCtr17           = 21
    ttcCtr18           = 22
    ttcCtr19           = 23
    ttcCtr20           = 24
    ttcCtr21           = 25
    ttcCtr22           = 26
    ttcCtr23           = 269
    ttcCtr24           = 270
    ttcCtr25           = 271
    ttcCtr26           = 272

    serCtr0            = 27

    txCtr0             = 28
    txCtr1             = 29
    txCtr2             = 30
    txCtr3             = 31
    txCtr4             = 32
    txCtr5             = 33

    desCtr0            = 34

    rxCtr0             = 35
    rxCtr1             = 36
    rxCtr2             = 37
    rxCtr3             = 38
    rxCtr4             = 39
    rxCtr5             = 40
    rxCtr6             = 41
    rxCtr7             = 42
    rxCtr8             = 43
    rxCtr9             = 44
    rxCtr10            = 45
    rxCtr11            = 46
    rxCtr12            = 47
    rxCtr13            = 48
    rxCtr14            = 49

    wdogCtr0           = 50
    wdogCtr1           = 51
    wdogCtr2           = 52
    wdogCtr3           = 53
    wdogCtr4           = 54
    configDone         = 365

    gbld_w0            = 55
    gbld_w1            = 56
    gbld_w2            = 57
    gbld_w3            = 58
    gbld_w4            = 59
    gbld_w5            = 60
    gbld_w6            = 61
    gbld_ID            = 253
    gbld_write         = 388
    gbld_read          = 389

    inEportCtr0        = 62
    inEportCtr1        = 63
    inEportCtr2        = 64
    inEportCtr3        = 65
    inEportCtr4        = 66
    inEportCtr5        = 67
    inEportCtr6        = 68
    inEportCtr7        = 69
    inEportCtr8        = 70
    inEportCtr9        = 71
    inEportCtr10       = 72
    inEportCtr11       = 73
    inEportCtr12       = 74
    inEportCtr13       = 75
    inEportCtr14       = 76
    inEportCtr15       = 77
    inEportCtr16       = 78
    inEportCtr17       = 79
    inEportCtr18       = 80
    inEportCtr19       = 81
    inEportCtr20       = 82
    inEportCtr21       = 83
    inEportCtr22       = 84
    inEportCtr23       = 85
    inEportCtr24       = 86
    inEportCtr25       = 87
    inEportCtr26       = 88
    inEportCtr27       = 89
    inEportCtr28       = 90
    inEportCtr29       = 91
    inEportCtr30       = 92
    inEportCtr31       = 93
    inEportCtr32       = 94
    inEportCtr33       = 95
    inEportCtr34       = 96
    inEportCtr35       = 97
    inEportCtr36       = 98
    inEportCtr37       = 99
    inEportCtr38       = 100
    inEportCtr39       = 101
    inEportCtr40       = 102
    inEportCtr41       = 103
    inEportCtr42       = 104
    inEportCtr43       = 105
    inEportCtr44       = 106
    inEportCtr45       = 107
    inEportCtr46       = 108
    inEportCtr47       = 109
    inEportCtr48       = 110
    inEportCtr49       = 111
    inEportCtr50       = 112
    inEportCtr51       = 113
    inEportCtr52       = 114
    inEportCtr53       = 115
    inEportCtr54       = 116
    inEportCtr55       = 117
    inEportCtr56       = 118
    inEportCtr57       = 119
    inEportCtr58       = 120
    inEportCtr59       = 121
    inEportCtr60       = 122
    inEportCtr61       = 123
    inEportCtr62       = 124
    inEportCtr63       = 125
    inEportCtr64       = 126
    inEportCtr65       = 127
    inEportCtr66       = 128
    inEportCtr67       = 129
    inEportCtr68       = 130
    inEportCtr69       = 131
    inEportCtr70       = 132
    inEportCtr71       = 133
    inEportCtr72       = 134
    inEportCtr73       = 135
    inEportCtr74       = 136
    inEportCtr75       = 137
    inEportCtr76       = 138
    inEportCtr77       = 139
    inEportCtr78       = 140
    inEportCtr79       = 141
    inEportCtr80       = 142
    inEportCtr81       = 143
    inEportCtr82       = 144
    inEportCtr83       = 145
    inEportCtr84       = 146
    inEportCtr85       = 147
    inEportCtr86       = 148
    inEportCtr87       = 149
    inEportCtr88       = 150
    inEportCtr89       = 151
    inEportCtr90       = 152
    inEportCtr91       = 153
    inEportCtr92       = 154
    inEportCtr93       = 155
    inEportCtr94       = 156
    inEportCtr95       = 157
    inEportCtr96       = 158
    inEportCtr97       = 159
    inEportCtr98       = 160
    inEportCtr99       = 161
    inEportCtr100      = 162
    inEportCtr101      = 163
    inEportCtr102      = 164
    inEportCtr103      = 165
    inEportCtr104      = 166
    inEportCtr105      = 167
    inEportCtr106      = 168
    inEportCtr107      = 169
    inEportCtr108      = 170
    inEportCtr109      = 171
    inEportCtr110      = 172
    inEportCtr111      = 173
    inEportCtr112      = 174
    inEportCtr113      = 175
    inEportCtr114      = 176
    inEportCtr115      = 177
    inEportCtr116      = 178
    inEportCtr117      = 179
    inEportCtr118      = 180
    inEportCtr119      = 181
    inEportCtr120      = 182
    inEportCtr121      = 183
    inEportCtr122      = 184
    inEportCtr123      = 185
    inEportCtr124      = 186
    inEportCtr125      = 187
    inEportCtr126      = 188
    inEportCtr127      = 189
    inEportCtr128      = 190
    inEportCtr129      = 191
    inEportCtr130      = 192
    inEportCtr131      = 193
    inEportCtr132      = 194
    inEportCtr133      = 195
    inEportCtr134      = 196
    inEportCtr135      = 197
    inEportCtr136      = 198
    inEportCtr137      = 199
    inEportCtr138      = 200
    inEportCtr139      = 201
    inEportCtr140      = 202
    inEportCtr141      = 203
    inEportCtr142      = 204
    inEportCtr143      = 205
    inEportCtr144      = 206
    inEportCtr145      = 207
    inEportCtr146      = 208
    inEportCtr147      = 209
    inEportCtr148      = 210
    inEportCtr149      = 211
    inEportCtr150      = 212
    inEportCtr151      = 213
    inEportCtr152      = 214
    inEportCtr153      = 215
    inEportCtr154      = 216
    inEportCtr155      = 217
    inEportCtr156      = 218
    inEportCtr157      = 219
    inEportCtr158      = 220
    inEportCtr159      = 221
    inEportCtr160      = 222
    inEportCtr161      = 223
    inEportCtr162      = 224
    inEportCtr163      = 225
    inEportCtr164      = 226
    inEportCtr165      = 227
    inEportCtr166      = 228
    inEportCtr167      = 229
    inEportCtr168      = 230
    inEportCtr169      = 231
    inEportCtr170      = 232
    inEportCtr171      = 233
    inEportCtr172      = 234
    inEportCtr173      = 235
    inEportCtr174      = 236
    inEportCtr175      = 237
    fuseBlowAddressLSB = 238
    fuseBlowAddressMSB = 239
    fuseBlowData       = 240
    inEportCtr179      = 241
    inEportCtr180      = 242
    inEportCtr181      = 243
    inEportCtr182      = 244
    inEportCtr183      = 245
    inEportCtr184      = 246
    inEportCtr185      = 247
    inEportCtr186      = 248
    inEportCtr187      = 249
    inEportCtr188      = 250
    inEportCtr189      = 251
    inEportCtr190      = 252
    inEportCtr192      = 320
    inEportCtr193      = 321
    inEportCtr194      = 322
    inEportCtr195      = 323
    inEportCtr196      = 324
    inEportCtr197      = 325
    inEportCtr198      = 326

    outEportCtr0       = 254
    outEportCtr1       = 255
    outEportCtr2       = 256
    outEportCtr3       = 257
    outEportCtr4       = 258
    outEportCtr5       = 259
    outEportCtr6       = 260
    outEportCtr7       = 261
    outEportCtr8       = 262
    outEportCtr9       = 263
    outEportCtr10      = 264
    outEportCtr11      = 265
    outEportCtr12      = 266
    outEportCtr13      = 267
    outEportCtr14      = 268
    outEportCtr15      = 327
    outEportCtr16      = 328
    outEportCtr17      = 329
    outEportCtr18      = 330
    outEportCtr19      = 331
    outEportCtr20      = 332
    outEportCtr21      = 333
    outEportCtr22      = 334
    outEportCtr23      = 335
    outEportCtr24      = 336
    outEportCtr25      = 337
    outEportCtr26      = 338
    outEportCtr27      = 339
    outEportCtr28      = 340
    outEportCtr29      = 341
    outEportCtr30      = 342
    outEportCtr31      = 343
    outEportCtr32      = 344
    outEportCtr33      = 345
    outEportCtr34      = 346
    outEportCtr35      = 347
    outEportCtr36      = 348
    outEportCtr37      = 349
    outEportCtr38      = 350
    outEportCtr39      = 351
    outEportCtr40      = 352
    outEportCtr41      = 353
    outEportCtr42      = 354
    outEportCtr43      = 355
    outEportCtr44      = 356
    outEportCtr45      = 357
    outEportCtr46      = 358
    outEportCtr47      = 359
    outEportCtr48      = 360
    outEportCtr49      = 361

    # Read Only
    configFuseData          = 366
    testFuseData1           = 367
    testFuseData2           = 368
    BERTCounterLSB          = 369
    BERTCounterMSB          = 370
    scStatusA               = 371
    scStatusB               = 372
    scStatusC               = 373
    config_reg_error_count  = 375
    status0                 = 376
    status1                 = 377
    status2                 = 378
    status3                 = 379
    status4                 = 380
    gbld_r0                 = 381
    gbld_r1                 = 382
    gbld_r2                 = 383
    gbld_r3                 = 384
    gbld_r4                 = 385
    gbld_r5                 = 386
    gbld_r6                 = 387
    dllLocked               = 390
    channelLockedGroup0     = 391
    channelLockedGroup1     = 392
    channelLockedGroup2     = 393
    channelLockedGroup3     = 394
    channelLockedGroup4     = 395
    channelLockedGroup5     = 396
    channelLockedGroup6     = 397
    phaseSelectOutEc        = 398
    phaseSelectOutGroup0_0  = 399
    phaseSelectOutGroup0_1  = 400
    phaseSelectOutGroup0_2  = 401
    phaseSelectOutGroup0_3  = 402
    phaseSelectOutGroup1_0  = 403
    phaseSelectOutGroup1_1  = 404
    phaseSelectOutGroup1_2  = 405
    phaseSelectOutGroup1_3  = 406
    phaseSelectOutGroup2_0  = 407
    phaseSelectOutGroup2_1  = 408
    phaseSelectOutGroup2_2  = 409
    phaseSelectOutGroup2_3  = 410
    phaseSelectOutGroup3_0  = 411
    phaseSelectOutGroup3_1  = 412
    phaseSelectOutGroup3_2  = 413
    phaseSelectOutGroup3_3  = 414
    phaseSelectOutGroup4_0  = 415
    phaseSelectOutGroup4_1  = 416
    phaseSelectOutGroup4_2  = 417
    phaseSelectOutGroup4_3  = 418
    phaseSelectOutGroup5_0  = 419
    phaseSelectOutGroup5_1  = 420
    phaseSelectOutGroup5_2  = 421
    phaseSelectOutGroup5_3  = 422
    phaseSelectOutGroup6_0  = 423
    phaseSelectOutGroup6_1  = 424
    phaseSelectOutGroup6_2  = 425
    phaseSelectOutGroup6_3  = 426
    TxRxEPllLocked          = 427
    phase_shifter           = 428
    ttcEarly                = 429
    ttcLate                 = 430
    InstLockPuFSM           = 431
    rxRefPllLossOfLockCount = 432
    EPLLTXlossOfLockCount   = 433
    EPLLRXlossOfLockCount   = 434
    FECcorrectionCount      = 435


@unique
class TxSwitchesControlTxSwitch0(IntEnum):
    """P62 GBTx Manual"""
    All0            = 0
    Standard        = 1
    All0Alt         = 2
    RxSwtich0Output = 3


@unique
class TxSwitchesControlTxSwitch1(IntEnum):
    """P62 GBTx Manual"""
    TxSwitch0Output = 0
    Scrambler       = 1
    All0            = 2
    RxSwtich1Output = 3


@unique
class TxSwitchesControlTxSwitch2(IntEnum):
    """P62 GBTx Manual"""
    TxSwitch1Output             = 0
    FecEncoderInterleaverOutput = 1
    All0                        = 2
    RxSwtich2Output             = 3


@unique
class Loopback(IntEnum):
    """P62 GBTx Manual"""
    A = 0
    B = 1
    C = 2

@unique
class GBTxPuFSMStatus(IntEnum):
    reset           = 0
    waitVCOstable   = 25
    FCLRN           = 1
    Contention      = 2
    FSETP           = 3
    Update          = 4
    pauseForConfig  = 5
    initXPLL        = 6
    waitXPLLLock    = 7
    resetDES1       = 8
    resetDES2       = 9
    waitDESLock     = 10
    resetRXEPLL1    = 11
    resetRXEPL2     = 12
    waitRXEPLLLock  = 13
    resetSER1       = 14
    resetSER2       = 15
    waitSERLock     = 16
    resetTXEPLL1    = 17
    resetTXEPLL2    = 18
    waitTXEPLLLock  = 19
    dllReset        = 20
    waitdllLocked   = 21
    paReset         = 22
    initScram       = 23
    resetPSpll1     = 26
    resetPSpll2     = 27
    waitPSpllLocked = 28
    resetPSdll      = 29
    waitPSdllLocked = 30
    Idle            = 24

minimal_config_internal_clock_index = [27, 29, 30, 31, 32, 34, 35, 37, 38, 39, 41, 46, 47, 48, 50, 52, 242, 243, 244, 281, 283, 313, 314, 315, 316, 317, 318]
minimal_config_external_clock_index = [27, 29, 30, 31, 32, 34, 35, 37, 38, 39, 41, 46, 47, 48, 50, 52, 242, 243, 244, 283]

class GBTx(object):
    """Implementation of the GBTx chip on the RU"""

    def __init__(self, index, board=None, sca=None):
        """init"""
        self._index = None
        self._board = None
        self._sca = None
        self._controller = None
        self._controller_type = None
        self._read_function = None
        self._write_function = None

        self.set_index(index)
        self.set_board(board)
        self.set_sca(sca)
        self.set_controller()
        self.logger = logging.getLogger("GBTx {0}".format(index))

    def set_index(self, index):
        assert index in range(3)
        self._index = index

    def get_index(self):
        return self._index

    def set_board(self, board):
        self._board = board

    def get_board(self):
        return self._board

    def set_sca(self, sca):
        self._sca = sca

    def get_sca(self):
        return self._sca

    def set_controller(self, value=None):
        if value is not None:
            value = Controller(value)
            self._controller_type = value
        elif self._board is not None and self._sca is None:
            self._controller_type = Controller.RDO
            self._controller = self._board.i2c_gbtx
        elif self._board is None and self._sca is not None:
            self._controller_type = Controller.SCA
            self._controller = self._sca
        else:
            raise NotImplementedError

    def get_controller_type(self):
        return self._controller_type

    def write(self, register, value, check=True):
        assert self._controller_type is not None
        self._controller.write_gbtx_register(gbtx_index=self._index, register=register, value=value, check=check)

    def read(self, register, check=True):
        assert self._controller_type is not None
        return self._controller.read_gbtx_register(gbtx_index=self._index, register=register, check=check)

    def reset_controller_counters(self):
        if self._controller_type is Controller.RDO:
            self._controller.reset_counters()
        elif self._controller_type is Controller.SCA:
            pass
        else:
            raise NotImplementedError("No reset implemented!")

    # Config

    def _get_config_registers_xml(self, filename):

        filename = os.path.realpath(filename)
        assert os.path.isfile(filename), f"File not found: {filename}"
        xmldoc = minidom.parse(filename)
        signalList = xmldoc.getElementsByTagName("Signal")

        reg = [0] * 366
        for signal in signalList:
            name = signal.attributes["name"].value
            tripl = True if (signal.attributes["triplicated"].value == "true") else False
            nob = int(signal.attributes["numberBits"].value)
            val = int(signal.getElementsByTagName("value")[0].firstChild.data)
            startAddr0 = int(signal.getElementsByTagName("location")[0].getAttribute("startAddress"))
            startBit0 = int(signal.getElementsByTagName("location")[0].getAttribute("startBitIndex"))
            lastBit0 = int(signal.getElementsByTagName("location")[0].getAttribute("lastBitIndex"))
            reg[startAddr0] |= (val << startBit0)
            if tripl:
                startAddr1 = int(signal.getElementsByTagName("location")[1].getAttribute("startAddress"))
                startBit1 = int(signal.getElementsByTagName("location")[1].getAttribute("startBitIndex"))
                lastBit1 = int(signal.getElementsByTagName("location")[1].getAttribute("lastBitIndex"))
                reg[startAddr1] |= val << startBit1

                startAddr2 = int(signal.getElementsByTagName("location")[2].getAttribute("startAddress"))
                startBit2 = int(signal.getElementsByTagName("location")[2].getAttribute("startBitIndex"))
                lastBit2 = int(signal.getElementsByTagName("location")[2].getAttribute("lastBitIndex"))
                reg[startAddr2] |= val << startBit2

        # Convert to list of tuples
        reg_tuples = [(reg, val) for reg, val in enumerate(reg)]
        return reg_tuples

    def _get_config_registers_txt(self, filename, minimal=False, restart_powerup_seq=True):
        filename = os.path.realpath(filename)
        assert os.path.isfile(filename), f"File not found: {filename}"
        with open(filename) as f:
            lines = f.readlines()
        config = [(reg, int(val, 16)) for (reg, val) in enumerate(lines)]
        if not restart_powerup_seq:
            config = config[:-1]
        if minimal is not False:
            if minimal == "Internal":
                index = minimal_config_internal_clock_index
                config = [config[i] for i in index]
            elif minimal == "External":
                index = minimal_config_external_clock_index
                config = [config[i] for i in index]
        return config

    def configure(self, filename, check=False, pre_check_fsm=True, use_xml=False, minimal=False, restart_powerup_seq=True, verbose=False):
        """Write GBTx xml configuration data in file "filename" to GBTx "gbtx_index" """
        try:
            self.read(register=0)
        except:
            self.logger.error("Could not read GBTx - stopping config!")
            return False, False
        pu_fsm_status = self.read_fsm_status()
        if not self.is_gbtx_ready_for_config(pu_fsm_status) and pre_check_fsm:
            if self.is_gbtx_config_completed(pu_fsm_status):
                if verbose:
                    self.logger.warning("GBTx already configured. Run with --pre_check_fsm=False to ignore this and run anyway.")
                return True, True
            else:
                self.logger.error(f"GBTx not paused for config - stopping config! Current state: {GBTxPuFSMStatus(pu_fsm_status).name}")
                return False, False
        self.reset_controller_counters()
        if use_xml:
            regs = self._get_config_registers_xml(filename=filename)
        else:
            regs = self._get_config_registers_txt(filename=filename, minimal=minimal, restart_powerup_seq=restart_powerup_seq)
        self._controller.gbtx_config(registers=regs, gbtx_index=self._index, check=check)
        if not check:
            time.sleep(1)
        return self.is_gbtx_config_completed(), False

    def check_config(self, filename, use_xml=False, minimal=False):
        self.reset_controller_counters()
        if use_xml:
            regs = self._get_config_registers_xml(filename=filename)
        else:
            regs = self._get_config_registers_txt(filename=filename, minimal=minimal)
        return self._controller.check_gbtx_config(registers=regs, gbtx_index=self._index)

    def dump_config(self):
        vals = []
        for reg in range(366):
            vals.append(f"{self.read(reg):02x}")
        return vals

    def set_xpll_mode_xosc(self):
        self.write(GBTxAddress.ckCtr44, 0x4e)
        self.write(GBTxAddress.ckCtr45, 0x4e)
        self.write(GBTxAddress.ckCtr46, 0x4e)

    def set_xpll_mode_pll(self):
        self.write(GBTxAddress.ckCtr44, 0xce)
        self.write(GBTxAddress.ckCtr45, 0xce)
        self.write(GBTxAddress.ckCtr46, 0xce)

    # Resets

    def reset(self):
        self.reset_tx_logic()
        self.reset_tx_control()
        self.reset_rx_control()
        self.reset_rx()
        self.reset_rx_pll()


    def reset_tx_logic(self):
        reg_value = self.read(register=GBTxAddress.wdogCtr4)
        reg_value_reset = reg_value | (0x7)
        self.write(register=GBTxAddress.wdogCtr4, value=reg_value_reset)
        time.sleep(0.1)
        self.write(register=GBTxAddress.wdogCtr4, value=reg_value)

    def reset_tx_control(self):
        reg_value = self.read(register=GBTxAddress.txCtr5)
        reg_value_reset = reg_value | (0x7)
        self.write(register=GBTxAddress.txCtr5, value=reg_value_reset)
        time.sleep(0.1)
        self.write(register=GBTxAddress.txCtr5, value=reg_value)

    def reset_rx_control(self):
        reg_value = self.read(register=GBTxAddress.rxCtr6)
        reg_value_reset = reg_value | (0x7)
        self.write(register=GBTxAddress.rxCtr6, value=reg_value_reset)
        time.sleep(0.1)
        self.write(register=GBTxAddress.rxCtr6, value=reg_value)

    def reset_rx(self):
        reg_value = self.read(register=GBTxAddress.wdogCtr0)
        reg_value_reset = reg_value | (0x7 << 3)
        self.write(register=GBTxAddress.wdogCtr0, value=reg_value_reset)
        time.sleep(0.1)
        self.write(register=GBTxAddress.wdogCtr0, value=reg_value)

    def reset_rx_pll(self):
        reg_value = self.read(register=GBTxAddress.wdogCtr3)
        reg_value_reset = reg_value | (0x3F)
        self.write(register=GBTxAddress.wdogCtr3, value=reg_value_reset)
        time.sleep(0.1)
        self.write(register=GBTxAddress.wdogCtr3, value=reg_value)


    # Address access
    def getreg_fec(self):
        """Return the Forward Error Correction counter"""
        return self.read(register=GBTxAddress.FECcorrectionCount)

    def setreg_coarse_delay(self, channel, delay):
        """Sets the coarse delay for the clock of the clock for the channel"""
        assert delay in range(0x1F+1)
        assert channel in range(8)
        return self.write(register=GBTxAddress.ttcCtr4+channel, value=delay)

    def getreg_coarse_delay(self, channel):
        """Gets the coarse delay for the clock of the clock for the channel"""
        assert channel in range(8)
        return self.read(register=GBTxAddress.ttcCtr4+channel)

    def setreg_fine_delay(self, channel, delay):
        """Sets the fine delay for the clock of the clock for the channel"""
        assert delay in range(0xF+1)
        assert channel in range(8)
        register = GBTxAddress.ttcCtr0 + int(channel/2)
        pos = channel%2
        oldval = self.read(register=register)
        if pos==0:
            value = oldval & 0xF0 | delay
        else:
            value = value << 4 | oldval & 0xF
        return self.write(register=register, value=delay)

    def getreg_fine_delay(self, channel):
        """Gets the fine delay for other clock of the clock for the channel"""
        assert channel in range(8)
        register = GBTxAddress.ttcCtr0 + int(channel/2)
        pos = channel%2
        value = self.read(register=register)
        if pos == 0:
            value = value & 0xF
        else:
            value = value >> 4 & 0xF
        return value

    def getreg_instlock_pu_fsm(self):
        return self.read(register=GBTxAddress.InstLockPuFSM)

    def getreg_rx_ref_pll_lol_cnt(self):
        return self.read(register=GBTxAddress.rxRefPllLossOfLockCount)

    def getreg_rx_epll_lol_cnt(self):
        return self.read(register=GBTxAddress.EPLLRXlossOfLockCount)

    def getreg_tx_rx_pll_lock(self):
        """Gets the tx/rx pll are locked
        P203 GBTx manual"""
        return self.read(register=GBTxAddress.TxRxEPllLocked)

    def setreg_tx_switches_control(self,
                                   tx_switch_0,
                                   tx_switch_1,
                                   tx_switch_2):
        """Sets the thress register for tx_switch control
        P62 GBTX manual"""
        tx_switch_0 = TxSwitchesControlTxSwitch0(tx_switch_0)
        tx_switch_1 = TxSwitchesControlTxSwitch1(tx_switch_1)
        tx_switch_2 = TxSwitchesControlTxSwitch2(tx_switch_2)
        value = tx_switch_2<<4 | tx_switch_1 << 2 | tx_switch_0
        self.write(register=GBTxAddress.txCtr1, value=value)
        self.write(register=GBTxAddress.txCtr2, value=value)
        self.write(register=GBTxAddress.txCtr3, value=value)

    def getreg_tx_switches_control(self):
        """Gets the thress register for tx_switch control
        P62 GBTX manual"""
        value_a = self.read(register=GBTxAddress.txCtr1)
        value_b = self.read(register=GBTxAddress.txCtr2)
        value_c = self.read(register=GBTxAddress.txCtr3)
        assert value_a == value_b == value_c
        tx_switch_0 = value_a >> 0 & 0x3
        tx_switch_1 = value_a >> 2 & 0x3
        tx_switch_2 = value_a >> 4 & 0x3
        return tx_switch_0, tx_switch_1, tx_switch_2


    def get_sn(self):
        """Return the fused chip serial number"""
        lsb = self.read(register=GBTxAddress.testFuseData1)
        msb = self.read(register=GBTxAddress.testFuseData2)
        return (msb << 8) + lsb

    # Higher level methods
    def is_tx_rx_pll_locked(self):
        """Checks if the tx/rx pll are locked
        P203 GBTx manual"""
        return (self.getreg_tx_rx_pll_lock() & 0x5) == 0x5

    def read_fsm_status(self):
        return (self.getreg_instlock_pu_fsm() >> 2)

    def is_gbtx_ready_for_config(self, status=None):
        if status is None:
            status = self.read_fsm_status()
        return status == GBTxPuFSMStatus.pauseForConfig

    def is_gbtx_config_completed(self, status=None):
        if status is None:
            status = self.read_fsm_status()
        return status == GBTxPuFSMStatus.Idle

    def get_pu_fsm_status(self):
        status = self.read_fsm_status()
        if status in [e.value for e in GBTxPuFSMStatus]:
            return GBTxPuFSMStatus(status).name
        else:
            return "UNKNOWN STATE"

    def set_internal_loopback(self, loopback=Loopback.A):
        """Sets the internal loopback for the SWT"""
        loopback = Loopback(loopback)
        if loopback == Loopback.A:
            tx_switch_0 = TxSwitchesControlTxSwitch0.RxSwtich0Output
            tx_switch_1 = TxSwitchesControlTxSwitch1.Scrambler
            tx_switch_2 = TxSwitchesControlTxSwitch2.TxSwitch1Output
        else:
            raise NotImplementedError

    def set_phase_detector_charge_pump(self, value):
        """set the GBTx charge pump value"""
        assert value | 0xf == 0xf
        current_val = self.read(register=GBTxAddress.rxCtr0)
        new_val = (current_val & 0x0f) | (value<<4)
        self.write(register=GBTxAddress.rxCtr0, value=new_val, check=False)

    def get_phase_detector_charge_pump(self):
        """read the phase detector charge pump value"""
        return((self.read(register=GBTxAddress.rxCtr0, check=False))>>4)
