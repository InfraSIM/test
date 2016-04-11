'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T33272_idic_vPDUInvalidPassword(CBaseCase):
    '''
    [Purpose ]: 
    [Author  ]: june.zhou@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        try:
            self.stack.walk_pdu().next()
        except StopIteration:
            self.result(BLOCK, 'No PDU in stack at all')

    def test(self):
        self.log('INFO', 'Start Test...')

        # power off
        for obj_rack in self.stack.get_rack_list():

            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    pdu_pwd = power_unit[0].get_outlet_password(power_unit[1])
                    pdu_pwd_temp = pdu_pwd+'ToMakeInvalidPWD'

                    power_unit[0].match_outlet_password(power_unit[1], pdu_pwd_temp)

                    if power_unit[0].power_off(power_unit[1]):
                        self.result(FAIL, 'Node can power off with wrong PDU outlet '
                                          'password. Node is {}, outlet is {}.'.
                                    format(obj_node.get_name(), power_unit[1]))

                self.log('INFO', 'Wait 10 seconds for possible power off ...')
                time.sleep(10)

        # power on
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    # power on
                    if power_unit[0].power_on(power_unit[1]):
                        self.result(FAIL, 'Node can power on with wrong PDU outlet '
                                          'password. Node is {}, outlet is {}.'.
                                    format(obj_node.get_name(), power_unit[1]))

        self.log('INFO', 'End Test...')

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
