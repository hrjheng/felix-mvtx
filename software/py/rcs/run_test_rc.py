#!/usr/bin/env python3.9

import socket
import sys, os, time
import configparser
import logging
import argparse

script_path=os.path.dirname(os.path.realpath(__file__))+'/'
genconf = configparser.ConfigParser()
genconf.read(script_path+'../../config/rcs_setup.cfg')

# read from config in main
HOST_LIST = []

def snd_rcv_one(cmd, host, port):
    start_time = time.time()
    logging.debug(cmd + ': Sending on {}:{}'.format(host,port))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(bytes(cmd + "\n", "utf-8"))
        ret = str(sock.recv(1024), "utf-8").strip()
    end_time = time.time()
    logging.debug(ret + ' (returned in {:.1f})'.format(end_time-start_time) )
    return ret,end_time-start_time

def snd_rcv(cmd, catch_errors=True):
    start = time.time()
    ret_list = []
    logging.info('Sending '+cmd)
    # send
    socks = []
    for setup,host,port in HOST_LIST:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall(bytes(cmd + "\n", "utf-8"))
        socks.append([setup,sock,time.time()])
    for setup,sock,start_time in socks:
        ret = str(sock.recv(1024), "utf-8").strip()
        t = time.time()-start_time
        sock.close()
        logging.info('  {:<5s}'.format(setup)+': '+ret+' (returned in {:.2f})'.format(t) )
        ret_list.append(ret)
    if not catch_errors: return ret_list
    for ret in ret_list:
        if 'error' in ret.lower():
            snd_rcv('STOP_TRIGGER_LTU', catch_errors=False)
            snd_rcv('TEAR_DOWN', catch_errors=False)
            snd_rcv('STOP_READOUT', catch_errors=False)
            snd_rcv('STOP', catch_errors=False)
            sys.exit()
    return ret_list


###################################################################
if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="A script to run in pair with Run Control Server to execute a test.")
    argparser.add_argument('setups', metavar='SETUPS', choices=genconf.sections()+['ALL']+['BOT']+['TOP']+['ALL_NO_L6T'], type=lambda s: s.upper(),
                           nargs='*', help='Setups to run the test on.')
    args = argparser.parse_args()
    print(args)

    if 'ALL' in args.setups: args.setups = ['PP1I7', 'PP1O0', 'PP1I6', 'PP1O6', 'PP1I2', 'PP1I5', 'PP1I25', 'PP1O7', 'PP1I0', 'PP1O1', 'PP1I1', 'PP1O2', 'PP1O5', 'PP1O25']
    if 'BOT' in args.setups: args.setups = ['PP1I7', 'PP1O0', 'PP1I6', 'PP1O6', 'PP1I2', 'PP1I5', 'PP1I25']
    if 'TOP' in args.setups: args.setups = ['PP1I0', 'PP1O7', 'PP1O1', 'PP1I1', 'PP1O2', 'PP1O5', 'PP1O25']
    if 'ALL_NO_L6T' in args.setups: args.setups = ['PP1I7', 'PP1O0', 'PP1I6', 'PP1O6', 'PP1I2', 'PP1I5', 'PP1I25', 'PP1O1', 'PP1I1', 'PP1O2', 'PP1O5', 'PP1O25']
    for setup in args.setups:
        host = genconf.get(setup, 'host')
        port = genconf.getint(setup, 'port')
        HOST_LIST.append((setup,host,port))

    # setup logging
    logging.getLogger().setLevel(logging.INFO)
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")    
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(log_format)
    logging.getLogger().addHandler(sh)

    # run procedure
    for cmd in ['SETUP_NEW_RUN', 'PREPARE_FOR_TRIGGERS', 'START_RUN', 'TEAR_DOWN', 'STOP_READOUT', 'STOP', 'MOVE_DATA']:
        snd_rcv(cmd)
        
    logging.info('Finished')
