'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 22, 2015

@author: Tony Su
*********************************************************
'''

from lib.Device import CDevice
from lib.IOL import CIOL


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

    def get_ip(self):
        return self.ip

    def set_ip(self, ip):
        self.ip = ip

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password
