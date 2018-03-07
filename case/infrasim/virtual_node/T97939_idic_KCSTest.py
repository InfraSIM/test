from case.CBaseCase import *
from lib.Apps import md5
from lib.Apps import dhcp_query_ip
from lib.SSH import CSSH
import urllib
import re
import gevent
import paramiko
import os

PROMPT_GUEST = "infrasim@infrasim:~$"
# Due to bug IN-1419: ipmitool sensor list response: 'Unable to send command: Invalid argument'
# Test for command 'ipmitool sensor list' is skipped, will add back after IN-1419 is fixed.

str_ipmitool_script_content ='''
#!/bin/bash
set -e

echo "To collect ipmitool fru print..."
sudo ipmitool fru print |grep 'Product Name'
if [ $? -eq 0 ]; then
    echo "Node get fru print as expected!"
else
    echo "Can't get fru print info"
fi

echo "To collect ipmitool fru print 0..."
sudo ipmitool fru print 0 |grep 'Product Name'
if [ $? -eq 0 ]; then
    echo "Node get fru print 0 as expected!"
else
    echo "Can't get fru print 0 info"
fi

echo "To collect ipmitool lan print info..."
sudo ipmitool lan print 1 |grep 'IP Address'
if [ $? -eq 0 ]; then
    echo "Node get lan print 1 as expected!"
else
    echo "Can't get lan print 1 info"
fi

echo "To collect ipmitool sensor discrete list..."
sudo ipmitool sensor list |grep 'discrete'
if [ $? -eq 0 ]; then
    echo "Node get sensor discrete value as expected!"
else
    echo "Can't get sensor discrete value info"
fi

echo "To collect ipmitool sensor Temperature list ..."
sudo ipmitool sensor list |grep 'degree'
if [ $? -eq 0 ]; then
    echo "Node get sensor Temperature value as expected!"
else
    echo "Can't get sensor Temperature value info"
fi

echo "To clear SEL list..."
sudo ipmitool sel clear |grep "Clearing SEL"
if [ $? -eq 0 ]; then
    echo "Node SEL cleared"
else
    echo "Can't clear SEL"
fi

echo "To get SEL list..."
sudo ipmitool sel list |grep "Log area reset/cleared"
if [ $? -eq 0 ]; then
    echo "Node SEL info correct"
else
    echo "SEL info not correct"
fi
'''

