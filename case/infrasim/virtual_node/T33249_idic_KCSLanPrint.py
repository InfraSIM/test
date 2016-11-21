'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re


class T33249_idic_KCSLanPrint(CBaseCase):
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)

        # Config all node to go to host.
        self.result(SKIP, "Deprecated, refer to case 97939")
        return
        self.enable_hypervisor_ssh()

    def test(self):
        # Because disk vmdk file will be locked by hypervisor, this
        # case only take one node and test.
        self.test_node = self.stack.random_node()

        self.log('INFO', 'Getting the fru data from node {}'.format(
            self.test_node.get_name()))

        str_ret, str_rsp = self.test_node.get_bmc().ipmi.ipmitool_standard_cmd(
            'fru print 0')

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
                        format(self.test_node.get_name(), str_rsp))

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
            # Mount disk vmdk to virtual node
            # Boot all nodes QEMU host to disk
            try:
                self.stack.boot_to_disk(self.test_node,
                                        disk_image=self.data['disk_image'])
            except Exception, e:
                self.result(BLOCK, 'Fail to boot node to disk: {}'.format(e))
                return
            try:
                qemu_conn = self.stack.get_host_ssh(self.test_node,
                                                    username=self.data[
                                                        'host_username'],
                                                    password=self.data[
                                                        'host_password'],
                                                    dhcp_server=self.data[
                                                        'dhcp_server'],
                                                    dhcp_user=self.data[
                                                        'dhcp_username'],
                                                    dhcp_pass=self.data[
                                                        'dhcp_password'])
            except Exception, e:
                self.result(BLOCK, 'Fail to get host access: {}'.format(e))
                return

            qemu_conn.remote_shell(
                'echo {} | sudo -S modprobe ipmi_devintf'.format(
                    self.data['host_password']))
            qemu_conn.remote_shell('echo {} | sudo -S modprobe ipmi_si'.format(
                self.data['host_password']))

            rsp = qemu_conn.remote_shell(
                'echo {} | sudo -S ipmitool lan print {}'.format(
                    self.data['host_password'], node_lan_channel))

            self.log('INFO', 'rsp: \n{}'.format(rsp))

            if rsp['exitcode'] == 0:
                self.log('INFO',
                         'Able to issue local IPMI command ipmitool lan')
            else:
                self.result(FAIL,
                            'Failed to issue local IPMI command ipmitool lan, return: {}'.format(
                                rsp))

    def deconfig(self):
        # Umount ubuntu disk image and recover node
        return
        self.stack.recover_disk(self.test_node)

        CBaseCase.deconfig(self)
