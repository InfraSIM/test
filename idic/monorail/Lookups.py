'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: Lookup.py
[Author  ]: Yuki Wu(Yuki.Wu@emc.com)
[Purpose ]: Define Monorail Lookups abstraction
*********************************************************
'''

from lib.Device import CDevice
#from idic.monorail.CatalogCollection import CCatalogCollection
#from idic.monorail.PollerCollection import CPollerCollection
#from idic.monorail.ObmCollection import CObmCollection


class CLookups(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """
        # Initialize resource name, parents and URI
        self.resource_name = "lookups"

        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)
        self.log('INFO', 'URI {}'.format(self.uri))
        self.mon_data = {}
        self.look_up = {}

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)["json"]
        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def get_lookups(self):
        """
        Get the whole lookups list
        """
        self.update()
        return self

    def get_lookup_by_macOrIP(self,str_macOrIP):
        """
        Get the lookups list
        @str_macOrIP: mac address or IP address
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # mon_data analysis
        str_uri_lookup_macOrIP = '{}?q={}'.format(self.uri,  str_macOrIP) 
        self.look_up = self.rest_get(str_uri_lookup_macOrIP)["json"]
        return self.look_up