from case.CBaseCase import *
from lib.Apps import dhcp_query_ip, md5
import gevent

PROMPT_GUEST = "root@localhost"
CONF = {}
class T130052_idic_ESXiTest(CBaseCase):
    '''
    [Purpose ]: Boot ESXi OS in InfraSIM host and send esx commands.
    [Author  ]: june.zhou@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        self.enable_node_ssh()

        if not os.path.isfile(os.environ["HOME"]+"/images/esxi6p3-1.qcow2"):
            print os.environ["HOME"]+"/images/esxi6p3-1.qcow2"
            self.log('INFO', "No esxi image for test.")
            raise Exception('No esxi image not found. Please put one in folder \'~/images/\'')
    
    def test(self):
        gevent.joinall([gevent.spawn(self.boot_to_disk, obj_node)
                       for obj_node in self.stack.walk_node()])
        gevent.joinall([gevent.spawn(self.esxcli_test, obj_node)
                       for obj_node in self.stack.walk_node()])

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def boot_to_disk(self, node):
        # Delete existing image if any, it might lead issue with booting
        print node.ssh.send_command_wait_string(str_command="echo infrasim | sudo -S rm -f /tmp/esxi6p3-1.qcow2"+chr(13), wait="~$")

        dst_path = node.send_file(os.environ["HOME"]+"/images/esxi6p3-1.qcow2", "/tmp/esxi6p3-1.qcow2")
        #dst_path = "/tmp/esxi6p3-1.qcow2"

        str_node_name = node.get_instance_name()

        payload = [
            {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"bootindex":1, "size": 8, "file": dst_path}]
            },
            {
                "type": "ahci", #to change to lsisas3008 after qemu lsi code merge in
                 "max_drive_per_controller":6,
                 "drives": [{"size": 8, "file": "/tmp/sda.img"}]
            }
        ]
        node.update_instance_config(str_node_name, payload, "compute", "storage_backend")

        payload = {
                "size":4096
        }

        node.update_instance_config(str_node_name, payload, "compute", "memory")

        payload = {
                "features":"+vmx"
        }
        node.update_instance_config(str_node_name, payload, "compute", "cpu")
        
        # Running ESXi really requires KVM to be present, using default value without specifying it
        # node.update_instance_config(str_node_name, "true", "compute", "kvm_enabled")

        node.update_instance_config(str_node_name, "e1000", "compute", "networks", 0, "device")
        node.update_instance_config(str_node_name, "bridge", "compute", "networks", 0, "network_mode")
        node.update_instance_config(str_node_name, "br0", "compute", "networks", 0, "network_name")

        # Set boot order to hard disk
        self.log('INFO', 'Set next boot option to disk on {}...'.format(node.get_name()))
        ret, rsp = node.get_bmc().ipmi.ipmitool_standard_cmd("chassis bootdev disk")
        if ret != 0:
            self.result(BLOCK, "Fail to set instance {} on {} boot from disk".
                        format(str_node_name, node.get_ip()))

        # Reboot to esxi img
        self.log('INFO', 'Power cycle guest to boot to disk on {}...'.format(node.get_name()))
        ret, rsp = node.get_bmc().ipmi.ipmitool_standard_cmd("chassis power cycle")
        if ret != 0:
            self.result(BLOCK, "Fail to set instance {} on {} boot from disk".
                        format(str_node_name, node.get_ip()))
            return

    def esxcli_test(self, node):
        str_node_name = node.get_instance_name()
        qemu_config = node.get_instance_config(str_node_name)
        qemu_first_mac = qemu_config["compute"]["networks"][0]["mac"].lower()
        # Get qemu IP
        
        rsp = node.ssh.send_command_wait_string(str_command=r"arp -e | grep {} | awk '{{print $1}}'".
                                                format(qemu_first_mac)+chr(13),
                                                wait="~$")
        qemu_first_ip = rsp.splitlines()[1]
        if not is_valid_ip(qemu_first_ip):
            # If fail to get IP via arp, try to query via dhcp lease
            try:
                qemu_first_ip = self.get_guest_ip(qemu_first_mac)
            except:
                self.result(BLOCK, "Fail to get virtual compute IP address on {} {}".
                            format(node.get_name(), node.get_ip()))
                return
        self.log("INFO", "Guest IP is {} on node {}".format(qemu_first_ip, node.get_name()))

        # SSH to guest, retry for 30 times
        times = 30
        time.sleep(30)
        for i in range(times):
            # Need to remove relative key to avoid key change alarm
            node.ssh.send_command_wait_string(str_command="ssh-keygen -f /home/infrasim/.ssh/known_hosts -R {}".  \
               format(qemu_first_ip)+chr(13), int_time_out = 10, wait="~$")

            node.ssh.send_command_wait_string(str_command="ssh root@{}".format(qemu_first_ip)+chr(13), 
                wait=["(yes/no)", "Password"])

            match_index = node.ssh.get_match_index()

            if match_index == 0:
                time.sleep(20)
                continue

            elif match_index == 1:
                node.ssh.send_command_wait_string(str_command="yes"+chr(13),
                                                  wait="Password")

            node.ssh.send_command_wait_string(str_command=self.data['host_password']+chr(13),
                                                  wait=PROMPT_GUEST)
            break

        if match_index == 0:
            self.result(BLOCK, "Tried ssh to guest on {} for {} times already, but still failed.".format(node.get_name(), times))
        else:
            self.esx_test_ipmi_fru(node)
            self.esx_test_storage_device(node)


    def esx_test_ipmi_fru(self, node):
        rsp = node.ssh.send_command_wait_string(str_command='esxcli hardware ipmi fru list'+chr(13),
                                                wait=PROMPT_GUEST)
        if 'Part Name: PowerEdge R730' not in rsp:
            self.result(FAIL, 'Node {} host get "esxcli hardware ipmi fru list" result on ESXi is unexpected, rsp\n{}'.
                        format(node.get_name(), json.dumps(rsp, indent=4)))
        self.log('INFO', 'rsp: \n{}'.format(rsp))

    def esx_test_storage_device(self, node):
        rsp = node.ssh.send_command_wait_string(str_command='esxcli storage core device list'+chr(13),
                                                wait=PROMPT_GUEST)
        if 'Display Name: Local ATA Disk' not in rsp:
            self.result(FAIL, 'Node {} host get "esxcli storage core device list" result on ESXi is unexpected, rsp\n{}'.
                        format(node.get_name(), json.dumps(rsp, indent=4)))
        self.log('INFO', 'rsp: \n{}'.format(rsp))

    def get_guest_ip(self, str_mac):
        DHCP_SERVER = self.data["DHCP_SERVER"]
        DHCP_USERNAME = self.data["DHCP_USERNAME"]
        DHCP_PASSWORD = self.data["DHCP_PASSWORD"]

        self.log('INFO', 'Query IP for MAC {} from DHCP server'.format(str_mac))

        time_start = time.time()
        guest_ip = ''
        while time.time() - time_start < 300:
            try:
                guest_ip = dhcp_query_ip(server=DHCP_SERVER,
                                         username=DHCP_USERNAME,
                                         password=DHCP_PASSWORD,
                                         mac=str_mac)
                rsp = os.system('ping -c 1 {}'.format(guest_ip))
                if rsp != 0:
                    self.log('INFO', 'Find an IP {} lease for MAC {}, but this IP is not online'.
                             format(guest_ip, str_mac))
                    time.sleep(30)
                    continue
                else:
                    self.log('INFO', 'Find an IP {} lease for MAC {}, this IP works'.
                             format(guest_ip, str_mac))
                    break
            except:
                self.log('WARNING', 'Fail to query IP for MAC {}'.format(str_mac))

        if not guest_ip:
            raise Exception('Fail to get IP for MAC {} in 300s'.format(str_mac))
        else:
            return guest_ip
