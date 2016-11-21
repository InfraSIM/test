'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T43943_idic_IPMISIMHelpAccessible(CBaseCase):
    '''
    [Purpose ]: test
    [Author  ]: june.zhou@emc.com
    [Tickets ]: 
    [Platform]: 
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_console()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'To try IPMI SIM accessible for each node of rack...')

                ipmi_console = obj_node.ssh_ipmi_console

                str_rsp = ipmi_console.send_command_wait_string(str_command='help'+chr(13),
                                                                wait='IPMI_SIM',
                                                                int_time_out=3,
                                                                b_with_buff=False)
                is_match = re.search("Available commands", str_rsp)

                if is_match is not None:
                    self.log('INFO', 'Matched part of "help" output message: '
                                     '\"Available commands\": {}'.
                             format(str_rsp))
                else:
                    self.result(FAIL, 'BMC IPMI_SIM of a node not accessible. '
                                      'Rack is {}, Node is {}, ipmi-console access: {}'.
                                format(obj_rack.get_name(),
                                       obj_node.get_name(),
                                       obj_node.get_ip(),
                                       obj_node.get_port_ipmi_console()))
                time.sleep(1)

    def deconfig(self):

        CBaseCase.deconfig(self)

