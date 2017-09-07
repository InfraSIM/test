'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*****************************************************************************************************
This file is a part of puffer automation test framework

[Filename]: CBaseCase.py
[Author  ]: Forrest Gu(Forrest.Gu@emc.com) Andy Huang(Andy.Huang2@emc.com)
[Purpose ]: Define all basic/common functions
[Contains]: This section will include the class, member function and some variable in this file
[History ]:
***********************************************************************************************************
  VERSION        EDITOR          DATE             COMMENT
***********************************************************************************************************
  R00            Forrest Gu      08/28/2013       Initial version
  R01            Andy Huang      09/06/2013       Revise attributes and functions of CBaseCase class
  R02            Andy Huang      09/12/2013       Add logger module bases on logging functions
  R03            Eric Wang       10/21/2013       Remove BMC console related IPMI command and fix some bugs
***********************************************************************************************************
'''

import time
import datetime
import os
import logging
import gevent
import traceback
import json

import lib.Env as Env
from lib.Logger import CLogger
from idic.graph.Graph import CGraph
from lib.Apps import is_valid_ip
from idic.stack.Stack import CStack

# Case result
PASS = 'pass'
FAIL = 'fail'
SKIP = 'skip'
BLOCK = 'block'
LIST_RESULT_SUPPORTED = (PASS, FAIL, SKIP, BLOCK)

AUTOMATED = 'automated'
INTERACTIVE = 'interactive'
UTILITY = 'utility'

# case status
STATUS_QUEUED = 'queued'
STATUS_ONGOING = 'ongoing'
STATUS_COMPLETED = 'completed'

INTERFACE_KCS = 'ipmi_kcs'
INTERFACE_IOL = 'ipmi_iol'
INTERFACE_IPMI = 'ipmi'

FIELD_INFRASIM = 'idic'
FIELD_RACKHD = 'rackhd'
LIST_FIELD_IN_CASE_NAME = [FIELD_INFRASIM, FIELD_RACKHD]

class CBaseCase(CLogger):
    '''
    ************************************************************************************************************
    [Type    ]: Class
    [Name    ]: CBaseCase
    [Author  ]: Forrest Gu(Forrest.Gu@emc.com)
    [Function]: Contains some member functions to help test case running
    [Input   ]: Some attributes for test case using
    [Output  ]: 
    
    [History ]:
    ************************************************************************************************************
      VERSION        EDITOR          DATE             COMMENT
    ************************************************************************************************************
      R00            Forrest Gu      08/28/2013       Initial version
      R01            Andy Huang      09/06/2013       Revise attributes and functions of CBaseCase class
      R02            Andy Huang      09/12/2013       Add logger module bases on logging functions
      R03            Forrest Gu      09/28/2013       Add b_pass, b_quit, str_error_code to enable control
      R04            Eric Wang       10/21/2013       Remove BMC console related IPMI command and fix some bugs
      R05            Bruce Yang      11/13/2013       Add run_action method to support action based case structure
      R06            Bruce Yang      11/13/2013       Revise the loging methods to support xml format
      R07            Forrest Gu      04/30/2014       Import IPMI, register interface in
                                                      function: config_interfaces_for_device_tree
      R08            Forrest Gu      05/06/2014       Add interface register for spa_ipmi, spb_ipmi, ipmi
    ************************************************************************************************************
    '''
    def __init__(self, str_case_name = None):
        CLogger.__init__(self)
        self.str_result = PASS        # str_pass: this case pass or not
        self.b_timeout=True      # b_timeout: case is timeout
        self.list_error_code=[]     # str_error_code: case error code
        self.str_status = STATUS_ONGOING
        self.time_start = None
        self.time_complete = None

        # These variable provides necessary attributes case uses in run time
        self.obj_xmlnode_case = None # xml node in task file
        self.obj_release = None # the release object
        self.b_valid = True # track if met unexpected error before run
        self.str_error_code = '' # track the error code met before run
        self.b_quit = False # indicating if a quit signal is received
        self.list_interface_required = []
        self.list_interface_name_supported = ['bmc_console',
                                              'ipmi_kcs',
                                              'ipmi_iol',
                                              'ipmi']
        self.list_interface_type_supported = ['bmc_console',
                                              'ipmi_kcs',
                                              'ipmi_iol',
                                              'ipmi']
        self.dict_interface = {'case':self}
        for each_interface in self.list_interface_name_supported:
            self.dict_interface[each_interface] = None
        self.dict_side_name = {'A':'spa', 'B':'spb'}

        # Runtime params
        self.str_platform = ''
        self.str_target_firmware_type = ''
        self.str_target_product_generation = ''
        self.str_case_name = str_case_name
        self.str_case_id = ''
        self.str_system_type = ''
        self.b_stop_on_error = False
        self.str_automation_level = AUTOMATED
        self.b_notification_on_failure = False
        self.b_unsafe_to_break = True
        self.str_work_directory = ''
        self.b_start_sellogger = True
        self.int_cycle_count = 1
        self.int_current_cycle_index = 0
        self.monorail = None
        self.graph = CGraph()
        self.stack = None
        self.data = {}

        # initialize test case interface
        self.obj_rest_agent = None
        self.restful = None
        self.rest_get = None
        self.rest_put = None
        self.rest_delete = None
        self.rest_post = None
        self.rest_patch = None
        self.ssh = None

        # user input
        self.str_user_input = ''

        # self.__parse_info__()
        # Parse case name
        if self.__parse_case_name() != 0:
            self.b_valid = False
            self.str_error_code = 'Incorrect case name format'
            return

    def __parse_case_name(self):
        # check if the case name is set
        if self.str_case_name == None:
            self.b_valid = False
            return -1
        # check if the case name have four parts splited by '_'
        list_parts_in_case_name = self.str_case_name.split('_')

        if len(list_parts_in_case_name) != 3:
            self.log('ERROR', 'The case name is not following format of T[ID]_<type>_<name>')
            self.b_valid = False
            return -1
        # check if the first part is tc
        if not list_parts_in_case_name[0].startswith('T'):
            self.log('ERROR', 'the case name doesn\'t start with \'T\'')
            self.b_valid = False
            return -1

        # check the second part, should be the firmware type
        if list_parts_in_case_name[1] in LIST_FIELD_IN_CASE_NAME:
            self.str_target_firmware_type = list_parts_in_case_name[1]
            return 0
        else:
            self.log('ERROR', 'the firmware type(%s) in case name is not supported' % list_parts_in_case_name[1])
            self.b_valid = False
            return -1

    def validate(self):
        # if case is already invalid, skip the validate

        if not self.b_valid:
            return False

        # create workspace
        if not os.path.isdir(self.str_work_directory):
            try:
                os.makedirs(self.str_work_directory)
            except:
                self.b_valid = False
                self.str_error_code = 'Failed to create work director: %s' % self.str_work_directory
                return False

        return True

    def run(self):

        # Prepare runtime event logger
        if not self.create_logger():
            self.b_valid = False
            self.str_error_code = 'Failed to create event logger'
            return False

        # copy the logger of the case to the device
        self.set_device_logger()

        # general configuring part
        try:
            self._config()
        except Exception, e:
            '''
            If we find the first arg of exception is 'FAIL' or 'SKIP' or 'BLOCK',  
            here we know this is a manually raised exception indicating a 
            case config failure:
                raise Exception('SKIP', message)
                raise Exception('FAIL', message)
                raise Exception('BLOCK', message)
                (like the way we use self.result)
            We should do deconfig and make this case as SKIP/BLOCK.
            '''
            if len(e.args) == 2 and type(e.args[0]) is str and \
               e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                self.result(e.args[0].upper(), e.args[1])
            else:
                errmsg='Unexpected exception happened in _config(), \
                        trace back: \n%s' % traceback.format_exc()
                self.result(BLOCK, errmsg)

        #if case is marked as fail or block in _config(),
        #we need to _deconfig() and return.
        if self.str_result != PASS:
            try:
                self._deconfig()
            except:
                pass
            return

        # case specific configuring part
        try:
            self.config()

        except AttributeError, e:
            '''
            If we found:
                1. the traceback wanna use self.monorail/self.stack
                2. get AttributeError of 'NonType' object has no attribute...
                3. self.monorail/self.stack is None
            We know user want to:
                access HWIMO without setting --ip, or
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'AttributeError: \'NoneType\' object has no attribute'
            if msg in str_trace:
                if 'self.monorail' in str_trace and not self.monorail:
                    self.log('ERROR', 'Please set --ip to run {}'.format(self.name()))
                    self.result(BLOCK, 'HWIMO IP (--ip) is not set')
                elif 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except TypeError, e:
            '''
            If we found:
                1. the traceback wanna use self.stack as dictionary with a certain key
                2. self.stack is None
            We know user want to:
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'TypeError: \'NoneType\' object has no attribute \'__getitem__\''
            if msg in str_trace:
                if 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except Exception, e:
            '''
            If we find the first arg of exception is 'FAIL' or 'SKIP' or 'BLOCK',
            here we know this is a manually raised exception indicating a
            case config failure:
                raise Exception('SKIP', message)
                raise Exception('FAIL', message)
                raise Exception('BLOCK', message)
                (like the way we use self.result)
            We should do deconfig and make this case as SKIP/BLOCK.
            '''
            if len(e.args) == 2 and e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                self.result(e.args[0].upper(), e.args[1])
            else:
                errmsg = 'Unexpected exception happened in config(), \
                        trace back: \n%s' % traceback.format_exc()
                self.result(BLOCK, errmsg)

        #if case is marked as fail or block in config(),
        #we need to _deconfig() and deconfig() and return.
        if self.str_result != PASS:
            try:
                self.deconfig()
                self._deconfig()
                self.log('INFO', 'Exit case')
            except Exception, e:
                if len(e.args) == 2 and e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                    self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                    self.result(e.args[0].upper(), e.args[1])
                else:
                    errmsg = 'Unexpected exception happened in config(), \
                            trace back: \n%s' % traceback.format_exc()
                    self.result(FAIL, errmsg)
                    # if the deconfig failed to recover the env
            return

        # test case
        self.log('INFO', 'Starting test case ...')
        try:
            self.test()

        except AttributeError, e:
            '''
            If we found:
                1. the traceback wanna use self.monorail/self.stack
                2. get AttributeError of 'NonType' object has no attribute...
                3. self.monorail/self.stack is None
            We know user want to:
                access HWIMO without setting --ip, or
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'AttributeError: \'NoneType\' object has no attribute'
            if msg in str_trace:
                if 'self.monorail' in str_trace and not self.monorail:
                    self.log('ERROR', 'Please set --ip to run {}'.format(self.name()))
                    self.result(BLOCK, 'HWIMO IP (--ip) is not set')
                elif 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except TypeError, e:
            '''
            If we found:
                1. the traceback wanna use self.stack as dictionary with a certain key
                2. self.stack is None
            We know user want to:
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'TypeError: \'NoneType\' object has no attribute \'__getitem__\''
            if msg in str_trace:
                if 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except Exception, e:
            '''
            If we found the first argument of exception is 'FAIL' or 'SKIP',
            here we know this is a manually raised exception indicating a
            case has failed:
                raise Exception(FAIL, message)
                raise Exception(SKIP, message)
                (like the way we use self.result)
            We should do deconfig and make this case as FAIL.

            '''
            if len(e.args) == 2 and type(e.args[0]) is str and e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                self.result(e.args[0].upper(), e.args[1])
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s' \
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        # case specific de-configuring part
        try:
            self.deconfig()

        except AttributeError, e:
            '''
            If we found:
                1. the traceback wanna use self.monorail/self.stack
                2. get AttributeError of 'NonType' object has no attribute...
                3. self.monorail/self.stack is None
            We know user want to:
                access HWIMO without setting --ip, or
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'AttributeError: \'NoneType\' object has no attribute'
            if msg in str_trace:
                if 'self.monorail' in str_trace and not self.monorail:
                    self.log('ERROR', 'Please set --ip to run {}'.format(self.name()))
                    self.result(BLOCK, 'HWIMO IP (--ip) is not set')
                elif 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except TypeError, e:
            '''
            If we found:
                1. the traceback wanna use self.stack as dictionary with a certain key
                2. self.stack is None
            We know user want to:
                access stack without setting --stack
            '''
            str_trace = traceback.format_exc()
            msg = 'TypeError: \'NoneType\' object has no attribute \'__getitem__\''
            if msg in str_trace:
                if 'self.stack' in str_trace and not self.stack:
                    self.log('ERROR', 'Please set --stack to run {}'.format(self.name()))
                    self.result(BLOCK, 'Stack information (--stack) is not set')
                else:
                    errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                             % traceback.format_exc()
                    self.result(FAIL, errmsg)
            else:
                errmsg = 'Unexpected exception happened during case running, trace back: \n%s'\
                         % traceback.format_exc()
                self.result(FAIL, errmsg)

        except Exception, e:
            if len(e.args) == 2 and e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                self.result(e.args[0].upper(), e.args[1])
            else:
                errmsg = 'Unexpected exception happened in config(), \
                        trace back: \n%s' % traceback.format_exc()
                self.result(FAIL, errmsg)

        # the build-in deconfig
        try:
            self._deconfig()
        except Exception, e:
            if len(e.args) == 2 and e.args[0].upper() in ['FAIL', 'SKIP', 'BLOCK']:
                self.log('ERROR', traceback.format_exc()) # for debugger, to be deleted in formal release
                self.result(e.args[0].upper(), e.args[1])
            else:
                errmsg = 'Unexpected exception happened in _config(), \
                        trace back: \n%s' % traceback.format_exc()
                self.result(FAIL, errmsg)

        self.log('INFO', 'Exit case')
        self.remove_logger()

    def result(self, str_result, str_info = ''):
        '''
        *****************************************************************************************************
        [Type    ]: Function
        [Name    ]: result
        [Author  ]: Eric Wang(eric.wang5@emc.com)
        [Function]: Record the test case result
        [Input   ]: test result, error info
        [Output  ]: NA
        
        [History ]:
        *****************************************************************************************************
          VERSION        EDITOR          DATE             COMMENT
        *****************************************************************************************************
          R00            Eric Wang      10/29/2013        Initial version
          R01            Bruce Yang     11/13/2013        Remove timeout control
        *****************************************************************************************************
        '''
        str_result = str_result.lower()
        if str_result not in LIST_RESULT_SUPPORTED:
            self.log('WARNING', 'Result type(%s) not supported, set to FAIL' % str_result)
            str_result = FAIL

        if str_result == SKIP:
            self.str_result = str_result
        if str_result == BLOCK and self.str_result != SKIP:
            self.str_result = str_result
        if str_result == FAIL and self.str_result not in [SKIP, BLOCK]:
            self.str_result = str_result

        # add the cycle index in the error code when the cycle count is more
        # than 1
        if self.int_cycle_count > 1:
            str_info = '(cycle %d):%s' % (self.int_current_cycle_index, str_info)

        if str_result == FAIL:
            self.log('ERROR', 'Test case failed: \n%s' % str_info)
            self.list_error_code.append('\n{}'.format(str_info))
        elif str_result == SKIP:
            self.log('WARNING', 'Test case is skipped: \n%s' % str_info)
            self.list_error_code.append('\n{}'.format(str_info))
        elif str_result == BLOCK:
            self.log('WARNING', 'Test case is blocked: \n%s' % str_info)
            self.list_error_code.append('\n{}'.format(str_info))
        elif str_result == PASS:
            self.log('INFO', str_info)
            self.list_error_code.append('\n{}'.format(str_info))

    def save_status(self):
        '''
        *****************************************************************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Save the case status to the task node which is owned by TE
        [Input   ]: NA
        [Output  ]: NA
        [History ]:
        *****************************************************************************************************
          VERSION        EDITOR          DATE             COMMENT
        *****************************************************************************************************
          R00            Bruce Yang     10/31/2013       Initial version
        *****************************************************************************************************
        '''
        if self.obj_xmlnode_case == None:
            self.log('WARNING', 'This case is running without a XML node.')
            return
        self.obj_xmlnode_case.find('status').text = self.str_status
        self.obj_xmlnode_case.find('result').text = self.str_result
        self.obj_xmlnode_case.find('error_code').text = ', '.join(self.list_error_code).strip('\n')
        self.obj_xmlnode_case.find('start_time').text = str(self.time_start)
        self.obj_xmlnode_case.find('complete_time').text = str(self.time_complete)

        duration = self.time_complete - self.time_start
        days = duration.days
        seconds = duration.seconds
        hour = days*24 + seconds/3600
        min = (seconds%3600)/60
        sec = (seconds%3600)%60
        format_duration = str(hour)+":"+ str(min)+":"+str(sec)
        self.obj_xmlnode_case.find('duration_time').text = format_duration

    def name(self):
        '''
        *****************************************************************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: return the case name
        [Input   ]: NA
        [Output  ]: NA
        [History ]:
        *****************************************************************************************************
          VERSION        EDITOR          DATE             COMMENT
        *****************************************************************************************************
          R00            Bruce Yang     10/31/2013       Initial version
        *****************************************************************************************************
        '''
        return self.str_case_name

    def test(self):
        pass

    def config(self):
        pass

    def _config(self):
        '''
        *****************************************************************************************************
        [Type    ]: Function
        [Name    ]: config
        [Author  ]: Andy Huang(Andy.Huang2@emc.com)
        [Function]: Config system to expected status
        [Input   ]: 
        [Output  ]: return 0 - system is ready, return -1 - fail to config system or wrong parameters
        
        [History ]:
        *****************************************************************************************************
          VERSION        EDITOR          DATE             COMMENT
        *****************************************************************************************************
          R00            Andy Huang      09/06/2013       Initial version
          R01            Bruce Yang      11/14/2013       Revise
        *****************************************************************************************************
        '''
        self.log('INFO', 'Start case config')

        self.time_start = datetime.datetime.now()

        if self.monorail:
            if not self.config_hwimo():
                self.result(BLOCK, 'Failed to config runtime HWIMO environment for {}'.
                            format(self.name()))
                return -1

        if self.stack:
            if not self.config_stack():
                self.result(BLOCK, 'Failed to config runtime stack environment for {}'.
                            format(self.name()))
                return -1

        if not self.config_graph():
            self.result(BLOCK, 'Failed to config the graph environment for {}'.
                        format(self.name()))
            return -1
        self.log('INFO', 'End case config')

        return 0

    def deconfig(self):
        pass

    def _deconfig(self):
        '''
        *****************************************************************************************************
        [Type    ]: Function
        [Name    ]: deconfig
        [Author  ]: Andy Huang(Andy.Huang2@emc.com)
        [Function]: deconfig system to expected status
        [Input   ]: 
        [Output  ]: return 0 - system is ok, return -1 - fail to deconfig system or wrong parameters
        
        [History ]:
        *****************************************************************************************************
          VERSION        EDITOR          DATE             COMMENT
        *****************************************************************************************************
          R00            Andy Huang      09/06/2013       Initial version
        *****************************************************************************************************
        '''

        self.log('INFO', 'Deconfiguring.')

        # Verify exit criteria

        # Collect log if case fail
        # Collect ORA log
        # <Place holder here>

        self.str_status = STATUS_COMPLETED
        self.time_complete = datetime.datetime.now()
        self.log('INFO', 'Case completed, de-config the case')
        self.save_status()
        self.log('INFO', 'Case completed: name - %s, result - %s, errorcode - %s' % (self.name(),\
                                                                                     self.str_result,\
                                                                                     ':'.join(self.list_error_code)))

        # reset REST session
        try:
            self.monorail.obj_rest_agent.reset()
            self.monorail.obj_rest_agent.set_logger(None)
        except:
            pass
        # reset SSH session
        try:
            self.monorail.obj_ssh_agent.disconnect()
            self.monorail.obj_ssh_agent.reset()
            self.monorail.obj_ssh_agent.set_logger(None)
        except:
            pass

        # Deconfig stack
        try:
            self.deconfig_stack()
        except:
            pass

        return True

    def config_hwimo(self):
        # Config REST agent
        # Set session log
        self.log('INFO', 'Set REST API session log ...')
        str_log_file = os.path.join(self.str_work_directory, 'REST_{}_{}.txt'.
                                    format(self.str_case_name.split('_')[0],
                                            time.strftime(Env.TIME_FORMAT_FILE)))
        self.monorail.obj_rest_agent.set_session_log(str_log_file)
        self.monorail.obj_rest_agent.set_logger(self.obj_logger)
        self.log('INFO', 'REST API session log is set to: {}'.
                 format(self.monorail.obj_rest_agent.get_session_log()))

        self.obj_rest_agent = self.monorail.obj_rest_agent
        self.restful = self.obj_rest_agent.restful
        self.rest_get = self.obj_rest_agent.send_get
        self.rest_put = self.obj_rest_agent.send_put
        self.rest_post = self.obj_rest_agent.send_post
        self.rest_patch = self.obj_rest_agent.send_patch
        self.rest_delete = self.obj_rest_agent.send_delete

        # Config SSH agent
        self.log('INFO', 'Set SSH session log ...')
        str_ssh_log = os.path.join(self.str_work_directory, 'SSH_{}_{}.txt'.
                                   format(self.str_case_name.split('_')[0],
                                          time.strftime(Env.TIME_FORMAT_FILE)))
        self.monorail.obj_ssh_agent.set_logger(self.obj_logger)
        self.monorail.obj_ssh_agent.set_raw_log_file(str_ssh_log)
        self.monorail.obj_ssh_agent.set_log(1, True)
        self.ssh = self.monorail.obj_ssh_agent

        self.log('INFO', 'Connect SSH ...')
        if not self.monorail.obj_ssh_agent.is_connected():
            if not self.monorail.obj_ssh_agent.connect():
                raise Exception("BLOCK", "Cannot ssh to ssh agent {}".format(self.monorail.obj_ssh_agent.ip))
        self.monorail.obj_ssh_agent.send_command_wait_string(chr(13), '$', b_with_buff=False)

        return True

    def config_stack(self):

        # Config stack ABS according to dict
        self.log('INFO', 'Build stack ...')

        for obj_device in self.stack.walk():
            if obj_device.get_name:
                str_id = obj_device.get_name()
            elif obj_device.get_ip:
                str_id = obj_device.get_ip()
            else:
                str_id = ''
            self.log('INFO', 'Build {} {} ...'.format(obj_device.str_sub_type, str_id))
            obj_device.set_logger(self.obj_logger)

        self.enable_iol_session()

        for obj_node in self.stack.walk_node():
            # Verify node information is complete
            str_bmc_ip = obj_node.get_bmc().get_ip()
            if not is_valid_ip(str_bmc_ip):
                self.result(BLOCK, 'Node {} BMC IP is not valid: {}'.
                         format(obj_node.get_name(), str_bmc_ip))
                return False

            # Wait until vBMC's IPMI start to response
            # Retry every 3 seconds for 20 times
            b_bmc_ready = False
            int_retry = 40
            int_gap = 3
            for i in range(int_retry):
                ret, cc, rsp = obj_node.get_bmc().ipmi.ipmitool_raw_cmd('0x00 0x01')
                # BMC is not on, power on the virtual node in first loop
                if ret != 0:
                    if i == 0:
                        self.log('WARNING', 'Node {} vBMC fail to response IOL command, ret: {}, AC cycle the node ...'.
                                 format(obj_node.get_name(), ret))
                        if obj_node._has_power_control():
                            obj_node.power_off()
                            time.sleep(10)
                            obj_node.power_on()
                        else:
                            self.result(BLOCK, 'Node {} vBMC doesn\'t response IOL command, ret: {}'.
                                        format(obj_node.get_name(), ret))
                    else:
                        self.log('WARNING', 'Node {} vBMC doesn\'t response, ret: {}, retry...'.
                                 format(obj_node.get_name(), ret))
                    time.sleep(int_gap)
                    continue
                # System power is not on, do ipmi power on
                elif rsp[0] != '0x01':
                    ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis power on')
                    if ret == 0:
                        continue
                    else:
                        self.result(BLOCK, 'Node {} system fail to do chassis power on, '
                                           'ret: {}, completion code: {}, response data: {}'.
                                    format(obj_node.get_name(), ret, cc, rsp))
                        return False
                else:
                    b_bmc_ready = True
                    break

            if b_bmc_ready:
                self.log('INFO', 'Node {} BMC is alive, system is power on'.
                         format(obj_node.get_name()))
            else:
                self.result(BLOCK, 'Node {} is not ready after 1 minutes power on retry'.
                            format(obj_node.get_name()))
                return False

        self.log('INFO', 'Build stack done')

        return True

    def enable_iol_session(self, list_node=None):
        if list_node is None:
            list_node = self.stack.walk_node()
        gevent.joinall([gevent.spawn(self._enable_iol_session, obj_node)
                        for obj_node in list_node])

    def _enable_iol_session(self, obj_node):
        if obj_node.str_sub_type != 'vNode':
            self.log('WARNING', '{} is no virtual node, skip'.format(obj_node.get_name()))
            return

        # Set IOL session log
        str_bmc_ip = obj_node.get_bmc().get_ip()
        self.log('INFO', 'Build IOL on node {} IP {}...'.format(obj_node.get_name(), str_bmc_ip))
        iol_session_log = 'IOL_{}_{}_{}.txt'.format(str_bmc_ip,
                                                    self.str_case_name.split('_')[0],
                                                    time.strftime(Env.TIME_FORMAT_FILE))
        iol_session_log_path = os.path.join(self.str_work_directory, iol_session_log)
        obj_node.get_bmc().ipmi.set_session_log(iol_session_log_path)

        return

    def enable_ipmi_console(self, list_node=None):
        '''
        Prepare SSH link to all node in list
        If list is None (not set by any value), it will try to apply it for every node
        '''
        if list_node is None:
            list_node = self.stack.walk_node()
        gevent.joinall([gevent.spawn(self._enable_ipmi_console, obj_node)
                        for obj_node in list_node])

    def _enable_ipmi_console(self, obj_node):
        if obj_node.str_sub_type != 'vNode':
            self.log('WARNING', '{} is no virtual node, skip'.format(obj_node.get_name()))
            return

        self.log('INFO', 'Build ipmi-console access on node {} ...'.format(obj_node.get_name()))

        # SSH to node ipmi-console shell
        str_ipmi_sim_ssh_log = os.path.join(self.str_work_directory, 'IPMI_CONSOLE_{}_{}_{}.txt'.
                                   format(obj_node.get_ip(),
                                          self.str_case_name.split('_')[0],
                                          time.strftime(Env.TIME_FORMAT_FILE)))
        obj_ssh = obj_node.ssh_ipmi_console
        obj_ssh.set_logger(self.obj_logger)
        obj_ssh.set_raw_log_file(str_ipmi_sim_ssh_log)
        obj_ssh.set_log(1, True)
        if not obj_ssh.is_connected():
            if not obj_ssh.connect():
                raise Exception("BLOCK", "Cannot access to ipmi-console on node {}".format(obj_node.get_ip()))
        obj_ssh.send_command_wait_string(chr(13), 'IPMI_SIM>', b_with_buff=False)

        return

    def enable_node_ssh(self, list_node=None):
        '''
        Prepare SSH link to all node's BMC's port 22 in list
        If list is None (not set by any value), it will try to apply it for every node
        '''
        if list_node is None:
            list_node = self.stack.walk_node()
        gevent.joinall([gevent.spawn(self._enable_ssh, obj_node)
                        for obj_node in list_node])

    def enable_hypervisor_ssh(self, list_hypervisor=None):
        '''
        Prepare SSH link to all hypervisor's port 22 in list
        If list is None (not set by any value), it will try to apply it for every hypervisor
        '''
        if list_hypervisor is None:
            list_hypervisor = self.stack.walk_hypervisor()
        gevent.joinall([gevent.spawn(self._enable_ssh, obj_hypervisor)
                        for obj_hypervisor in list_hypervisor])

    def _enable_ssh(self, obj_device):
        if obj_device.str_sub_type == 'vNode':
            self.log('INFO', 'Build SSH on node {} ...'.format(obj_device.get_name()))

            # SSH to node on port 22
            str_ip = obj_device.get_ip()
            str_ssh_log = os.path.join(self.str_work_directory, 'SSH_{}_{}_{}.txt'.
                                       format(str_ip,
                                              self.str_case_name.split('_')[0],
                                              time.strftime(Env.TIME_FORMAT_FILE)))

            obj_ssh = obj_device.ssh
            str_prompt = '~$'
        elif obj_device.str_sub_type == 'hypervisor':
            self.log('INFO', 'Build hypervisor SSH on {} ...'.format(obj_device.get_ip()))

            str_ip = obj_device.get_ip()
            str_ssh_log = os.path.join(self.str_work_directory, 'HYPERVISOR_SSH_{}_{}_{}.txt'.
                                       format(str_ip,
                                              self.str_case_name.split('_')[0],
                                              time.strftime(Env.TIME_FORMAT_FILE)))

            obj_ssh = obj_device.ssh
            str_prompt = ':~]'
        else:
            self.log('WARNING', 'Not supporting SSH to {}: {}'.
                     format(obj_device.str_sub_type, obj_device.get_name()))
            return

        obj_ssh.set_logger(self.obj_logger)
        obj_ssh.set_raw_log_file(str_ssh_log)
        obj_ssh.set_log(1, True)
        if not obj_ssh.is_connected():
            if not obj_ssh.connect():
                raise Exception("BLOCK", "Cannot ssh to device {}".format(obj_device.get_ip()))
        obj_ssh.send_command_wait_string(chr(13), str_prompt, b_with_buff=False)

        return

    def enable_vpdu_shell(self, list_pdu=None):
        '''
        Prepare SSH link to all vPDU shell in list
        If list is None (not set by any value), it will try to apply it for every PDU
        '''
        if list_pdu is None:
            list_pdu = self.stack.walk_pdu()
        gevent.joinall([gevent.spawn(self._enable_vpdu_shell, obj_pdu)
                        for obj_pdu in list_pdu])

    def _enable_vpdu_shell(self, obj_pdu):
        if obj_pdu.str_sub_type != 'vPDU':
            self.log('WARNING', '{} is not virtual PDU, skip'.format(obj_pdu.get_name()))
            return

        self.log('INFO', 'Build vPDU shell on {} ...'.format(obj_pdu.get_name()))

        # SNMP agent event log
        obj_pdu.snmp.set_logger(self.obj_logger)

        # SSH to PDU control shell
        str_ip = obj_pdu.get_ip()
        str_vpdu_ssh_log = os.path.join(self.str_work_directory, 'vPDU_{}_{}_{}.txt'.
                                   format(str_ip,
                                          self.str_case_name.split('_')[0],
                                          time.strftime(Env.TIME_FORMAT_FILE)))
        obj_ssh = obj_pdu.ssh_vpdu
        obj_ssh.set_logger(self.obj_logger)
        obj_ssh.set_raw_log_file(str_vpdu_ssh_log)
        obj_ssh.set_log(1, True)
        if not obj_ssh.is_connected():
            if not obj_ssh.connect():
                raise Exception("BLOCK", "Cannot ssh to PDU host {}".format(obj_pdu.get_ip()))
        obj_ssh.send_command_wait_string(str_command='help' + chr(13),
                                         wait='[CONFIG] [HELP] [IP] [MAP] [PASS] [PASSWORD] [SAVE] [VPDU] \r\n(vPDU)',
                                         int_time_out=10,
                                         b_with_buff=False)

        return

    def deconfig_stack(self):

        self.log('INFO', 'Deconfig stack ...')

        # Node need to be deconfigured completely anyway
        gevent.joinall([gevent.spawn(self.deconfig_node, obj_node)
                        for obj_node in self.stack.walk_node()])

        gevent.joinall([gevent.spawn(self.deconfig_pdu, obj_pdu)
                        for obj_pdu in self.stack.walk_pdu()])

        gevent.joinall([gevent.spawn(self.deconfig_hypervisor, obj_hypervisor)
                        for obj_hypervisor in self.stack.walk_hypervisor()])

        self.log('INFO', 'Deconfig stack done')

        return True

    def deconfig_hypervisor(self, obj_hypervisor):
        self.log('INFO', 'Deconfig hypervisor {} ...'.format(obj_hypervisor.get_name()))

        # Deconfig SSH shell
        obj_ssh = obj_hypervisor.ssh
        obj_ssh.disconnect()
        obj_ssh.reset()
        obj_ssh.set_logger(None)

    def deconfig_node(self, obj_node):
        self.log('INFO', 'Deconfig node {} ...'.format(obj_node.get_name()))

        # Deconfig IPMI_SIM shell
        obj_ssh_ipmi_console = obj_node.ssh_ipmi_console
        obj_ssh_ipmi_console.disconnect()
        obj_ssh_ipmi_console.reset()
        obj_ssh_ipmi_console.set_logger(None)

        # Deconfig BMC IOL session
        obj_bmc_iol = obj_node.get_bmc().ipmi
        obj_bmc_iol.reset()
        obj_bmc_iol.set_logger(None)

        # Deconfig Node SSH, log, etc
        obj_node_ssh = obj_node.ssh
        obj_node_ssh.disconnect()
        obj_node_ssh.reset()
        obj_node_ssh.set_logger(None)


    def deconfig_pdu(self, obj_pdu):
        self.log('INFO', 'Deconfig PDU {} ...'.format(obj_pdu.get_name()))
        obj_ssh = obj_pdu.ssh_vpdu
        obj_ssh.disconnect()
        obj_ssh.reset()
        obj_ssh.set_logger(None)

    def config_graph(self):
        obj_ssh = self.monorail.obj_ssh_agent if self.monorail else None
        self.graph.config(self.monorail, obj_ssh, self.log, self.stack)

        return True

    def create_logger(self):
        self.str_logger_name = self.str_case_name + '_' + time.strftime(Env.TIME_FORMAT_FILE)
        self.obj_logger = logging.getLogger(self.str_logger_name)
        self.obj_logger.setLevel(logging.INFO)

        # define formater 
        str_formater = Env.str_logger_formater
        log_formater = logging.Formatter(str_formater)

        # define file handler
        self.str_event_log_file = os.path.join(self.str_work_directory, 'EVENT_' + self.str_case_name.split('_')[0] + '_' + time.strftime(Env.TIME_FORMAT_FILE) + '.xml')
        if not os.path.isfile(self.str_event_log_file):
            try:
                open(self.str_event_log_file, 'w').close()
            except:
                self.b_valid = False
                self.str_error_code = 'Failed to create logger'
                return False
        log_handler_file = logging.FileHandler(self.str_event_log_file, 'a')
        log_handler_file.setFormatter(log_formater)
        log_handler_file.setLevel(logging.INFO)

        # add handler to logger
        self.obj_logger.addHandler(log_handler_file)
        return True

    def set_device_logger(self):
        if self.monorail:
            try:
                self.monorail.set_logger(self.obj_logger)
            except Exception:
                self.result(FAIL, 'Fail to set event log handler for HWIMO instance')
        if self.stack:
            try:
                self.stack.set_logger(self.obj_logger)
                for obj_device in self.stack.walk():
                    obj_device.set_logger(self.obj_logger)
            except Exception:
                self.log('WARNING', 'CStack instance is not ready, can\'t set event log handler')

    def remove_logger(self):
        for handler in self.obj_logger.handlers:
            self.obj_logger.removeHandler(handler)

        self.obj_logger = None


    def env_stack_verify(self):
        b_update = False
        stack_config = self.stack.get_config()

        # Verify node IP
        # Update ip dict first
        # dict_nodes_on_all_hyper:
        # {
        #     "hyper1": {
        #         "vbmc_dell_r630_release-2-0_13.ova_1463454332.28": "172.31.128.6"
        #     }
        # }
        #
        # dict_nodes_id:
        # {
        #     "hyper1": {
        #         "vbmc_dell_r630_release-2-0_13.ova_1463454332.28": "3501"
        #     }
        # }

        dict_nodes_on_all_hyper = {}
        dict_nodes_id = {}
        for obj_hyper in self.stack.walk_hypervisor():
            dict_nodes_on_all_hyper[obj_hyper.get_name()] = {}
            dict_nodes_id[obj_hyper.get_name()] = obj_hyper.get_all_vmid()

        for obj_node in self.stack.walk_node():
            the_hyper = self.stack.get_hypervisor(obj_node.get_hypervisor())
            the_vm_id = dict_nodes_id[obj_node.get_hypervisor()][obj_node.get_name()]
            the_vm_ip = the_hyper.get_vm_ip(the_vm_id)
            dict_nodes_on_all_hyper[obj_hyper.get_name()][obj_node.get_name()] = the_vm_ip

        # Update configuration
        for dict_rack in stack_config['vRacks']:
            for dict_node in dict_rack['vNode']:
                node_hyper = dict_node['hypervisor']
                node_name = dict_node['name']
                origin_bmc_ip = dict_node['bmc']['ip']
                expect_bmc_ip = dict_nodes_on_all_hyper[node_hyper][node_name]

                if origin_bmc_ip != expect_bmc_ip:
                    self.log('WARNING', 'Node {} BMC IP is changed to {}'.format(node_name, expect_bmc_ip))
                    dict_node['bmc']['ip'] = expect_bmc_ip
                    b_update = True

        if b_update:
            self.log('INFO', 'Stack configuration update start')

            # Update general environment variable: stack
            Env.dict_stack = stack_config
            Env.obj_stack = CStack(Env.dict_stack)
            # Update case environment variable: stack
            self.stack = Env.obj_stack
            # Update configuration file
            with open(Env.str_stack_file, 'w+') as fp:
                fp.write(json.dumps(Env.dict_stack, indent=4))
            with open(Env.str_stack_file_runtime, 'w+') as fp:
                fp.write(json.dumps(Env.dict_stack, indent=4))

            self.log('INFO', 'Stack configuration update is done')
        else:
            self.log('INFO', 'Stack configuration verification is done, no update')

    def env_update(self, key, value):
        if key not in Env.__dict__:
            self.log('WARNING', 'Fail to find {} in Environment Variable')
            return
        setattr(Env, key, value)

if __name__ == '__main__':
    print 'This module is not runnable!'
