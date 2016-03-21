'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: PollerCollection.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail poller collection abstraction
*********************************************************
'''

import gevent
import json
from lib.Device import CDevice
from idic.monorail.Poller import CPoller


class CPollerCollection(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        self.resource_name = 'pollers'
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        # Pre-defined next level object
        self.dict_pollers = {}
        self.list_poller_id = []
        
        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        Build sub resource:
            All pollers under this collection
        """
        self.log('INFO', 'Update {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)

        # init sub resource
        self.list_poller_id = []
        for member in self.mon_data['json']:
            self.list_poller_id.append(member['id'])
        self.log('INFO', 'Initialize pollers (total count: {0}) ...'.
                 format(len(self.list_poller_id)))
        gevent.joinall([gevent.spawn(self.__init_poller, poller_id)
                        for poller_id in self.list_poller_id])
        self.log('INFO', 'Initialize pollers (total count: {0}) done'.
                 format(len(self.list_poller_id)))

        self.log('INFO', 'Update {} done'.format(self.str_sub_type))

    def __init_poller(self, poller_id):
        """
        Instantiate sub resource:
            poller
        Make URI ready without sub resources' mon data
        """
        str_id = str(poller_id)
        self.log('INFO', 'Initialize poller {}...'.format(str_id))
        self.dict_pollers[str_id] = CPoller(self, str_id)

    def get_pollers(self):
        """
        @return: dict of sub resource in this format:
                key: poller id in string
                value: poller instances
            Instance's mon_data is ready
        """
        self.update()

        gevent.joinall([gevent.spawn(self.dict_pollers[dict_data['id']].set_mon_data, dict_data)
                        for dict_data in self.mon_data['json']])

        return self.dict_pollers

    def get_poller_count(self):
        """
        @return: Count of pollers
        """
        self.update()
        return len(self.list_poller_id)

    def get_poller_by_id(self, str_id):
        """
        @param str_id: poller ID in string
        @type str_id: string
        @return: The poller instance with the target ID
        """
        self.__init_poller(str_id)
        obj_poller = self.dict_pollers.get(str_id, None)
        obj_poller.update()
        return obj_poller

    def get_poller_info_per_command(self, str_command):
        """
        This function return a poller dict with certain command.
        It can only be called by a node.
        @param str_command: poller command in string
        @type str_command: string
        @return: The poller dict with the target command in config
        """
        self.log('INFO', 'Get poller for command: {} ...'.format(str_command))
        self.update()
        for dict_poller in self.mon_data['json']:
            if dict_poller.get('config', {}).get('command', '') == str_command:
                str_poller_id = dict_poller.get('id', '')
                self.log('INFO', 'Get poller for command: {} done, poller ID: {}, poller info: {}'.
                         format(str_command, str_poller_id, json.dumps(dict_poller, indent=1)))
                return dict_poller
        self.log('WARNING', 'No poller for command: {}'.format(str_command))
        return {}

    def set_poller_interval(self, str_poller_id, int_interval):
        self.__init_poller(str_poller_id)
        self.dict_pollers[str_poller_id].set_poller_interval(int_interval)

    def create_poller(self, dict_payload):
        """
        Create a poller using the payload
        @param dict_payload: a dict with "pollInterval", "type", "node"
            and "config"-"command", e.g.
            {
                "config": {
                    "command": "sel"
                },
                "node": <id>,
                "pollInterval": 60000,
                "type": "ipmi"
            }
        """
        rsp = self.rest_post(self.uri, dict_payload)

        if rsp['status'] != 200:
            raise Exception('Fail to create poller:\n{}'.format(json.dumps(dict_payload, indent=1)))
        else:
            self.log('INFO', 'Create poller succeeds:\n{}'.format(json.dumps(dict_payload, indent=1)))

