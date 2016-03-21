'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: Sku.py
[Author  ]: Payne Wang(Payne.Wang@emc.com)
[Purpose ]: Define Monorail SKU abstraction
*********************************************************
'''

from lib.Device import CDevice
from idic.monorail.NodeCollection import CNodeCollection

class CSku(CDevice):
    def __init__(self, obj_device, str_id):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        @param str_id: id of this SKU
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
        self.nodes = {}

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating SKU {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)
        if self.mon_data["status"] != 200:
            raise Exception('[{}][{}]'.
                            format(self.mon_data["status"], self.uri))
        self.created_at = self.get_mon('createdAt')
        self.id = self.get_mon('id')
        self.name = self.get_mon('name')
        self.rules = self.get_mon('rules')
        self.updated_at = self.get_mon('updatedAt')

        self.log('INFO', 'Updating SKU {} done'.format(self.str_sub_type))

    def set_mon_data(self, dict_data):
        """
        Update monorail data of SKU by directly assign instead of
        sending another REST API
        """
        self.log('INFO', 'Assigning SKU {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.created_at = dict_data.get('createdAt', None)
        self.id = dict_data.get('id', None)
        self.name = dict_data.get('name', None)
        self.rules = dict_data.get('rules', None)
        self.updated_at = dict_data.get('updatedAt', None)

        self.log('INFO', 'Assigning SKU {} done'.format(self.str_sub_type))

    def get_nodes(self):
        """
        Get all nodes of this SKU
        @return: a dict of nodes instances, with node ID as key, node instance
            as value.
        """
        self.nodes = CNodeCollection(self)
        self.nodes.update()
        return self.nodes.dict_nodes
