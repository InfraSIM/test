'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Nov 30, 2015

@author: Tony Su
*********************************************************
'''
from lib.Device import CDevice
from idic.stack.Hypervisor import CHypervisor
from idic.stack.Rack import CRack
from lib.restapi import APIClient
from lib.Apps import is_valid_ip, dhcp_query_ip
from lib.SSH import CSSH
from lib.IOL import CIOL

import json
import time
import os
import random


class CStack(CDevice):
    def __init__(self, dict_stack):

        CDevice.__init__(self, 'vStack')

        self.dict_config = dict_stack

        # HyperVisor
        self.hypervisors = {}
        for hypervisor_info in self.dict_config['available_HyperVisor']:
            obj_hypervisor = CHypervisor(hypervisor_info)
            self.hypervisors[obj_hypervisor.get_name()] = obj_hypervisor

        # vRacks
        self.racks = {}
        for rack_info in self.dict_config['vRacks']:
            obj_rack = CRack(rack_info)
            self.racks[obj_rack.get_name()] = obj_rack

        # vRackSystem REST agent
        self.dict_vracksystem = self.dict_config['vRackSystem']
        self.rest = APIClient(username=self.dict_vracksystem['username'],
                              password=self.dict_vracksystem['password'],
                              session_log=True)
        self.rest_root = '{}://{}:{}{}'.format(self.dict_vracksystem['protocol'],
                                               self.dict_vracksystem['ip'],
                                               self.dict_vracksystem['port'],
                                               self.dict_vracksystem['root'])

        self.b_valid = True

    def is_valid(self):
        return self.b_valid

    def update(self):
        return self

    def get_config(self):
        return self.dict_config

    def get_hypervisor_list(self):
        return self.hypervisors.values()

    def get_hypervisor_count(self):
        return len(self.hypervisors)

    def get_hypervisor(self, hypervisor_name):
        for hypervisor in self.walk_hypervisor():
            if hypervisor.get_name() == hypervisor_name:
                return hypervisor
        return None

    def get_rack_list(self):
        return self.racks.values()

    def get_rack_count(self):
        return len(self.racks)

    def get_rack(self, rack_name):
        for rack in self.walk_rack():
            if rack.get_name() == rack_name:
                return rack
        return None

    def have_rack(self):
        '''
        If any rack in this stack
        '''
        if self.racks:
            return True
        else:
            return False

    def have_pdu(self):
        '''
        If any PDU in this stack
        '''
        for obj_rack in self.walk_rack():
            if obj_rack.have_pdu():
                return True
        return False

    def have_node(self):
        '''
        If any node in this stack
        '''
        for obj_rack in self.walk_rack():
            if obj_rack.have_node():
                return True
        return False

    def have_switch(self):
        '''
        If any switch in this stack
        '''
        for obj_rack in self.walk_rack():
            if obj_rack.have_switch():
                return True
        return False

    def walk(self):
        '''
        Generator to traverse all resources in stack
        In a sequence of hypervisor, rack, pdu, node, switch
        '''
        for obj_device in self.walk_hypervisor():
            yield obj_device

        for obj_device in self.walk_rack():
            yield obj_device

        for obj_device in self.walk_pdu():
            yield obj_device

        for obj_device in self.walk_node():
            yield obj_device

        for obj_device in self.walk_switch():
            yield obj_device

    def walk_hypervisor(self):
        '''
        Generator to traverse hypervisors in this stack
        '''
        for obj_hypervisor in self.hypervisors.values():
            yield obj_hypervisor

    def walk_rack(self):
        '''
        Generator to traverse racks in this stack
        '''
        for obj_rack in self.racks.values():
            yield obj_rack

    def walk_pdu(self):
        '''
        Generator to traverse all pdus in this stack
        '''
        for obj_rack in self.walk_rack():
            for obj_pdu in obj_rack.walk_pdu():
                yield obj_pdu

    def walk_node(self):
        '''
        Generator to traverse all nodes in this stack
        '''
        for obj_rack in self.walk_rack():
            for obj_node in obj_rack.walk_node():
                yield obj_node

    def walk_switch(self):
        '''
        Generator to traverse all switches in this stack
        '''
        for obj_rack in self.walk_rack():
            for obj_switch in obj_rack.walk_switch():
                yield obj_switch

    def query_node(self, str_condition):
        '''
        Return a node object if it match condition
        Support IP query now.
        '''
        if is_valid_ip(str_condition):
            for obj_node in self.walk_node():
                if obj_node.get_bmc().get_ip() == str_condition:
                    return obj_node
        return None

    def random_node(self):
        '''
        Return a random node
        '''
        try:
            self.walk_node().next()
        except StopIteration:
            self.log('WARNING', 'No node in stack at all')
            return None

        list_nodes = []
        for node in self.walk_node():
            list_nodes.append(node)

        the_node = random.choice(list_nodes)

        self.log('INFO', '*'*80)
        self.log('INFO', '*   Life is like a box of chocolates, you never know what you\'re gonna get.    *')
        self.log('INFO', '*                                               - Forrest                      *')
        self.log('INFO', '*   The node to test is: {}*'.format(the_node.get_name().ljust(54)))
        self.log('INFO', '*'*80)

        return the_node

    # ------------------------------
    # vRack access via vRackSystem
    # ------------------------------

    def rest_get_hypervisor_id(self, str_hypervisor_ip):
        uri_esix = '{}/esxi/'.format(self.rest_root)
        rsp = self.rest.send_get(uri_esix)
        if rsp['status'] != 200:
            raise Exception('Fail to get esxi information')
        for dict_esxi in rsp['json']:
            if dict_esxi['esxiIP'] == str_hypervisor_ip:
                return dict_esxi['id']
        raise Exception('Hypervisor (IP: {}) is not registered in vRackSystem'.
                        format(str_hypervisor_ip))

    def rest_get_node_power_status(self, str_hyperisor_ip, str_node_name):
        int_hypervisor_id = self.rest_get_hypervisor_id(str_hyperisor_ip)
        uri_getvm = '{}/esxi/{}/getvms'.format(self.rest_root, int_hypervisor_id)
        rsp = self.rest.send_get(uri_getvm)
        if rsp['status'] != 200:
            raise Exception('Fail to get esxi vm information')
        for dict_vm in json.loads(rsp['json']):
            if dict_vm['name'] == str_node_name:
                return dict_vm['status']
        raise Exception('Node ({}) is not managed by hypervisor (IP: {})'.
                        format(str_node_name, str_hyperisor_ip))

    # ------------------------------
    # vRack access via ESXi vim-cmd
    # ------------------------------

    def boot_to_disk(self, obj_node, disk_image):
        '''
        Try to connect to host, if fail, reconfig to boot from disk, then connect
        '''

        dtstore = obj_node.get_datastore()
        vm_name = obj_node.get_name()
        hypervisor = self.get_hypervisor(obj_node.get_hypervisor())

        # Mount drive
        vm_id = hypervisor.get_vmid(dtstore, vm_name)
        self.log('INFO', 'VM {} ID is got: {}'.format(obj_node.get_name(), vm_id))

        hypervisor.power_off(vm_id)
        self.log('INFO', 'VM {} powering off, wait 10s ...'.format(obj_node.get_name()))
        time.sleep(10)

        hypervisor.drive_delete(dtstore, vm_name, 0, 1)
        image_path = hypervisor.search_datastore(disk_image)[0]
        hypervisor.drive_add(dtstore, vm_name, image_path)

        hypervisor.power_on(vm_id)
        self.log('INFO', 'VM {} powering on, wait up to 90s ...'.format(obj_node.get_name()))
        time_start = time.time()
        while time.time() - time_start < 90:
            ip = hypervisor.get_vm_ip(vm_id)
            if ip:
                if obj_node.get_bmc().get_ip() == ip:
                    obj_node.get_bmc().ssh.connect()
                    break
                else:
                    obj_node.get_bmc().set_ip(ip)
                    obj_node.get_bmc().ssh = CSSH(ip, 'root', 'root')
                    obj_node.get_bmc().ssh.connect()
                    bmc_user = obj_node.get_bmc().get_username()
                    bmc_pass = obj_node.get_bmc().get_password()
                    obj_node.get_bmc().ipmi = CIOL(str_ip=ip, str_user=bmc_user, str_password=bmc_pass)
            time.sleep(10)

        self.log('INFO', 'VM {} booting host to disk, wait up to 40s ...'.format(obj_node.get_name()))
        # For ipmi_sim to boot
        time.sleep(30)
        ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis bootdev disk')
        if ret != 0:
            raise Exception('Fail to set VM {} to boot from disk'.format(obj_node.get_name()))
        ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis power cycle')
        if ret != 0:
            raise Exception('Fail to power cycle VM {}'.format(obj_node.get_name()))
        # For host to boot
        time.sleep(10)

        return

    def get_host_ssh(self, obj_node, username, password, **kwargs):
        '''
        Build a SSH connection to host in virtual node
        '''
        if 'qemu_ip' in kwargs:
            self.log('INFO', 'Build host SSH to {}@{}'.format(username, kwargs['qemu_ip']))
            conn = CSSH(ip=kwargs['qemu_ip'], username=username, password=password, port=kwargs.get('port', 22))
            conn.connect()
            return conn

        # To get host's IP address:
        #     - Get MAC
        #     - Get IP via DHCP lease on DHCP server
        #     - Check if IP is available
        #     - SSH to host
        if 'dhcp_server' in kwargs and 'dhcp_user' in kwargs and 'dhcp_pass' in kwargs:
            self.log('INFO', 'Query host IP from DHCP server {} ...'.format(kwargs['dhcp_server']))

            # Get IP
            rsp_qemu = obj_node.get_bmc().ssh.remote_shell('ps aux | grep qemu')
            if rsp_qemu['exitcode'] != 0:
                raise Exception('Fail to get node {} qemu MAC address'.format(obj_node.get_name()))
            qemu_mac = rsp_qemu['stdout'].split('mac=')[1].split(' ')[0].lower()
            self.log('INFO', 'Node {} host MAC address is: {}'.format(obj_node.get_name(), qemu_mac))

            self.log('INFO', 'Wait node {} host IP address in up to 300s ...'.format(obj_node.get_name()))
            time_start = time.time()
            qemu_ip = ''
            while time.time() - time_start < 300:
                try:
                    qemu_ip = dhcp_query_ip(server=kwargs['dhcp_server'],
                                            username=kwargs['dhcp_user'],
                                            password=kwargs['dhcp_pass'],
                                            mac=qemu_mac)
                    if qemu_ip == obj_node.get_bmc().get_ip():
                        self.log('WARNING', 'IP lease for mac {} is {} to node {}\'s BMC, '
                                            'waiting for host IP lease, retry after 30s ...'.
                                 format(qemu_mac, qemu_ip, obj_node.get_name()))
                        time.sleep(30)
                        continue
                    rsp = os.system('ping -c 1 {}'.format(qemu_ip))
                    if rsp != 0:
                        self.log('WARNING', 'Find an IP {} lease for mac {} on node {}, '
                                            'but this IP address is not available, retry after 30s ...'.
                                 format(qemu_ip, qemu_mac, obj_node.get_name()))
                        time.sleep(30)
                        continue
                    else:
                        self.log('INFO', 'Node {} host get IP {}'.format(obj_node.get_name(), qemu_ip))
                        break
                except Exception, e:
                    self.log('WARNING', 'Fail to get node {}\'s host IP: {}'.format(obj_node.get_name(), e))
                    time.sleep(30)

            if not qemu_ip:
                raise Exception('Fail to get node {}\'s host IP in 300s, '
                                'check if vSwith\'s promiscuous mode is "Accept"'.
                                format(obj_node.get_name()))

            conn = CSSH(ip=qemu_ip,
                        username=kwargs.get('host_username', 'june'),
                        password=kwargs.get('host_password', '111111'),
                        port=kwargs.get('port', 22))
            conn.connect()
            return conn

    def recover_disk(self, obj_node):

        dtstore = obj_node.get_datastore()
        vm_name = obj_node.get_name()
        hypervisor = self.get_hypervisor(obj_node.get_hypervisor())

        # Mount drive
        vm_id = hypervisor.get_vmid(dtstore, vm_name)
        self.log('INFO', 'VM {} ID is got: {}'.format(obj_node.get_name(), vm_id))

        hypervisor.power_off(vm_id)
        self.log('INFO', 'VM {} powering off, wait 10s ...'.format(obj_node.get_name()))
        time.sleep(10)

        hypervisor.drive_delete(dtstore, vm_name, 0, 1)
        image_path = hypervisor.search_datastore('{}_1.vmdk'.format(obj_node.get_name()))[0]
        hypervisor.drive_add(dtstore, vm_name, image_path)

        hypervisor.power_on(vm_id)
        self.log('INFO', 'VM {} powering on, wait up to 90s ...'.format(obj_node.get_name()))
        time_start = time.time()
        while time.time() - time_start < 90:
            ip = hypervisor.get_vm_ip(vm_id)
            if ip:
                if obj_node.get_bmc().get_ip() == ip:
                    obj_node.get_bmc().ssh.connect()
                    break
                else:
                    obj_node.get_bmc().set_ip(ip)
                    obj_node.get_bmc().ssh = CSSH(ip, 'root', 'root')
                    obj_node.get_bmc().ssh.connect()
                    bmc_user = obj_node.get_bmc().get_username()
                    bmc_pass = obj_node.get_bmc().get_password()
                    obj_node.get_bmc().ipmi = CIOL(str_ip=ip, str_user=bmc_user, str_password=bmc_pass)
            time.sleep(10)

        return

if __name__ == '__main__':
    '''
    Unit Test
    '''

    dict_stack = \
{
    "available_HyperVisor": [
        {
            "name": "hyper1",
            "type": "ESXi",
            "ip": "192.168.1.2",
            "username": "username",
            "password": "password"
        }
    ],
    "vRacks": [
        {
            "name": "vRack1",
            "hypervisor": "hyper1",
            "vPDU": [
                {
                    "name": "vpdu_1",
                    "datastore": "Datastore01",
                    "community": "foo",
                    "ip": "172.31.128.1",
                    "outlet": {
                        "1.1": "bar",
                        "1.2": "bar",
                        "1.3": "bar"
                    }
                }
            ],
            "vSwitch": [
            ],
            "vNode": [
                {
                    "name": "vnode_a_20160126114700",
                    "datastore": "Datastore01",
                    "power": [
                        {"vPDU": "vpdu_1", "outlet": "1.1"}
                    ],
                    "network": [],
                    "bmc": {
                        "ip": "172.31.128.2",
                        "username": "admin",
                        "password": "admin"
                    }
                }
            ]
        }
    ]
}

    # Stack Object
    obj_stack = CStack(dict_stack)

    # isVaild
    print "isVaild", obj_stack.is_valid()

    # HyperVisor
    print "HyperVisorList", obj_stack.get_hypervisor_list()
    print "HyperVisorCount", obj_stack.get_hypervisor_count()
    for obj_hypervisor in obj_stack.get_hypervisor_list():
        print "HyperVisorInfo", \
            obj_hypervisor.get_ip(),\
            obj_hypervisor.get_username(),\
            obj_hypervisor.get_password()

    # vRack
    print "vRackList", obj_stack.get_rack_list()
    print "vRackConut", obj_stack.get_rack_count()
    # obj_rack_list = obj_stack.get_rack_list()
    # obj_rack_1 = obj_rack_list[0]
    for obj_rack in obj_stack.get_rack_list():

        # vNode
        print "vNodeList", obj_rack.get_node_list()
        print "vNodeCount", obj_rack.get_node_count()
        for obj_node in obj_rack.get_node_list():
            print "vNodeName", obj_node.get_name()
            obj_bmc = obj_node.get_bmc()
            print "vBMCIP", obj_bmc.get_ip()
            print "vBMCUsername", obj_bmc.get_username()
            print "vBMCPassword", obj_bmc.get_password()
        else:
            print "No vBMC on this vRack"

        # vPDU
        print "vPDUList", obj_rack.get_pdu_list()
        print "vPDUCount", obj_rack.get_pdu_count()
        # obj_pdu_list = obj_stack.get_pdu_list(obj_rack_1)
        # obj_pdu_1 = obj_pdu_list[0]
        for obj_pdu in obj_rack.get_pdu_list():
            print "vPDUIP", obj_pdu.get_ip()
            print "vPDUName", obj_pdu.get_name()
        else:
            print "No vPDU on this vRack"

        # vSwitch
        print "vSwitchList", obj_rack.get_switch_list()
        print "vSwitchCount", obj_rack.get_switch_count()
        # obj_switch_list = obj_stack.get_switch_list(obj_rack_1)
        # obj_switch_1 = obj_switch_list[0]
        for obj_switch in obj_rack.get_switch_list():
            print "vSwitchIP", obj_switch.get_config()
        else:
            print "No vSwitch on this vRack"
