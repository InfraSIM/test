'''
*********************************************************
 Copyright 2013 EMC Inc.

[Filename]: TestManager.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: 
[Contains]: 
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        Bruce.Yang@emc.com    09/22/2013       First edition
  V1.1        Bruce.Yang@emc.com    09/22/2013       Change each function module into thread
********************************************************************
'''

# Imports
import Env
import os
import time
import uuid
from xml.etree import ElementTree as ET
from threading import RLock

# Constants
TASK_NODE = '''
                <task>
                    <task_id></task_id>
                    <folder></folder>
                    <alias></alias>
                    <hwimo_version></hwimo_version>
                    <hwimo_ip></hwimo_ip>
                    <stack></stack>
                    <work_directory></work_directory>
                    <priority></priority>
                    <puffer_ip></puffer_ip>
                    <creation_time></creation_time>
                    <estimated_start></estimated_start>
                    <start_time></start_time>
                    <estimated_complete></estimated_complete>
                    <closure_time />
                    <status></status>
                    <platform></platform>
                    <test_plan></test_plan>
                    <test_run_id></test_run_id>
                </task>
            '''

CASE_NODE = '''
                <case>
                    <script_name></script_name>
                    <case_id></case_id>
                    <status>queued</status>
                    <result></result>
                    <error_code></error_code>
                    <start_time></start_time>
                    <complete_time></complete_time>
                    <duration_time></duration_time>
                </case>
        '''
obj_lock_for_uuid = RLock()


def deco_add_lock(func):
    '''
    Edited by Eric Wang
    This function is a decorator, used to add lock for every actions.
    '''
    global obj_lock_for_uuid

    def new_func(*args):
        obj_lock_for_uuid.acquire()
        try:
            return func(*args)
        finally:
            obj_lock_for_uuid.release()
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    return new_func


@deco_add_lock
def _new_uuid():
    # generate a new uuid of type 1
    # return the hex list of the uuid
    return str(uuid.uuid1(clock_seq=int(time.strftime('%Y%m%d%H%M%S'), 10)))


def _task_id_in_task_file_full_path(str_task):
    try:
        str_task_id = os.path.basename(str_task).split('_')[0]
    except:
        str_task_id = ''
    return str_task_id


def _time_stamp_in_uuid(str_uuid):
    try:
        import uuid
    except:
        print '[ERROR][TESTMANAGER][NEW_TASK_ID] Failed to import module uuid'
        exit(-1)
    obj_uuid = uuid.UUID(str_uuid)
    
    return str(obj_uuid.get_time())


def create_case_xmlnode(str_case_name):
    obj_xmlnode_case = ET.fromstring(CASE_NODE)
    obj_xmlnode_case.find('script_name').text = str_case_name
    obj_xmlnode_case.find('case_id').text = _new_uuid()
    return obj_xmlnode_case


def parse_case_list(list_case):
    list_ret = []
    case_folder = 'case'
    for each_case in list_case:
        # check if it is a folder in the list
        path = os.path.join(case_folder, each_case)
        if os.path.isdir(path):
            # folder; need to import every case in the folder
            # including sub-folder.
            dict_case = Env.get_case_in_dir(path)
            list_ret += dict_case.keys()
        else:
            '''
            don't check duplication in list and loose case;
            if T0000 is in case/clean and case list is like this:
                clean
                0000
            Then T0000 will be executed twice.
            '''
            list_ret.append(each_case)

    return list_ret

            
def create_task_file(str_platform='',
                     str_alias='',
                     str_hwimo_version='',
                     str_hwimo_ip='',
                     str_target_stack='',
                     str_work_directory='',
                     str_case_list='',
                     list_case=[],
                     str_source_folder='',
                     flag_dedup=False,
                     test_run_id=None,):
    list_case = parse_case_list(list_case)

    if not list_case:
        Env.log('INFO', 'No cases are assigned')
        return ''
    if flag_dedup:
        Env.log('INFO', 'Removing duplicated cases in the list')
        # removing duplication while keeping the order.
        # list(set()) does not keep the order.
        list_tmp = []
        for i in list_case:
            if i not in list_tmp:
                list_tmp.append(i)

        list_case = list_tmp

    obj_xmlnode_task = ET.fromstring(TASK_NODE)
    obj_xmlnode_task.find('task_id').text = _new_uuid()
    obj_xmlnode_task.find('folder').text = str_source_folder
    obj_xmlnode_task.find('alias').text = str_alias
    obj_xmlnode_task.find('hwimo_version').text = str_hwimo_version
    obj_xmlnode_task.find('hwimo_ip').text = str_hwimo_ip
    obj_xmlnode_task.find('stack').text = str_target_stack
    obj_xmlnode_task.find('work_directory').text = str_work_directory
    obj_xmlnode_task.find('priority').text = '4'
    obj_xmlnode_task.find('creation_time').text = time.strftime('%Y-%m-%d %H:%M:%S')
    obj_xmlnode_task.find('status').text = 'queued'
    obj_xmlnode_task.find('test_plan').text = str_case_list
    obj_xmlnode_task.find('platform').text = str_platform
    if test_run_id:
        obj_xmlnode_task.find('test_run_id').text = '%d' % test_run_id
    for each_case in list_case:
        obj_xmlnode_case = create_case_xmlnode(each_case)
        obj_xmlnode_task.append(obj_xmlnode_case)
    
    if not os.path.isdir(str_work_directory):
        os.makedirs(str_work_directory)
    str_task_file = os.path.join(str_work_directory,
                                 "task_{}_{}.xml".format(obj_xmlnode_task.find('task_id').text, str_platform))
    try:
        f_write = open(str_task_file, 'w')
    except IOError:
        Env.log('WARNING', 'Failed to create task file: %s' % str_task_file)
        return ''
    f_write.write(ET.tostring(obj_xmlnode_task))
    f_write.close()
    return str_task_file       
        
if __name__ == '__main__':
    print 'This module is not runnable!'
