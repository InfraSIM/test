'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: Env.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: This file includes all environment variables, 
            And it also provides interfaces to get all these
            environments
[Contains]: 
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
1.0     Bruce.Yang@emc.com  2013/10/12    First Edition
*********************************************************
'''

# show welcome page
import time
import os
import sys
import json
from threading import Thread
import xml.etree.ElementTree as ET
import traceback

# environments
str_version = 'InfraSIM'
str_original_cwd = os.getcwd()
str_root_folder = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(str_root_folder)
sys.path.append(os.path.join(str_root_folder, 'case'))
os.chdir(str_root_folder)
str_task_folder = os.path.join(str_root_folder, 'task')
str_log_folder = os.path.join(str_root_folder, 'log')
str_archived_task_folder = os.path.join(str_root_folder, 'task', 'archived')
str_case_folder = os.path.join(str_root_folder, 'case')
str_configure_package = 'configure'
str_configure_folder = os.path.join(str_root_folder, str_configure_package)
str_config_file = 'conf.xml'
str_stack_file = ''
str_stack_file_runtime = ''
str_puffer_remote_root = ''
str_testrail_root = ''
str_testrail_username = ''
str_testrail_password = ''
str_alias = ''

if not os.path.isfile(str_config_file):
    msg = 'conf.xml not found. Please create one based on conf.xml ' \
          'and put it in the same folder with puffer.py'
    print msg
    exit()

# TBD
str_source_folder = ''
str_logger_formater = '%(message)s'
str_smtp_server = 'mailhub.lss.emc.com:25'
str_mail_from = ''
obj_log_handler_file = None
obj_log_handler_console = None
obj_config_manager = None
obj_email_server = None
obj_tftp_server = None
obj_jsonrpc_server = None
obj_stack = None
obj_hwimo = None
puffer_logger = None
str_logger_name = 'puffer'
int_tm_id = 1
list_tracked_platform_types = []
list_platform_tm = []   # a list in which each element is a pair of (TM type, TM instance)
list_thread_tm = []     # a list of all running TM thread 
 
dict_ID_enclosure = {}
dict_platform_enclosureIDs = {}
dict_enclosureID_TMID ={} 
dict_ID_TM = {}
dict_ID_case = {}
dict_stack = {}
dict_hwimo = {}

#flags
#b_update_enclosure_before_test = True
b_update_enclosure_before_test = False

# Constants
TIME_FORMAT_LOG = '%Y-%m-%d %H:%M:%S'
TIME_FORMAT_FILE = '%Y%m%d%H%M%S'  

def get_idle_enclosure(str_platform, int_tm_id=None):
    global dict_ID_enclosure
    list_idle_enclosure = []
    list_all_enclosure_id = dict_ID_enclosure.keys()
    for each_enclosure_id in list_all_enclosure_id:
        if dict_ID_enclosure[each_enclosure_id].str_platform != str_platform:
            continue
        if dict_enclosureID_TMID[each_enclosure_id] != None:
            continue
        list_idle_enclosure.append(each_enclosure_id)
    if int_tm_id == None:
        return list_idle_enclosure
    return lock_enclosures(list_idle_enclosure, int_tm_id)

def lock_enclosures(list_enclosure_id, int_tm_id):
    list_enclosure_id_locked = []
    for each_enclosure_id in list_enclosure_id:
        if not dict_enclosureID_TMID.has_key(each_enclosure_id):
            log('INFO', 'TM%d is locking enclosure(%s) which doesn\'t exist, pls check config file' % (int_tm_id, each_enclosure_id))
            continue
        if dict_enclosureID_TMID[each_enclosure_id] == None:
            log('INFO', 'TM%d is locking enclosure:%s' % (int_tm_id, each_enclosure_id))
            dict_enclosureID_TMID[each_enclosure_id] = int_tm_id
            list_enclosure_id_locked.append(each_enclosure_id)
        else:
            log('WARNING', 'TM%d trying to lock enclosure(%s) which has been locked by TM%d'
                % (int_tm_id, each_enclosure_id, dict_enclosureID_TMID[each_enclosure_id]))
    return list_enclosure_id_locked

def get_enclosure(str_enclosure_id):
    global dict_ID_enclosure
    if dict_ID_enclosure.has_key(str_enclosure_id):
        return dict_ID_enclosure[str_enclosure_id]
    raise Exception('Failed to find enclosure(%s)' % str_enclosure_id)

def get_case(str_case_id_or_name):
    global dict_ID_case
    if dict_ID_case.has_key(str_case_id_or_name):
        return dict_ID_case[str_case_id_or_name]
    if dict_ID_case.values().count(str_case_id_or_name) > 0:
        return str_case_id_or_name
    # Bruce 2015/01/12:
    # below i don't use exception because we need to allow/consider
    # the case where use typed a wrong case_id or name
    return ''

def release_enclosures(list_enclosure_id, int_tm_id):
    list_enclosure_id_released = []
    for each_enclosure_id in list_enclosure_id:
        if dict_enclosureID_TMID[each_enclosure_id] == int_tm_id:
            log('INFO', 'TM%d is releasing enclosure:%s' % (int_tm_id, each_enclosure_id))
            list_enclosure_id_released.append(each_enclosure_id)
            dict_enclosureID_TMID[each_enclosure_id] = None
        else:
            log('WARNING', 'TM%d trying to release enclosure(%s) which has been locked by TM%d' % (\
                        int_tm_id, each_enclosure_id, dict_enclosureID_TMID[each_enclosure_id]))
    return list_enclosure_id_released

def log(str_level, str_message):
    global puffer_logger
    puffer_logger.log(str_level, str_message)
        
def start_email_server():    
    log('INFO', 'Start email server')
    obj_email_server.start()
    log('INFO', 'Email server started')
    
def start_jsonrpc_server():
    global obj_jsonrpc_server
    log('INFO', 'Start JSONRPC server')
    thread_jsonrpc_server = Thread(target = obj_jsonrpc_server.run)
    thread_jsonrpc_server.setDaemon(True)
    thread_jsonrpc_server.start()
    log('INFO', 'JSONRPC server started')
    
def send_email(str_subject, list_information):
    global obj_email_server
    if not obj_email_server:
        return -1
    obj_email_server.raise_email_request(str_subject, list_information)
    return 0

def refresh_case_pool():
    global dict_ID_case
    case_dir='case'
    
    dict_ID_case = {}

    list_file = os.listdir(case_dir)
    dict_ID_case = get_case_in_dir(case_dir)

def get_case_in_dir(case_dir):
    '''
    function to get all case file in the given folder.
    will recurse into sub-folder.
    '''
    dict_ID_case = {}
    list_file = os.listdir(case_dir)

    for f in list_file:
        path=os.path.join(case_dir, f)
        if os.path.isfile(path):
            if f.startswith('T') and f.endswith('.py'):
                str_id = f.split('_')[0][1:]
                if dict_ID_case.has_key(str_id):
                    raise Exception('Duplicate(%s) ID found in case pool' % str_id)
                dict_ID_case[str_id] = path[:-3]
        elif os.path.isdir(path):
            #sub folder. need to add all case in the sub-folder.
            ret=get_case_in_dir(path)
            for i in ret.keys():
                if dict_ID_case.has_key(i):
                    raise Exception('Duplicate(%s) ID found in case pool' % i)
            dict_ID_case.update(ret)

    return dict_ID_case

def load_stack(str_target_stack=''):
    '''
    Load stack information into environment
    :param str_target_stack: package name or absolute name
        If it's an absolute name and can be json.load, load_stack continues
        else it will load a stack packet from configuration/ folder
    '''
    try:
        # Try to import stack info
        # package_name is configure
        # all stack file should be started with stack_, followed
        # by stack name
        global str_stack_file
        if os.path.isfile(str_target_stack):
            str_stack_file = str_target_stack
            f_stack = file(str_target_stack)
            j_stack = json.load(f_stack)
        else:
            str_stack_file = os.path.join(str_configure_folder,
                                          'stack_{}.json'.format(str_target_stack))
            f_stack = file(str_stack_file)
            j_stack = json.load(f_stack)
        global dict_stack
        dict_stack = j_stack
        log('INFO', 'Stack ({0}) is loaded into Environment'.format(str_target_stack))

    except:
        #log the reason of case import failure.
        errmsg='Unexpected exception happened when loading stack {0}, \
                trace back: \n{1}'.format(str_target_stack, traceback.format_exc())
        log('ERROR', errmsg)

def load_hwimo(str_hwimo_ip, str_hwimo_username, str_hwimo_password):
    '''
    Load HWIMO IP/username/password into environment
    '''
    try:
        str_hwimo_file = os.path.join(str_configure_folder,
                                      'hwimo.json')
        f_hwimo = file(str_hwimo_file)
        j_hwimo = json.load(f_hwimo)
        j_hwimo['ip'] = str_hwimo_ip
        j_hwimo['username'] = str_hwimo_username
        j_hwimo['password'] = str_hwimo_password
        global dict_hwimo
        dict_hwimo = j_hwimo

        log('INFO', 'HWIMO ({}:{}@{}) is loaded into Environment'.
            format(str_hwimo_username, str_hwimo_password, str_hwimo_ip))

    except:
        errmsg = 'Unexpected exception happened when loading HWIMO {0}:{1}@{2}, trace back: \n{3}'.\
            format(str_hwimo_username, str_hwimo_password, str_hwimo_ip, traceback.format_exc())
        log('ERROR', errmsg)
        
 
if __name__ == '__main__':
    print 'Env module is not runnable'