class T97939_idic_KCSTest(CBaseCase):
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
        self.enable_node_ssh()


    def test(self):
        gevent.joinall([gevent.spawn(self.boot_to_disk, obj_node)
                        for obj_node in self.stack.walk_node()])
        gevent.joinall([gevent.spawn(self.kcs_test, obj_node)
                        for obj_node in self.stack.walk_node()])

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def boot_to_disk(self, node):
        dst_path = "/mnt/ubuntu_16.04.3.img"
        str_node_name = node.retry_get_instance_name()
        if str_node_name == '':
            self.result(BLOCK, "Failed to start infrasim instance on {}".
                        format(node.get_ip()))
            return

        payload = [
            {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8, "file": dst_path}]
            }
        ]
        node.update_instance_config(str_node_name, payload, "compute", "storage_backend")

        # Set boot order to hard disk
        self.log('INFO', 'Set next boot option to disk on {}...'.format(node.get_name()))
        ret, rsp = node.get_bmc().ipmi.ipmitool_standard_cmd("chassis bootdev disk")
        if ret != 0:
            self.result(BLOCK, "Fail to set instance {} on {} boot from disk".
                        format(str_node_name, node.get_ip()))
            return

        # Reboot to ubuntu_16.04.3.img
        self.log("INFO", "Power cycle guest to boot to disk on {}...".format(node.get_name()))
        ret, rsp = node.get_bmc().ipmi.ipmitool_standard_cmd("chassis power cycle")
        if ret != 0:
            self.result(BLOCK, "Fail to set instance {} on {} boot from disk".
                        format(str_node_name, node.get_ip()))
            return

    def kcs_test(self, node):
        str_node_name = node.retry_get_instance_name()
        if str_node_name == '':
            self.result(BLOCK, "Failed to start infrasim instance on {}".
                        format(node.get_ip()))
            return
        qemu_config = node.get_instance_config(str_node_name)
        qemu_macs = []
        for i in range(0, len(qemu_config["compute"]["networks"])):
            mac = qemu_config["compute"]["networks"][i].get("mac", None)
            if mac:
                qemu_macs.append(mac.lower())
        # Get qemu IP
        # Since in kcs image's network config, it has only one nic up with one bridge connected,
        # when there are mutiple nics in qemu config, not sure which one will be brought up, check
        # all one by one until we find the online ip.

        for mac in qemu_macs[:]:
            self.log("INFO", "Node {} qemu mac address: {}".format(node.get_name(), mac))

        self.log("INFO", "Getting guest IP for node {} ...".format(node.get_name()))
        for mac in qemu_macs[:]:
            rsp = node.ssh.send_command_wait_string(str_command=r"arp -e | grep {} | awk '{{print $1}}'".
                                                    format(mac)+chr(13),
                                                    wait="~$", int_time_out=100, b_with_buff=False)
            qemu_guest_ip = rsp.splitlines()[1]
            if not is_valid_ip(qemu_guest_ip) or not is_active_ip(qemu_guest_ip):
                qemu_guest_ip = None
            else:
                self.log("INFO", "Guest IP is {} on node {}".format(qemu_guest_ip, node.get_name()))

        # If fail to get IP via arp, try to query via dhcp lease
        if not qemu_guest_ip:
            qemu_guest_ip = self.get_guest_ip(qemu_macs)
            if qemu_guest_ip:
                self.log("INFO", "Guest IP is {} on node {}".format(qemu_guest_ip, node.get_name()))

            else:
                self.result(BLOCK, "Fail to get virtual compute IP address on {} {}".
                            format(node.get_name(), node.get_ip()))
                return

        # To create ipmitool shell script to run on guest OS.
        f = open('ipmitool.sh', 'w')
        f.write(str_ipmitool_script_content)
        f.close()

        # Copy script to guest OS.
        os.system("sshpass -p infrasim scp -o StrictHostKeyChecking=no ./ipmitool.sh infrasim@{}:/tmp/ipmitool.sh ".format(qemu_guest_ip))

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=qemu_guest_ip, port=22, username='infrasim', password='infrasim')
        chan = ssh.get_transport().open_session()
        self.log("INFO", "Executing script on remote guest IP: {} on node {}".format(node.get_ip(), node.get_name()))
        chan.exec_command('sudo bash +x /tmp/ipmitool.sh')

        # # skip error checking due to S2600KP issue IN-1420
        # stdin, stdout, stderr = chan.exec_command('sudo bash +x /tmp/ipmitool.sh')
        # error = stderr.readlines()
        # if error:
        #     print 'Script Running Failed!'
        #     for line in error:
        #         print line
        #     exit()

        if chan.recv_exit_status() == 0:
            self.result(PASS, "ipmitool execute succeeded on Node {} remotely! exit status: {}".
                        format(node.get_name(), chan.recv_exit_status()))
        else:
            self.result(FAIL, "ipmitool execute failed on Node {} remotely! exit status: {}".
                        format(node.get_name(), chan.recv_exit_status()))
        ssh.close()

    def get_guest_ip(self, macs):
        DHCP_SERVER = self.data["DHCP_SERVER"]
        DHCP_USERNAME = self.data["DHCP_USERNAME"]
        DHCP_PASSWORD = self.data["DHCP_PASSWORD"]

        self.log('INFO', 'Query IP for MAC {} from DHCP server'.format(macs))

        time_start = time.time()
        elapse_time = 300
        guest_ip = None
        while time.time() - time_start < elapse_time:
            for str_mac in macs:
                try:
                    guest_ip = dhcp_query_ip(server=DHCP_SERVER,
                                             username=DHCP_USERNAME,
                                             password=DHCP_PASSWORD,
                                             mac=str_mac)
                    rsp = os.system('ping -c 1 {}'.format(guest_ip))
                    if rsp != 0:
                        self.log('INFO', 'Find an IP {} lease for MAC {}, but this IP is not online'.
                                 format(guest_ip, str_mac))
                        guest_ip = None
                    else:
                        self.log('INFO', 'Find an IP {} lease for MAC {}, this IP works'.
                                 format(guest_ip, str_mac))
                        return guest_ip
                except:
                    self.log('WARNING', 'Fail to query IP for MAC {}'.format(str_mac))
            time.sleep(30)

        if not guest_ip:
            self.log('WARNING', 'Fail to get IP for MAC {} in {}s'.format(str_mac, elapse_time))
            return