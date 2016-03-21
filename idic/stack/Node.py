'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 28, 2015

@author: Forrest Gu
*********************************************************
'''
from lib.Device import CDevice
from idic.stack.BMC import CBMC

class CNode(CDevice):
    def __init__(self, dict_node):

        CDevice.__init__(self, 'vNode')

        self.dict_config = dict_node

        # vBMC
        obj_bmc = CBMC(self.dict_config.get('bmc', {}))
        self.bmc = obj_bmc

        # Power, a tuple of PDU information:
        # (obj_pdu, str_outlet)
        self.power = []

        self.name = self.dict_config.get('name', '')
        self.datastore = self.dict_config.get('datastore', '')

    def get_config(self):
        return self.dict_config

    def get_datastore(self):
        return self.datastore

    def get_name(self):
        return self.name

    def set_bmc(self, obj_bmc):
        self.bmc = obj_bmc

    def get_bmc(self):
        return self.bmc

    def power_on(self):
        if not self.power:
            raise Exception('Can\'t operate node\'s power, please bind to any PDU first.')
        for power_unit in self.power:
            power_unit[0].match_outlet_password(power_unit[1])
            power_unit[0].power_on(power_unit[1])

    def power_off(self):
        if not self.power:
            raise Exception('Can\'t operate node\'s power, please bind to any PDU first.')
        for power_unit in self.power:
            power_unit[0].match_outlet_password(power_unit[1])
            power_unit[0].power_off(power_unit[1])
