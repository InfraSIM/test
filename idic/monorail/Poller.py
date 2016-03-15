'''
Copyright 2015 EMC Inc
This file is a part of puffer automation test framework
[Filename]: Poller.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail poller abstraction
'''

from lib.Device import CDevice


class CPoller(CDevice):
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

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating poller {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)
        if self.mon_data["status"] != 200:
            raise Exception('[{}][{}]'.
                            format(self.mon_data["status"], self.uri))
        self.node = self.get_mon('node')
        self.config = self.get_mon('config')
        self.created_at = self.get_mon('createdAt')
        self.failure_count = self.get_mon('failureCount')
        self.last_finished = self.get_mon('lastFinished')
        self.last_started = self.get_mon('lastStarted')
        self.lease_expires = self.get_mon('leaseExpires')
        self.lease_token = self.get_mon('leaseToken')
        self.next_scheduled = self.get_mon('nextScheduled')
        self.id = self.get_mon('id')
        self.paused = self.get_mon('paused')
        self.poll_interval = self.get_mon('pollInterval')
        self.type = self.get_mon('type')
        self.updated_at = self.get_mon('updatedAt')

        self.log('INFO', 'Updating poller {} done'.format(self.str_sub_type))

    def set_mon_data(self, dict_data):
        """
        Update monorail data of poller by directly assign instead of
        sending another REST API
        """
        self.log('INFO', 'Assigning poller {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.node = dict_data.get('node', None)
        self.config = dict_data.get('config', None)
        self.created_at = dict_data.get('createdAt', None)
        self.failure_count = dict_data.get('failureCount', None)
        self.last_finished = dict_data.get('lastFinished', None)
        self.last_started = dict_data.get('lastStarted', None)
        self.lease_expires = dict_data.get('leaseExpires', None)
        self.lease_token = dict_data.get('leaseToken', None)
        self.next_scheduled = dict_data.get('nextScheduled', None)
        self.id = dict_data.get('id', None)
        self.paused = dict_data.get('paused', None)
        self.poll_interval = dict_data.get('pollInterval', None)
        self.type = dict_data.get('type', None)
        self.updated_at = dict_data.get('updatedAt', None)

        self.log('INFO', 'Assigning poller {} done'.format(self.str_sub_type))

    def set_poller_interval(self, int_interval):
        """
        @param int_interval: interval to set, shall raise exception if
            operation fails
        """
        data = {'pollInterval': int_interval}
        rsp = self.rest_patch(self.uri, data)
        if rsp['status'] != 200:
            raise Exception('Set poller (ID: {}) interval to {} fail, HTTP status: {}'.
                            format(self.resource_name, int_interval, rsp['status']))
        else:
            self.log('INFO', 'Set poller (ID: {}) interval to {} succeeds')

    def pause(self):
        """
        Pause this poller, will raise exception if HTTP status is not 200
        """
        rsp = self.rest_patch('{}/pause'.format(self.uri), {})
        if self.type:
            str_poller_readable = 'type: {}'.format(self.type)
        else:
            str_poller_readable = 'command: {}'.format(self.config['command'])
        if rsp['status'] != 200:
            raise Exception('Fail to pause poller (ID: {}) ({})'.
                            format(self.id, str_poller_readable))
        else:
            self.log('INFO', 'Pause poller (ID: {}) ({}) succeeds'.
                     format(self.id, str_poller_readable))

    def resume(self):
        """
        Resume this poller, will raise exception if HTTP status is not 200
        """
        rsp = self.rest_patch('{}/resume'.format(self.uri), {})
        if self.type:
            str_poller_readable = 'type: {}'.format(self.type)
        else:
            str_poller_readable = 'command: {}'.format(self.config['command'])
        if rsp['status'] != 200:
            raise Exception('Fail to resume poller (ID: {}) ({})'.
                            format(self.id, str_poller_readable))
        else:
            self.log('INFO', 'Resume poller (ID: {}) ({}) succeeds'.
                     format(self.id, str_poller_readable))

    def delete(self):
        """
        Delete this poller, will raise exception if HTTP status is not 204
        """
        rsp = self.rest_delete(self.uri)
        if self.type:
            str_poller_readable = 'type: {}'.format(self.type)
        else:
            str_poller_readable = 'command: {}'.format(self.config['command'])
        print rsp
        if rsp['status'] != 204:
            raise Exception('Fail to delete poller (ID: {}) ({}), HTTP status: {}, expect: 204'.
                            format(self.id, str_poller_readable, rsp['status']))
        else:
            self.log('INFO', 'Delete poller (ID: {}) ({}) succeeds'.
                     format(self.id, str_poller_readable))
