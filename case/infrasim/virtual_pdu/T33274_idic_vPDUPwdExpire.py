'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T33274_idic_vPDUPwdExpire(CBaseCase):
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
        for obj_rack in self.stack.get_rack_list():

            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    pdu_pwd = power_unit[0].get_outlet_password(power_unit[1])
                    power_unit[0].match_outlet_password(power_unit[1], pdu_pwd)

        self.log('INFO', 'Wait 120s for outlet password to be expired ...')
        time.sleep(121)

        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                #power off
                for power_unit in obj_node.power:
                    is_off  = power_unit[0].power_off(power_unit[1])
                    if True == is_off:
                        self.result(FAIL, 'PDU password didn\'t expire after 2 minutes. Node can power off after PDU outlet password been matched 2 minutes ago. Node is {}, outlet is {}.'.
                                format(obj_node.get_name(),power_unit[1]))

        self.log('INFO', 'Wait 5 seconds for possible power off ...')
        time.sleep(5)
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                #power on
                for power_unit in obj_node.power:
                    is_on = power_unit[0].power_on(power_unit[1])
                    if True == is_on:
                        self.result(FAIL, 'PDU password didn\'t expire after 2 minutes. Node can be power on after PDU outlet password been matched 2 minutes ago. Node is {}, outlet is {}.'.
                                format(obj_node.get_name(),power_unit[1]))

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
