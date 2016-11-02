'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re


class T46194_idic_QEMUBootAutomatically(CBaseCase):

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

                node_ssh = obj_node.ssh
                str_rsp = node_ssh.send_command_wait_string(str_command='ps ax | grep "qemu-system-x86_64"'+chr(13),
                                                            wait='$',
                                                            int_time_out=10,
                                                            b_with_buff=False)

                self.log('INFO', 'rsp: \n{}'.format(str_rsp))

                if re.search("qemu-system-x86_64", str_rsp) is not None:
                    self.log('INFO', 'Process of QEMU is boot automatically.')
                else:
                    self.result(FAIL, 'Failed to automatically boot process of QEMU.')

                time.sleep(1)

    def deconfig(self):
        self.log('INFO', 'Deconfig')
        CBaseCase.deconfig(self)
