'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: SkuCollection.py
[Author  ]: Payne Wang(Payne.Wang@emc.com)
[Purpose ]: Define Monorail SKU collection abstraction
*********************************************************
'''

import gevent

from lib.Device import CDevice
from idic.monorail.Sku import CSku

class CSkuCollection(CDevice):
    def __init__(self, obj_device, str_id):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        @param str_id: id of this poller
        @type str_id: string
        """

        # Initialize resource name, parents and URI
        self.resource_name = str_id
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        self.mon_data = {}
        self.list_sku_id = []
        # dict_names is a mapping from id to SKU name
        self.dict_names = {}
        # dict_skus is a mapping from id to SKU instance
        self.dict_skus = {}

    def update(self):
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))
        self.mon_data = self.rest_get(self.uri)

        # init sub resource
        self.list_sku_id = []
        for member in self.mon_data['json']:
            str_sku_id = member['id']
            str_sku_name = member['name']
            self.list_sku_id.append(str_sku_id)
            self.dict_names[str_sku_id] = str_sku_name
            self.__init_sku(str_sku_id)

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def __init_sku(self, sku_id):
        """
        Instantiate sub resource:
            SKU
        Make URI ready without sub resources' mon data
        """
        self.log('INFO', 'Initialize SKU {} (ID: {})...'.format(self.dict_names[sku_id], sku_id))
        self.dict_skus[sku_id] = CSku(self, sku_id)

    def get_skus(self):
        """
        @return: dict of sub resource in this format:
                key: SKU id in string
                value: SKU instances
            Instance's mon_data is ready
        """
        self.update()

        gevent.joinall([gevent.spawn(self.dict_skus[dict_data['id']].set_mon_data, dict_data)
                        for dict_data in self.mon_data['json']])

        return self.dict_skus

    def get_sku_id(self, node_type):
        """
        @node_type: the type of node
        @return: the sku id of this node, if fail to find
            corresponding ID, return an empty string
        """
        self.update()
        for str_sku_id in self.dict_names:
            if self.dict_names[str_sku_id] == node_type:
                return str_sku_id
        return ''

    def get_sku_via_id(self, sku_id):
        """
        @sku_id: the id of the specific sku
        @return: the detail of the specific sku
        """
        self.__init_sku(sku_id)
        obj_sku = self.dict_skus.get(sku_id, None)
        obj_sku.update()
        return obj_sku

    def get_sku_via_type(self, node_type):
        """
        @node_type: the type of node
        @return: the detail of the specific sku
        """
        self.log('INFO', 'Get SKU for node type: {} ...'.format(node_type))
        self.update()
        for str_sku_id in self.dict_names:
            if self.dict_names[str_sku_id] == node_type:
                self.log('INFO', 'SKU ID of node type: {} is {}'.format(node_type, str_sku_id))
                return self.get_sku_via_id(str_sku_id)
        return None

    def get_sku_nodes(self, sku_id):
        """
        @sku_id: the id of specific sku
        @return: the nodes info of the specific sku in dict
            key is node ID, value is node instance
        """
        self.__init_sku(sku_id)
        obj_sku = self.dict_skus.get(sku_id, None)
        return obj_sku.get_nodes()
