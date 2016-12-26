'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: WorkflowCollection.py
[Purpose ]: Define Monorail workflow collection abstraction
*********************************************************
'''

import gevent
import json
from urllib2 import HTTPError
from lib.Device import CDevice
from idic.monorail.Workflow import CWorkflow


class CWorkflowCollection(CDevice):
    def __init__(self, obj_device):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        """

        # Initialize resource name, parents and URI
        self.resource_name = "workflows"
        CDevice.__init__(self, self.resource_name)
        self.obj_parent = obj_device
        self.set_logger(self.obj_parent.obj_logger)
        self.set_rest_agent(self.obj_parent.obj_rest_agent)
        self.str_device_type = self.obj_parent.str_device_type
        self.uri = '{}/{}'.format(self.obj_parent.uri, self.resource_name)

        # Pre-defined downstream resource
        self.dict_workflows = {}
        self.list_workflow_id = []

        self.mon_data = {}

    def update(self, active=None):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # mon_data analysis
        session_uri = ""
        if active is None:
            session_uri = self.uri
        elif active is True:
            session_uri = self.uri+"?active=true"
        elif active is False:
            session_uri = self.uri+"?active=false"
        self.mon_data = self.rest_get(session_uri)

        # init downstream resource
        self.list_workflow_id = []
        self.dict_workflows = {}
        for member in self.mon_data['json']:
            self.list_workflow_id.append(member['instanceId'])
        self.log('INFO', 'Initialize workflows (total count: {0}) ...'.
                 format(len(self.list_workflow_id)))
        gevent.joinall([gevent.spawn(self.__init_workflow, workflow_id)
                        for workflow_id in self.list_workflow_id])
        self.log('INFO', 'Initialize workflows (total count: {0}) done'.
                 format(len(self.list_workflow_id)))

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def __init_workflow(self, workflow_id):
        """
        Instantiate downstream resource:
            workflow
        Make URI ready without downstream resources' mon data
        """
        str_id = str(workflow_id)
        self.log('INFO', 'Initialize workflow {}...'.format(str_id))
        self.dict_workflows[str_id] = CWorkflow(self, str_id)

    def get_workflows(self, active=None):
        """
        @return: dict of downstream resource in this format:
                key: workflow id in string
                value: workflow instances
            Instance's mon_data is ready
        """
        self.update(active=active)
        # print self.dict_workflows
        # print self.mon_data['json']

        gevent.joinall([gevent.spawn(self.dict_workflows[dict_data['instanceId']].set_mon_data, dict_data)
                        for dict_data in self.mon_data['json']])

        return self.dict_workflows

    def get_workflow_by_id(self, str_id):
        """
        @param str_id: workflow ID in string
        @type str_id: string
        @return: The workflow instance with the target ID
        """
        self.__init_workflow(str_id)
        obj_workflow = self.dict_workflows.get(str_id, None)
        obj_workflow.update()
        return obj_workflow

    def get_active_workflow(self):
        """
        Get current active workflow
        @return: CWorkflow instance with resource name active
        """
        obj_workflow = CWorkflow(self, 'active')
        obj_workflow.update()
        return obj_workflow

    def delete_active_workflow(self):
        """
        Delete current active workflow
        """
        obj_workflow = CWorkflow(self, 'active')
        obj_workflow.delete()

    def create_workflow(self, dict_payload):
        """
        Create workflow for node
        @param dict_payload: payload to post for creating a workflow
        @return: CWorkflow instance
        """
        str_query = '&'.join('{}={}'.format(str_key, str_value)
                             for str_key, str_value in dict_payload.items())

        rsp = self.rest_post('{}?{}'.format(self.uri, str_query), data={})
        if rsp['status'] != 201:
            raise HTTPError(self.uri, rsp['status'],
                            "Fail to POST {} with payload:\n{}".
                            format(self.uri, json.dumps(dict_payload, indent=4)),
                            None, None)
        dict_workflow = rsp['json']
        str_workflow_id = dict_workflow['id']
        self.__init_workflow(str_workflow_id)
        self.dict_workflows[str_workflow_id].set_mon_data(dict_workflow)
        return self.dict_workflows[str_workflow_id]

    def post_workflow(self, query="", payload={}):
        """
        POST a workflow with specific query
        @param query: e.g. "name=Graph.InstallCentOS"
        """
        session_uri = "{}?{}".format(self.uri, query)
        rsp = self.rest_post(uri=session_uri, data=payload)
        if rsp["status"] != 201:
            raise HTTPError(self.uri, rsp['status'],
                            "Fail to POST {} with payload:\n{}".
                            format(self.uri, json.dumps(payload, indent=4)),
                            None, None)
        return rsp

