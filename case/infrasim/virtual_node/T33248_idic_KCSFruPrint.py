from case.CBaseCase import *
from lib.SSH import CSSH
from lib.Apps import dhcp_query_ip


class T33248_idic_KCSFruPrint(CBaseCase):
    '''
    [Purpose ]: Boot OS in InfraSIM host and send ipmi command.
    [Author  ]: forrest.gu@emc.com
    '''
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

        # Mount disk vmdk to virtual node
        # Boot all nodes QEMU host to disk
        try:
            self.stack.boot_to_disk(self.test_node, disk_image=self.data['disk_image'])
        except Exception, e:
            self.result(BLOCK, 'Fail to boot node to disk: {}'.format(e))
            return
        try:
            qemu_conn = self.stack.get_host_ssh(self.test_node,
                                                username=self.data['host_username'],
                                                password=self.data['host_password'],
                                                dhcp_server=self.data['dhcp_server'],
                                                dhcp_user=self.data['dhcp_username'],
                                                dhcp_pass=self.data['dhcp_password'])
        except Exception, e:
            self.result(BLOCK, 'Fail to get host access: {}'.format(e))
            return

        qemu_conn.remote_shell('echo {} | sudo -S modprobe ipmi_devintf'.format(self.data['host_password']))
        qemu_conn.remote_shell('echo {} | sudo -S modprobe ipmi_si'.format(self.data['host_password']))

        rsp = qemu_conn.remote_shell('echo {} | sudo -S ipmitool fru print'.format(self.data['host_password']))
        if 'Product Name' not in rsp['stdout']:
            self.result(FAIL, 'Node {} host get "frp print" result on KCS is unexpected, rsp\n{}'.
                        format(self.test_node.get_name(), json.dumps(rsp, indent=4)))

        rsp = qemu_conn.remote_shell('echo {} | sudo -S ipmitool fru print 0'.format(self.data['host_password']))
        if 'Product Name' not in rsp['stdout']:
            self.result(FAIL, 'Node {} host get "frp print 0" result on KCS is unexpected\n{}'.
                        format(self.test_node.get_name(), json.dumps(rsp, indent=4)))

        qemu_conn.disconnect()
    
    def deconfig(self):
        return
        # Umount ubuntu disk image and recover node
        self.stack.recover_disk(self.test_node)

        CBaseCase.deconfig(self)

