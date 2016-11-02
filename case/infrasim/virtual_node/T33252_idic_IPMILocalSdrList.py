'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T33252_idic_IPMILocalSdrList(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_node_ssh()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))

                obj_bmc = obj_node.get_bmc()
                bmc_ssh = obj_bmc.ssh
                str_rsp = bmc_ssh.send_command_wait_string(str_command='ipmitool -I lanplus -H localhost -U {} -P {} sdr list {}'.
                                                           format(obj_bmc.get_username(), obj_bmc.get_password(), chr(13)),
                                                           wait='$',
                                                           int_time_out=10,
                                                           b_with_buff = False)
                self.log('INFO', 'rsp: \n{}'.format(str_rsp))
                is_match = re.search("failed", str_rsp)
                if is_match == None:
                    self.log('INFO', 'Able to issue local IPMI command ipmitool sdr list')
                else:
                    self.result(FAIL, 'Failed to issue local IPMI command ipmitool sdr list, return: {}'.format(str_rsp))

                time.sleep(1)

    def deconfig(self):
        self.log('INFO', 'Deconfig')
        CBaseCase.deconfig(self)

