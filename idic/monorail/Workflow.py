'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: Workflow.py
[Purpose ]: Define Monorail workflow abstraction
*********************************************************
'''


import re
from lib.Device import CDevice

p_hash = re.compile(r'[0-9a-f]{8}\-([0-9a-f]{4}\-){3}[0-9a-f]{12}')


class CWorkflow(CDevice):
    def __init__(self, obj_device, str_id):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        self.resource_name = str_id
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type

        # If str_id is 'active', this workflow shoud be a
        # downstream resource of Node
        if str_id.lower() == 'active':
            self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)
        # If str_id is a 24 width hash code, this workflow
        # should be a downstream resource of Monorail root
        elif p_hash.findall(str_id):
            str_root = '/'.join(self.obj_parent.uri.split('/', 5)[0:5])
            self.uri = '{}/workflows/{}'.format(str_root, str_id)
        # If str_id is 'library', which is specified by a static
        # library workflow definition, this workflow shall have no
        # upstream resource, but only maintain a static data.
        # It can't be udpated.
        elif str_id == 'library':
            self.uri = ''
        # Else, it's not valid
        else:
            raise Exception('Invalid workflow resource name: {}'.format(str_id))

        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating workflow {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)
        self.id = self.get_mon('id')
        self.status = self.get_mon('_status')
        self.cancelled = self.get_mon('cancelled')
        self.complete = self.get_mon('completeEventString')
        self.context = self.get_mon('context')
        self.createdAt = self.get_mon('createdAt')
        self.definition = self.get_mon('definition')
        self.failedStates = self.get_mon('failedStates')
        self.finishedStates = self.get_mon('finishedStates')
        self.finishedTasks = self.get_mon('finishedTasks')
        self.injectableName = self.get_mon('injectableName')
        self.instanceId = self.get_mon('instanceId')
        self.name = self.get_mon('name')
        self.node = self.get_mon('node')
        self.tasks = self.get_mon('tasks')
        self.updatedAt = self.get_mon('updatedAt')
        self.logcontext = self.get_mon('logContext')
        self.pendingtasks = self.get_mon('pendingTasks')
        self.ready = self.get_mon('ready')
        self.servicegraph = self.get_mon('serviceGraph')
        self.friendlyname = self.get_mon('friendlyName')

        self.log('INFO', 'Updating workflow {} done'.format(self.str_sub_type))

    def set_mon_data(self, dict_data):
        """
        Update monorail data of catalog by directly assign instead of
        sending another REST API
        """
        self.log('INFO', 'Assigning workflow {} ...'.format(self.str_sub_type))

        self.id = dict_data.get('id', None)
        self.status = dict_data.get('_status', None)
        self.cancelled = dict_data.get('cancelled', None)
        self.complete = dict_data.get('completeEventString', None)
        self.context = dict_data.get('context', None)
        self.createdAt = dict_data.get('createdAt', None)
        self.definition = dict_data.get('definition', None)
        self.failedStates = dict_data.get('failedStates', None)
        self.finishedStates = dict_data.get('finishedStates', None)
        self.finishedTasks = dict_data.get('finishedTasks', None)
        self.injectableName = dict_data.get('injectableName', None)
        self.instanceId = dict_data.get('instanceId', None)
        self.name = dict_data.get('name', None)
        self.node = dict_data.get('node', None)
        self.tasks = dict_data.get('tasks', None)
        self.updatedAt = dict_data.get('updatedAt', None)
        self.logcontext = dict_data.get('logContext', None)
        self.pendingtasks = dict_data.get('pendingTasks', None)
        self.ready = dict_data.get('ready', None)
        self.servicegraph = dict_data.get('serviceGraph', None)
        self.friendlyname = dict_data.get('friendlyName', None)

        self.log('INFO', 'Assigning workflow {} done'.format(self.str_sub_type))

    def delete(self):
        """
        Delete this active workflow for node
        Limited to active workflow on a certain node only
        """

        # Validate this is active workflow on a certain node
        try:
            list_element = self.uri.rsplit('/', 4)
            if list_element[1] != 'nodes':
                raise Exception('Try to delete a workflow not mounted on node, '
                                'this is not supported by Monorail now')
            if list_element[-1] != 'active':
                raise Exception('Try to delete a random workflow, but only '
                                'active workflow on a node can be deleted')
        except Exception:
            raise Exception('Invalid workflow URI: {}'.format(self.uri))

        self.log('INFO', 'Delete active workflow on node (ID: {})...'.format(list_element[2]))
        rsp = self.rest_delete(self.uri)
        if rsp.get('status', None) != 204 and rsp.get('status', None) != 200:
            raise Exception('Delete node (ID: {}) active workflows fail, http status: {}, response: {}'.
                            format(list_element[2], rsp.get('status', None), rsp.get('text', '')))
        else:
            self.log('INFO', 'Delete node (ID: {}) active workflow done'.
                     format(list_element[2]))

    def cancel(self):
        """
        Cancel this workflow if it's active
        """
        payload = {
            "command": "cancel",
            "options": {}
        }
        self.log('INFO', 'Cancel workflow (instance ID: {})...'.format(self.instanceId))
        rsp = self.rest_put(self.uri+"/action", payload)

        if rsp.get('status', None) != 202:
            raise Exception('Cancel workflow (instance ID: {}) fail, http status: {}, response: {}'.
                            format(self.instanceId, rsp.get('status', None), rsp.get('text', '')))
        else:
            self.log('INFO', 'Cancel workflow (instance ID: {}) done'.
                     format(self.instanceId))

