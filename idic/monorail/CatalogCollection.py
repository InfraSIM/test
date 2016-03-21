'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: CatalogCollection.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail catalog collection abstraction
*********************************************************
'''

import gevent

from lib.Device import CDevice
from idic.monorail.Catalog import CCatalog


class CCatalogCollection(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        self.resource_name = 'catalogs'
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        # Pre-defined next level object
        self.dict_catalogs = {}
        self.list_catalog_id = []
        
        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        Build sub resource:
            All catalogs under this collection
        """
        self.log('INFO', 'Update {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)

        # init sub resource
        self.list_catalog_id = []
        for member in self.mon_data['json']:
            self.list_catalog_id.append(member['id'])
        self.log('INFO', 'Initialize catalogs (total count: {0}) ...'.
                 format(len(self.list_catalog_id)))
        gevent.joinall([gevent.spawn(self.__init_catalog, catalog_id)
                        for catalog_id in self.list_catalog_id])
        self.log('INFO', 'Initialize catalogs (total count: {0}) done'.
                 format(len(self.list_catalog_id)))

        self.log('INFO', 'Update {} done'.format(self.str_sub_type))

    def __init_catalog(self, catalog_id):
        """
        Instantiate sub resource:
            catalog
        Make URI ready without sub resources' mon data
        """
        str_id = str(catalog_id)
        self.log('INFO', 'Initialize catalog {}...'.format(str_id))
        self.dict_catalogs[str_id] = CCatalog(self, str_id)

    def get_catalogs(self):
        """
        @return: dict of sub resource in this format:
                key: catalog id in string
                value: catalog instances
            Instance's mon_data is ready
        """
        self.update()

        # gevent.joinall([gevent.spawn(catalog.update)
        #                 for catalog in self.dict_catalogs.values()])

        gevent.joinall([gevent.spawn(self.dict_catalogs[dict_data['id']].set_mon_data, dict_data)
                        for dict_data in self.mon_data['json']])

        return self.dict_catalogs

    def get_catalog_sources(self):
        """
        @return: A list of source each catalog data comes from
        """
        list_source = []
        self.update()
        gevent.joinall([gevent.spawn(catalog.update)
                        for catalog in self.dict_catalogs.values()])
        for instance in self.dict_catalogs.values():
            list_source.append(instance.source)
        return list_source

    def get_catalog_count(self):
        """
        @return: Count of catalogs
        """
        self.update()
        return len(self.list_catalog_id)

    def get_catalog_from_identity(self, str_identity):
        """
        If nodes get catalog from certain identity, it shall return
        a catalog instance
        @param str_identity: identity of a certain catalog for search
            for node, source name should be provided as identity
            for raw catalog, catalog id should be the identity
        @return: a instance of catalog from target source
        """
        self.log('INFO', 'Initialize node catalog from identity {}...'.
                 format(str_identity))
        obj_catalog = CCatalog(self, str_identity)
        obj_catalog.update()
        return obj_catalog


