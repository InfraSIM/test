'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from threading import Lock, Event, Thread
import sys
import os
import xml.etree.ElementTree as ET
from Logger import CLogger

# constant
XMLNODE_ENCLOSURE = 'enclosure' 
DEFAULT_TEST_PLAN = 'full_test'

class CConfigManager(CLogger):
    
    def __init__(self, str_config_file):
        CLogger.__init__(self)
        self.str_config_file = str_config_file
        self.lock_update_file = Lock()
        self.event_quit = Event()
        self.event_quit.clear()
        self.str_source_folder = ''
        self.lst_enclosure = []
        self.lst_apc = []
        self.dict_runtime = {}
        self.dict_system_type = {}
        self.dict_branch_name_platform = {}
        self.dict_email = {}
        self.et_root = None
        if self.refresh() != 0:
            self.log('ERROR', 'Failed to parse config file')
            sys.exit()
    
    def refresh(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is to refresh the configuration by
                    re-loading information from the config file. It will
                    try to read from the back up file if the config file
                    gets destroyed
        [Input   ]:
        [Output  ]: 
        [History ]:     
        ************************************************
        '''
        self.lock_update_file.acquire()
        
        # Read the configuration from the original config file
        try:
            self.et_root = ET.parse(self.str_config_file)
        except:
            self.et_root = None
        # if the target config file is destroyed, try read from the backup file
        if self.et_root is None:
            try:
                self.et_root = ET.parse(self.str_config_file + '.temp')
            except:
                self.et_root = None
                self.lock_update_file.release()
                return -1
        # quit the system if both are invalid
            if self.et_root is None:
                self.lock_update_file.release()
                return -1
        # re-store the config file
            f_read = open(self.str_config_file+'.temp', 'r')
            f_write = open(self.str_config_file, 'wb')
            f_write.write(f_read.read())
            f_write.close()
            f_read.close()
        self.lock_update_file.release()
        return 0
    
    def parse_configuration(self):
        """
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is to cache all configurations in
                    a parsed format
        [Input   ]:
        [Output  ]: 
        [History ]:     
        ************************************************
        """
        self.log('INFO', 'Start parsing configuration')
        self._parse_default_test_plan()
        self._parse_branch_config()
        self.log('INFO', 'end parsing configuration')
        
    def _parse_default_test_plan(self):
        global DEFAULT_TEST_PLAN
        xmlnode_default_test_plan = self.et_root.find('default_test_plan')
        if xmlnode_default_test_plan is None:
            return
        if xmlnode_default_test_plan.text is None:
            return
        
        DEFAULT_TEST_PLAN = xmlnode_default_test_plan.text
    
    def _parse_branch_config(self):
        self.log('INFO', 'Start parsing code branch configuration')
        list_xmlnode_code_branch = self.et_root.findall('code_branch')
        for each_xmlnode_code_branch in list_xmlnode_code_branch:
            obj_branch = CCodeBranch(each_xmlnode_code_branch)
            if not obj_branch.is_valid():
                self.log('WARNING', 'Invalid code branch node found')
                continue
            if self.dict_branch_name_platform.has_key(obj_branch.str_name):
                dict_branch_platform_value = self.dict_branch_name_platform[obj_branch.str_name]
                if dict_branch_platform_value.has_key(obj_branch.str_platform):
                    self.log('WARNING', 'Found duplicate branch(name:%s, platform:%s)' % \
                                     (obj_branch.str_name, obj_branch.str_platform))
                    continue
                dict_branch_platform_value[obj_branch.str_platform] = obj_branch
            else:
                self.dict_branch_name_platform[obj_branch.str_name] = {}
                self.dict_branch_name_platform[obj_branch.str_name][obj_branch.str_platform] = obj_branch
        self.log('INFO', 'end parsing code branch configuration')

    def get_source_folder(self):
        str_source_folder = None
        try:
            str_source_folder = self.et_root.find('source_folder').text.lower()
        except:
            return str_source_folder
        import os.path
        if os.path.isdir(str_source_folder):
            return str_source_folder
        return ''
    
    def save_config(self):
        pass
    
    def tm_nodes_for_platform(self, platform):
        list_tm_nodes_for_platform = []
        list_all_xmlnode_tm = self.et_root.findall('test_manager')
        for each_xmlnode_tm in list_all_xmlnode_tm:
            if each_xmlnode_tm.find('platform').text.lower() == platform.lower():
                list_tm_nodes_for_platform.append(each_xmlnode_tm)
        return list_tm_nodes_for_platform
    
    def tracked_platform_types(self):
        list_tracked_platform_types = []
        list_xmlnode_enclosure = self.et_root.findall(XMLNODE_ENCLOSURE)
        if list_xmlnode_enclosure != None:
            for each_xmlnode_enclosure in list_xmlnode_enclosure:
                str_platform_type = each_xmlnode_enclosure.find('platform').text.lower()
                if str_platform_type != None and list_tracked_platform_types.count(str_platform_type) == 0:
                    list_tracked_platform_types.append(str_platform_type)
        return list_tracked_platform_types
    
    def get_test_plan(self, str_platform, str_branch = 'main'):
        """
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Puffer will assign test plans based on platform types
                    and branch name. This function will get the test plan
                    based on a given platform type and a given branch name
        [Input   ]:
        [Output  ]: 
        [History ]:     
        ************************************************
        """
        str_test_plan = DEFAULT_TEST_PLAN
        if not self.dict_branch_name_platform.has_key(str_branch):
            str_branch = 'main'
            dict_branch_platform_value = self.dict_branch_name_platform['main']
        else:
            dict_branch_platform_value = self.dict_branch_name_platform[str_branch]
        
        if not dict_branch_platform_value.has_key(str_platform):
            self.log('ERROR', 'Branch configuration not found(name:%s, platform:%s)' % (str_branch, str_platform))
        else:
            obj_branch = dict_branch_platform_value[str_platform]
            str_test_plan = obj_branch.str_test_plan
        return str_test_plan
        
    def get_enclosure_nodes(self):
        return get_sub_nodes(self.et_root, 'enclosure')
    
    def get_tftp_node(self):
        try:
            obj_tftp_node = get_sub_nodes(self.et_root, 'tftp_server')[0]
        except:
            self.log('WARNING', 'No TFTP server information is available')
            return None
        return obj_tftp_node
    
    def get_apc_nodes(self):
        return get_sub_nodes(self.et_root, 'apc')
    
    def get_smpt_server_node(self):
        try:
            obj_smpt_node = get_sub_nodes(self.et_root, 'smtp_config')[0]
        except:
            self.log('WARNING', 'No smpt server node')
            return None
        return obj_smpt_node
    
    def get_puffer_root(self):
        try:
            obj_puffer_root_node = get_sub_nodes(self.et_root, 'puffer_root')[0]
        except:
            self.log('WARNING', 'No puffer root information in conf.xml')
            return None
        return obj_puffer_root_node.text

    def get_testrail(self):
        """
        @return: a dict that has below attribute:
        {
            'testrail_root': '',
            'username': '',
            'password': ''
        }
        """
        try:
            obj_testrail_node = get_sub_nodes(self.et_root, 'testrail_config')[0]
        except:
            self.log('WARNING', 'No testrail information in conf.xml')
            return {}

        dict_testrail = {}
        try:
            dict_testrail['testrail_root'] = obj_testrail_node.find('root').text
        except:
            self.log('WARNING', 'Testrail root address is not defined in conf.xml')
        try:
            dict_testrail['username'] = obj_testrail_node.find('username').text
        except:
            self.log('WARNING', 'Testrail user name is not defined in conf.xml')
        try:
            dict_testrail['password'] = obj_testrail_node.find('password').text
        except:
            self.log('WARNING', 'Testrail password is not defined in conf.xml')

        return dict_testrail
            
        
def get_sub_nodes(et_father_node, str_subnode_name):
    list_sub_nodes = et_father_node.findall(str_subnode_name)
    if list_sub_nodes == None:
        return []
    else:
        return list_sub_nodes
    
class CCodeBranch():
    
    def __init__(self, obj_xmlnode_code_branch):
        self.obj_xmlnode = obj_xmlnode_code_branch
        self.str_name = ''
        self.str_platform = ''
        self.int_major_version = -1
        self.int_mid_version = -1
        self.list_product = []
        self.str_test_plan = ''
        self.b_valid = True
        self.parse_xmlnode()
    
    def parse_xmlnode(self):
        try:
            self.str_name = self.obj_xmlnode.find('name').text.lower()
            self.str_platform = self.obj_xmlnode.find('platform').text.lower()
            self.str_test_plan = self.obj_xmlnode.find('test_plan').text
            if self.str_test_plan is None:
                self.str_test_plan = DEFAULT_TEST_PLAN
            self.str_test_plan = self.str_test_plan.lower()
        except:
            self.b_valid = False
            
        try:
            str_major_version = self.obj_xmlnode.find('major_version').text.lower()
            if str_major_version.isdigit():
                self.int_major_version = int(str_major_version, 10)
            str_mid_version  = self.obj_xmlnode.find('mid_version').text.lower()
            if str_mid_version.isdigit():
                self.int_mid_version = int(str_mid_version, 10)
            str_product = self.obj_xmlnode.find('product').text.lower()
            self.list_product = str_product.split(',')
        except:
            pass
        
    def is_valid(self):
        return self.b_valid