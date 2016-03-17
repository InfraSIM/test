'''
Copyright 2015 EMC Inc
This file is a part of puffer automation test framework
[Filename]: Node.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com)
[Purpose ]: Define Monorail node abstraction
'''

from lib.Device import CDevice
from idic.monorail.CatalogCollection import CCatalogCollection
from idic.monorail.PollerCollection import CPollerCollection
from idic.monorail.ObmCollection import CObmCollection
from idic.monorail.WorkflowCollection import CWorkflowCollection
from lib.Apps import is_valid_ip


class CNode(CDevice):
    def __init__(self, obj_device, str_id):
        """
        @param obj_device: Parent device that init this one
        @type obj_device: CDevice
        @param str_id: node ID
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

        self.obj_catalog_collection = None
        self.obj_poller_collection = None
        self.obj_obm_collection = None
        self.obj_workflow_collection = None
        self.mon_data = {}

    def update(self):
        """
        Update monorail data of self
        """
        self.log('INFO', 'Updating {} ...'.format(self.str_sub_type))

        # mon_data analysis
        self.mon_data = self.rest_get(self.uri)
        self.catalogs = self.get_mon('catalogs')
        self.created_at = self.get_mon('createdAt')
        self.id = self.get_mon('id')
        self.identifiers = self.get_mon('identifiers')
        self.name = self.get_mon('name')
        self.sku = self.get_mon('sku')
        self.type = self.get_mon('type')
        self.updated_at = self.get_mon('updatedAt')
        self.workflows = self.get_mon('workflows')
        self.relations = self.get_mon('relations')

        self.log('INFO', 'Updating {} done'.format(self.str_sub_type))

    def set_mon_data(self, dict_data):
        """
        Update monorail data of node by directly assign instead of
        sending another REST API
        """
        self.log('INFO', 'Assigning node {} ...'.format(self.str_sub_type))

        self.catalogs = dict_data.get('catalogs', None)
        self.created_at = dict_data.get('createdAt', None)
        self.id = dict_data.get('id', None)
        self.identifiers = dict_data.get('identifiers', None)
        self.name = dict_data.get('name', None)
        self.sku = dict_data.get('sku', None)
        self.type = dict_data.get('type', None)
        self.updated_at = dict_data.get('updatedAt', None)
        self.workflows = dict_data.get('workflows', None)
        self.relations = dict_data.get('relations', None)

        self.log('INFO', 'Assigning node {} done'.format(self.str_sub_type))

    def __init_catalogs(self):
        """
        Instantiate sub resource:
            catalog collection
        Make URI ready without sub resources' on data
        """
        self.log('INFO', 'Initialize node catalog collection ...')
        self.obj_catalog_collection = CCatalogCollection(self)
        self.log('INFO', 'Initialize node catalog collection done')

    def __init_pollers(self):
        """
        Instantiate sub resource:
            poller collection
        Make URI ready without sub resources' on data
        """
        self.log('INFO', 'Initialize node poller collection ...')
        self.obj_poller_collection = CPollerCollection(self)
        self.log('INFO', 'Initialize node poller collection done')

    def __init_obms(self):
        """
        Instantiate sub resource:
            obm collection
        Make URI ready without sub resources' on data
        """
        self.log('INFO', 'Initialize node obm collection ...')
        self.obj_obm_collection = CObmCollection(self)
        self.log('INFO', 'Initialize node obm collection done')

    def __init_workflows(self):
        """
        Instantiate downstream resource:
            workflow collection
        Make URI ready without downstream resources' on data
        """
        self.log('INFO', 'Initialize node workflow collection ...')
        self.obj_workflow_collection = CWorkflowCollection(self)
        self.log('INFO', 'Initialize node workflow collection done')

    def get_catalog(self):
        """
        Get full node catalog
        @return: a instance of full catalog collection
        """
        self.__init_catalogs()
        self.obj_catalog_collection.update()
        return self.obj_catalog_collection

    def get_catalog_from_source(self, str_source):
        self.__init_catalogs()
        return self.obj_catalog_collection.get_catalog_from_source(str_source)

    def get_pollers(self):
        self.__init_pollers()
        return self.obj_poller_collection.get_pollers()

    def get_poller_by_id(self, str_id):
        self.__init_pollers()
        return self.obj_poller_collection.get_poller_by_id(str_id)

    def get_poller_info_per_command(self, str_command):
        self.__init_pollers()
        return self.obj_poller_collection.get_poller_info_per_command(str_command)

    def delete(self):
        """
        Delete this node
        """
        self.log('INFO', 'Delete node {} ...'.format(self.resource_name))
        rsp = self.rest_delete(self.uri)
        if rsp.get('status', None) != 200:
            raise Exception('Delete node fail, http status: {}, response: {}'.
                            format(rsp.get('status', None), rsp.get('text', '')))
        else:
            self.log('INFO', 'Delete node {} done'.format(self.resource_name))

    def get_obm(self):
        self.__init_obms()
        return self.obj_obm_collection.get_obm()

    def get_obm_of_service(self, str_service):
        self.__init_obms()
        return self.obj_obm_collection.get_obm_of_service(str_service)

    def get_workflows(self):
        self.__init_workflows()
        return self.obj_workflow_collection.get_workflows()

    def get_workflow_by_id(self, str_id):
        self.__init_workflows()
        return self.obj_workflow_collection.get_workflow_by_id(str_id)

    def get_active_workflow(self):
        self.__init_workflows()
        self.obj_workflow_collection.get_active_workflow()

    def delete_active_workflow(self):
        self.__init_workflows()
        self.obj_workflow_collection.delete_active_workflow()

    def create_workflow(self, dict_payload):
        self.__init_workflows()
        self.obj_workflow_collection.create_workflow(dict_payload)

    def get_bmc_ip(self):
        """
        Get BMC IP of this node
        @return: str_bmc_ip, IP in string
        """
        try:
            obj_bmc_catalog = self.get_catalog_from_source('bmc')
        except Exception, e:
            raise Exception('Computer system {}  (ID: {}) fail to get catalog from source BMC:\n{}'.
                            format(self.name, self.id, e.args[0]))
        try:
            str_bmc_ip = obj_bmc_catalog.data['IP Address']
        except KeyError:
            raise Exception('Computer system {}  (ID: {}) catalog (source BMC) has no IP defined'.
                            format(self.name, self.id))
        if is_valid_ip(str_bmc_ip):
            if str_bmc_ip.startswith('172.'):
                self.log('INFO', 'Computer system {}  (ID: {}) BMC IP is valid: {}'.
                         format(self.name, self.id, str_bmc_ip))
            else:
                self.log('WARNING', 'Computer system {}  (ID: {}) BMC IP is: {}, not in 172 segment, '
                                    'please check'.format(self.name, self.id, str_bmc_ip))
            return str_bmc_ip
        else:
            raise Exception('Computer system {}  (ID: {}) BMC IP is invalid: {}'.
                            format(self.name, self.id, str_bmc_ip))

