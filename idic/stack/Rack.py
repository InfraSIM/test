'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
'''
Created on Dec 22, 2015

@author: Tony Su
'''
from lib.Device import CDevice
from idic.stack.PDU import CPDU
from idic.stack.Node import CNode
from idic.stack.Switch import CSwitch

class CRack(CDevice):
    def __init__(self, dict_rack):

        CDevice.__init__(self, 'vRack')

        self.dict_config = dict_rack

        self.name = self.dict_config.get('name', '')
        self.hypervisor = self.dict_config.get('hypervisor', '')
        self.nodes = {}
        self.pdus = {}
        self.switchs = {}

        # vPDU
        for pdu_info in self.dict_config['vPDU']:
            obj_pdu = CPDU(pdu_info)
            self.add_pdu(obj_pdu)

        # vSwitch
        for switch_info in self.dict_config['vSwitch']:
            obj_switch = CSwitch(switch_info)
            self.add_switch(obj_switch)

        # vNode
        for node_info in self.dict_config['vNode']:
            obj_node = CNode(node_info)
            self.add_node(obj_node)

            # Bind Node to PDU outlet
            for dict_power in obj_node.get_config().get('power', {}):
                str_pdu_name = dict_power['vPDU']
                str_outlet = dict_power['outlet']
                obj_pdu = self.pdus.get(str_pdu_name, None)
                if (obj_pdu, str_outlet) not in obj_node.power:
                    obj_node.power.append((obj_pdu, str_outlet))
                obj_pdu.outlet[str_outlet]['node'] = obj_node

            # Bind Node to Switch port

    def get_config(self):
        return self.dict_config

    def get_name(self):
        return self.name

    def get_hypervisor(self):
        return self.hypervisor

    def add_node(self, obj_node):
        self.nodes[obj_node.get_name()] = obj_node

    def get_node_list(self):
        return self.nodes.values()

    def get_node_count(self):
        return self.nodes.__len__()

    def have_node(self):
        if self.nodes:
            return True
        else:
            return False

    def walk_node(self):
        '''
        Generator to traverse all nodes in this racks
        '''
        for obj_node in self.nodes.values():
            yield obj_node

    def add_pdu(self, obj_pdu):
        self.pdus[obj_pdu.get_name()] = obj_pdu

    def get_pdu_list(self):
        return self.pdus.values()

    def get_pdu_count(self):
        return self.pdus.__len__()

    def have_pdu(self):
        if self.pdus:
            return True
        else:
            return False

    def walk_pdu(self):
        '''
        Generator to traverse all pdus in this racks
        '''
        for obj_pdu in self.pdus.values():
            yield obj_pdu

    def add_switch(self, obj_switch):
        self.switchs[obj_switch.get_name()] = obj_switch

    def get_switch_list(self):
        return self.switchs.values()

    def get_switch_count(self):
        return self.switchs.__len__()

    def have_switch(self):
        if self.switchs:
            return True
        else:
            return False

    def walk_switch(self):
        '''
        Generator to traverse all switches in this racks
        '''
        for obj_switch in self.switchs.values():
            yield obj_switch
