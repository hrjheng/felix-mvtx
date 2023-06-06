"""Implements the control for the ws_gbt_word_inject wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule
import trigger

@unique
class WsGbtWordInjectAddress(IntEnum):
    """Memory mapping for the ws_gbt_word_inject taken from gbtx_word_inject.vhd"""
    GBT0              = 0x00
    GBT1              = 0x01
    GBT2              = 0x02
    GBT3              = 0x03
    GBT4              = 0x04
    GBT5              = 0x05
    NUM_TRG_PER_TRAIN = 0x06
    TRG_SPACING_LSB   = 0x07
    TRAIN_SPACING_LSB = 0x08
    NUM_TRAIN         = 0x09
    TRG_SPACING_MSB   = 0x0A
    TRAIN_SPACING_MSB = 0x0B

@unique
class TriggerExecute(IntEnum):
    TRG_EXECUTE            = 0x1
    TRAIN_EXECUTE          = 0x2
    TRAIN_EXECUTE_BUS_HOLD = 0x4

class WsGbtWordInject(WishboneModule):
    """Wishbone slave for injecting GBT words"""

    def __init__(self, moduleid, board_obj):
        super(WsGbtWordInject, self).__init__(moduleid=moduleid, name="GBT word inject", board_obj=board_obj)
        self.num_triggers_per_train = 0
        self.trigger_spacing = 0
        self.train_spacing = 0
        self.num_trains = 0

    def _inject_word(self, word, inject_train=False, use_wb_hold=False, commitTransaction=True):
        """Injects a GBT word into the trigger pipeline, if inject_train is set, then this is to be executed as a train"""
        assert (word | 0xFFFFFFFFFFFFFFFFFFFF == 0xFFFFFFFFFFFFFFFFFFFF), "Injected word must be 80 bits"
        self.write(WsGbtWordInjectAddress.GBT0, (word >>  0) & 0xFFFF, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.GBT1, (word >> 16) & 0xFFFF, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.GBT2, (word >> 32) & 0xFFFF, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.GBT3, (word >> 48) & 0xFFFF, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.GBT4, (word >> 64) & 0xFFFF, commitTransaction=False)
        if inject_train:
            if use_wb_hold:
                self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRAIN_EXECUTE_BUS_HOLD, commitTransaction=commitTransaction)
            else:
                self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRAIN_EXECUTE, commitTransaction=commitTransaction)
        else:
            self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRG_EXECUTE, commitTransaction=commitTransaction)

    def send_trigger(self, triggerType=0x10, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a trigger with the parameters given"""
        assert triggerType | 0xFFF == 0xFFF
        assert bc | 0xFFF == 0xFFF
        assert orbit | 0xFFFFFFFF == 0xFFFFFFFF
        self._inject_word(word=((orbit << 48) | (bc << 32) | triggerType), inject_train=False, commitTransaction=commitTransaction)

    def send_trigger_train(self, num_triggers_per_train, trigger_spacing, num_trains, train_spacing,
                           triggerType=0x10, bc=0xabc, orbit=0x43215678, wait_until_done=True, hold_wb_bus=False, commitTransaction=True):
        """Sends a train og triggers with the parameters given"""
        assert triggerType | 0xFFF == 0xFFF
        assert bc | 0xFFF == 0xFFF
        assert orbit | 0xFFFFFFFF == 0xFFFFFFFF
        assert num_triggers_per_train | 0xFFFF == 0xFFFF
        assert trigger_spacing | 0xFFFFFFFF == 0xFFFFFFFF
        assert num_trains | 0xFFFF == 0xFFFF
        assert train_spacing | 0xFFFFFFFF == 0xFFFFFFFF
        assert not (wait_until_done and hold_wb_bus), "Using both WB wait and holding of WB bus until done is unneceseary, choose either one or none"
        sequence_time = (num_triggers_per_train + trigger_spacing*(num_triggers_per_train-1))*num_trains + train_spacing*(num_trains-1)
        if hold_wb_bus:
            assert sequence_time | 0x000FFFFF == 0x000FFFFF, "Trigger sequence longer than WB watchdog timeout, WB bus error will be created, use wait_until_done instead"
        trigger_spacing_lsb = trigger_spacing & 0xFFFF
        trigger_spacing_msb = (trigger_spacing >> 16) & 0xFFFF
        train_spacing_lsb = train_spacing & 0xFFFF
        train_spacing_msb = (train_spacing >> 16) & 0xFFFF
        self.write(WsGbtWordInjectAddress.NUM_TRG_PER_TRAIN, num_triggers_per_train, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.TRG_SPACING_LSB, trigger_spacing_lsb, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.TRG_SPACING_MSB, trigger_spacing_msb, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.TRAIN_SPACING_LSB, train_spacing_lsb, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.TRAIN_SPACING_MSB, train_spacing_msb, commitTransaction=False)
        self.write(WsGbtWordInjectAddress.NUM_TRAIN, num_trains, commitTransaction=False)
        self.num_triggers_per_train = num_triggers_per_train
        self.trigger_spacing = trigger_spacing
        self.train_spacing = train_spacing
        self.num_trains = num_trains
        if wait_until_done:
            self._inject_word(word=((orbit << 48) | (bc << 32) | triggerType), inject_train=True, commitTransaction=False)
            self.board.wait(sequence_time, commitTransaction=commitTransaction)
        else:
            self._inject_word(word=((orbit << 48) | (bc << 32) | triggerType), inject_train=True, use_wb_hold=hold_wb_bus, commitTransaction=commitTransaction)

    def re_execute_trigger(self, commitTransaction=True):
        """Re-executes previously loaded trigger"""
        self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRG_EXECUTE, commitTransaction=commitTransaction)

    def rerun_trigger_train(self, wait_until_done=True, hold_wb_bus=False, commitTransaction=True):
        """Reruns previously loaded trigger train"""
        assert not (wait_until_done or hold_wb_bus), "Using both WB wait and holding of WB bus until done is unneceseary, choose either one or none"
        sequence_time = (self.num_triggers_per_train + self.trigger_spacing*(self.num_triggers_per_train-1))*self.num_trains + self.train_spacing*(self.num_trains-1)
        if wait_until_done or hold_wb_bus:
            assert self.num_triggers_per_train > 0, "Run send_trigger_train first to initialize parameters, this function can not be run from fire when wait_until_done is true."
            self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRAIN_EXECUTE, commitTransaction=False)
            self.board.wait(sequence_time, commitTransaction=commitTransaction)
        elif hold_wb_bus:
            assert self.num_triggers_per_train > 0, "Run send_trigger_train first to initialize parameters, this function can not be run from fire when wait_until_done is true."
            assert sequence_time | 0x000FFFFF == 0x000FFFFF, "Trigger sequence longer than WB watchdog timeout, WB bus error will be created, use wait_until_done instead"
            self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRAIN_EXECUTE_BUS_HOLD, commitTransaction=commitTransaction)
        else:
            self.write(WsGbtWordInjectAddress.GBT5, TriggerExecute.TRAIN_EXECUTE, commitTransaction=commitTransaction)

    def send_sot(self, orbit=0x43215678, commitTransaction=True):
        """Sends a start of triggered mode trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.SOT) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.TF) | (1 << trigger.BitMap.ORBIT)),
                          bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_eot(self, orbit=0x43215678, commitTransaction=True):
        """Sends a end of triggered mode trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.EOT) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.TF) | (1 << trigger.BitMap.ORBIT)),
                          bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_soc(self, orbit=0x43215678, commitTransaction=True):
        """Sends a start of continous mode trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.SOC) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.TF) | (1 << trigger.BitMap.ORBIT)),
                          bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_eoc(self, orbit=0x43215678, commitTransaction=True):
        """Sends a end of continous mode trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.EOC) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.TF) | (1 << trigger.BitMap.ORBIT)),
                          bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_physics(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=(1 << trigger.BitMap.PHYSICS), bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def send_hb_accept(self, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.HB) | (1 << trigger.BitMap.ORBIT)), bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_hb_reject(self, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.HBr) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.ORBIT)), bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def send_hb_check(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=(1 << trigger.BitMap.HC), bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def send_prepulse(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=(1 << trigger.BitMap.PP), bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def send_calibration(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=(1 << trigger.BitMap.CAL), bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def send_timeframe(self, orbit=0x43215678, commitTransaction=True):
        """Sends a physics trigger"""
        self.send_trigger(triggerType=((1 << trigger.BitMap.TF) | (1 << trigger.BitMap.ORBIT) | (1 << trigger.BitMap.HB)), bc=0, orbit=orbit, commitTransaction=commitTransaction)

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsGbtWordInjectAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
