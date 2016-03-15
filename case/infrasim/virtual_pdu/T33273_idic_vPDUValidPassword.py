'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T33273_idic_vPDUValidPassword(CBaseCase):
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
        #power off
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    pdu_pwd = power_unit[0].get_outlet_password(power_unit[1])
                    power_unit[0].match_outlet_password(power_unit[1], pdu_pwd)
                    if False == power_unit[0].power_off(power_unit[1]):
                        self.result(FAIL, 'Node failed powering off with correct PDU outlet password. Node is {}, outlet is {}.'.
                                format(obj_node.get_name(),power_unit[1]))
                    else:
                        self.log('INFO', 'Node succeed in powering off with correct PDU outlet password. Node is {}, outlet is {}'.
                                 format(obj_node.get_name(),power_unit[1]))

        self.log('INFO', 'Wait 5 seconds for power off ...')
        time.sleep(5)

        #power on
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    if False == power_unit[0].power_on(power_unit[1]):
                        self.result(FAIL, 'Node failed powering on with correct PDU outlet password. Node is {}, outlet is {}.'.
                                format(obj_node.get_name(),power_unit[1]))
                    else:
                        self.log('INFO', 'Node succeed in powering on with correct PDU outlet password. Node is {}, outlet is {}'.
                                 format(obj_node.get_name(),power_unit[1]))

        self.log('INFO', 'Wait 5 seconds for power on ...')
        time.sleep(5)
        for obj_rack in self.stack.get_rack_list():
            obj_hyper = self.stack.hypervisors[obj_rack.get_hypervisor()]
            for obj_node in obj_rack.get_node_list():
                str_power_status = self.stack.rest_get_node_power_status(
                    obj_hyper.get_ip(),
                    obj_node.get_name()
                )
                if str_power_status != 'On':
                    self.result(FAIL, 'Node {} power status is {} after power on'.
                                format(obj_node.get_name(), str_power_status))
                else:
                    self.log('INFO', 'Node {} power on done'.format(obj_node.get_name()))

        self.log('INFO', 'End Test...')

    def deconfig(self):
        # To do: Case specific deconfig
        self.log('INFO', 'Wait 30s for all nodes to boot ...')
        time.sleep(30)
        CBaseCase.deconfig(self)
