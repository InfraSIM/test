from case.CBaseCase import *
import re

class T78170_idic_IPMISIMHistory30Commands(CBaseCase):
    '''
    [Purpose ]: 
    [Author  ]: @emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_sim()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO','To try IPMI SIM history when more than 30 commands run for each node of rack...')

                bmc_obj = obj_node.get_bmc()

                bmc_ssh = bmc_obj.ssh_ipmi_sim

                count = 0
                while (count<40):
                    bmc_ssh.send_command_wait_string(str_command = 'sensor info'+chr(13),
                                                 wait = 'IPMI_SIM',
                                                 int_time_out =3,
                                                 b_with_buff = False)
                    count =  count+1


                bmc_ssh.send_command_wait_string(str_command = 'sel'+chr(13),
                                                 wait = 'IPMI_SIM',
                                                 int_time_out =3,
                                                 b_with_buff = False)
                bmc_ssh.send_command_wait_string(str_command = 'sensor'+chr(13),
                                                 wait = 'IPMI_SIM',
                                                 int_time_out =3,
                                                 b_with_buff = False)
                bmc_ssh.send_command_wait_string(str_command = 'help'+chr(13),
                                                 wait = 'IPMI_SIM',
                                                 int_time_out =3,
                                                 b_with_buff = False)
                str_rsp = bmc_ssh.send_command_wait_string(str_command = 'history'+chr(13),
                                                           wait = 'IPMI_SIM',
                                                           int_time_out =3,
                                                           b_with_buff = False)

                count = 0
                lines = str_rsp.split('\n', str_rsp.count('\n'))
                self.log('INFO', 'IPMI_SIM History from node '+bmc_obj.get_ip()+' is \r'+str_rsp)
                for line in lines:
                    count = count+1

                #lines[count-1] is 'IPMI_SIM'
                #lines[count-2] is '\r'
                p_sensor = r'\d*\ssel\r'#pattern for lines[count-5]
                p_help_sensor = r'\d*\ssensor\r'#pattern for lines[count-4]
                p_help = r'\d*\shelp\r'#pattern for lines[count-3]

                if re.search(p_sensor, lines[count-5])  \
                        and re.search(p_help_sensor, lines[count-4])  \
                        and re.search(p_help, lines[count-3]) :
                    self.log('INFO', 'History from Node:{} .Rack is {}, Node is {}, BMC IP is: {}'.
                            format(str_rsp, obj_node.get_name(),obj_node.get_name(), bmc_obj.get_ip()))
                else:
                    self.result(FAIL,
                                'When history has more than 30 entries, '
                                'the last 3 entries are expected to be "sel", "sensor", "help".'
                                'See log for actual entries.'
                                'Rack is {}, Node is {}, BMC IP is: {}'
                                .format(obj_rack.get_name(),obj_node.get_name(), bmc_obj.get_ip()))

                time.sleep(1)

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
