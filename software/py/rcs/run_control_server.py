#!/usr/bin/env python

import os, sys, time, shutil
import glob, json, logging, datetime
import argparse
import configparser
import socketserver
import subprocess
import traceback
import smtplib

script_path=os.path.dirname(os.path.realpath(__file__))+'/'
genconf = configparser.ConfigParser()
genconf.read(script_path+'../../config/rcs_setup.cfg')

path_cru_its = genconf.get('DEFAULT', 'path_cru_its')
sys.path.append(path_cru_its+'software/py/')

import testbench
from fakehitrate import FakeHitRate
from obtest import ObTest

class FakeHitScan(ObTest, FakeHitRate):
    pass

class RunControlServer(socketserver.BaseRequestHandler):
    #__________________________________________
    def setup_new_run(self):
        self.server.test = FakeHitScan()
        self.server.test.activate_tuning()
        self.server.test.setup_logging(main=True, prefix=self.server.conf.get(self.server.setup, 'log_prefix'))
        self.server.test.configure_run(config_file=self.server.conf.get(self.server.setup, 'external_daqtest_config'))
        self.server.test.setup_links(staves=json.loads(self.server.conf.get(self.server.setup, 'staves')))
        self.server.test.initialize_testbench()
        self.server.test.testbench.setup_cru()
        self.server.test.testbench.setup_ltu()
        self.server.test.setup_comms()
        self.server.test.testbench.clean_all_datapaths()

        try:
            self.server.test.testbench.cru.initialize(gbt_ch=self.server.test.config.CTRL_AND_DATA_LINK_LIST[0])
            time.sleep(1)
            try:
                self.server.test.testbench.setup_rdos(connector_nr=self.server.test.config.MAIN_CONNECTOR)
                for rdo in self.server.test.testbench.rdo_list:
                    rdo.initialize()
                    gbt_channel = rdo.comm.get_gbt_channel()
                    if self.server.test.config.PA3_READ_VALUES or self.server.test.config.PA3_SCRUBBING_ENABLE:
                        self.server.test.testbench.cru.pa3.initialize()
                        self.server.test.testbench.cru.pa3.config_controller.clear_scrubbing_counter()
                    if self.server.test.config.PA3_SCRUBBING_ENABLE:
                        self.server.test.testbench.cru.pa3.config_controller.start_blind_scrubbing()
                        self.server.test.logger.info(f"Running blind scrubbing on RDO {gbt_channel}")
            except Exception as e:
                raise e
        except Exception as e:
            self.server.test.logger.exception("Exception in Run")
        finally:
            self.server.test.testbench.stop()
            self.server.test.stop()


        return 'Done starting run'
    
    #__________________________________________
    def prepare_for_triggers(self):
        self.server.test.prepare_for_triggers()
        return ('Done')
    #__________________________________________
    def run(self):
        self.server.test.logger.info(f"ltu master conf {self.server.conf.getboolean(self.server.setup, 'ltu_master')}")
        self.server.test.run(rcs=True, ltu_master=self.server.conf.getboolean(self.server.setup, 'ltu_master'))
        return ('Done')
    #__________________________________________
    def tear_down(self):
        self.server.test.tearDown()
        return ('Done')
    #__________________________________________
    def stop_readout(self):
        self.server.test.stop()
        return ('Done')
    #__________________________________________
    def stop(self):
        self.server.test.testbench.stop()
        return ('Done')

    #__________________________________________
    def move_raw_data(self):
        ls_command = "ls -td -- ./logs/*/ | grep "+self.server.conf.get(self.server.setup, 'log_prefix')+" | head -n 1 | cut -d'/' -f3"
        self.server.test.logger.info(ls_command)
        log_name = subprocess.run(ls_command, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
        
        subprocess.run(["mkdir", "-p", "/data/ob_comm/raw/"+log_name])
        subprocess.run(["mkdir", "-p", "/data/ob_comm/logs/"+log_name])
        rsync_command = "rsync -a logs/"+log_name+" /data/ob_comm/logs/"+log_name
        subprocess.run(rsync_command, shell=True, stdout=subprocess.PIPE)
        self.server.test.logger.info(rsync_command)

        find_raw_data_command = "cat "+self.server.conf.get(self.server.setup, 'external_readout_config')+" | grep fileName | grep lz4"
        raw_data_path = subprocess.run(find_raw_data_command, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip().strip('fileName=')
        mv_raw_data_command = "mv "+raw_data_path+" /data/ob_comm/raw/"+log_name+"/"
        self.server.test.logger.info(f"move rae data command {mv_raw_data_command}")
        subprocess.run(mv_raw_data_command, shell=True, stdout=subprocess.PIPE)
        
        return ('Done')

    #__________________________________________
    def handle(self):
        data = self.request.recv(1024).strip().decode('utf-8').split()
        if len(data) == 0: return
        cmd = data[0].upper()

        # Run Control Server part
        start_time = time.time()
        ret = 'ERROR'
        self.server.log.info(cmd + ' request received')
        
        try:
            if cmd == 'SETUP_NEW_RUN': 
                ret = self.setup_new_run()
            elif cmd == 'PREPARE_FOR_TRIGGERS':
                ret = self.prepare_for_triggers()
            elif cmd == 'START_RUN':
                ret = self.run()
            elif cmd == 'TEAR_DOWN':
                ret = self.tear_down()
            elif cmd == 'STOP_READOUT':
                ret = self.stop_readout()
            elif cmd == 'STOP':
                ret = self.stop()
            elif cmd == 'MOVE_DATA':
                ret = self.move_raw_data()
            else:
                ret = 'ERROR unknown command'

        except:
            traceback.print_stack()
            self.server.log.exception(f'Command {cmd} failed!') # TODO: add exception handling and recover software/hardware
            
        self.server.log.info(cmd + ' returned ' + ret + ' (executed in {:.1f}s)'.format(time.time()-start_time))

        ret = cmd +' '+ ret + '\n'
        self.request.sendall(bytes(ret, "utf-8"))
        self.server.last_ret = ret
                 

###################################################################
if __name__ == "__main__":
    margparser = argparse.ArgumentParser(description="Server acting as fake ECS for IB.")
    margparser.add_argument('setup', metavar='SETUP', choices=genconf.sections(), type=lambda s: s.upper(),
                           help='Setup to be control by Run Control server.')
    margs = margparser.parse_args()

    log_fname_prefix = genconf.get(margs.setup, 'path_logs')+'rcs_' + margs.setup+'_' + \
                       datetime.datetime.today().strftime('%Y-%m-%d')+'_'
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(log_format)
    logging.getLogger().addHandler(sh)
    
    log_file = logging.FileHandler(log_fname_prefix+'info.log', mode='a')
    log_file.setLevel(logging.INFO)
    log_file.setFormatter(log_format)
    logging.getLogger().addHandler(log_file)
    
    log_file_err = logging.FileHandler(log_fname_prefix+'error.log', mode='a')
    log_file_err.setLevel(logging.WARNING)
    log_file_err.setFormatter(log_format)
    logging.getLogger().addHandler(log_file_err)

    log = logging.getLogger('run_control')
    log.setLevel(logging.DEBUG)
    
    try:
        os.unlink(genconf.get(margs.setup, 'path_logs')+'rcs_' + margs.setup+'_info.log')
        os.unlink(genconf.get(margs.setup, 'path_logs')+'rcs_' + margs.setup+'_error.log')
    except:
        pass
    os.symlink(log_fname_prefix+'info.log', genconf.get(margs.setup, 'path_logs')+'rcs_' + margs.setup+'_info.log')
    os.symlink(log_fname_prefix+'error.log', genconf.get(margs.setup, 'path_logs')+'rcs_' + margs.setup+'_error.log')

    HOST = genconf.get(margs.setup, 'host')
    PORT = genconf.getint(margs.setup, 'port')
    try:
        server_running = False
        while(not server_running):
            try:
                with socketserver.TCPServer((HOST, PORT), RunControlServer) as server:
                    server.setup = margs.setup
                    server.conf = genconf
                    server.log = log
                    server.tb = None
                    server.test = None
                    server.last_ret = None
                    server.last_cmd = None
                    log.info('Listening on port {:d}'.format(PORT))
                    server_running = True
                    server.serve_forever()
            except OSError:
                wait = 3
                log.info('Port {} not available, waiting {}s and retrying...'.format(PORT,wait))
                time.sleep(wait)
    except KeyboardInterrupt:
        log.info('User exit')

