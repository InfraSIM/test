'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T33249_idic_IPMILocalLanPrint(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_bmc_ssh()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))

                obj_bmc = obj_node.get_bmc()
                bmc_ssh = obj_bmc.ssh
                str_rsp = bmc_ssh.send_command_wait_string(str_command='ipmitool -I lanplus -H localhost -U {} -P {} fru print 0 {}'.
                                                           format(obj_bmc.get_username(), obj_bmc.get_password(), chr(13)),
                                                           wait='$',
                                                           int_time_out=10,
                                                           b_with_buff=False)
                if not str_rsp:
                    self.result(BLOCK, 'Fail to get node {} FRU information and get specified data')
                    return

                fru = {}
                for item in str_rsp.split('\n'):
                    key = item.split(': ')[0].strip()
                    value = item.split(': ')[-1].strip()
                    fru[key] = value

                # If ipmitool not response as expected, key shall be lost
                # and this test shall be blocked on this node
                if 'Product Name' not in fru:
                    self.result(BLOCK, 'Node {} fail to get fru print information, '
                                       'response of ipmitool is:\n{}'.
                                format(obj_node.get_name(), str_rsp))
                    continue

                try:
                    node_lan_channel = self.data[fru['Product Name']]

                except KeyError, e:
                    self.result(BLOCK,
                    """
                    KeyError: {}.
                    Please supplement product name of node ({}) and the corresponding lan channel in {}.json.
                    For more details, please read the document: https://infrasim.readthedocs.org/en/latest/
                    """
                                .format(e, e, self.__class__.__name__))
                else:
                    str_rsp = bmc_ssh.send_command_wait_string(str_command='ipmitool -I lanplus -H localhost -U {} -P {} lan print {} {}'.
                                                               format(obj_bmc.get_username(), obj_bmc.get_password(), node_lan_channel, chr(13)),
                                                               wait='$',
                                                               int_time_out=3,
                                                               b_with_buff = False)

                    self.log('INFO', 'rsp: \n{}'.format(str_rsp))
                    is_match = re.search("failed", str_rsp)
                    if is_match == None:
                        self.log('INFO', 'Able to issue local IPMI command ipmitool lan')
                    else:
                        self.result(FAIL, 'Failed to issue local IPMI command ipmitool lan, return: {}'.format(str_rsp))

                time.sleep(1)

    def deconfig(self):
        self.log('INFO', 'Deconfig')
        CBaseCase.deconfig(self)

