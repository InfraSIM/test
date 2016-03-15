'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T46141_idic_IPMISIMHistoryAccessible(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_sim()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO','To try IPMI SIM history command accessible for each node of rack...')

                bmc_obj = obj_node.get_bmc()

                bmc_ssh = bmc_obj.ssh_ipmi_sim

                bmc_ssh.send_command_wait_string(str_command = 'help'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                bmc_ssh.send_command_wait_string(str_command = 'help sensor'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                bmc_ssh.send_command_wait_string(str_command = 'sensor'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                str_rsp = bmc_ssh.send_command_wait_string(str_command = 'history'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)

                if re.search("help", str_rsp) and re.search("help sensor", str_rsp) and re.search("sensor", str_rsp):
                    self.log('INFO', 'History from Node:{} .Rack is {}, Node is {}, BMC IP is: {}'.
                            format(str_rsp, obj_node.get_name(),obj_node.get_name(), bmc_obj.get_ip()))
                else:
                    self.result(FAIL, 'BMC IPMI_SIM sensor command of a node not accessible. Rack is {}, Node is {}, BMC IP is: {}'.
                                format(obj_rack.get_name(),obj_node.get_name(), bmc_obj.get_ip()))

                time.sleep(1)

    def deconfig(self):

        CBaseCase.deconfig(self)


