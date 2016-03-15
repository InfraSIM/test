'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
'''
Created on Dec 22, 2015

@author: Tony Su
'''
from lib.Device import CDevice

class CSwitch(CDevice):
    def __init__(self, dict_switch):
        CDevice.__init__(self, 'vSwitch')

        self.dict_config = dict_switch

    def get_config(self):
        return self.dict_config