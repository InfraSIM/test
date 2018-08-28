'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 28, 2015

@author: Forrest Gu
*********************************************************
'''
import re
from lib.Device import CDevice
from idic.stack.Node import CNode
from lib.SSH import CSSH
from lib.Apps import with_connect
from lib.Apps import update_option, get_option, strip_color_code


class CChassis(CDevice):
    def __init__(self, dict_chassis):
        """
        dict_chassis example:
        {
            "name": "chassis",
            "ip": "192.168.132.144",
            "username": "infrasim",
            "password": "infrasim",
            "chassis_node_a": [{
                "admin": {
                    "ip": "10.62.83.141",
                    "username": "infrasim",
                    "password": "infrasim",
                    "port": "18022"
                },
                "guest_os": {
                    "ip": "10.62.83.132",
                    "username": "infrasim",
                    "password": "infrasim",
                    "port": "22"
                },
                "bmc": {
                    "ip": "10.62.83.141",
                    "username": "admin",
                    "password": "admin"
                }
            }],
            "chassis_node_b": [{
                "admin": {
                    "ip": "10.62.83.145",
                    "username": "infrasim",
                    "password": "infrasim",
                    "port": "28022"
                },
                "guest_os": {
                    "ip": "10.62.83.136",
                    "username": "infrasim",
                    "password": "infrasim",
                    "port": "22"
                },
                "bmc": {
                    "ip": "10.62.83.145",
                    "username": "admin",
                    "password": "admin"
                }
            }]
        }
        """

        CDevice.__init__(self, 'vChassis')

        self.dict_config = dict_chassis

        # Power, a tuple of PDU information:
        # (obj_pdu, str_outlet)
        self.power = []

        self.name = self.dict_config.get('name', '')
        self.node_a_name = '{}_a'.format(self.name)
        self.node_b_name = '{}_b'.format(self.name)

        self.ip = self.dict_config.get('ip', '')
        self.dict_node_a = self.dict_config.get(self.node_a_name)
        self.dict_node_b = self.dict_config.get(self.node_b_name)

        self.username = self.dict_config.get('username', '')
        self.password = self.dict_config.get('password', '')
        self.port_ipmi_console = self.dict_config.get('ipmi-console', 9300)
        self.ssh_ipmi_console = CSSH(self.ip, username='', password='', port=self.port_ipmi_console)
        self.ssh = CSSH(self.ip, username=self.username, password=self.password, port=22)

    def get_config(self):
        return self.dict_config

    def get_name(self):
        return self.name

    def get_ip(self):
        return self.ip

    def set_ip(self, str_ip):
        self.ip = str_ip

    def get_guest_ip(self, node):
        self.guest_ip = node.dict_config['guest_os'].get('ip', '')
        return self.guest_ip

    def get_guest_user(self, node):
        self.guest_user = node.dict_config['guest_os'].get('username', '')
        return self.guest_user

    def get_guest_password(self, node):
        self.guest_password = node.dict_config['guest_os'].get('password', '')
        return self.guest_password

    def get_username(self):
        return self.username

    def set_username(self, str_username):
        self.username = str_username

    def get_password(self):
        return self.password

    def get_node_list(self):
        node_list = []
        for item in self.dict_config:
            p_node = re.search(r'{}_(.*)'.format(self.name), item)
            if p_node:
                obj_node = CNode(self.dict_config.get(item))
                node_list.append(obj_node)
        return node_list

    def set_password(self, str_password):
        self.password = str_password

    @with_connect('ssh')
    def chassis_start(self):
        '''
        To start a chassis, which will include infrasim chassis, node_a and node_b
        :return:
        '''
        self.log("INFO", "Start infrasim chassis {}...".format(self.name))
        str_command = "sudo infrasim chassis start {}".format(self.name)
        self.ssh.remote_shell(str_command)

    @with_connect('ssh')
    def get_instance_name(self):
        '''
        Get run time chassis, node_a and node_b name from chassis host vm.
        :return: chassis_ins_name, node_ins_a, node_ins_b
        '''
        self.log("INFO", "Get chassis runtime instance name from {}...".format(self.get_ip()))
        command = 'ps ax |grep infrasim-chassis |grep -v grep'
        rsp_dict = self.ssh.remote_shell(command)
        rsp = rsp_dict.get('stdout')
        chassis_ins_name = strip_color_code((rsp.split('\n'))[0].split()[6])

        self.log("INFO", "Get node_a runtime instance name ...")
        str_command = "sudo infrasim node status {}".format(self.node_a_name)
        rsp = self.ssh.remote_shell(str_command)
        p_name = re.search(r'(.*)-node is running', rsp.get('stdout'))
        node_ins_a = ''
        if p_name:
            node_ins_a = self.node_a_name
        else:
            self.log("WARNING", "Node {} is not running".format(self.node_a_name))

        self.log("INFO", "Get node_b runtime instance name ...")
        str_command = 'sudo infrasim node status {}'.format(self.node_b_name)
        rsp = self.ssh.remote_shell(str_command)
        p_name = re.search(r'(.*)-node is running', rsp.get('stdout'))
        node_ins_b = ''
        if p_name:
            node_ins_b = self.node_b_name
        else:
            self.log("WARNING", "Node {} is not running".format(self.node_b_name))

        return chassis_ins_name, node_ins_a, node_ins_b

    @with_connect('ssh')
    def guest_access(self, node):
        '''
        Access to node_a and node_b guest OS: ping the ip address in guest os
        :return: True or False
        '''
        guest_ip = self.get_guest_ip(node)
        str_command = 'ping {} -c 3 '.format(guest_ip)
        rsp = self.ssh.remote_shell(str_command)
        ping = re.search(r'0% packet loss', rsp.get('stdout'))

        if ping:
            return True
        else:
            self.log("WARNING", "Guest OS can not access; Check your chassis!!")
            return False

    @with_connect('ssh')
    def ipmi_lan_print(self, node):
        '''
        run ipmitool lan print on a/b node
        :return:
        '''
        cmd = 'ipmitool -I lanplus -H {} -U {} -P {} lan print'.format(node.bmc.get_ip(),
                                                                       node.bmc.get_username(),
                                                                       node.bmc.get_password())
        rsp = self.ssh.remote_shell(cmd)
        return rsp.get("stdout")

    @with_connect('ssh')
    def ipmi_fru_print(self, node):
        '''
        run ipmitool command to get fru info on a/b node
        :return:
        '''
        cmd = 'ipmitool -I lanplus -H {} -U {} -P {} fru print'.format(node.bmc.get_ip(),
                                                                       node.bmc.get_username(),
                                                                       node.bmc.get_password())
        rsp = self.ssh.remote_shell(cmd)
        return rsp.get('stdout')

    @with_connect('ssh')
    def send_command_to_guest(self, node, cmd_str):
        '''
        Send command to guest os
        :return: {
            'stdout': str_stdout,
            'stderr': str_stderr,
            'exitcode': int_exitcode
        }
        '''
        cmd = r"sudo sshpass -p {} ssh -o StrictHostKeyChecking=no -tt {}@{} '{}' ".format(node.guest_password,
                                                                                           node.guest_user,
                                                                                           node.guest_ip,
                                                                                           cmd_str)
        rst_dict = self.ssh.remote_shell(cmd)
        return rst_dict
