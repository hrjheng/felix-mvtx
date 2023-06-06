#!/usr/bin/env python3.9

import socket
import sys, os
import configparser

script_path=os.path.dirname(os.path.realpath(__file__))+'/'
genconf = configparser.ConfigParser()
genconf.read(script_path+'../../config/rcs_setup.cfg')

SETUP = sys.argv[1]
assert SETUP in genconf.sections()

HOST = genconf.get(SETUP, 'host')
PORT = genconf.getint(SETUP, 'port')

data = " ".join(sys.argv[2:])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT))
    sock.sendall(bytes(data + "\n", "utf-8"))

    received = str(sock.recv(1024), "utf-8")

print("Sent:     {}".format(data))
print("Received: {}".format(received))
