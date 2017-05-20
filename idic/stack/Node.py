'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 28, 2015

@author: Forrest Gu
*********************************************************
'''
import time
import re
import json
import yaml
import os
from lib.Device import CDevice
from idic.stack.BMC import CBMC
from lib.SSH import CSSH
from lib.Apps import with_connect
from lib.Apps import update_option


class CNode(CDevice):
    def __init__(self, dict_node):
        """
        dict_node example:
        {
            "name": "vnode_a_20160126114700",
            "power": [
                {"vPDU": "vpdu_1", "outlet": "1.1"}
            ],
            "admin":{
                "ip": "192.168.134.114",
                "username": "infrasim",
                "password": "infrasim"
            },
            "bmc": {
                "ip": "172.31.128.2",
                "username": "admin",
                "password": "admin"
            }
        }
        """

        CDevice.__init__(self, 'vNode')

        self.dict_config = dict_node

        # vBMC
        obj_bmc = CBMC(self.dict_config.get('bmc', {}))
        self.bmc = obj_bmc

        # Power, a tuple of PDU information:
        # (obj_pdu, str_outlet)
        self.power = []

        self.name = self.dict_config.get('name', '')
        if 'admin' not in self.dict_config:
            raise Exception('No "admin" network defined for node {}'.format(self.name))
        self.ip = self.dict_config['admin'].get('ip', '')
        self.username = self.dict_config['admin'].get('username', '')
        self.password = self.dict_config['admin'].get('password', '')
        self.port_ipmi_console = self.dict_config.get('ipmi-console', 9300)
        self.ssh_ipmi_console = CSSH(self.ip, username='', password='', port=self.port_ipmi_console)
        self.ssh = CSSH(self.ip, username=self.username, password=self.password, port=22)
        self.b_sol = False

    def get_config(self):
        return self.dict_config

    def get_name(self):
        return self.name

    def set_bmc(self, obj_bmc):
        self.bmc = obj_bmc

    def get_bmc(self):
        return self.bmc

    def get_ip(self):
        return self.ip

    def set_ip(self, str_ip):
        self.ip = str_ip

    def get_username(self):
        return self.username

    def set_username(self, str_username):
        self.username = str_username

    def get_password(self):
        return self.password

    def set_password(self, str_password):
        self.password = str_password

    def get_port_ipmi_console(self):
        return self.port_ipmi_console

    def power_on(self):
        if not self.power:
            raise Exception('Can\'t operate node\'s power, please bind to any PDU first.')
        for power_unit in self.power:
            if not power_unit[0].match_outlet_password(power_unit[1]):
                return False
            if not power_unit[0].power_on(power_unit[1]):
                return False
        return True

    def power_off(self):
        if not self.power:
            raise Exception('Can\'t operate node\'s power, please bind to any PDU first.')
        for power_unit in self.power:
            if not power_unit[0].match_outlet_password(power_unit[1]):
                return False
            if not power_unit[0].power_off(power_unit[1]):
                return False
        return True

    def _has_power_control(self):
        if self.power:
            return True
        else:
            return False

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
        self.ssh.send_command('ipmitool -I lanplus -H {} -U {} -P {} sol activate{}'.
                              format(self.bmc.get_ip(),
                                     self.bmc.get_username(),
                                     self.bmc.get_password(),
                                     chr(13)))

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

    @with_connect('ssh')
    def send_file(self, src, dst):
        '''
        Put file from src to dst, return canonicalized path of destination
        '''
        self.log("INFO", "Send file {} to {} on node {}...".format(src, dst, self.get_name()))
        with self.ssh.h_ssh.open_sftp() as sftp:
            sftp.put(src, dst)
            return str(sftp.normalize(dst))

    @with_connect('ssh')
    def get_instance_name(self):
        '''
        Get run time node names from admin network.
        You may get multiple instances in the same environment, but this function
        has not handled this condition yet.
        It now focus on one infrasim instances in one admin network.
        :return:
        '''
        self.log("INFO", "Get runtime instance name from node {}...".format(self.get_ip()))
        p_name = re.compile(r"] (.*)-node is running")

        rsp = self.ssh.send_command_wait_string(str_command='echo {} | sudo -S infrasim node status {}'.
                                                format(self.password, chr(13)),
                                                wait='~$')

        list_name = list(set(p_name.findall(rsp)))
        active_num = len(list_name)
        if active_num == 1:
            return list_name[0]
        elif active_num == 0:
            raise Exception("Infrasim node is not running on {}".format(self.ip))
        else:
            raise Exception("Multiple infrasim instances {} are detected on {}. "
                            "This is not supported yet.".
                            format(list_name, self.ip))

    @with_connect('ssh')
    def update_instance_config(self, str_instance_name, payload, *key):
        '''
        Update configuration file, assign payload to target key.
        :param str_instance_name:
        :param dict_payload:
        :return:
        '''
        self.log("INFO", "Update config for instance {} on node {}...".format(str_instance_name, self.get_ip()))
        str_key = []
        for element in key:
            str_key.append(str(element))
        self.log("INFO", "{}: \n{}".format(" > ".join(str_key), json.dumps(payload, indent=4)))
        remote_path = os.path.join(".infrasim", str_instance_name, "etc", "infrasim.yml")
        with self.ssh.h_ssh.open_sftp() as sftp:
            conf = None
            with sftp.open(remote_path, 'r') as remote_file:
                conf = yaml.load(remote_file)
                update_option(conf, payload, *key)
            with sftp.open('tmp.yml', 'w') as remote_file:
                yaml.dump(conf, remote_file, default_flow_style=False)

        self.ssh.send_command_wait_string(str_command="echo {} | sudo -S mv tmp.yml {}".
                                          format(self.password, remote_path)+chr(13),
                                          wait="~$")

    @with_connect('ssh')
    def get_instance_config(self, str_instance_name):
        '''
        Get configuration
        :param str_instance_name:
        :param dict_payload:
        :return:
        '''
        self.log("INFO", "Get config for instance {} on node {}...".format(str_instance_name, self.get_ip()))
        remote_path = os.path.join(".infrasim", str_instance_name, "etc", "infrasim.yml")
        with self.ssh.h_ssh.open_sftp() as sftp:
            with sftp.open(remote_path, 'r') as remote_file:
                return yaml.load(remote_file)
