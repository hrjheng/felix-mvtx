#!/usr/bin/env python3

import sys
import os
from tkinter import *

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

import hameg


COMPORT_H = "/dev/ttyHAMEG0"


class PowerGui(Frame):
    def __init__(self, master=None):

        self.root = master
        Frame.__init__(self, master)
        self.pack()

        self.hameg = hameg.Hameg(port=COMPORT_H)
        #self.hameg.configure_channel(3, 5.0, 2.8)

        self.v_h1 = StringVar()
        self.a_h1 = StringVar()
        self.v_h2 = StringVar()
        self.a_h2 = StringVar()
        self.v_h3 = StringVar()
        self.a_h3 = StringVar()
        self.v_h4 = StringVar()
        self.a_h4 = StringVar()

        self.v_h1.set(str(self.hameg.get_voltage(1)))
        self.a_h1.set(str(self.hameg.get_current(1)))
        self.v_h2.set(str(self.hameg.get_voltage(2)))
        self.a_h2.set(str(self.hameg.get_current(2)))
        self.v_h3.set(str(self.hameg.get_voltage(3)))
        self.a_h3.set(str(self.hameg.get_current(3)))
        self.v_h4.set(str(self.hameg.get_voltage(3)))
        self.a_h4.set(str(self.hameg.get_current(3)))

        # HAMEG Channel 1:
        Label(self,
              text="RUv2",
              width=15, height=2).grid(column=1, row=1)
        Label(self,
              textvariable=self.v_h1,
              width=15, height=2).grid(column=1, row=2)
        Label(self,
              textvariable=self.a_h1,
              width=15, height=2).grid(column=1, row=3)
        Button(self,
               text="Act",
               command = lambda: self.hameg.activate_channel(1)
        ).grid(column=1, row=4)
        Button(self,
               text="DeAct",
               command = lambda: self.hameg.deactivate_channel(1)
        ).grid(column=1, row=5)
        Button(self,
               text="quit",
               command = self._quit_
        ).grid(column=1, row=7)

        # HAMEG Channel 2:
        Label(self,
              text="PB 5V",
              width=15, height=2).grid(column=2, row=1)
        Label(self,
              textvariable=self.v_h2,
              width=15, height=2).grid(column=2, row=2)
        Label(self,
              textvariable=self.a_h2,
              width=15, height=2).grid(column=2, row=3)
        Button(self,
               text="Act",
               command = lambda: self.hameg.activate_channel(2)
        ).grid(column=2, row=4)
        Button(self,
               text="DeAct",
               command = lambda: self.hameg.deactivate_channel(2)
        ).grid(column=2, row=5)
        Button(self,
               text="Out",
               command = lambda: self.hameg.activate_output(True)
        ).grid(column=2, row=7)

        # HAMEG Channel 3:
        Label(self,
              text="PB 3.3V",
              width=15, height=2).grid(column=3, row=1)
        Label(self,
              textvariable=self.v_h3,
              width=15, height=2).grid(column=3, row=2)
        Label(self,
              textvariable=self.a_h3,
              width=15, height=2).grid(column=3, row=3)
        Button(self,
               text="Act",
               command = lambda: self.activate_pb()
               ).grid(column=3, row=4)
        Button(self,
               text="DeAct",
               command = lambda: self.hameg.deactivate_channel(3)
        ).grid(column=3, row=5)
        Button(self,
               text="Fuse On",
               command = lambda: self.hameg.fuse_on(3)
        ).grid(column=3, row=6)
        Button(self,
               text="Off",
               command = lambda: self.hameg.activate_output(False)
        ).grid(column=3, row=7)

        # HAMEG Channel 4:
        Label(self,
              text="Ch 4",
              width=15, height=2).grid(column=4, row=1)
        Label(self,
              textvariable=self.v_h4,
              width=15, height=2).grid(column=4, row=2)
        Label(self,
              textvariable=self.a_h4,
              width=15, height=2).grid(column=4, row=3)
        Button(self,
               text="Act",
               command = lambda: self.hameg.activate_channel(4)
        ).grid(column=4, row=4)
        Button(self,
               text="DeAct",
               command = lambda: self.hameg.deactivate_channel(4)
        ).grid(column=4, row=5)

        self.root.configure(bg="grey")
        self.root.update()

    def _quit_(self):
        self.root.destroy()

    def activate_pb(self):
        self.hameg.fuse_off(3)
        self.hameg.activate_channel(3)

    def periodic_task(self):
        self.v_h1.set(str(self.hameg.get_voltage(1)))
        self.a_h1.set(str(round(self.hameg.get_current(1))))
        self.v_h2.set(str(self.hameg.get_voltage(2)))
        self.a_h2.set(str(round(self.hameg.get_current(2))))
        self.v_h3.set(str(self.hameg.get_voltage(3)))
        self.a_h3.set(str(round(self.hameg.get_current(3))))
        self.v_h4.set(str(self.hameg.get_voltage(4)))
        self.a_h4.set(str(round(self.hameg.get_current(4))))

        #print(self.hameg.get_voltage(1))
        #print(self.hameg.get_current(1))
        #print(self.hameg.get_voltage(2))
        #print(self.hameg.get_current(2))
        #print(self.hameg.get_voltage(3))
        #print(self.hameg.get_current(3))

        self.root.update()
        self.root.after(500,self.periodic_task)


root = Tk()
root.title("POWER GUI")

app = PowerGui(master=root)
root.after(1000, app.periodic_task)
root.protocol("WM_DELETE_WINDOW", app._quit_)

root.mainloop()
