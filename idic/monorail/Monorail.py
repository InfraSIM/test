'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
This file is a part of puffer automation test framework
[Filename]: Monorail.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail abstraction
*********************************************************
'''

import traceback

from lib.restapi import APIClient
from lib.SSH import CSSH
from lib.Device import CDevice
from idic.monorail.CatalogCollection import CCatalogCollection
from idic.monorail.NodeCollection import CNodeCollection
from idic.monorail.PollerCollection import CPollerCollection
from idic.monorail.ObmCollection import CObmCollection
from idic.monorail.Lookups import CLookups
from idic.monorail.WorkflowCollection import CWorkflowCollection
from idic.monorail.Workflow import CWorkflow
from idic.monorail.SkuCollection import CSkuCollection
from urllib2 import HTTPError


class CMonorail(CDevice):
    def __init__(self, dict_hwimo):
        '''
        Init Monorail instance
        :param dict_hwimo: a dict includes HWIMO information, e.g.
        {
            "ip": "192.168.128.1"
            "platform": "RackHD",
            "monorail_rest_rev": "1.1",
            "monorail_rest_protocol": "http",
            "monorail_rest_port": 8080,
            "username": "",
            "password": ""
        }
        '''

        CDevice.__init__(self, 'Monorail', None, None)

        try:
            self.str_device_type = 'monorail'
            self.str_sub_type = 'Root'
            # Monorail IP
            self.ip = dict_hwimo['ip']
            self.username = dict_hwimo['username']
            self.password = dict_hwimo['password']
            self.rest_username = dict_hwimo['rest_username']
            self.rest_password = dict_hwimo['rest_password']

            # Monorail REST info
            self.str_mon_rev = dict_hwimo['rest_rev']
            self.str_mon_protocol = dict_hwimo['rest_protocol']
            self.str_mon_port =dict_hwimo['rest_port']
            self.uri = '{0}://{1}:{2}/api/{3}'.format(self.str_mon_protocol,
                                                      self.ip,
                                                      self.str_mon_port,
                                                      self.str_mon_rev)
        except Exception:
            self.log('ERROR', 'Fail to build {}\n{}'\
                     .format(self.str_sub_type, traceback.format_exc()))

        self.obj_rest_agent = APIClient()
        self.set_rest_agent(self.obj_rest_agent)
        self.set_rackhd_rest_auth()
        self.obj_ssh_agent = CSSH(self.ip, self.username, self.password)

        self.b_valid = True

        # Pre-defined next level object
        self.catalogs = None
        self.config = None
        self.files = None
        self.obj_lookups = None
        self.nodes = None
        self.obms = None
        self.pollers = None
        self.profiles = None
        self.schemas = None
        self.skus = None
        self.tasks = None
        self.templates = None
        self.versions = None
        self.workflowtasks = None
        self.workflows = None
        self.workflow_library = None
        self.mon_data = {}

    def is_valid(self):
        """
        Check if resource is successfully built
        """
        return self.b_valid

    def update(self):
        """
        Update mon data of self
        Init sub resource:
            catalogs
            config
            files
            obj_lookups
            nodes
            obms
            pollers
            profiles
            schemas
            skus
            tasks
            templates
            versions
            workflowtasks
            workflows
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # init sub resource
        self.__init_catalogs()
        self.__init_nodes()

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def __init_catalogs(self):
        """
        Instantiate downstream resource:
            catalog collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize catalog collection ...')
        self.catalogs = CCatalogCollection(self)
        self.log('INFO', 'Initialize catalog collection done')

    def __init_config(self):
        pass

    def __init_files(self):
        pass

    def __init_nodes(self):
        """
        Instantiate downstream resource:
            node collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize node collection ...')
        self.nodes = CNodeCollection(self)
        self.log('INFO', 'Initialize node collection done')

    def __init_obms(self):
        """
        Instantiate downstream resource:
            obm collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize obm collection ...')
        self.obms = CObmCollection(self)
        self.log('INFO', 'Initialize obm collection done')

    def __init_pollers(self):
        """
        Instantiate downstream resource:
            poller collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize poller collection ...')
        self.pollers = CPollerCollection(self)
        self.log('INFO', 'Initialize poller collection done')

    def __init_lookups(self):
        """
        Instantiate downstream resource:
            poller collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize poller collection ...')
        self.obj_lookups = CLookups(self)
        self.log('INFO', 'Initialize poller collection done')


    def __init_profiles(self):
        pass

    def __init_schemas(self):
        pass

    def __init_skus(self):
        self.log('INFO', 'Initialize SKUS ...')
        self.skus = CSkuCollection(self, "skus")
        self.log('INFO', 'Initialize SKUS done')

    def __init_tasks(self):
        pass

    def __init_templates(self):
        pass

    def __init_versions(self):
        pass

    def __init_workflowtasks(self):
        pass

    def __init_workflows(self):
        """
        Instantiate downstream resource:
            workflow collection
        Make URI ready without downstream resources' mon data
        """
        self.log('INFO', 'Initialize workflow collection ...')
        self.workflows = CWorkflowCollection(self)
        self.log('INFO', 'Initialize workflow collection done')

    def get_catalogs(self):
        self.__init_catalogs()
        return self.catalogs.get_catalogs()

    def get_catalog_sources(self):
        self.__init_catalogs()
        return self.catalogs.get_catalog_sources()

    def get_catalog_count(self):
        self.__init_catalogs()
        return self.catalogs.get_catalog_count()

    def get_catalog_from_identity(self, str_identity):
        self.__init_catalogs()
        return self.catalogs.get_catalog_from_identity(str_identity)

    def get_nodes(self, *node_type):
        self.__init_nodes()
        return self.nodes.get_nodes(*node_type)

    def get_nodes_collection(self):
        # return the mon_data of NodeCollection.
        # Please check the node type (compute or enclosure) in the cases.
        self.__init_nodes()
        self.nodes.update()
        return self.nodes

    def get_node_count(self):
        self.__init_nodes()
        return self.nodes.get_node_count()

    def get_node_by_id(self, str_id):
        self.__init_nodes()
        return self.nodes.get_node_by_id(str_id)

    def delete_node(self, str_id):
        self.__init_nodes()
        self.nodes.delete_node(str_id)

    def get_pollers(self):
        self.__init_pollers()
        return self.pollers.get_pollers()

    def get_poller_by_id(self, str_id):
        self.__init_pollers()
        return self.pollers.get_poller_by_id(str_id)

    def get_obm(self):
        self.__init_obms()
        return self.obms.get_obm()

    def get_obm_by_id(self, node_id):
        self.__init_nodes()
        return self.nodes.get_obm(node_id)

    def get_obm_of_service(self, str_service):
        self.__init_obms()
        return self.obms.get_obm_of_service(str_service)

    def put_node_ipmi_obm(self, node_id, host, username, password):
        payload = {
            "service": "ipmi-obm-service",
            "nodeId": node_id,
            "config": {
                "host": host,
                "user": username,
                "password": password
            }
        }

        self.__init_obms()
        return self.obms.put_node_obm(payload)

    def get_lookups(self):
        self.__init_lookups()
        return self.obj_lookups.get_lookups()

    def get_skus(self):
        self.__init_skus()
        return self.skus.get_skus()

    def get_skus_collection(self):
        self.__init_skus()
        self.skus.update()
        return self.skus

    def get_lookup_by_macOrIP(self, str_mac_or_IP):
        self.__init_lookups()
        return self.obj_lookups.get_lookup_by_macOrIP(str_mac_or_IP)

    def verify_ipmi_obm_service(self):
        """
        Verify south bound has ipmi obm service working, all
        expected attributes are there, or an exception shall be raised.
        """
        dict_ipmi_obm = self.get_obm_of_service('ipmi-obm-service')
        list_lost_attribute = []
        if not dict_ipmi_obm.has_key('service'):
            list_lost_attribute.append('service')
        if not dict_ipmi_obm.has_key('config'):
            list_lost_attribute.append('config')
        if not dict_ipmi_obm.get('config', {}).has_key('host'):
            list_lost_attribute.append('config:host')
        if not dict_ipmi_obm.get('config', {}).has_key('user'):
            list_lost_attribute.append('config:user')
        if not dict_ipmi_obm.get('config', {}).has_key('password'):
            list_lost_attribute.append('config:password')
        # Summarize
        if list_lost_attribute:
            raise Exception('ipmi-obm-service is not valid, attribute lost: {}'.
                            format(str(list_lost_attribute)))
        else:
            return

    def set_poller_interval(self, str_poller_id, int_interval):
        self.__init_pollers()
        self.pollers.set_poller_interval(str_poller_id, int_interval)

    def create_poller(self, dict_payload):
        self.__init_pollers()
        self.pollers.create_poller(dict_payload)

    def get_workflows(self):
        self.__init_workflows()
        return self.workflows.get_workflows()

    def get_workflow_by_id(self, str_id):
        self.__init_workflows()
        return self.workflows.get_workflow_by_id(str_id)

    def get_workflow_library(self):
        """
        Get a list of workflow objects.
        These workflows are defined in library and possble to run
        :return: a list of workflow objects with mon_data ready
        """
        mon_data_workflow_library = self.rest_get('{}/workflows/library'.format(self.uri))
        if mon_data_workflow_library['status'] != 200:
            raise HTTPError(self.uri, self.mon_data['status'],
                            "Fail to get response from '{}/workflows/library'".format(self.uri),
                            None, None)
        list_workflows = []
        for dict_workflow in mon_data_workflow_library['json']:
            obj_workflow = CWorkflow(self, 'library')
            obj_workflow.set_mon_data(dict_workflow)
            list_workflows.append(obj_workflow)

        return list_workflows

    def get_config(self):
        """
        Get monorail config of the API /config
        @return: a dict of monorail config, got from API response
        """
        rsp = self.rest_get('{}/config'.format(self.uri))
        if rsp['status'] != 200:
            raise HTTPError(self.uri, rsp['status'], "Fail to get response from '{}'".
                            format(self.uri), None, None)
        else:
            return rsp['json']

    def get_revision(self):
        pass

    def set_rackhd_rest_auth(self):
        """
        This routine will set token for RackHD REST api handler.
        """
        str_token = self.get_rackhd_rest_token()
        if str_token:
            self.obj_rest_agent.http_header['Authorization'] = "JWT "+str_token
        else:
            raise Exception('Fail to set RackHD API authentication token')

    def get_rackhd_rest_token(self):
        """
        This routine will login RackHD to get a token.
        """

	login_url = "{0}://{1}:{2}/login".format(self.str_mon_protocol,
                                                 self.ip,
                                                 self.str_mon_port)
        login_payload = {"username": self.rest_username, "password": self.rest_password}

        try:
            self.obj_rest_agent.disable_log()
            login_resp = self.obj_rest_agent.restful(str(login_url), 'post', rest_payload=login_payload)
        finally:
            self.obj_rest_agent.enable_log()

        firstlogin_payload = {"username": self.rest_username, "role":"Administrator","password": self.rest_password}
        register_url = "{0}://{1}:{2}/api/{3}/users".format(self.str_mon_protocol,self.ip,self.str_mon_port,self.str_mon_rev )
       
	if login_resp["status"] != 200:
	    self.obj_rest_agent.disable_log()
            self.log('INFO', 'Rigester a new account')
            register_resp = self.obj_rest_agent.restful(str(register_url), 'post',rest_payload=firstlogin_payload)	
            if register_resp["status"] != 201:
                self.log('WARNING', 'Fail to register to rackhd')
            login_resp = self.obj_rest_agent.restful(str(login_url), 'post', rest_payload=login_payload)

        if login_resp["status"] != 200:
            self.log('WARNING', 'Fail to get OnRack authentication token')
        else:
            token = login_resp['json']['token']
        return str(token)

