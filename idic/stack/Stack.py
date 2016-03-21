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

import json


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
                              session_log=False)
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

    def get_rack_list(self):
        return self.racks.values()

    def get_rack_count(self):
        return len(self.racks)

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

    # ------------------------------
    # vRack access via vRackSystem,
    # i.e. via hypervisor
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
