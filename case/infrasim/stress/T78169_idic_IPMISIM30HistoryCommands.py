from case.CBaseCase import *
import re

class T78169_idic_IPMISIM30HistoryCommands(CBaseCase):
    '''
    [Purpose ]: Stress sending 30 history commands and verify it record
                history accordingly
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_console()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'To try ipmi-console history when more '
                                 'than 30 commands run for node {}...'.
                         format(obj_node.get_name()))

                ipmi_console = obj_node.ssh_ipmi_console

                count = 0
                while count < 30:
                    self.log('INFO', 'Stress history command {}/30'.format(count))
                    str_rsp = ipmi_console.send_command_wait_string(str_command='history' + chr(13),
                                                                    wait='IPMI_SIM>',
                                                                    int_time_out=10,
                                                                    b_with_buff=False)
                    count += 1

                p = re.compile(r"(\d)*\s*history")
                m = p.findall(str_rsp)
                if len(m) != 30:
                    self.result(FAIL, 'Fail to find 30 history command entry '
                                      'in last history query, count: {}'.
                                format(len(m)))

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
