'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re
class T36705_idic_IPMIRemoteChangeBootOption(CBaseCase):


    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
    
    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Change boot option of node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                boot_devices = ['disk','cdrom','pxe']
                for boot_device in boot_devices:
                    ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis bootdev '+boot_device)
                    self.log('INFO', 'ret: {}'.format(ret))
                    self.log('INFO', 'rsp: \n{}'.format(rsp))
                    if ret != 0 or re.search('Set Boot Device to '+boot_device, rsp)==None:
                        self.result(FAIL, 'Node {} on rack {} fail to change boot device to {}, '
                                    'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                    format(obj_node.get_name(), obj_rack.get_name(), boot_device, ret, rsp))
                    else:
                        self.log('INFO', 'Command for setting boot device of Node {} on rack {} to {} succeed.'.format(obj_node.get_name(), obj_rack.get_name(), boot_device))

                    ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis power reset')
                    self.log('INFO', 'ret: {}'.format(ret))
                    self.log('INFO', 'rsp: \n{}'.format(rsp))
                    if ret != 0 or re.search('Chassis Power Control: Reset', rsp)==None:
                        self.result(FAIL, 'Node {} on rack {} fail to reset chassis power, '
                                    'ipmitool return: {}, expect: 0, rsp: \n{}'.
                                    format(obj_node.get_name(), obj_rack.get_name(), ret, rsp))
                    else:
                        self.log('INFO', 'Command for reset chassis power of Node {} on rack {} succeed.'.format(obj_node.get_name(), obj_rack.get_name() ))

                    #TODO: Verify the boot option on the node through VNC viewer.

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

