#!/usr/bin/env python
"""File implementing the logbookAddComment

Freely inspired from
https://gitlab.cern.ch/msuljic/ib-commissioning-tools/blob/master/run_control_server.py
"""

from email.mime.text import MIMEText
from timeout_decorator import timeout
from timeout_decorator.timeout_decorator import TimeoutError

import errno
import logging
import os
import smtplib
import subprocess


TIMEOUT_TIME = 3
TIMEOUT_MSG = 'Command interrupted because it took too long to execute!'
EXECUTABLE = '/opt/logbookAddComment'
DEFAULT_MAIL_RECIPIENT = 'its.ru.ci@cern.ch'

class Logbook:
    """Class implementing the call to EXECUTABLE
    Falls back to email if file not found
    """
    def __init__(self, subrack, group='WP10', dry=True,
                 mail_recipient=DEFAULT_MAIL_RECIPIENT):
        """
        subrack: subrack, must be in crate mapping
        group: name for group running the test
        dry: if True does not submit the log entry, but sends email
        """
        self.subrack = subrack
        self.group = group
        self.dry = dry
        self.mail_recipient = mail_recipient

        self.flp = os.uname()[1]
        self.logger = logging.getLogger('Logbook')

    def __del__(self):
        pass

    @staticmethod
    def send_email(to, subject, body=''):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = 'noreply@cern.ch'
        msg['To'] = to
        s = smtplib.SMTP('cernmx.cern.ch')
        s.sendmail(msg['From'], msg['To'], msg.as_string())
        s.quit()
        return True

    def _send_logentry(self, title, entry=''):
        try:
            subprocess.run([EXECUTABLE, title, entry], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.logger.error('Problem submitting logbook entry!')
            self.logger.error(f"{e.stdout.decode('utf-8')}")
            return False
        except FileNotFoundError as fnfe:
            msg = f'Ask Sylvain to install {EXECUTABLE} on {self.flp}'
            self.logger.error('Problem submitting logbook entry: file not found')
            self.logger.error(msg)
            self.logger.warning('Fall back to email due to error')
            entry += f'\n\n{msg}'
            self.send_email(self.mail_recipient, title, entry)
            return False

    @timeout(TIMEOUT_TIME, exception_message=TIMEOUT_MSG)
    def submit_log_entry(self, test, comment):
        title = f'{self.group} {self.subrack} {test}'
        entry = f'From {self.flp} on {self.subrack}\n\n{comment}\n'
        entry = entry.replace("'", "")
        if not self.dry:
            return self._send_logentry(title,entry)
        return self.send_email(self.mail_recipient, title, entry)


if __name__=="__main__":
    """Only for testing purposes"""
    logdir = os.path.join(
        os.getcwd(),
        'logs')
    try:
        os.makedirs(logdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    log_file = os.path.join(logdir, "logboook.log")
    log_file_errors = os.path.join(logdir,
                                   "logbook_errors.log")

    # setup logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh2 = logging.FileHandler(log_file_errors)
    fh2.setLevel(logging.ERROR)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(fh2)
    logger.addHandler(ch)

    l = Logbook('PP1-O-Test',dry=False)
    l.submit_log_entry('The test', 'This is a log entry')
