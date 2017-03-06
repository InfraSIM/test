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

                rst_dict = node_ssh.remote_shell("ps ax | grep \"qemu-system-x86_64\"")

                self.log('INFO', 'rsp: \n{}'.format(rst_dict["stdout"]))

                if re.search("qemu-system-x86_64 .*-name", rst_dict["stdout"]) is not None:
                    self.log('INFO', 'Process of QEMU is boot automatically.')
                else:
                    self.result(FAIL, 'Failed to automatically boot process of QEMU.')

                time.sleep(1)

    def deconfig(self):
        self.log('INFO', 'Deconfig')
        CBaseCase.deconfig(self)
