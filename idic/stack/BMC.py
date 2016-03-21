'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 22, 2015

@author: Tony Su
*********************************************************
'''
import os
import time

from lib.Device import CDevice
from lib.IOL import CIOL
from lib.SSH import CSSH
from lib.Apps import with_connect

class CBMC(CDevice):
    def __init__(self, dict_bmc):

        CDevice.__init__(self, 'vBMC')

        self.dict_config = dict_bmc

        self.ip = self.dict_config.get('ip', '')
        self.username = self.dict_config.get('username', '')
        self.password = self.dict_config.get('password', '')
        self.ipmi = CIOL(str_ip=self.ip,
                         str_user=self.username,
                         str_password=self.password)
        self.ssh_ipmi_sim = CSSH(self.ip, username='', password='', port=9300)
        self.ssh = CSSH(self.ip, username='root', password='root', port=22)
        self.b_sol = False

        """
        self.pdu_ip = "0.0.0.0"
        self.switch_ip = "0.0.0.0"
        """

    def get_ip(self):
        return self.ip

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    @with_connect('ssh')
    def sol_activate(self, log_dir=''):
        '''
        SSH to this BMC, then activate SOL
        Leverage SSH to capture output flow
        '''

        if self.b_sol:
            self.log('WARNING', 'BMC {} SOL has been activated'.format(self.ip))
            return

        # Connect
        self.ssh.send_command('ipmitool -I lanplus -H localhost -U {} -P {} sol activate{}'.
                              format(self.username, self.password, chr(13)))

        # Wait 2s to flush heading string
        time.sleep(2)

        self.b_sol = True

    @with_connect('ssh')
    def sol_is_alive(self):

        if not self.b_sol:
            self.log('WARNING', 'BMC {} SOL is not activated'.format(self.ip))
            return False

        retry = 30
        for i in range(retry):
            self.ssh.start_cache()
            time.sleep(3)
            str_cache = self.ssh.get_cache()
            if str_cache:
                self.log('INFO', 'SOL is alive')
                return True
        self.log('WARNING', 'BMC {} SOL is not alive, no output in 90s'.format('self.ip'))
        return False

    @with_connect('ssh')
    def sol_deactivate(self):
        '''
        Deactivate SOL, then disconnect SSH on this BMC port 22
        '''

        if not self.b_sol:
            self.log('WARNING', 'BMC {} SOL is not activated'.format(self.ip))
            return

        # Disconnect
        self.ssh.send_command('~.')

        self.b_sol = False

    """
    def set_pdu_ip(self, pdu_ip):
        self.pdu_ip = pdu_ip

    def get_pdu_ip(self):
        return self.pdu_ip

    def set_switch_ip(self, switch_ip):
        self.switch_ip = switch_ip

    def get_switch_ip(self):
        return self.switch_ip
    """