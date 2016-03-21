'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: JSONRPCServer.py
[Author  ]: eric.wang5@emc.com
[Purpose ]: The JSONRPCServer provides interface for the 
            communication with Spectrum for other clients.  
[Contains]: 
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        eric.wang5@emc.com    05/12/2014       First edition
********************************************************************
'''

import os
import xml.etree.ElementTree as ET
import time
from Logger import CLogger
from SocketServer import ThreadingMixIn
from threading import *
import xmlrpclib


TASK_FILE_BASE_PATH = 'task'
TASK_FILE_ARCHIVED_PATH = 'archived'
LOG_FILE_BASE_PATH = 'log'
DEBUG_MODE = False
BASE_PATH = ''

if DEBUG_MODE is True:
    BASE_PATH = '..'
else:
    BASE_PATH = '.'

class CJSONRPCFunc(CLogger):
    '''
    ************************************************************************************************************
    [Type    ]: Class
    [Name    ]: CJSONRPCFunc
    [Author  ]: Eric Wang
    [Function]: This class provides all of the functions that can be called be Spectrum
    [Input   ]: 
    [Output  ]: 
    
    [History ]:
    ************************************************************************************************************
      VERSION        EDITOR          DATE             COMMENT
    ************************************************************************************************************
      R00            Eric Wang      05/12/2014       Initial version
    ************************************************************************************************************
    '''
    def __init__(self, obj_logger = None):
        CLogger.__init__(self)
        self.set_logger(obj_logger)
        result, info = self._parse_task_file('T000000', 'abc')
        self.dict_result = info
    
    def _parse_task_file(self, str_task_id, str_platform):
        self.log('INFO', 'PARSE TASK FILE')
        dict_task_info = {}
        str_task_file = os.path.join(BASE_PATH, TASK_FILE_BASE_PATH, str_task_id + '_' + str_platform + '.xml')
        str_archived_task_file = os.path.join(BASE_PATH, TASK_FILE_BASE_PATH, TASK_FILE_ARCHIVED_PATH, str_task_id + '_' + str_platform + '.xml')
        if not os.path.isfile(str_task_file):
            if not os.path.isfile(str_archived_task_file):
                self.log('ERROR', 'Can not find task file %s' % str_task_file)
                return -1, dict_task_info
            else:
                str_task_file = str_archived_task_file
        # Open the task file(.xml)
        try:
            et_task = ET.parse(str_task_file)
        except:
            self.log('ERROR', 'Fail to open the task file %s' % str_task_file)
            return -1, dict_task_info
        # Parse the task file xml node.
        try:
            str_task_id = et_task.find('task_id').text
            str_task_id = '' if str_task_id is None else str_task_id
        except:
            self.log('ERROR', 'Fail to find the task id of task %s' % str_task_id)
            str_task_id = ''
        dict_task_info['task_id'] = str_task_id
        try:
            str_folder = et_task.find('folder').text
            str_folder = '' if str_folder is None else str_folder
        except:
            self.log('ERROR', 'Fail to find the folder of task %s' % str_task_id)
            str_folder = ''
        dict_task_info['folder'] = str_folder
        try:
            str_work_directory = et_task.find('work_directory').text
            str_work_directory = '' if str_work_directory is None else str_work_directory
        except:
            self.log('ERROR', 'Fail to find the work directory of task %s' % str_task_id)
            str_work_directory = ''
        dict_task_info['work_directory'] = str_work_directory
        try:
            str_priority = et_task.find('priority').text
            str_priority = '' if str_priority is None else str_priority
        except:
            self.log('ERROR', 'Fail to find the priority of task %s' % str_task_id)
            str_priority = ''
        dict_task_info['priority'] = str_priority
        try:
            str_creation_time = et_task.find('creation_time').text
            str_creation_time = '' if str_creation_time is None else str_creation_time
        except:
            self.log('ERROR', 'Fail to find the creation time of task %s' % str_task_id)
            str_creation_time = ''
        dict_task_info['creation_time'] = str_creation_time
        try:
            str_estimated_start = et_task.find('estimated_start').text
            str_estimated_start = '' if str_estimated_start is None else str_estimated_start
        except:
            self.log('ERROR', 'Fail to find the estimated start of task %s' % str_task_id)
            str_estimated_start = ''
        dict_task_info['estimated_start'] = str_estimated_start
        try:
            str_start_time = et_task.find('start_time').text
            str_start_time = '' if str_start_time is None else str_start_time
        except:
            self.log('ERROR', 'Fail to find the start time of task %s' % str_task_id)
            str_start_time = ''
        dict_task_info['start_time'] = str_start_time
        try:
            str_estimated_complete = et_task.find('estimated_complete').text
            str_estimated_complete = '' if str_estimated_complete is None else str_estimated_complete
        except:
            self.log('ERROR', 'Fail to find the estimated complete of task %s' % str_task_id)
            str_estimated_complete = ''
        dict_task_info['estimated_complete'] = str_estimated_complete
        try:
            str_closure_time = et_task.find('closure_time').text
            str_closure_time = '' if str_closure_time is None else str_closure_time
        except:
            self.log('ERROR', 'Fail to find the closure time of task %s' % str_task_id)
            str_closure_time = ''
        dict_task_info['closure_time'] = str_closure_time
        try:
            str_enclosure_id = et_task.find('enclosure_id').text
            str_enclosure_id = '' if str_enclosure_id is None else str_enclosure_id
        except:
            self.log('ERROR', 'Fail to find the enclosure id of task %s' % str_task_id)
            str_enclosure_id = ''
        dict_task_info['enclosure_id'] = str_enclosure_id
        try:
            str_status = et_task.find('status').text
            str_status = '' if str_status is None else str_status
        except:
            self.log('ERROR', 'Fail to find the status of task %s' % str_task_id)
            str_status = ''
        dict_task_info['status']= str_status
        try:
            str_platform = et_task.find('platform').text
            str_platform = '' if str_platform is None else str_platform
        except:
            self.log('ERROR', 'Fail to find the platform of task %s' % str_task_id)
            str_platform = ''
        dict_task_info['platform'] = str_platform
        try:
            str_release = et_task.find('release').text
            str_release = '' if str_release is None else str_release
        except:
            self.log('ERROR', 'Fail to find release of task %s' % str_task_id)
            str_release = ''
        dict_task_info['release'] = str_release
        try:
            str_test_plan = et_task.find('test_plan').text
            str_test_plan = '' if str_test_plan is None else str_test_plan
        except:
            self.log('ERROR', 'Fail to find the test_plan of task %s' % str_task_id)
            str_test_plan = ''
        dict_task_info['test_plan'] = str_test_plan
        list_case_info = []
        try:
            list_case_node = et_task.findall('case')
            for case_node in list_case_node:
                dict_case_info = {}
                str_case_name = case_node.find('script_name').text
                str_case_name = '' if str_case_name is None else str_case_name
                dict_case_info['script_name'] = str_case_name
                str_case_id = case_node.find('case_id').text
                str_case_id = '' if str_case_id is None else str_case_id
                dict_case_info['case_id'] = str_case_id
                str_case_status = case_node.find('status').text
                str_case_status = '' if str_case_status is None else str_case_status
                dict_case_info['status'] = str_case_status
                str_case_result = case_node.find('result').text
                str_case_result = '' if str_case_result is None else str_case_result
                dict_case_info['result'] = str_case_result
                str_case_error_code = case_node.find('error_code').text
                str_case_error_code = '' if str_case_error_code is None else str_case_error_code
                dict_case_info['error_code'] = str_case_error_code
                str_case_tested_on = case_node.find('tested_on').text
                str_case_tested_on = '' if str_case_tested_on is None else str_case_tested_on
                dict_case_info['tested_on'] = str_case_tested_on
                str_case_start_time = case_node.find('start_time').text
                str_case_start_time = '' if str_case_start_time is None else str_case_start_time
                dict_case_info['start_time'] = str_case_start_time
                str_case_complete_time = case_node.find('complete_time').text
                str_case_complete_time = '' if str_case_complete_time is None else str_case_complete_time
                dict_case_info['complete_time'] = str_case_complete_time
                list_case_info.append(dict_case_info)
        except:
            self.log('ERROR', 'Fail to find test case info of task %s' % str_task_id)
        dict_task_info['case'] = list_case_info
        return 0, dict_task_info
    
    def get_task_status(self, str_task_id, str_platform):
        dict_result = {}
        int_result, dict_task_info = self._parse_task_file(str_task_id, str_platform)
        if int_result == -1:
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = {}
        else:
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = dict_task_info
        return dict_result
    
    def auto_flash(self):
        pass
    
    def _create_task_file(self, str_task_id, str_platform, dict_task_info):
        int_execute_result = 0
        str_task_node_template = \
        '''
        <task>
            <task_id></task_id>
            <folder></folder>
            <work_directory></work_directory>
            <priority></priority>
            <creation_time></creation_time>
            <estimated_start></estimated_start>
            <estimated_complete></estimated_complete>
            <closure_time />
            <enclosure_id></enclosure_id>
            <status></status>
            <platform></platform>
            <release></release>
            <test_plan></test_plan>
        </task>
        '''
        str_case_node_template = \
        '''
        <case>
            <script_name></script_name>
            <status>queued</status>
            <result></result>
            <error_code></error_code>
            <tested_on></tested_on>
            <start_time></start_time>
            <complete_time></complete_time>
        </case>
        '''
        obj_xmlnode_task_info = ET.fromstring(str_task_node_template)
        try:
            obj_xmlnode_task_info.find('task_id').text = dict_task_info['task_id']
        except:
            self.log('ERROR', 'The task template missing task id')
            return -1
        try:
            obj_xmlnode_task_info.find('folder').text = dict_task_info['folder']
        except:
            self.log('ERROR', 'The task template % s missing folder' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('work_directory').text = dict_task_info['work_directory']
        except:
            self.log('ERROR', 'The task template % s missing work dir' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('priority').text = dict_task_info['priority']
        except:
            self.log('ERROR', 'The task template %s missing priority' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('creation_time').text = dict_task_info['creation_time']
        except:
            self.log('ERROR', 'The task template %s missing creation_time' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('status').text = 'queued'
        except:
            self.log('ERROR', 'The task template %s missing status' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('platform').text = dict_task_info['platform']
        except:
            self.log('ERROR', 'The task template %s missing platform' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('release').text = dict_task_info['release']
        except:
            self.log('ERROR', 'The task template %s missing release' % str_task_id)
            int_execute_result = -1
        try:
            obj_xmlnode_task_info.find('test_plan').text = dict_task_info['test_plan']
        except:
            self.log('ERROR', 'The task template %s missing test_plan' % str_task_id)
            int_execute_result = -1
        try:
            if len(dict_task_info['case']) == 0:
                self.log('WARNING', 'User %d: The task template %s does not contain any test cases')
            else:
                for case in dict_task_info['case']:
                    if not case['script_name'].startswith('tc_'):
                        continue
                    obj_xmlnode_case = ET.fromstring(str_case_node_template)
                    obj_xmlnode_case.find('script_name').text = case['script_name']
                    obj_xmlnode_task_info.append(obj_xmlnode_case)
        except:
            self.log('ERROR', 'The task template %s missing case' % str_task_id)
            int_execute_result = -1
        return int_execute_result, obj_xmlnode_task_info
            
    def create_task(self, str_task_id, str_platform, dict_task_info):
        dict_result = {}
        int_result, obj_xmlnode_task_info = self._create_task_file(str_task_id, str_platform, dict_task_info)
        if int_result == -1:
            self.log('ERROR', 'The task template is not complete, can not create the task file with id %s, please check' % str_task_id)
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = {}
        else:
            str_task_file = os.path.join(BASE_PATH, 'task', str_task_id + '_' + str_platform + '.xml')
            self.log('INFO', 'Save the task node to task file(%s)' % os.path.basename(str_task_file))
            if not os.path.isfile(str_task_file):
                self.log('INFO', 'Task folder not found, creating...')
                try:
                    with open(str_task_file, 'w+') as fWrite:
                        fWrite.write(ET.tostring(obj_xmlnode_task_info))
                except:
                    self.log('ERROR', 'Create task file %s fail' % os.path.basename(str_task_file))
            else:
                    self.log('WARNING', 'Double check if anyone else has create the task file %s' % os.path.basename(str_task_file))
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = {}
        return dict_result

    def _detect_task_file(self):
        lst_task_file = []
        str_task_file_path = os.path.join(BASE_PATH, TASK_FILE_BASE_PATH)
        try:
            lst_task_file = [x.split('.')[0] for x in os.listdir(str_task_file_path) if x.endswith('.xml')]
        except:
            return -1, lst_task_file
        return 0, lst_task_file

    def detect_task_list(self):
        dict_result = {}
        int_result, lst_result = self._detect_task_file()
        if int_result == -1:
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = []
        else:
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = lst_result
        return dict_result

    def _parse_conf_file(self):
        """
        This function is used to parse the conf file in order to get the dut information. Edited by Eric, 05/27/2014
        """
        self.log('INFO', 'Parse conf file')
        list_dut_info = []
        str_conf_file_path = os.path.join(BASE_PATH, 'conf.xml')
        if not os.path.isfile(str_conf_file_path):
            self.log('ERROR', 'Can not find conf file %s' % str_conf_file_path)
            return -1, list_dut_info
        #Open the conf file(conf.xml)
        try:
            et_conf = ET.parse(str_conf_file_path)
        except:
            self.log('ERROR', 'Fail to open the conf file %s' % str_conf_file_path)
            return -1, list_dut_info
        # Parse the conf file enclosure node.
        try:
            list_enclosure_node =  et_conf.findall('enclosure')
        except:
            self.log('ERROR', 'Fail to find the enclosure node')
            return -1, list_dut_info
        for node_enclosure in list_enclosure_node:
            dict_dut_info = {}
            try:
                str_platform_name = node_enclosure.find('id').text
                str_platform_type = node_enclosure.find('platform').text
                str_platform_status = node_enclosure.find('status').text
                list_sp_node = node_enclosure.findall('sp')
                if len(list_sp_node) == 0:
                    self.log('ERROR', 'No sp found')
                    continue
                elif len(list_sp_node) == 1:
                    str_platform_sp = 'single'
                else:
                    str_platform_sp = 'dual'
            except:
                self.log('ERROR', 'Enclosure info invalid')
                continue
            dict_dut_info['platform_name'] = str_platform_name
            dict_dut_info['platform_type'] = str_platform_type
            dict_dut_info['status'] = str_platform_status
            dict_dut_info['platform_sp'] = str_platform_sp
            list_dut_info.append(dict_dut_info)
        if len(list_dut_info) == 0:
            return -1, list_dut_info
        else:
            return 0, list_dut_info
            
    def get_dut_status(self):
        """
        This function is used to get the dut status. Edited by Eric, 05/27/2014
        """
        dict_result = {}
        int_result, list_result = self._parse_conf_file()
        if int_result == -1:
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = []
        else:
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = list_result
        return dict_result
        
    def _parse_test_case_log_file(self, str_platform, str_release, str_case_name, str_log_type):
        """
        This function is used to parse the test case log file. Edited by Eric.
        """
        str_test_case_log = ''
        str_test_case_log_base_path = os.path.join(BASE_PATH, LOG_FILE_BASE_PATH, str_platform, \
                                              str_release, str_case_name)
        str_test_case_log_full_path = ''
        list_case_log_name = os.listdir(str_test_case_log_base_path)
        for case_log_name in list_case_log_name:
            if case_log_name.startswith(str_log_type):
                str_test_case_log_full_path = os.path.join(str_test_case_log_base_path, case_log_name)
                break
            else:
                continue
        try:
            with open(str_test_case_log_full_path) as f_log:
                str_test_case_log = '\n'.join(f_log.readlines())
        except:
            return -1, ''
        return 0, str_test_case_log
        
    def get_test_case_log(self, str_platform, str_release, str_case_name, str_log_type = 'EVENT'):
        """
        This function is used to get test case log. Edited by Eric
        """
        dict_result = {}
        int_result, str_result = self._parse_test_case_log_file(str_platform, str_release, str_case_name, str_log_type)
        if int_result == -1:
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = ''
        else:
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = str_result
        return dict_result        

    def list_log_files(self, str_path):
        """
        This function is used to list a specific case's log files.
        """
        self.log("INFO", "List log files for case: %s" % str_path)
        dict_result = {}
        if os.path.exists(str_path):
            lst_log_file = [x for x in os.listdir(str_path)]
            self.log("INFO", "List log files for case: %s success" % str_path)
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = lst_log_file
        else:
            self.log("ERROR", "List log files for case: %s fail" % str_path)
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = []
        return dict_result

    def get_file_size(self, str_path):
        """
        This function is used to get a specific file size.
        """
        self.log('INFO', 'Get file size: %s' % str_path)
        dict_result = {}
        if os.path.exists(str_path):
            self.log("INFO", "Get file size success: %s" % str_path)
            dict_result['execute_result'] = 0x00
            dict_result['return_value'] = os.path.getsize(str_path)
        else:
            self.log("ERROR", "Get file size fail: %s" % str_path)
            dict_result['execute_result'] = 0x01
            dict_result['return_value'] = ''
        return dict_result

    def download_file(self, str_path, pos, block = 1024*1024*1):
        """
        This function is used to download a specific file via JSONRPC.
        """
        self.log("INFO", "Download file: %s" % str_path)
        f_file = open(str_path, "rb")
        f_file.seek(pos)
        data = xmlrpclib.Binary(f_file.read(block))
        return data

class CJSONRPCServer(ThreadingMixIn, SimpleJSONRPCServer, CLogger):
    """
    ************************************************************************************************************
    [Type    ]: Class
    [Name    ]: CXMLRPCServer
    [Author  ]: Eric Wang
    [Function]: Provides interface(functions) to communicate with XMLRPC client
    [Input   ]: 
    [Output  ]: 
    
    [History ]:
    ************************************************************************************************************
      VERSION        EDITOR          DATE             COMMENT
    ************************************************************************************************************
      R00            Eric Wang      03/31/2014       Initial version
    ************************************************************************************************************
    """
    def __init__(self, addr = None, obj_logger = None):
        CLogger.__init__(self)
        self.set_logger(obj_logger)
        # if the IP is not set, use the server ip
        if addr == None:
            import socket
            str_server_name = socket.getfqdn(socket.gethostname())
            list_server_ip = socket.gethostbyname_ex(str_server_name)
            str_server_ip = '' 
            for each_ip in list_server_ip[2]:
                if each_ip.startswith('10.'):
                    str_server_ip = each_ip
                    break
            if str_server_ip == '':
                print '[ERROR] Cannot find IP of 10.xxx.xxx.xxx. Exit'
                import sys
                sys.exit()
            addr = (str_server_ip, 8003)
        SimpleJSONRPCServer.__init__(self, addr, logRequests = False)
        self.instance_register()
        self._deactivate_socket()
        
    def _activate_socket(self):        
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        self.server_bind()
        self.server_activate()
    
    def _deactivate_socket(self):
        self.socket.close()
        
    def instance_register(self):
        self.register_instance(CJSONRPCFunc(self.obj_logger))
        self.register_function(self.help, 'help')
        
    def help(self, str_method = None):
        if str_method == None:
            return self.system_listMethods()
        elif self.system_listMethods().count(str_method) != 0:
            return self.system_methodHelp(str_method)
        else:
            return 'Command not found'
    
    def run(self):
        self._activate_socket()
        self.serve_forever()
    
if __name__ == "__main__":
    
    jsonrpc_server = CJSONRPCServer()
    obj_thread = Thread(target=jsonrpc_server.run)
    obj_thread.setDaemon(True)
    obj_thread.start()
    while True:
        time.sleep(2)
        print enumerate()
