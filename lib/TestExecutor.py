'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: TestExecutor.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: 
[Contains]: 
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        Bruce.Yang@emc.com    10/17/2013       First edition
********************************************************************
'''

# imports
import re
import json
import logging
import datetime
import shutil
import JUnit
from lib.TRClient import TestRailClient
from Logger import CLogger
from SelLogger import *

try:
    import Env
except:
    print 'Failed to import Env'
    exit(1)
try:
    from Release import CRelease
except:
    print 'Failed to import CRelease from Release module'
    exit(1)

# contants
# case status
STATUS_QUEUED = 'queued'
STATUS_ONGOING = 'ongoing'
STATUS_COMPLETED = 'completed'

class CTestExecutor(CLogger):
    '''
    '''

    def __init__(self, str_task_file=''):
        CLogger.__init__(self)
        self.b_valid = True
        self.str_error_code = ''
        self.b_quit = False
        self.b_status_change = False
        self.b_completed = False
        self.b_still_case_queued = True
        self._b_create_junit_report = True
        self.str_task_file = os.path.basename(str_task_file)
        self.str_report_file = ''
        self.str_work_directory = 'temp'
        self.str_task_file_full_path = str_task_file
        self.str_platform = 'unknown'
        self.str_hwimo_version = ''
        self.str_hwimo_ip = ''
        self.str_stack = ''
        self.str_test_alias = ''
        self.str_test_title = ''
        self.str_task_ID = os.path.basename(self.str_task_file).split('_')[0]
        self.dict_thread_case_running = {}
        self.dict_case_result_error_code = {}
        self.int_case_retry_threshold = 2
        self.list_xmlnode_case = []
        if str_task_file == '':
            raise Exception('No task file is found when initialize a test executor.')
        self.test_run_id = None
        self.testrail = None
        self.dict_pqa_tr_id = {}
        self.__parse_info__()

    def info(self):
        dict_info = {}
        dict_info['task_id'] = self.task_id()
        dict_info['task_file_full_path'] = self.str_task_file_full_path
        dict_info['priority'] = str(self.priority())
        dict_info['status'] = self.status()
        dict_info['log_folder'] = self.str_work_directory
        if not self.obj_release:
            dict_info['release_name'] = ''
        else:
            dict_info['release_name'] = self.obj_release.name()
        dict_info['release_folder'] = self.str_release_folder
        dict_info['ETC'] = self.time_etc
        dict_info['ETS'] = self.time_ets
        dict_cases = {}
        int_total_case_number = len(self.list_xmlnode_case)
        for int_case_order in range(int_total_case_number):
            dict_case_info = {}
            xmlnode_case = self.list_xmlnode_case[int_case_order]
            dict_case_info['script_name'] = xmlnode_case.find('script_name').text
            dict_case_info['index'] = str(int_case_order + 1)
            dict_case_info['case_id'] = xmlnode_case.find('case_id').text
            dict_case_info['status'] = xmlnode_case.find('status').text
            dict_case_info['result'] = xmlnode_case.find('result').text
            dict_case_info['error_code'] = xmlnode_case.find('error_code').text
            dict_case_info['start_time'] = xmlnode_case.find('start_time').text
            dict_case_info['complete_time'] = xmlnode_case.find('complete_time').text
            dict_case_info['duration_time'] = xmlnode_case.find('duration_time').text
            dict_cases[str(int_case_order + 1)] = dict_case_info
        dict_info['cases'] = dict_cases
        return dict_info

    def set_title(self, str_title):
        self.str_test_title = str_title

    def add_cases(self):
        pass

    def all_cases(self):
        list_case = []
        list_xmlnode_case = self.et_task.findall('case')
        for each_xmlnode_case in list_xmlnode_case:
            list_case.append(each_xmlnode_case.find('script_name').text)
        return list_case

    def __parse_info__(self):
        self.et_task = None
        # check if the task file exists
        import os
        if not os.path.isfile(self.str_task_file_full_path):
            self.b_valid = False
            self.str_error_code = 'Task file(%s) not found' % self.str_task_file_full_path
            return

        # read the task file into XML tree        
        int_retry = 0
        while True:
            try:
                self.et_task = ET.parse(self.str_task_file_full_path)
            except:
                int_retry += 1
                if int_retry < 5:
                    # since the task creation and task execution are in two independent thread in TM
                    # so there is possibility that a task got started before the task is fully prepared, 
                    # in which case TE will fail to parse the task file
                    # This retry is to wait until the task is full prepared.
                    # The sync between task creation and task execution is being worked on.
                    time.sleep(1)
                    continue
                self.b_valid = False
                self.str_error_code = 'failed to parse the task file: %s' % self.str_task_file_full_path

                # failed to parse the task file, move to archived folder
                str_archived_task_folder = Env.str_archived_task_folder
                if not os.path.isdir(str_archived_task_folder):
                    os.makedirs(str_archived_task_folder)
                archived_task_file_path = os.path.join(str_archived_task_folder, self.str_task_file)
                if os.path.exists(archived_task_file_path):
                    self.log('WARNING', 'A task file with same name already exists in archived folder!')
                    os.remove(archived_task_file_path)
                else:
                    shutil.move(self.str_task_file_full_path, str_archived_task_folder)
                return
            break
        if self.et_task == None:
            self.b_valid = False
            self.str_error_code = 'task file(%s) invalid' % self.str_task_file_full_path
            return

        # Load stack information
        self.str_stack = self.et_task.find('stack').text

        # Load HWIMO information
        self.str_hwimo_ip = self.et_task.find('hwimo_ip').text

        # Parse platform information
        self.str_platform = self.et_task.find('platform').text

        # Parse release folder information
        # then puffer can leverage latest image to update
        str_release_full_path = self.et_task.find('folder').text
        if str_release_full_path == None:
            str_release_full_path = ''
            # self.str_test_title = ''
            self.str_release_folder = ''
        else:
            # self.str_test_title = str_release_full_path.split(os.sep)[-1]
            self.str_release_folder = os.path.basename(str_release_full_path)

        # Parse test title from task file
        # this title is alias
        # if alias is empty, use HWIMO version
        self.str_test_alias = self.et_task.find('alias').text
        self.str_hwimo_version = self.et_task.find('hwimo_version').text or ''
        if self.str_test_alias:
            self.str_test_title = self.str_test_alias
        elif self.str_hwimo_version:
            self.str_test_title = self.str_hwimo_version
        elif self.str_stack:
            self.str_test_title = '{}'.format(os.path.basename(self.str_stack))

        # Parse work directory information
        self.str_work_directory = self.et_task.find('work_directory').text
        if self.str_work_directory != None and\
            os.path.isdir(self.str_work_directory) == False:
            os.makedirs(self.str_work_directory)
        self.str_priority = self.et_task.find('priority').text
        self.time_create = self.et_task.find('creation_time').text
        self.time_start = self.et_task.find('start_time').text
        self.time_ets = self.et_task.find('estimated_start').text
        self.time_etc = self.et_task.find('estimated_complete').text
        self.time_complete = self.et_task.find('closure_time').text
        self.str_status = self.et_task.find('status').text
        if self.str_status != 'completed':
            self.str_status = 'in test'
        obj_xmlnode_release = self.et_task.find('release')
        if obj_xmlnode_release == None or \
            obj_xmlnode_release.text == None:
            self.str_release_name = 'UNKNOWN'
        else:
            self.str_release_name = self.et_task.find('release').text
        self.list_xmlnode_case = self.et_task.findall('case')

        # initialize release object
        if self.str_work_directory != None:
            self.obj_release = CRelease(self.str_work_directory, self.str_platform)
            if self.obj_release.status() != 0:
                self.log('WARNING', 'The work directory is not a valid release')
                self.obj_release = CRelease(str_release_full_path, self.str_platform)
        else:
            self.obj_release = CRelease(str_release_full_path, self.str_platform)
        # add support for TE with no release object
        if self.obj_release.status() != 0:
            self.obj_release = None
        else:
            self.str_release_name = self.obj_release.name()

        # create log folder if the task is being tested for the first time
        if self.str_work_directory == None:
            try:
                self.str_work_directory = os.path.join(Env.str_log_folder, self.str_platform, self.log_folder_name())
            except:
                self.str_work_directory = os.path.join(os.path.curdir, self.str_platform, self.log_folder_name())
            if not os.path.isdir(self.str_work_directory):
                try:
                    os.makedirs(self.str_work_directory)
                except:
                    self.b_valid = False
                    self.str_error_code = 'Work directory cannot be created'
                    return

        # create testrail client if necessary.
        self.test_run_id = self.et_task.find('test_run_id').text
        if self.test_run_id:
            self.test_run_id = int(self.test_run_id)
            self.testrail = TestRailClient(str_server_addr=Env.str_testrail_root,
                                           str_user=Env.str_testrail_username,
                                           str_password=Env.str_testrail_password)

    def send_qual_start_email(self):
        self.log('INFO', 'Sending qual start email ...')
        if self.obj_release == None:
            list_image_basename = []
        else:
            list_image_full_path = self.obj_release.image_files_full_path()
            list_image_basename = []
            for each_image_full_path in list_image_full_path:
                list_image_basename.append(os.path.basename(each_image_full_path))

        if list_image_basename != []:
            list_info = list_image_basename
        else:
            list_info = self.all_cases()

        if not self.str_test_title:
            str_title = self.task_id()
        else:
            str_title = self.str_test_title

        list_information_qual_start = [[self.str_platform.capitalize()+':'+ str_title,
                                        self.str_hwimo_version,
                                        Env.str_version],
                                       list_info,
                                       []]
        Env.send_email('Qual Start', list_information_qual_start)

    def send_qual_complete_email(self):
        self.log('INFO', 'Sending qual completed email ...')

        if self.str_test_title == '':
            str_title = self.task_id()
        else:
            str_title = self.str_test_title

        list_information_qual_complete = [[self.str_platform.capitalize() + ':' + str_title,
                                           self.str_hwimo_version,
                                           self.time_create,
                                           self.time_complete,
                                           Env.str_version],
                                          [self.str_report_file,],
                                          [self.str_report_file,]]
        Env.send_email('Qual Complete', list_information_qual_complete)

    def run(self):
        try:

            self.log('INFO', 'TE for %s start' % self.str_task_file)

            self.time_start = time.strftime(Env.TIME_FORMAT_LOG)

            #copy conf.xml to working folder for future debug.
            self.copy_conf_to_workdirectory()

            if not self.copy_release_folder_to_workdirectory():
                self.clean_up()
                return

            self.set_all_noncomplete_case_to_queued()

            self.send_qual_start_email()

            # load case
            self.log('INFO', 'start loading case to idle system for execution')
            while self.b_still_case_queued:
                # fetch the next queued case
                obj_xmlnode_next_case = self.get_next_queued_case()
                if obj_xmlnode_next_case == None:
                    continue
                str_case_name = obj_xmlnode_next_case.find('script_name').text
                #=======================================================
                # #Bruce 2015/01/06: Since now we don't insert the background autoflash
                # # into task file. We will not skip the autoflash explicitly added in
                # # the task file
                # if self.b_update_enclosure_before_test == True and \
                #    str_case_name == 'T2350_uefi_Autoflash':
                #    self.log('INFO', 'Autoflash already tested when update the enclosure to target firmware')
                #    self.et_task.getroot().remove(obj_xmlnode_next_case)
                #    self.save_status()
                #    continue
                #=======================================================
                self.log('INFO', 'Case(%s) found, load to test executor' % (str_case_name))
                self.launch_case(obj_xmlnode_next_case)

            # clean up
            self.clean_up()
        except Exception, e:
            self.log('ERROR', 'Exception caught in TE(%s):\n%s' % (self.str_platform, traceback.format_exc()))

    def launch_case(self, obj_xmlnode_next_case):
        str_case_name_or_id = obj_xmlnode_next_case.find('script_name').text
        self.log('INFO', 'Start launching case(%s)' % (str_case_name_or_id))
        str_case_name = Env.get_case(str_case_name_or_id)
        if str_case_name == '':
            self.log('WARNING', 'Case(%s) not found' % str_case_name_or_id)
            obj_xmlnode_next_case.find('status').text = STATUS_COMPLETED
            obj_xmlnode_next_case.find('result').text = 'skip'
            obj_xmlnode_next_case.find('error_code').text = 'Case script not found'
            obj_xmlnode_next_case.find('start_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('complete_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('duration_time').text = '0'
            self.save_status()
            return
        # import case
        obj_case = self.import_case(str_case_name)

        # Failed to import the case, mark the result na, and update error code
        if obj_case == None:
            self.log('ERROR', 'failed to import case %s' % str_case_name)
            obj_xmlnode_next_case.find('status').text = STATUS_COMPLETED
            obj_xmlnode_next_case.find('result').text = 'fail'
            obj_xmlnode_next_case.find('error_code').text = 'Failed to import case'
            obj_xmlnode_next_case.find('start_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('complete_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('duration_time').text = '0'
            self.save_status()
            return
        obj_case.obj_xmlnode_case = obj_xmlnode_next_case
        # success import the case, prepare and run the case
        self.update_case_with_te_info(obj_case)
        # set environment variable for cases
        obj_case.monorail = Env.obj_hwimo
        obj_case.stack = Env.obj_stack
        # validate the case
        obj_case.validate()
        if not obj_case.b_valid:
            self.log('WARNING', 'case %s: %s' % (str_case_name, obj_case.str_error_code))
            self.log('INFO','Skip case %s' %str_case_name)
            obj_xmlnode_next_case.find('status').text = STATUS_COMPLETED
            obj_xmlnode_next_case.find('result').text = 'block'
            obj_xmlnode_next_case.find('error_code').text = obj_case.str_error_code
            obj_xmlnode_next_case.find('start_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('complete_time').text = str(datetime.datetime.now())
            obj_xmlnode_next_case.find('duration_time').text = '0'
            self.save_status()
            return

        self.execute_daemon(obj_case)

        return

    def add_enclosure(self, list_enclosure):
        for each_enclosure_id in list_enclosure:
            # this will check if the enclosure has already been tried by this enclosure
            # TE will refuse those enclosures which cannot been updated to target FW set
            if self.dict_enclosure_updated.has_key(each_enclosure_id):
                if self.dict_enclosure_updated[each_enclosure_id] == -1:
                    continue
            if self.dict_enclosure_case.has_key(each_enclosure_id):
                self.log('WARNING', 'TE(%s) get new enclosure(%s) which is already occupied by it' % \
                         (self.task_id(), each_enclosure_id))
                continue
            self.log('INFO', 'Get new enclosure(%s)' % each_enclosure_id)
            self.dict_enclosure_case[each_enclosure_id] = ''
            obj_enclosure = Env.dict_ID_enclosure[each_enclosure_id]
            if obj_enclosure.b_dual_sp:
                self.b_has_dual_sp_enclosure = True

    def still_need_enclosure(self):
        return self.b_still_case_queued

    def remove_enclosure(self, list_enclosure_id):
        for str_enclosure_id in list_enclosure_id:
            if self.list_enclosure_released.count(str_enclosure_id) > 0:
                self.list_enclosure_released.remove(str_enclosure_id)
                self.log('INFO', 'Enclosure(%s) removed from TE(%s)' % (str_enclosure_id, self.task_id()))
            else:
                self.log('ERROR', 'TE%s is trying to remove enclosure(%s) which is not occupied by it' % \
                         (self.task_id(), str_enclosure_id))

    def copy_conf_to_workdirectory(self):
        '''
        copy current conf.xml to working dir.
        '''
        shutil.copy(Env.str_config_file, self.str_work_directory)
        #shutil.copy('conf.xml', os.path.join(self.str_work_directory, self.str_task_file))

        # If run with HWIMO, copy HWIMO configuration
        if self.str_hwimo_ip:
            with open(os.path.join(self.str_work_directory, 'hwimo.json'), 'w') as fp:
                fp.write(json.dumps(Env.dict_hwimo, indent=4))

        # If run with virtual stack, copy stack configuration
        if self.str_stack:
            if os.path.isfile(self.str_stack):
                shutil.copy(self.str_stack, self.str_work_directory)
            else:
                shutil.copy(os.path.join(Env.str_configure_folder, 'stack_{}.json'.format(self.str_stack)),
                            self.str_work_directory)

    def copy_release_folder_to_workdirectory(self):
        if self.b_valid == False:
            return False
        # add support for case: the release is not set
        if not self.obj_release:
            return True
        self.log('INFO', 'double check the release')
        if self.obj_release.status() != 0:
            self.log('ERROR', 'release folder invalid or not ready:%s' % self.obj_release.str_full_path)
            self.b_valid = False
            return False
        # here is a bug that if never true, but no value to fix as moving to external control 
        if self.obj_release.full_path().lower() == self.str_work_directory.lower():
            self.log('INFO', 'Release already in work directory')
            self.log('INFO', 'Unzip the image package')
            self.obj_release.unzip_image_package() # for moons
            self.log('INFO', 'Done unzipping the image package')
            return True
        self.log('INFO', 'copy release(%s) to work directory(%s)' % (self.obj_release.base_folder_name(), self.str_work_directory))
        if not self.obj_release.copy_to(self.str_work_directory):
            self.log('ERROR', 'failed to copy the release: %s' % self.obj_release.base_folder_name())
            return False
        self.obj_release.unzip_image_package() # for moons
        self.log('INFO', 'Image copied to work directory')
        return True

    def is_valid(self):
        return self.b_valid

    def task_id(self):
        return self.str_task_ID

    def priority(self):
        if type(self.str_priority) == int:
            return self.str_priority
        try:
            int_priority = int(self.str_priority, 10)
        except:
            int_priority = 10
        return int_priority

    def set_all_noncomplete_case_to_queued(self):
        # set the status all interrupted case to queued
        self.log('INFO', 'set the status of all interrupted cases to \'queued\'')
        for each_xmlnode_case in self.list_xmlnode_case:
            if each_xmlnode_case.find('status') == None:
                self.log('INFO', 'status for the case node of %s is not found, remove...' % each_xmlnode_case.find('script_name').text)
                self.list_xmlnode_case.remove(each_xmlnode_case)
                continue
            if each_xmlnode_case.find('status').text != STATUS_COMPLETED and \
            each_xmlnode_case.find('status').text != STATUS_QUEUED:
                each_xmlnode_case.find('status').text = STATUS_QUEUED
                self.log('INFO', 'status of case %s set to \'queued\'' % each_xmlnode_case.find('script_name').text)
                self.save_status()

    def enclosures(self):
        return self.dict_enclosure_case.keys()

    def release_enclosure(self, str_enclosure_id):
        self.log('INFO', 'Releasing enclosure(%s)' % str_enclosure_id)
        if not self.dict_enclosure_case.has_key(str_enclosure_id):
            self.log('WARNING', \
                     'TE is trying to release enclosure(%s) which is either not occupied by the TE or already released from the TE' % str_enclosure_id)
            return
        if self.dict_enclosure_case[str_enclosure_id] != '':
            self.log('WARNING', 'Enclosure(%s) cannot be released, it is still occupied by case(%s)' % (str_enclosure_id, \
                                                                                                        self.dict_enclosure_case[str_enclosure_id]))
            return
        self.dict_enclosure_case.pop(str_enclosure_id)
        self.list_enclosure_released.append(str_enclosure_id)
        self.log('INFO', 'Enclosure(%s) released from TE(%s)' % (str_enclosure_id, self.task_id()))

    def enclosure_released(self):
        return self.list_enclosure_released

    def get_next_queued_case(self):
        xmlnode_next_queued_case = None
        for each_xmlnode_case in self.list_xmlnode_case:
            if each_xmlnode_case.find('status').text == STATUS_QUEUED:
                xmlnode_next_queued_case = each_xmlnode_case
                each_xmlnode_case.find('status').text = STATUS_ONGOING
                each_xmlnode_case.find('result').text = 'ongoing' # Bruce: 07/16 added to enable spectrum to
                            # poll status of the ongoing tasks
                self.save_status()
                break
        if xmlnode_next_queued_case is None:
            self.log('INFO', 'No queued case found, all cases are in test or completed')
            self.b_still_case_queued = False
        return xmlnode_next_queued_case

    def log_folder_name(self):
        return self.str_release_folder

    def save_status(self):
        # update status
        self.et_task.find('status').text = self.str_status
        self.et_task.find('work_directory').text = self.str_work_directory
        self.et_task.find('start_time').text = self.time_start
        self.et_task.find('closure_time').text = self.time_complete

        # save to file
        try:
            self.et_task.write(self.str_task_file_full_path)
        except:
            try:
                f_write = open(self.str_task_file, 'w')
            except:
                self.log('ERROR', 'Failed to save the status')
            else:
                f_write.write(ET.tostring(self.et_task.getroot()))
                f_write.close()

        # copy the task file to log folder
        if self.str_task_file_full_path == os.path.join(self.str_work_directory, self.str_task_file):
            return
        try:
            shutil.copy(self.str_task_file_full_path, os.path.join(self.str_work_directory, self.str_task_file))
        except:
            self.log('WARNING', 'Failed to copy the task file to log folder')

    def import_case(self, case_name_path):
        self.log('INFO', 'Importing case %s' % case_name_path)
        case_name=os.path.basename(case_name_path)
        package_name=case_name_path.replace(os.sep, '.')
        obj_case = None
        self.log('INFO', 'from %s import %s' % (package_name, case_name))
        exec('from %s import %s' % (package_name, case_name))
        # create the case object
        exec('obj_case = %s()' %  case_name)
        try:
            # import the case module
            # case_name_path contains path: case\\clean\\Txxxx_uefi_Tx
            # each folder should be a module with __init__.py
            # so we can import from case.clean.Txxxx import Txxxx

            exec('from %s import %s' % (package_name, case_name))
            # create the case object
            exec('obj_case = %s()' %  case_name)
        except:
            #log the reason of case import failure.
            errmsg='Unexpected exception happened when importing test case, \
                    trace back: \n%s' % traceback.format_exc()
            self.log('ERROR', errmsg)
            obj_case = None

        return obj_case

    def update_case_with_te_info(self, obj_case):
        obj_case.obj_release = self.obj_release
        obj_case.str_work_directory = os.path.join(self.str_work_directory, obj_case.name().split('_')[0])
        if self.list_xmlnode_case.count(obj_case.obj_xmlnode_case) == 0:
            self.log('WARNING', 'The case is not in the task file')
        str_case_id = obj_case.obj_xmlnode_case.find('case_id').text
        if str_case_id == None:
            self.log('WARNING', 'No case id for case: %s' % obj_case.name())
        else:
            obj_case.str_work_directory = obj_case.str_work_directory + '_' + str_case_id

    def execute_daemon(self, obj_case):
        '''
        This daemon wrap the real execute() with injecting runtime data.
        For each runtime data defined in case.json, this daemon will run case once,
        then finally summarize case results and report the worst.
        It will report result for each runtime data to TestRail, given --test_run
        '''

        # For each data set, run case once, and upload case result to TestRail
        list_case_info = []
        self.log('INFO', 'Start running case: %s' % obj_case.name())

        # Load case specific data set first
        case_id = obj_case.str_case_name.split('_')[0][1:]
        case_name_with_path = Env.dict_ID_case[case_id]
        # get case config file
        case_config_file = '%s.json'%case_name_with_path

        # Load JSON config
        try:
            with open(case_config_file, 'r') as f:
                case_data_set = json.load(f)
        except IOError:
            self.log('WARNING', 'Case {} runtime data matrix is not defined'.
                     format(obj_case.str_case_name))
            case_data_set = [{}]

        for i in range(len(case_data_set)):
            case_data = case_data_set[i]
            self.log('INFO', 'Case {} with data ({}/{}) start to run...'.
                     format(obj_case.str_case_name, i+1, len(case_data_set)))

            # Clear previous result
            obj_case.data = case_data
            obj_case.str_result = 'pass'
            obj_case.list_error_code = []

            try:
                self.execute_case(obj_case)
                result = obj_case.str_result
                error_data = ','.join(obj_case.list_error_code)
                list_case_info.append({'result': result, 'error_data': error_data})
            except Exception:
                list_case_info. append({'result': 'fail', 'error_data': traceback.format_exc()})

            if self.testrail:
                # Upload test result to testrail
                try:
                    error_log = ','.join(obj_case.list_error_code)
                    str_case_data = json.dumps(obj_case.data, indent=4)
                    if len(case_data_set) == 1:
                        msg_testrail = error_log
                    else:
                        msg_testrail = '**{}. {}**\n{}\n\nData matrix:\n{}'.\
                            format(i+1, obj_case.str_result, error_log, str_case_data)
                    self.testrail_sync(obj_case, msg_testrail)
                except:
                    self.log('WARNING', 'Fail to update case {} result with data ({}/{}) to testrail'.
                         format(obj_case.str_case_name, i+1, len(case_data_set)))
            self.log('INFO', 'Case {} with data ({}/{}) is done, result: {}, error code: {}'.
                     format(obj_case.name(),
                            i+1,
                            len(case_data_set),
                            obj_case.str_result,
                            ','.join(obj_case.list_error_code)))

        # Summarize case result and fill the worst result to TestRail
        if len(case_data_set) > 1:
            self.summarize(list_case_info, obj_case)

    def execute_case(self, obj_case):
        try:
            obj_case.run()
        except:
            obj_case.result('fail', 'RUMTIME ERROR: %s' % traceback.format_exc())
            # deconfig the case if runtime error happened in the case
            try:
                obj_case.deconfig()
            except:
                pass
            obj_case.save_status()
            self.save_status()
            self.add_case_result_to_track_list(obj_case)
            self.log('ERROR', 'runtime error happen in case(%s): %s' % (obj_case.name(), traceback.format_exc()))
        else:
            self.add_case_result_to_track_list(obj_case)

    def summarize(self, list_case_info, obj_case):
        """
        For a case run with several data, summarize its data:
        1. Update case result and error log
        2. Store result to task file
        3. Update to testrail if necessary
        @param list_result: Stores results and logs for all data set
        @type list_result: a list of dict, e.g
        [
            {'result': pass, 'error_data': 'This case pass'},
            {'result': fail, 'error_data': 'Error data'}
        ]
        @param obj_case: Case instance
        """
        self.log('INFO', 'Summarize case result ...')
        str_general_result = ''
        str_summary = ''

        # Summarize general result
        list_case_results = [dict_case_info['result'] for dict_case_info in list_case_info]
        if 'fail' in list_case_results:
            str_general_result = 'fail'
        elif 'block' in list_case_results:
            str_general_result = 'block'
        elif 'pass' in list_case_results:
            str_general_result = 'pass'
        else:
            str_general_result = 'skip'

        # Summarize result
        str_summary = '[Summary]\n'
        for i in range(len(list_case_info)):
            dict_case_info = list_case_info[i]
            str_summary += '**{0}. {1}**\n{2}\n\n'.\
                format(i+1, dict_case_info['result'], dict_case_info['error_data'])
            # Below 3 lines is to add detail error log for summary
            # if dict_case_info['result'] != 'pass':
            #     str_log_detail += '[DATA: {}]\n{}\nERROR:\n{}\n'.\
            #         format(i+1, json.dumps(obj_case.data, indent=4), dict_case_info['error_data'])

        # Set result to case
        obj_case.str_result = ''
        obj_case.list_error_code = []
        obj_case.result(str_general_result, str_summary)
        obj_case.save_status()
        self.save_status()
        self.add_case_result_to_track_list(obj_case)

        # Send result to TestRail if necessary
        if self.testrail:
            msg_testrail = ','.join(obj_case.list_error_code)
            self.testrail_sync(obj_case, msg_testrail)

        self.log('INFO', 'Summarize: case {} result is {}\n{}'.
                 format(obj_case.str_case_name,
                        obj_case.str_result.upper(),
                        str_summary.strip('\n').replace('*', '')))

    def testrail_sync(self, obj_case, msg_testrail):
        self.log('INFO', 'Uploading test result to Testrail R%d' \
                         % self.test_run_id)
        dict_result = {'pass': 1,
                       'fail': 5,
                       'skip': 6,
                       'block': 2}

        case_id_pattern = '[tTcC]([0-9]{4}\d*)_'
        ret = re.search(case_id_pattern, obj_case.str_case_name)

        if ret:
            case_tr_id = int(ret.group(1))
        else:
            raise Exception('Failed to get test ID of case %s' \
                            % obj_case.str_case_name)

        case_result = dict_result[obj_case.str_result]
        case_duration = obj_case.obj_xmlnode_case.find('duration_time').text

        try:
            rsp = self.testrail.add_case_result(self.test_run_id, case_tr_id,
                                                case_result, msg_testrail, case_duration)
        except:
            self.log('WARNING',
                     'Fail to upload case({0}) result to testrun({1})'.
                     format(case_tr_id, self.test_run_id))

    def add_case_result_to_track_list(self, obj_case):
        self.dict_case_result_error_code[obj_case.name()] = [obj_case.str_result,
                                                             ','.join(obj_case.list_error_code)]

    def create_logger(self, str_logger_name):
        if not self.b_valid:
            self.obj_logger = None
            return
        self.str_logger_name = str_logger_name
        self.obj_logger = logging.getLogger(self.str_logger_name)
        self.obj_logger.setLevel(logging.INFO)

        # define formater 
        str_formater = Env.str_logger_formater
        log_formater = logging.Formatter(str_formater)

        # define file handler
        # log file format: Event_TE#TEID_#PLATFORM_#TIMESTAMP.log
        str_log_file = 'Event_%s' % self.str_task_file
        str_log_file = os.path.join(self.str_work_directory, str_log_file)
        if not os.path.isfile(str_log_file):
            try:
                open(str_log_file, 'w').close()
            except:
                print '[ERROR][TM%s]:Failed to create the log file:%s' % (self.task_id(),\
                                                                          str_log_file)
                return
        log_handler_file = logging.FileHandler(str_log_file, 'a')
        log_handler_file.setFormatter(log_formater)
        log_handler_file.setLevel(logging.INFO)

        # add handler to logger
        self.obj_logger.addHandler(log_handler_file)

    def show_info(self):
        if not self.b_valid:
            return
        print '%-15s:\t%s' % ('TASK ID:', self.str_task_ID)
        print '%-15s:\t%s' % ('RELEASE FOLDER:', self.str_release_folder)
        print '%-15s:\t%s' % ('RELEASE NAME:', self.str_release_name)
        print '%-15s:\t%s' % ('STATUS:', self.str_status)
        for each_case in self.list_xmlnode_case:
            print '%-15s:\t%-25s, %-10s' % ('TEST CASE', each_case.find('script_name').text, each_case.find('result').text)

    def clean_up(self):
        self.str_status = 'completed'
        self.time_complete = time.strftime(Env.TIME_FORMAT_LOG)
        self.save_status()
        self.log('INFO', 'Send report for %s' % self.str_test_title)
        # generate report
        self.generate_report()
        self.generate_junit_report()
        self.update_case_name_in_task_file()

        self.log('INFO', 'TE %s clean up' % self.str_task_ID)
        self.log('INFO', 'TE %s exit.' % self.str_task_ID)
        self.send_qual_complete_email()
        self.b_completed = True

    def update_case_name_in_task_file(self):
        '''
        if the script name is only an ID, update the field with
        full script name
        '''
        for each_xmlnode_case in self.list_xmlnode_case:
            str_original_case_name = each_xmlnode_case.find('script_name').text
            str_updated_case_name = Env.get_case(str_original_case_name)
            if not str_updated_case_name:
                continue
            each_xmlnode_case.find('script_name').text = str_updated_case_name
        self.save_status()

    def generate_junit_report(self):
        self.log('INFO', 'Create Junit report for %s' % self.str_task_ID)
        str_junit_report = os.path.join(self.str_work_directory, 'junit_%s.xml' % self.str_task_ID)
        list_cases = []
        for xmlnode_case in self.list_xmlnode_case:
            # name
            str_case_name = xmlnode_case.find('script_name').text
            str_case_name = Env.get_case(str_case_name)
            str_package_name=str_case_name.replace(os.sep, '.')
            str_case_name=os.path.basename(str_case_name)
            if not str_case_name:
                self.log('WARNING', 'Case(%s) not included in JUnit report. It is not found' % str_case_name)
                continue

            # status check
            str_status = xmlnode_case.find('status').text
            if str_status != 'completed':
                self.log('WARNING', 'Case(%s) not included in JUnit report. It is not completed' % str_case_name)
                continue

            # duration
            try:
                str_duration = xmlnode_case.find('duration_time').text
                list_h_m_s = str_duration.split(':')
                int_hour = int(list_h_m_s[0], 10)
                int_minute = int(list_h_m_s[1], 10)
                int_second = int(list_h_m_s[2], 10)
                int_duration = 3600*int_hour + 60*int_minute + int_second
            except:
                int_duration = None

            # create TestCase object
            junit_test_case = JUnit.TestCase(name = str_case_name,\
                                             classname = str_package_name,\
                                             elapsed_sec=int_duration)
            # result update
            str_result = xmlnode_case.find('result').text
            str_error_code = xmlnode_case.find('error_code').text
            if str_result in ['fail', 'block']:
                junit_test_case.add_failure_info(failuretype=str_result,\
                                                 message = str_error_code)
            elif str_result == 'error':
                junit_test_case.add_error_info(errortype=str_result, message=str_error_code)
            elif str_result == 'skip':
                junit_test_case.add_skipped_info(message=str_error_code)
            elif str_result != 'pass':
                self.log('WARNING', 'Case(%s) not included in JUnit report. Result(%s) not recognized' % (str_case_name,\
                                                                                                      str_result))
                continue
            list_cases.append(junit_test_case)

        # generate TestSuites
        junit_test_suite = JUnit.TestSuite(name='puffer',\
                                           test_cases=list_cases,\
                                           timestamp=self.time_start)

        # generate Junit report
        try:
            JUnit.TestSuite.to_file(str_junit_report, [junit_test_suite,])
        except:
            self.log('WARNING', 'Failed to generate Junit report for %s: %s' % (self.str_task_ID,\
                                                                                traceback.format_exc()))
        else:
            self.log('INFO', 'JUnit report generated for %s' % self.str_task_ID)

    def generate_report(self):
        # import report template
        str_report_template_file = os.path.join('doc', 'QUAL_REPORT.html')
        str_report_content = ''
        try:
            str_report_content = open(str_report_template_file, 'r').read()
        except Exception, e:
            print e
            self.log('ERROR', 'Failed to import report template')
            return -1

        # create result table
        int_pass_case_number = 0
        int_fail_case_number = 0
        int_skip_case_number = 0
        int_block_case_number = 0

        str_case_result_table = ''
        str_case_result_table_template = '''<tr><td style="border-style: none none solid solid; border-color: rgb(141, 179, 226); border-width: 1pt; font-size: 10pt; width: 200px; font-family: Arial;"><a href="$CASEHYPERLINK">$CASE_NAME</a></td><td style="border-style: none none solid solid; border-color: rgb(141, 179, 226); border-width: 1pt; text-align: center; font-size: 10pt; width: 80px; font-family: Arial;"><span style="font-weight: bold; color: $COLOR;">$CASE_RESULT</span></td><td style="border-style: none solid solid; border-color: rgb(141, 179, 226); border-width: 1pt; font-size: 10pt; width: 300px; font-family: Arial;">$CASE_NOTE</td></tr>'''
        for obj_xmlnode_case in self.list_xmlnode_case:
            try:
                str_line = str_case_result_table_template
                str_case_name = obj_xmlnode_case.find('script_name').text
                str_case_id = obj_xmlnode_case.find('case_id').text
                str_line = str_line.replace('$CASE_NAME', str_case_name)
#                 #get server ip
#                 server_name = socket.getfqdn(socket.gethostname())
#                 #all ip addr of current server, in list
#                 lst_server_ip = socket.gethostbyname_ex(server_name)
#                 print 'server_name:',server_name
#                 server_ip = ''
#                 for ip in lst_server_ip[2]:
#                     #get first 10.xx like IP
#                     if ip.startswith('10.'):
#                         server_ip = ip
#                         break
#                 if server_ip == '':
#                     msg='Corp network ip not found. Using hostname instead.'
#                     self.log('WARNING', msg)
#                     server_ip=server_name

                case_uuid='T%s_%s'%(str_case_name.split('_')[0], str_case_id)

                #use os.path.sep instead of hardcoding '\\\\' for compatibility
                case_log_folder = os.path.join(Env.str_puffer_remote_root, 'log',
                        self.str_platform,
                        os.path.basename(self.str_work_directory),
                        case_uuid)
                str_line = str_line.replace('$CASEHYPERLINK', case_log_folder)

                str_case_result = obj_xmlnode_case.find('result').text.lower()

                if str_case_result == 'pass':
                    int_pass_case_number += 1
                    str_line = str_line.replace('$COLOR', 'rgb(20, 137, 44)')
                if str_case_result == 'fail':
                    int_fail_case_number += 1
                    str_line = str_line.replace('$COLOR', 'rgb(208, 68, 55)')
                if str_case_result == 'skip':
                    int_skip_case_number += 1
                    str_line = str_line.replace('$COLOR', 'rgb(0, 0, 0)')
                if str_case_result == 'block':
                    int_block_case_number += 1
                    str_line = str_line.replace('$COLOR', 'rgb(101, 73, 130)')

                str_line = str_line.replace('$CASE_RESULT', str_case_result)

                if obj_xmlnode_case.find('error_code').text == None or obj_xmlnode_case.find('error_code').text == '':
                    str_line = str_line.replace('$CASE_NOTE', '&nbsp;')
                else:
                    str_line = str_line.replace('$CASE_NOTE', obj_xmlnode_case.find('error_code').text)
            except:
                msg='Failed to add case result(%s) to report' \
                    % obj_xmlnode_case.find('script_name').text
                msg+=traceback.format_exc()
                self.log('ERROR', msg)
                continue
            str_case_result_table += '\n' + str_line

        # update report content
        str_report_content = str_report_content.replace('$RELEASE_NAME', self.str_hwimo_version)
        str_report_content = str_report_content.replace('$START_TIME', self.time_create)
        str_report_content = str_report_content.replace('$END_TIME', self.time_complete)
        str_report_content = str_report_content.replace('$PLATFORM', self.str_platform.capitalize())
        str_report_content = str_report_content.replace('$RELEASE_NAME', self.str_test_title)
        str_report_content = str_report_content.replace('$RESULT_TABLE', str_case_result_table)
        str_report_content = str_report_content.replace('$NUM_PASS', str(int_pass_case_number))
        str_report_content = str_report_content.replace('$NUM_FAIL', str(int_fail_case_number))
        str_report_content = str_report_content.replace('$NUM_SKIP', str(int_skip_case_number))
        str_report_content = str_report_content.replace('$NUM_BLOCK', str(int_block_case_number))
        str_report_content = str_report_content.replace('$NUM_TOTAL', str(int_pass_case_number + \
                                                                          int_fail_case_number + \
                                                                          int_skip_case_number + \
                                                                          int_block_case_number))
        str_report_content = str_report_content.replace('$VERSION', 'InfraSIM')

        # generate report file
        self.str_report_file = os.path.join(self.str_work_directory, 'test_report.html')
        try:
            f_report = open(self.str_report_file, 'w')
        except:
            self.log('ERROR', 'Failed to create report file')
            return -1
        f_report.write(str_report_content)
        f_report.close()

        return 0

    def status(self):
        return self.str_status

    def cancel_case(self, str_case_name):
        for each_xmlnode_case in self.list_xmlnode_case:
            if each_xmlnode_case.find('script_name').text == str_case_name:
                if each_xmlnode_case.find('status').text == STATUS_QUEUED:
                    each_xmlnode_case.find('status').text = STATUS_COMPLETED
                    each_xmlnode_case.find('result').text = 'skip'
                    each_xmlnode_case.find('error_code').text = 'Cancelled by user'
                    each_xmlnode_case.find('start_time').text = str(datetime.datetime.now())
                    each_xmlnode_case.find('complete_time').text = str(datetime.datetime.now())
                    each_xmlnode_case.find('duration_time').text = '0'
                    return True
        return False


if __name__ == '__main__':
    pass
