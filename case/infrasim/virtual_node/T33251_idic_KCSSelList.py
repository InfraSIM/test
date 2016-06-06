'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T33251_idic_KCSSelList(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)

    def test(self):
        # Because disk vmdk file will be locked by hypervisor, this
        # case only take one node and test.
        self.test_node = self.stack.random_node()

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

        qemu_conn.remote_shell('echo {} | sudo -S modprobe ipmi_devintf'.format(
            self.data['host_password']))
        qemu_conn.remote_shell('echo {} | sudo -S modprobe ipmi_si'.format(
            self.data['host_password']))

        rsp = qemu_conn.remote_shell(
            'echo {} | sudo -S ipmitool sel list'.format(
                self.data['host_password']))

        self.log('INFO', 'rsp: \n{}'.format(rsp))

        if rsp['exitcode'] == 0:
            self.log('INFO',
                     'Able to issue local IPMI command ipmitool sel list')
        else:
            self.result(FAIL,
                        'Failed to issue local IPMI command ipmitool sel list, return: {}'.format(
                            rsp))

        qemu_conn.disconnect()

    def deconfig(self):
        self.log('INFO', 'Deconfig')
        CBaseCase.deconfig(self)

