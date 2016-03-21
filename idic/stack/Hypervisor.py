'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 22, 2015

@author: Tony Su
*********************************************************
'''
from lib.Device import CDevice

class CHypervisor(CDevice):
    def __init__(self, dict_hypervisor):

        CDevice.__init__(self, 'hypervisor')

        self.dict_config = dict_hypervisor

        self.name = self.dict_config.get('name', '')
        self.type = self.dict_config.get('type', '')
        self.ip = self.dict_config.get('ip', '')
        self.username = self.dict_config.get('username', '')
        self.password = self.dict_config.get('password', '')

    def get_config(self):
        return self.dict_config

    def get_name(self):
        return self.name

    def get_ip(self):
        return self.ip

    def set_ip(self, ip):
        self.ip = ip

    def get_username(self):
        return self.username

    def set_username(self, username):
        self.username = username

    def get_password(self):
        return self.password

    def set_password(self, password):
        self.password = password
