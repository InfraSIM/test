'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: ObmCollection.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail OBM collection abstraction
*********************************************************
'''

from lib.Device import CDevice


class CObmCollection(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        # If this is obm for nodes, its resource name should be:
        #     obm
        # If this is obm managed by monorail, its resource name should be:
        #     obms/library
        self.obj_parent = obj_device
        if 'nodes' in self.obj_parent.uri.split('/'):
            self.resource_name = 'obm'
        else:
            self.resource_name = 'obms/library'

        CDevice.__init__(self, self.resource_name)
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        self.dict_obm = {}
        self.list_obm_service = []
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

        for obm in self.mon_data['json']:
            str_service = obm.get('service', None)
            if str_service:
                self.dict_obm[str_service] = obm
                self.list_obm_service.append(str_service)
            else:
                self.log('WARNING', 'No service definition for obm: {}'.
                         format(self.uri))

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def get_obm(self):
        """
        Get OBM data of API /nodes/{node_id}/obm or /obms/library. 
        @return: a list of obm in dict
        """
        self.update()
        return self.mon_data['json']

    def get_obm_of_service(self, str_service):
        """
        Get the OBM with target service
        @param str_service: service name, e.g. "amt-obm-service"
        @return: a dict of obm, e.g.
        {
            "config": {},
            "service": "amt-obm-service"
        }
        """
        self.update()
        return self.dict_obm[str_service]


