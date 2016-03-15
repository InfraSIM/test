'''
Copyright 2015 EMC Inc
This file is a part of puffer automation test framework
[Filename]: NodeCollection.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail node collection abstraction
'''

import gevent

from lib.Device import CDevice
from idic.monorail.Node import CNode


class CNodeCollection(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        self.resource_name = 'nodes'
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        # Pre-defined next level object
        self.dict_nodes = {}
        self.list_node_id = []
        
        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        Build sub resource:
            All nodes under this collection
        """
        self.log('INFO', 'Update {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)

        # init sub resource
        self.list_node_id = []
        for member in self.mon_data['json']:
            self.list_node_id.append(member['id'])
        self.log('INFO', 'Initialize nodes (total count: {0}) ...'.
                 format(len(self.list_node_id)))
        gevent.joinall([gevent.spawn(self.__init_node, node_id)
                        for node_id in self.list_node_id])
        self.log('INFO', 'Initialize nodes (total count: {0}) done'.
                 format(len(self.list_node_id)))

        self.log('INFO', 'Update {} done'.format(self.str_sub_type))

    def __init_node(self, str_node_id):
        """
        Instantiate sub resource:
            node
        Make URI ready without sub resources' mon data
        """
        str_id = str(str_node_id)
        self.log('INFO', 'Initialize node {}...'.format(str_id))
        self.dict_nodes[str_id] = CNode(self, str_id)

    def get_nodes(self, *node_type):
        """
        @param node_type: accept node type in string as input,
            several node type in use: 'compute' | 'enclosure'
        @return: dict of sub resource in this format:
                key: node id in string
                value: node instances
            Instance's mon_data is ready
        """
        self.update()
        gevent.joinall([gevent.spawn(self.dict_nodes[dict_data['id']].set_mon_data, dict_data)
                        for dict_data in self.mon_data['json']])
        # Filter node type according to input
        dict_filter = self.dict_nodes
        for str_id in dict_filter.keys():
            if dict_filter[str_id].type not in node_type:
                del(dict_filter[str_id])
        return dict_filter

    def get_node_count(self):
        """
        @return: Count of catalogs
        """
        self.update()
        return len(self.list_node_id)

    def get_node_by_id(self, str_id):
        """
        Get node by its ID
        @param str_id: ID to search
        @type str_id: string
        @return: The computer node instance with the target ID
        """
        self.__init_node(str_id)
        self.dict_nodes[str_id].update()
        return self.dict_nodes[str_id]

    def delete_node(self, str_id):
        """
        Delete node with target ID
        @param str_id: ID to delete
        @type str_id: string
        """
        if not self.dict_nodes.get(str_id, None):
            self.__init_node(str_id)
        self.dict_nodes[str_id].delete()

    def get_obm(self, str_id):
        self.__init_node(str_id)
        return self.dict_nodes[str_id].get_obm()



