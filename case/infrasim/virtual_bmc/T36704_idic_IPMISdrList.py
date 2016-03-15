'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T36704_idic_IPMISdrList(CBaseCase):
    '''
    [Purpose ]: Validate IPMI SDR list
    [Author  ]: Echo.cheng@emc.com
    [Sprint  ]: Lykan Sprint 25
    [Tickets ]: SST-629
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
    
    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} sdr list ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('sdr list')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))
                if ret != 0:
                    self.result(FAIL, 'Node {} on rack {} fail to check BMC sdr list, '
                                'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
