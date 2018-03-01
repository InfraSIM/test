from case.CBaseCase import *
from lib.Apps import md5
from lib.Apps import dhcp_query_ip
from lib.SSH import CSSH
import urllib
import re
import gevent

PROMPT_GUEST = "infrasim@infrasim:~$"

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
        time.sleep(4)
        # SSH to guest
        print node.ssh.send_command_wait_string(str_command="ssh infrasim@{}".format(qemu_guest_ip)+chr(13),
                                          wait=["(yes/no)", "password"], int_time_out=100, b_with_buff=False)
        match_index = node.ssh.get_match_index()
        if match_index == 0:
            self.result(BLOCK, "Fail to ssh to guest {} on {} {}".
                        format(qemu_guest_ip, node.get_name(), node.get_ip()))
            return
        elif match_index == 1:
            node.ssh.send_command_wait_string(str_command="yes"+chr(13),
                                              wait="password", int_time_out=100, b_with_buff=False)
        node.ssh.send_command_wait_string(str_command="infrasim"+chr(13),
                                          wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)

        time.sleep(4)
        self.kcs_test_fru_print(node)
        self.kcs_test_lan_print(node)
        self.kcs_test_sensor_list(node)
        self.kcs_test_sel_list(node)

    def kcs_test_fru_print(self, node):
        rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool fru print'+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)
        if 'Product Name' not in rsp:
            self.result(FAIL, 'Node {} host get "fru print" result on KCS is unexpected, rsp\n{}'.
                        format(node.get_name(), json.dumps(rsp, indent=4)))
        self.log('INFO', 'rsp: \n{}'.format(rsp))

        rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool fru print 0'+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)
        if 'Product Name' not in rsp:
            self.result(FAIL, 'Node {} host get "frp print 0" result on KCS is unexpected\n{}'.
                        format(node.get_name(), json.dumps(rsp, indent=4)))
        self.log('INFO', 'rsp: \n{}'.format(rsp))

    def kcs_test_lan_print(self, node):
        ret, rsp = node.get_bmc().ipmi.ipmitool_standard_cmd('fru print 0')

        fru = {}
        for item in rsp.split('\n'):
            key = item.split(': ')[0].strip()
            value = item.split(': ')[-1].strip()
            fru[key] = value

        try:
            node_lan_channel = self.data[fru['Product Name']]

        except KeyError, e:
            self.result(BLOCK,
                        """
                        KeyError: {}.
                        Please supplement product name of node ({}) and the
                        corresponding lan channel in {}.json.
                        """
                        .format(e, e, self.__class__.__name__))
            return

        rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool lan print {}'.
                                                format(node_lan_channel)+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)
        self.log('INFO', 'rsp: \n{}'.format(rsp))

        if "IP Address" not in rsp:
            self.result(FAIL, 'IPMI command via kcs on node {} fail: lan print {}'.
                        format(node.get_name(), node_lan_channel))

    def kcs_test_sensor_list(self, node):
        lan_result_str = ''
        local_result_str = ''
        lan_ret, lan_rsp = node.get_bmc().ipmi.ipmitool_standard_cmd('sensor list')
        self.log('INFO', 'ret: {}'.format(lan_ret))
        self.log('INFO', 'rsp: \n{}'.format(lan_rsp))
        if lan_ret != 0:
            self.result(FAIL, 'Node {} fail to check BMC sensor list, '
                              'ipmitool return: {}, expect: 0, rsp: \n{}'.
                        format(node.get_name(), lan_ret, lan_rsp))
        # To match "degree" and "discrete".
        # Any system should show both word in sensor list info if sensor list display normally.
        is_match_discrete = re.search(r'discrete', format(lan_rsp))
        is_match_degress = re.search(r'degree', format(lan_rsp))
        if is_match_discrete is None or is_match_degress is None:
            lan_result_str = 'IPMI command via lanplus on node {} fail: \
                             ipmitool -I lanplus -H {} -U admin -P admin sensor list \n'.\
                             format(node.get_name(),node.get_bmc().get_ip())

        local_rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool sensor list'+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)
        self.log('INFO', 'rsp: \n{}'.format(local_rsp))

        is_match_discrete = re.search(r'discrete', format(local_rsp))
        is_match_degress = re.search(r'degree', format(local_rsp))
        if is_match_discrete is None or is_match_degress is None:
            local_result_str = 'IPMI command via kcs on node {} fail: ipmitool sensor list \n'.format(node.get_name())

        if lan_result_str or local_result_str:
            self.result(FAIL, lan_result_str + local_result_str)

    def kcs_test_sel_list(self, node):

        rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool sel clear'+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)

        rsp = node.ssh.send_command_wait_string(str_command='sudo ipmitool sel list'+chr(13),
                                                wait=PROMPT_GUEST, int_time_out=100, b_with_buff=False)
        self.log('INFO', 'rsp: \n{}'.format(rsp))

        # To match "Log area reset/cleared".
        if "Log area reset/cleared" not in rsp:
            self.result(FAIL, 'IPMI command via kcs on node {} fail: ipmitool sel list'.
                        format(node.get_name()))

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
