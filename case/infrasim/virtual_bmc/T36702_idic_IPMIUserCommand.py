'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T36702_idic_IPMIUserCommand(CBaseCase):
    '''
    [Purpose ]: Validate remote user command
    [Author  ]: Echo.Cheng@emc.com
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
                self.log('INFO', 'Check node {} of rack {} user command ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                # Check user command
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('user')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))
                if ret != 0:
                    self.result(FAIL, 'Node {} on rack {} fail to check user command, '
                                'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))
            # Check user list
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} user list ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('user list')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))
                if ret != 0:
                    self.result(FAIL, 'Node {} on rack {} fail to check user list, '
                                'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))

            # Check compressed user list
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} compressed user list ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('-c user list')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))
                if ret != 0:
                    self.result(FAIL, 'Node {} on rack {} fail to check compressed user list, '
                                'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))

            # Check user summary
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} user summary ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('user summary')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))
                if ret != 0:
                    self.result(FAIL, 'Node {} on rack {} fail to check user summary, '
                                'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
