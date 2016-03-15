'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T37571_idic_SensorThresholdSetting(CBaseCase):


    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_bmc_ssh()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Setting sensor threshold of node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))

                obj_bmc = obj_node.get_bmc()
                bmc_ssh = obj_bmc.ssh
                str_rsp = bmc_ssh.send_command_wait_string(str_command = 'ipmitool -I lanplus -H localhost -U {} -P {} fru print 0 {}'.format(obj_bmc.get_username(), obj_bmc.get_password(), chr(13)), wait = '$', int_time_out = 3, b_with_buff = False)

                fru = {}
                for item in str_rsp.split('\n'):
                    key = item.split(': ')[0].strip()
                    value = item.split(': ')[-1].strip()
                    fru[key] = value

                sensor = self.data[fru['Product Name']]

                str_rsp = bmc_ssh.send_command_wait_string(str_command = 'ipmitool -I lanplus -H localhost -U {} -P {} sensor thresh {} lower 600 700 800 900 upper {}'.format(obj_bmc.get_username(), obj_bmc.get_password(), sensor, chr(13)), wait = '$', int_time_out = 3, b_with_buff = False)

                str_rsp += bmc_ssh.send_command_wait_string(str_command = 'ipmitool -I lanplus -H localhost -U {} -P {} sensor thresh {} lower 450 400 420 {}'.format(obj_bmc.get_username(), obj_bmc.get_password(), sensor, chr(13)), wait = '$', int_time_out = 3, b_with_buff = False)

                if re.search('Error', str_rsp) or re.search('Failed', str_rsp):
                    self.result(FAIL, 'Failed to issue local IPMI command to set sensor threshold, return: {}'.format(str_rsp))
                else:
                    self.log('INFO', 'Set sensor threshold: {}'.format(str_rsp))

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)


