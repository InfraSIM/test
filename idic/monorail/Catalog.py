'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: Catalog.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail catalog abstraction
*********************************************************
'''

from lib.Device import CDevice


class CCatalog(CDevice):
    def __init__(self, obj_device, str_attr):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        @param str_attr: attribute of this catalog, could be:
            - id for catalog in catalogs
            - source for catalog in nodes
        @type str_attr: string
        """

        # Initialize resource name, parents and URI
        self.resource_name = str_attr
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)
        if self.mon_data["status"] != 200:
            raise Exception('[{}][{}]'.
                            format(self.mon_data["status"], self.uri))
        self.created_at = self.get_mon('createdAt')
        self.data = self.get_mon('data')
        self.id = self.get_mon('id')
        self.node = self.get_mon('node')
        self.source = self.get_mon('source')
        self.updated_at = self.get_mon('updatedAt')

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def set_mon_data(self, dict_data):
        """
        Update monorail data of catalog by directly assign instead of
        sending another REST API
        """
        self.log('INFO', 'Assigning catalog {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.created_at = dict_data.get('createdAt', None)
        self.data = dict_data.get('data', None)
        self.id = dict_data.get('id', None)
        self.node = dict_data.get('node', None)
        self.source = dict_data.get('source', None)
        self.updated_at = dict_data.get('updatedAt', None)

        self.log('INFO', 'Assigning catalog {} done'.format(self.str_sub_type))
