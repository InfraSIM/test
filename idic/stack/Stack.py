'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Nov 30, 2015

@author: Tony Su
*********************************************************
'''
from lib.Device import CDevice
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

        # vRacks
        self.racks = {}
        for rack_info in self.dict_config['vRacks']:
            obj_rack = CRack(rack_info)
            self.racks[obj_rack.get_name()] = obj_rack

        self.b_valid = True

    def is_valid(self):
        return self.b_valid

    def update(self):
        return self

    def get_config(self):
        return self.dict_config

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

    def have_chassis(self):
        '''
        If any chassis in this stack
        '''
        for obj_rack in self.walk_rack():
            if obj_rack.have_switch():
                return True
        return False

    def walk(self):
        '''
        Generator to traverse all resources in stack
        In a sequence of rack, pdu, node, switch, chassis
        '''

        for obj_device in self.walk_rack():
            yield obj_device

        for obj_device in self.walk_pdu():
            yield obj_device

        for obj_device in self.walk_node():
            yield obj_device

        for obj_device in self.walk_switch():
            yield obj_device

        for obj_device in self.walk_chassis():
            yield obj_device

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

    def walk_chassis(self):
        '''
        Generator to traverse all chassis in this stack
        '''
        for obj_rack in self.walk_rack():
            for obj_chassis in obj_rack.walk_chassis():
                yield obj_chassis

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

if __name__ == '__main__':
    '''
    Unit Test
    '''

    dict_stack = \
{
    "vRacks": [
        {
            "name": "vRack1",
            "vPDU": [
                {
                    "name": "vpdu_1",
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
                    "power": [
                        {"vPDU": "vpdu_1", "outlet": "1.1"}
                    ],
                    "admin": {
                        "ip": "192.168.134.114",
                        "username": "infrasim",
                        "password": "infrasim"
                    },
                    "bmc": {
                        "ip": "172.31.128.14",
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

    # vRack
    print "vRackList", obj_stack.get_rack_list()
    print "vRackConut", obj_stack.get_rack_count()

    for obj_element in obj_stack.walk():
        print "element:", obj_element.get_name()

    for obj_rack in obj_stack.walk_rack():

        # vNode
        print "vNodeList", obj_rack.get_node_list()
        print "vNodeCount", obj_rack.get_node_count()
        for obj_node in obj_rack.walk_node():
            print "vNodeName", obj_node.get_name()
            print "vNodeAdminIP", obj_node.get_ip()
            print "vNodeAdminUsername", obj_node.get_username()
            print "vNodeAdminPassword", obj_node.get_password()

            obj_bmc = obj_node.get_bmc()
            print "vBMCIP", obj_bmc.get_ip()
            print "vBMCUsername", obj_bmc.get_username()
            print "vBMCPassword", obj_bmc.get_password()

        # vPDU
        print "vPDUList", obj_rack.get_pdu_list()
        print "vPDUCount", obj_rack.get_pdu_count()
        for obj_pdu in obj_rack.walk_pdu():
            print "vPDUIP", obj_pdu.get_ip()
            print "vPDUName", obj_pdu.get_name()

        # vSwitch
        print "vSwitchList", obj_rack.get_switch_list()
        print "vSwitchCount", obj_rack.get_switch_count()
        for obj_switch in obj_rack.walk_switch():
            print "vSwitchIP", obj_switch.get_config()

        # vChassis
        print "vChassisList", obj_rack.get_chassis_list()
        for obj_chassis in obj_rack.walk_chassis():
            print "vChassis", obj_chassis.get_config()