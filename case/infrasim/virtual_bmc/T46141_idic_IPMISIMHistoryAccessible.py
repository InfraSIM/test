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
        self.enable_ipmi_console()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'To try IPMI SIM history for each node of rack...')

                bmc_obj = obj_node.get_bmc()

                ipmi_console = obj_node.ssh_ipmi_console

                ipmi_console.send_command_wait_string(str_command='help'+chr(13),
                                                      wait='IPMI_SIM',
                                                      int_time_out=3,
                                                      b_with_buff=False)
                ipmi_console.send_command_wait_string(str_command='help sensor'+chr(13),
                                                      wait='IPMI_SIM',
                                                      int_time_out=3,
                                                      b_with_buff=False)
                ipmi_console.send_command_wait_string(str_command='sensor'+chr(13),
                                                      wait='IPMI_SIM',
                                                      int_time_out=3,
                                                      b_with_buff=False)
                str_rsp = ipmi_console.send_command_wait_string(str_command='history'+chr(13),
                                                                wait='IPMI_SIM',
                                                                int_time_out=3,
                                                                b_with_buff=False)

                count = 0
                lines = str_rsp.split('\n', str_rsp.count('\n'))
                self.log('INFO', 'IPMI_SIM History from ipmi-console {}:{} is \r{}'.
                         format(obj_node.get_ip(),
                                obj_node.get_port_ipmi_console(),
                                str_rsp))
                for line in lines:
                    count += 1

                # lines[count-1] is 'IPMI_SIM'
                # lines[count-2] is '\r'
                p_sensor = r'\d*\ssensor\r'  # pattern for lines[count-3]
                p_help_sensor = r'\d*\shelp\ssensor\r'  # pattern for lines[count-4]
                p_help = r'\d*\shelp\r'  # pattern for lines[count-5]

                if len(lines) >= 5:
                    if re.search(p_sensor, lines[count-3]) \
                            and re.search(p_help_sensor, lines[count-4]) \
                            and re.search(p_help, lines[count-5]):
                        self.log('INFO', 'History from Node:{} .'
                                         'Rack is {}, Node is {}, BMC IP is: {}'.
                                 format(str_rsp,
                                        obj_node.get_name(),
                                        obj_node.get_name(),
                                        bmc_obj.get_ip()))
                    else:
                        self.result(FAIL,
                                    'When history has less than 30 entries, '
                                    'the last 3 entries are expected to be "help", "help sensor", "sensor".'
                                    'See log for actual entries. '
                                    'Rack is {}, Node is {}, ipmi-console access: {}:{}'
                                    .format(obj_rack.get_name(),
                                            obj_node.get_name(),
                                            obj_node.get_ip(),
                                            obj_node.get_port_ipmi_console()))
                else:
                        self.result(FAIL,
                                    'History contains less commands than expected which were run. '
                                    'Please check IPMI_SIM accessibility. '
                                    'Rack is {}, Node is {}, ipmi-console access: {}:{}'
                                    .format(obj_rack.get_name(),
                                            obj_node.get_name(),
                                            obj_node.get_ip(),
                                            obj_node.get_port_ipmi_console()))

                time.sleep(1)

    def deconfig(self):

        CBaseCase.deconfig(self)


