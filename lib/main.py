'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: main.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: 
    This file is the main control file of puffer
[Contains]: 
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        Bruce.Yang@emc.com    2015/01/08       First edition
********************************************************************
'''

import time
import os
import sys
import logging

import ConfigManager
import TestManager
import TestExecutor
import EmailWorker
import Env

from idic.monorail.Monorail import CMonorail
from idic.stack.Stack import CStack
from optparse import OptionParser, OptionGroup
from lib.TRClient import TestRailClient

obj_options = None

def load_environment():

    global obj_options

    Env.refresh_case_pool()

    Env.log('INFO', 'Load puffer configuration ...')
    Env.obj_config_manager = ConfigManager.CConfigManager(Env.str_config_file)
    Env.obj_config_manager.set_logger(Env.puffer_logger.obj_logger)
    Env.obj_config_manager.parse_configuration()
    Env.log('INFO', 'Load puffer configuration done')

    # Configure testrail setting
    Env.log('INFO', 'Load TestRail configuration ...')
    if obj_options.test_run_id:
        dict_testrail = Env.obj_config_manager.get_testrail()
        if obj_options.testrail_root:
            Env.str_testrail_root = obj_options.testrail_root
        else:
            Env.str_testrail_root = dict_testrail.get('testrail_root', '')

        if obj_options.testrail_user and obj_options.testrail_password:
            Env.str_testrail_username = obj_options.testrail_user
            Env.str_testrail_password = obj_options.testrail_password
        else:
            if not obj_options.testrail_user and not obj_options.testrail_password:
                pass
            elif not obj_options.testrail_user:
                Env.log('WARNING', 'TestRail user is missing in options, '
                                    'please use --testrail_user to set')
            else:
                Env.log('WARNING', 'TestRail password is missing in options, '
                                    'please use --testrail_user to set')
            Env.log('INFO', 'Load TestRail authentication from conf.xml')
            Env.str_testrail_username = dict_testrail.get('username', '')
            Env.str_testrail_password = dict_testrail.get('password', '')
    Env.log('INFO', 'Load TestRail configuration done')

    # Configure test device information
    # Configure enclosure with stack_xxx.json
    if obj_options.str_stack:
        # Load stack informations
        Env.log('INFO', 'Load stack information...')
        Env.load_stack(obj_options.str_stack)
        # Initialize stack in next commit
        Env.obj_stack = CStack(Env.dict_stack)
        Env.log('INFO', 'Load stack information done')
    else:
        Env.log('WARNING', 'No stack information provided')
    # Configure HWIMO with IP and hwimo.json
    if obj_options.str_hwimo_ip:
        # Load HWIMO informations
        Env.log('INFO', 'Load HWIMO information...')
        Env.load_hwimo(obj_options.str_hwimo_ip,
                       obj_options.str_hwimo_username,
                       obj_options.str_hwimo_password)
        Env.obj_hwimo = CMonorail(Env.dict_hwimo)
        Env.log('INFO', 'Load HWIMO information done')
    else:
        Env.log('WARNING', 'No HWIMO information provided')

    if obj_options.str_stack or obj_options.str_hwimo_ip:
        pass
    else:
        Env.log('WARNING', 'Both stack and HWIMO information are missing')

    # Configure email server
    try:
        obj_mail_node = Env.obj_config_manager.get_smpt_server_node()

        # Parse information
        Env.str_smtp_server = obj_mail_node.find('server').text
        str_mail_from_address = obj_mail_node.find('from_address').text
        str_mail_from_name = obj_mail_node.find('from_name').text
        Env.str_mail_from = '"{}" <{}>'.format(str_mail_from_name, str_mail_from_address)
        if str_mail_from_address:
            EmailWorker.set_default_from_address(Env.str_mail_from)

        # Build mail server
        Env.obj_email_server = EmailWorker.CEmailServer()
        Env.obj_email_server.obj_email_sender.set_SMTP_host_address(Env.str_smtp_server)
    except:
        import traceback
        print traceback.format_exc()
        Env.log('WARNING', 'Fail to get mail configuration, email will not work')
        return -1
    try:
        list_xmlnode_notification_event = obj_mail_node.findall('notification_event')
    except:
        Env.log('WARNING', 'Failed to get notification event configuration, email will not work')
        Env.obj_email_server = None
        return -1

    for each_notification_event in list_xmlnode_notification_event:
        Env.obj_email_server.obj_email_builder.add_template_xml(each_notification_event)

    # Get puffer root for remote access to log file
    Env.str_puffer_remote_root = Env.obj_config_manager.get_puffer_root()

def build_puffer_main_logger(str_logger_name=''):
    if str_logger_name != '':
        temp_logger = logging.getLogger(str_logger_name)
    else:
        temp_logger = logging.getLogger(Env.str_logger_name)
    temp_logger.setLevel(logging.INFO)
    
    # define formater 
    str_formater = Env.str_logger_formater
    log_formater = logging.Formatter(str_formater)
    
    # define file handler
    # log file format: Event_TE#TEID_#PLATFORM_#TIMESTAMP.log
    str_log_file = 'puffer_%s.xml' % (time.strftime(Env.TIME_FORMAT_FILE))
    str_log_file = os.path.join(Env.str_log_folder, str_log_file)
    if not os.path.isdir(Env.str_log_folder):
        try:
            os.makedirs(Env.str_log_folder)
        except:
            print '[ERROR]: Failed to create log folder, exiting...'
    if not os.path.isfile(str_log_file):
        try:
            open(str_log_file, 'w').close()
        except:
            print '[ERROR]:Failed to create the log file'
    Env.obj_log_handler_file = logging.FileHandler(str_log_file, 'a')
    Env.obj_log_handler_file.setFormatter(log_formater)
    Env.obj_log_handler_file.setLevel(logging.INFO)
    
    
    # add handler to logger
    temp_logger.addHandler(Env.obj_log_handler_file)
    
    # use puffer logger
    from Logger import CLogger
    Env.puffer_logger = CLogger()
    Env.puffer_logger.set_logger(temp_logger)
    
def run_in_command_line_mode():
    """
    main entry point for puffer command line mode.
    """
    global obj_options
    
    Env.log('INFO', 'Puffer command: %s' % ' '.join(sys.argv))
    
    '''
    list_case contains 3 part:
        1. loose case
        2. content of test list file
        3. test suite
        folders are expended and checked in TestManager.py/parse_case_list()
    '''
    list_case = []
    str_work_directory = ''

    # whether to remove duplicated cases in the task;
    # determined by --dedub.
    flag_dedup = obj_options.dedup
    test_run_id = obj_options.test_run_id

    # Alias
    Env.str_alias = obj_options.str_alias

    # Case list by -s, test suite: folder.
    test_suite = obj_options.test_suite
    if test_suite:
        msg = 'Include cases in test suite(%s) into task file' % test_suite
        Env.log('INFO', msg)
        list_case += test_suite.split(',')

    # Case list by -l, test list file
    list_file = obj_options.str_case_list
    if list_file:
        msg = 'Include cases in list file(%s) into task file' % list_file
        Env.log('INFO', msg)
        # parse the file and add to list_case
        if not os.path.isfile(list_file):
            Env.log('WARNING', 'Case list file(%s) not found' % list_file)
        else:
            lines = open(list_file, 'r').read().splitlines()
            for i in lines:
                if i.startswith('#' or '/'):
                    # commented out. ignore.
                    continue
                list_case.append(i.strip())

    # Case list by -c, loose test cases
    if obj_options.str_cases:
        Env.log('INFO', 'Included cases(%s) into task file' % obj_options.str_cases)
        list_case += obj_options.str_cases.split(',')

    # Test environment
    # 1. HWIMO and stack both
    if Env.dict_stack and Env.dict_hwimo:
        str_platform = Env.dict_hwimo['platform']
    # 2. HWIMO only
    elif Env.dict_hwimo:
        str_platform = Env.dict_hwimo['platform']
    # 3. Stack only
    elif Env.dict_stack:
        str_platform = 'InfraSIM'
    # 4. No HWIMO, no stack
    # Wait to see if it's run with task file
    else:
        Env.log('ERROR', 'Quit with no DUT information, please issue --stack or --ip')
        return
    
    # alias: datetime+given name.
    test_run_alias = time.strftime('%Y%m%d%H%M%S')
    if obj_options.str_alias != '':
        if os.sep in obj_options.str_alias:
            obj_options.str_alias = obj_options.str_alias.replace(os.sep, '_')
        test_run_alias += '_%s' % obj_options.str_alias

    str_work_directory = os.path.join(Env.str_log_folder,
                                      str_platform,
                                      test_run_alias)
    Env.log('INFO', 'Logs are available at: %s' % str_work_directory)
    
    # check test result uploading setting

    if test_run_id:

        if obj_options.testrail_user and obj_options.testrail_password:
            str_source = 'command line option: --testrail_user, --testrail_password'
        else:
            str_source = '<testrail_config> in conf.xml'

        testrail = TestRailClient(str_server_addr=Env.str_testrail_root,
                                  str_user=Env.str_testrail_username,
                                  str_password=Env.str_testrail_password)

        # test run id provided. validate it
        try:
            testrail.get_test_run(test_run_id)
            msg = 'Test result will be uploaded to test run %d' % test_run_id
            Env.log('INFO', msg)
        except:
            Env.log('WARNING', 'TestRail connection fail, please check {}'.format(str_source))

    # Detect HWIMO revision
    str_hwimo_rev = ''
    if Env.obj_hwimo:
        str_hwimo_rev = Env.obj_hwimo.get_revision()

    str_task_file = TestManager.create_task_file(str_platform,
                                                 Env.str_alias,
                                                 str_hwimo_rev,
                                                 obj_options.str_hwimo_ip,
                                                 obj_options.str_stack,
                                                 str_work_directory,
                                                 list_file,
                                                 list_case,
                                                 obj_options.str_release_folder,
                                                 flag_dedup,
                                                 test_run_id)

    if obj_options.str_task != '':
        str_task_file = obj_options.str_task
        
    if str_task_file == '':
        Env.log('ERROR', 'Command invalid, please check the arguments')
        return 
        
    obj_TE = TestExecutor.CTestExecutor(str_task_file)
    if not obj_TE.is_valid():
        Env.log('INFO', 'Task file(%s) invalid' % str_task_file)
        return

    obj_TE.create_logger(obj_TE.task_id())

    obj_TE.run()
    
    now = time.clock()
    while True:
        # exit if all the queued emails are sent
        if Env.obj_email_server.is_idle():
            break
        # quit when the 10 min timer expired
        if time.clock() - now > 600:
            break
        time.sleep(0.01)
    
    Env.log('INFO', 'Puffer quits')
        
def run(): 
    
    parse_options()

    build_puffer_main_logger(obj_options.str_alias)
    
    Env.log('INFO', 'Puffer %s Running' % Env.str_version)

    try:
        load_environment()
    except Exception, e:
        Env.log('ERROR', 'Fail to load test environment')
        import traceback
        print traceback.format_exc()
        return
    
    if obj_options.b_start_email:
        Env.start_email_server()
        
    Env.b_update_enclosure_before_test = obj_options.b_update_before_test

    run_in_command_line_mode()
        
    os.chdir(Env.str_original_cwd)
    
def parse_options(): 
    global obj_options
       
    usage = 'usage: %prog [option]'
    
    parser = OptionParser(usage=usage)

    # general options
    group = OptionGroup(parser, 'General Options')

    group.add_option('-r', '--release', action='store', type='string',
                     dest='str_release_folder', default='',
                     help='target release folder to be executed.')
    group.add_option('-u', '--update', action='store_true',
                     dest='b_update_before_test', default=False,
                     help='Set if force to update firmware on each '
                          'enclosure before running test cases.')
    group.add_option('-a', '--alias', action='store', type='string',
                     dest='str_alias', default='',
                     help='set a alias for this running')
    group.add_option('-e', '--email', action='store_true',
                     dest='b_start_email', default=False,
                     help='Set if email server should be started')
    group.add_option('', '--dedup', action='store_true',
                     dest='dedup', default=False,
                     help='Set if duplicated cases should be removed '
                          'from test list.')
    parser.add_option_group(group)
    
    # Device config
    group_dut = OptionGroup(parser, 'Test target options')

    group_dut.add_option('', '--stack', action='store', type='string',
                     dest='str_stack', default='',
                     help='set target stack and load configuration')
    group_dut.add_option('', '--ip', action='store', type='string',
                     dest='str_hwimo_ip', default='',
                     help='set target HWIMO ip')
    group_dut.add_option('', '--username', action='store', type='string',
                     dest='str_hwimo_username', default='',
                     help='set target hwimo username')
    group_dut.add_option('', '--password', action='store', type='string',
                     dest='str_hwimo_password', default='',
                     help='set target hwimo password')
    
    parser.add_option_group(group_dut)

    # options to use case id
    group_test = OptionGroup(parser, 'Test case list options',
                             'Starting puffer by giving it a list of case id\n'
                             '-c, -l and -s could be used together.')

    group_test.add_option('-c', '--case', action='store', type='string',
                     dest='str_cases', default='',
                     help='4-digit test cases numbers to be executed '
                          'separated by \',\'; test case script file '
                          'should be in case\\ or its sub-folder.')
    group_test.add_option('-l', '--list', action='store', type='string',
                     dest='str_case_list', default='',
                     help='Name of file containing a list of test '
                          'cases/suites')
    group_test.add_option('-s', '--suite', action='store', type='string',
                     dest='test_suite', default='',
                     help='Folder path of the test suites separated by '
                          '\',\' based on case\\ folder structure; \'foo\' '
                          'means to load all cases in <puffer_root>\\case\\foo, '
                          '\'foo\\bar\' means to load all cases in '
                          '<puffer_root>\\case\\foo\\bar; Only folders in '
                          'case\\ are supported.')

    parser.add_option_group(group_test)

    # options to upload test result to testrail
    group_tr = OptionGroup(parser, 'Testrail options',
                        'If one of username or pass word is not set'
                        ', puffer will try to find them in conf.xml.')
    group_tr.add_option('', '--test_run', action='store', type='int',
                     dest='test_run_id', default=None,
                     help='Testrail test run ID to upload test result.')
    group_tr.add_option('', '--testrail_user', action='store', type='string',
                     dest='testrail_user', default=None,
                     help='Testrail account user name.')
    group_tr.add_option('', '--testrail_password', action='store', type='string',
                     dest='testrail_password', default=None,
                     help='Testrail account password.')
    group_tr.add_option('', '--testrail_root', action='store', type='string',
                     dest='testrail_root', default=None,
                     help='Testrail root address, default to GHE testrail.')

    parser.add_option_group(group_tr)

    # option to use task file
    msg = 'Starting puffer by giving it an existing task file'
    group = OptionGroup(parser, msg)
    group.add_option('-t', '--task', action='store', type='string',
                     dest='str_task', default='',
                     help='Task file to be executed.')

    parser.add_option_group(group)

    (obj_options, args) = parser.parse_args()

    return obj_options
