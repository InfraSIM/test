from case.CBaseCase import *
from lib.SSH import CSSH
from lib.Apps import dhcp_query_ip
import re


class T33250_idic_KCSSensorList(CBaseCase):
    '''
    [Purpose ]: Boot OS in InfraSIM host and send ipmi command.
    [Author  ]: june.zhou@emc.com
    '''

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)

        # Config all node to go to host.
        self.result(BLOCK, "Going to rewrite KCS test")
        return
        self.enable_hypervisor_ssh()

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
            'echo {} | sudo -S ipmitool sensor list'.format(
                self.data['host_password']))

        self.log('INFO', 'rsp: \n{}'.format(rsp))

        # To match "degree" and "discrete".
        # Any system should show both word in sensor list info if sensor list display normally.
        is_match_discrete = re.search(r'discrete', format(rsp))
        is_match_degress = re.search(r'degree', format(rsp))
        if is_match_discrete == None or is_match_degress == None:
            self.result(FAIL,
                        'Failed on local IPMI command ipmitool sensor list, return: {}'.format(
                            rsp['stdout']))
        else:
            self.log('INFO',
                     'Able to issue local IPMI command ipmitool sensor list')
        qemu_conn.disconnect()

    def deconfig(self):
        # Umount ubuntu disk image and recover node
        return
        self.stack.recover_disk(self.test_node)

        CBaseCase.deconfig(self)
