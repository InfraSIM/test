'''
#*********************************************************
# Copyright 2013 EMC Inc.
#
# [Filename]: SelLogger.py
# [Author  ]: Eric Wang(eric.wang5@emc.com)
# [Purpose ]: Implementation for SEL log dump by SSH
# [Contains]: 
#           
# [History ]:
#*********************************************************
# VERSION    EDITOR          DATE            COMMENT
#*********************************************************
# R00        Eric Wang       10/22/2013      First Edition
#*********************************************************
'''
import time
import os
from threading import Thread, RLock, Event
import xml.etree.ElementTree as ET
from lib.Logger import CLogger
import copy
import traceback

obj_lock_for_sel = RLock()


def deco_add_lock(func):
    '''
    Edited by Eric Wang
    This function is a decorator, used to add lock for every actions.
    '''
    global obj_lock_for_sel
    def new_func(*args):
        obj_lock_for_sel.acquire()
        try:
            return func(*args)
        finally:
            obj_lock_for_sel.release()
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    return new_func


class CSelLogger(CLogger):
    '''
    #*****************************************************
    # [Author     ]: Eric Wang(eric.wang5@emc.com)           
    # [Description]: Provide a class to polling sel log
    # [Method     ]: 
    # [History    ]: First edition by Eric Wang
    #*****************************************************
    '''
    
    LIST_BLACK_LIST = []
    
    
    def __init__(self, case_name, \
                 enclosure_id, \
                 case_start_time, \
                 sel_file_path, \
                 int_interval = 5, \
                 obj_ipmi_iol = None, \
                 str_sp_side = 'a'):
        CLogger.__init__(self)
        case_id=case_name.split('_')[0]
        db_file_name = 'sel_{}_{}{}_{}.db'.format(case_id, enclosure_id,
                                                  str_sp_side, case_start_time)
        self.sel_file_path=sel_file_path
        self.sel_db_full_path = os.path.join(sel_file_path, db_file_name)
        # The SEL log polling interval
        self.int_interval = int_interval

        # Setting true means that Sel logger thread quit flag
        self.b_quit = False

        # Setting true means that Sel logger will stop dumping SEL from NVRAM.
        # Added by Eric, 06/17/2014
        self.b_stop_dump = False

        # Flag which marks reserving the SELs in memory during SEL checking.
        # Added by Eric, 06/17/2014
        self.b_reserve_sel_in_memory = False

        self.b_valid = True
        self.b_error_warning_sel_occur = False

        # Forrest, True - clear_sel() will do its work;
        #          False - clear_sel() will skip clear
        self.b_clear_nvram = True

        # This flag is used to respond the external sel dump command.
        # Added by Eric, 10/28/2014
        self.b_dump_flag_from_external = False

        self.obj_ipmi_iol = obj_ipmi_iol
        self.list_error_warning_sel = []
        self.list_current_dump_sel = []

        # SEL list which will contain the SELs during the action 
        #  'checking matched SEL'.
        # Added by Eric, 06/17/2014
        self.list_sel_reserved_in_memory = []

        # Store the expected error SELs.
        # Added by Eric, 06/17/2014
        self.list_expected_error_sel = []

        # Store the black sel list (xml node).
        # Added by Eric
        self.list_black_sel_xml = []

        # Store normal SELs which are not matched in the black list.
        # Added by Eric, 07/01/2014
        self.list_normal_sel = []

        # Store the formatted black sel list.
        # Added by Eric, 07/02/2014

        self.list_formatted_black_sel = []
        self.int_last_dump_sel_count = 0
        self.int_new_dump_sel_count = 0
        self.event_reserve_sel_in_memory = Event()
        self.event_stop_dump_clear_sel = Event()

        # This event instance will be used to trigger dump by external command.
        # Added by Eric, 20/28/2014
        self.event_trigger_dump = Event()

        self.__parse_info__()

#        if CSelLogger.LIST_BLACK_LIST == []:
#            # to be compatible with previous version
#            self.get_black_sel_list()
#            self.parse_black_sel_list()
#        else:
#            self.list_formatted_black_sel = CSelLogger.LIST_BLACK_LIST[:]

    def __parse_info__(self):
        if not os.path.isdir(self.sel_file_path):
            self.b_valid = False
        if self.obj_ipmi_iol is None:
            self.b_valid = False

    def clear_sel(self):
        int_retry = 10
        b_sel_cleared = False
        iol = self.obj_ipmi_iol
        
        for i in range(int_retry):
            if self.b_clear_nvram:
                ret, resp = iol.ipmitool_standard_cmd('sel clear')
                if ret != 0:
                    time.sleep(2)
                    continue
                else:
                    time.sleep(2)
                    b_sel_cleared = True
                    break
            else:
                break
            
        return b_sel_cleared

    def reserve_sel(self):
        int_retry = 10
        
        for i in range(int_retry):
            ret, resp = self.obj_ipmi_iol.ipmitool_standard_cmd('raw 0x0a 0x42')
            list_return = resp.split()
            if ret != 0:
                time.sleep(2)
                continue
            else:
                try:
                    int(list_return[0], 16)
                    int(list_return[1], 16)
                except ValueError:
                    self.log('WARNING', 'Reservation ID is not digit: %s' % resp)
                    continue
                except Exception:
                    self.log('WARNING', 'Reservation is invalid: %s' % resp)
                    continue
                return resp

    def get_black_sel_list(self):
        '''
        # [Author  ]: Eric Wang(eric.wang5@emc.com)
        # [Function]: Get the black sel list from the black sel list file.
        # [Input   ]: None
        # [Output  ]: True or False.
        # [History ]: First edition by Eric Wang
        '''
        self.log('INFO', 'Load black list XML file')
        black_list_full_path = os.path.join(os.path.abspath('.'), 'pub', 'SELBlackList.xml')
        if not os.path.isfile(black_list_full_path):
            self.log('ERROR', 'Can not find SEL black list')
            return -1
        try:
            et_black_list = ET.parse(black_list_full_path)
        except:
            self.log('ERROR', 'Parse SEL black list fail')
            return -2
        # Parse the SEL node in the black sel list
        self.list_black_sel_xml = et_black_list.findall('sel_entry')
        self.log('INFO', 'Success loaded black list XML file')

    def parse_black_sel_list(self):
        '''
        # [Author  ]: Eric Wang(eric.wang5@emc.com)
        # [Function]: Parse black sel list.
        # [Input   ]: None
        # [Output  ]: True or False.
        # [History ]: First edition by Eric Wang
        '''
        for obj_sel_xml_node in self.list_black_sel_xml:
            self.list_formatted_black_sel.append(CSelLogger.parse_xml_sel_entry(obj_sel_xml_node))
        CSelLogger.LIST_BLACK_LIST = copy.deepcopy(self.list_formatted_black_sel)
    
    def dump_and_clear_sel(self):

        # Retry times: 10 
        b_done = False
        int_retry = 10
        iol = self.obj_ipmi_iol
        for i in range(int_retry):
            # Get reservation ID first
            str_reservation_id = self.reserve_sel()
            # if not str_reservation_id == '' or str_reservation_id == None:
            if str_reservation_id == '' or str_reservation_id is None:
                return False
            else:
                list_str_id = str_reservation_id.split()
                new_id = '0x%s 0x%s' % (list_str_id[0], list_str_id[1])
            
            # Dump SEL
            b_dump = False
            ret = -1
            lst_ret = []
            # Dump SEL by modified ipmitool with 10 retry
            for i in range(10):
                self.list_current_dump_sel = []
                cmd_raw_sel='sel raw %s' % self.sel_db_full_path
                ret, lst_ret=iol.ipmitool_standard_cmd(cmd_raw_sel)
                if ret != 0:
                    # ipmi tool failed; just delay and retry.
                    time.sleep(1)
                    continue
                else:
                    b_dump = True
                    break
            # Handle ipmitool response string
            lst_ret = lst_ret.strip().splitlines()
            for i in range(len(lst_ret)):
                lst_ret[i] = lst_ret[i].strip().lower()

            self.list_current_dump_sel = lst_ret
            
            if not b_dump:
                msg='Fail to dump SEL by ipmitool via IOL. '
                msg+='SEL generated during this period will lose track!'
                self.log('WARNING', msg)
                continue

            # Clear SEL
            try:
                # Use raw command to clear SEL
                clean_sel_command='raw 0x0a 0x47 %s 0x43 0x4c 0x52 0xaa'%new_id
                for j in range(3):
                    ret, resp = iol.ipmitool_standard_cmd(clean_sel_command) 
                    if ret != 0:
                        # If reservation ID mismatch, continue, retry
                        if resp.find('rsp=0xc5') >= 0:
                            raise Exception('0xc5')
                        elif resp.find('Unable to establish IPMI v2 / RMCP+ session') >= 0:
                            # If LAN is not available, try to clear SEL with the same
                            # reservation ID again
                            continue
                        else:
                            return False
                    else:
                        b_done = True
                        break 
                else:
                    continue
            except Exception, e:
                if e.args[0] == '0xc5':
                    # If completion code is 0xC5, SEL has been changed 
                    # and need to be reserved again
                    continue
                else:
                    return False

            # Write SEL to cache
            if self.b_reserve_sel_in_memory:
                if not self.event_reserve_sel_in_memory.isSet():
                    self.event_reserve_sel_in_memory.set()
                self.list_sel_reserved_in_memory.extend(self.list_current_dump_sel)
                break
            else:
                if self.event_reserve_sel_in_memory.isSet():
                    self.event_reserve_sel_in_memory.clear()
                break
            
        if not b_done:
            msg='Fail to clean SEL because reservation ID is always changing.'
            msg+=' There is always new SEL recorded during this time'
            self.log('WARNING', msg)
            return False
        else:
            return True

    def dump_and_clear_sel_with_black_list_checking(self):
        if not self.dump_and_clear_sel():
            return False
        
        if not self.check_sel_with_black_list(self.list_current_dump_sel):
            return False
        
        return True
    
    def parse_general_sel_entry(self, str_general_sel_entry):
        '''
        # [Author  ]: Eric Wang(eric.wang5@emc.com)
        # [Function]: Parse the general SEL entry.
        # [Input   ]: A general sel entry (string format)
        # [Output  ]: Result(0,1), the parsed sel entry dict.
        # [History ]: First edition by Eric Wang
        '''
        # Parse given sel entry
        dict_parsed_sel_entry = {}
        list_sel_entry = str_general_sel_entry.split(' ')
        
        try:
            str_generator_id = list_sel_entry[8].lower() + list_sel_entry[7].lower()
            dict_parsed_sel_entry['generator_id'] = str_generator_id
        except:
            self.log('ERROR', 'Parse sel generator ID fail')
            dict_parsed_sel_entry['generator_id'] = ''
        try:
            str_sensor_number = list_sel_entry[11].lower()
            dict_parsed_sel_entry['sensor_number'] = str_sensor_number
        except:
            self.log('ERROR', 'Parse sel sensor number fail')
            dict_parsed_sel_entry['sensor_number'] = ''
        try:
            str_sensor_type = list_sel_entry[10].lower()
            dict_parsed_sel_entry['sensor_type'] = str_sensor_type
        except:
            self.log('ERROR', 'Parse sel sensor type fail')
            dict_parsed_sel_entry['sensor_type'] = ''
        try:
            str_event_type = list_sel_entry[12].lower()
            dict_parsed_sel_entry['event_type'] = str_event_type
        except:
            self.log('ERROR', 'Parse sel event type fail')
            dict_parsed_sel_entry['event_type'] = ''
        try:
            list_event_data = [x.lower() for x in list_sel_entry[13:16]]
            dict_parsed_sel_entry['event_data'] = list_event_data
        except:
            self.log('ERROR', 'Parse sel event data fail')
            dict_parsed_sel_entry['event_data'] = []
        try:
            str_extended_sel = str_general_sel_entry[57:]
            dict_parsed_sel_entry['extended_sel'] = str_extended_sel
        except:
            self.log('WARNING', 'No extended sel')
            dict_parsed_sel_entry['extended_sel'] = ''
        return dict_parsed_sel_entry
    
    @staticmethod
    def parse_xml_sel_entry(obj_sel_xml_node):
        '''
        # [Author  ]: Eric Wang(eric.wang5@emc.com)
        # [Function]: Parse the XML SEL entry.
        # [Input   ]: A XML sel entry (XML node format)
        # [Output  ]: True or False.
        # [History ]: First edition by Eric Wang
        '''
        # Parse black sel xml node
        dict_parsed_sel_entry = {}
        try:
            str_generator_id = obj_sel_xml_node.find('generator_id').text[-2:].lower()
            dict_parsed_sel_entry['generator_id'] = str_generator_id
        except:
            dict_parsed_sel_entry['generator_id'] = ''
        try:
            str_source = obj_sel_xml_node.find('source').text
            dict_parsed_sel_entry['source'] = str_source
        except:
            dict_parsed_sel_entry['source'] = ''
        try:
            str_sensor_number = obj_sel_xml_node.find('sensor_number').text[-2:].lower()
            dict_parsed_sel_entry['sensor_number'] = str_sensor_number
        except:
            dict_parsed_sel_entry['sensor_number'] = ''
        try:
            str_sensor_type = obj_sel_xml_node.find('sensor_type').text[-2:].lower()
            dict_parsed_sel_entry['sensor_type'] = str_sensor_type
        except:
            dict_parsed_sel_entry['sensor_type'] = ''
        try:
            str_event_type = obj_sel_xml_node.find('event_type').text[-2:].lower()
            dict_parsed_sel_entry['event_type'] = str_event_type
        except:
            dict_parsed_sel_entry['event_type'] = ''
        try:
            str_event_data1 = obj_sel_xml_node.find('event_data_1').text[-2:].lower()
            str_event_data2 = obj_sel_xml_node.find('event_data_2').text[-2:].lower()
            str_event_data3 = obj_sel_xml_node.find('event_data_3').text[-2:].lower()
            list_event_data = [str_event_data1, str_event_data2, str_event_data3]
            dict_parsed_sel_entry['event_data'] = list_event_data
        except:
            dict_parsed_sel_entry['event_data'] = []
        try:
            str_event_data1_description = obj_sel_xml_node.find('event_data_1_description').text
            str_event_data2_description = obj_sel_xml_node.find('event_data_2_description').text
            str_event_data3_description = obj_sel_xml_node.find('event_data_3_description').text
            dict_parsed_sel_entry['event_data_description'] += \
                (' ->: ' + str_event_data1_description) if str_event_data1_description != 'None' else ''
            dict_parsed_sel_entry['event_data_description'] += \
                (' ->: ' + str_event_data2_description) if str_event_data2_description != 'None' else ''
            dict_parsed_sel_entry['event_data_description'] += \
                (' ->: ' + str_event_data3_description) if str_event_data3_description != 'None' else ''
        except:
            dict_parsed_sel_entry['event_data_description'] = ''
        try:
            str_extended_sel = obj_sel_xml_node.find('extended_sel').text
            if str_extended_sel == None:
                dict_parsed_sel_entry['extended_sel'] = ''
            else:
                dict_parsed_sel_entry['extended_sel'] = str_extended_sel
        except:
            dict_parsed_sel_entry['extended_sel'] = ''
        return dict_parsed_sel_entry
    
    def check_matched_black_sel(self, dict_given_sel_entry, dict_black_sel_entry):
        '''
        # Author:   Edited by Eric
        # Function: This function is used to check whether a given 
        #           SEL is matched with SELs in black list
        # Input:    A given SEL entry, a black sel xml node
        # Output:   0 or 1 or -1
        #           0: no matched; 1: matched; -1: execute error
        '''
        # Check the given sel and the black sel
        if int(dict_given_sel_entry['sensor_number'], 16) != int(dict_black_sel_entry['sensor_number'], 16):
            return 0
        if int(dict_given_sel_entry['generator_id'], 16) != int(dict_black_sel_entry['generator_id'], 16):
            return 0
        if int(dict_given_sel_entry['sensor_type'], 16) != int(dict_black_sel_entry['sensor_type'], 16):
            return 0
        if int(dict_given_sel_entry['event_type'], 16) != int(dict_black_sel_entry['event_type'], 16):
            return 0
        if dict_given_sel_entry['event_data'] != dict_black_sel_entry['event_data']:
            return 0
        if dict_black_sel_entry['extended_sel'].find(dict_given_sel_entry['extended_sel']) == -1:
            if dict_given_sel_entry['extended_sel'].find(dict_black_sel_entry['extended_sel']) == -1:
                return 0
        # Check whether the sel is in white list.
        for str_expected_error_sel in self.list_expected_error_sel:
            dict_error_sel = self.parse_general_sel_entry(str_expected_error_sel)
            if dict_given_sel_entry['sensor_number'] != dict_error_sel['sensor_number']:
                continue
            if dict_given_sel_entry['generator_id'] != dict_error_sel['generator_id']:
                continue
            if dict_given_sel_entry['sensor_type'] != dict_error_sel['sensor_type']:
                continue
            if dict_given_sel_entry['event_type'] != dict_error_sel['event_type']:
                continue
            if dict_given_sel_entry['event_data'] != dict_error_sel['event_data']:
                continue
            if dict_error_sel['extended_sel'] == '' or dict_given_sel_entry['extended_sel'] == '':
                if dict_error_sel['extended_sel'] == '' and dict_given_sel_entry['extended_sel'] == '':
                    pass
                else:
                    continue
            else:
                if dict_error_sel['extended_sel'].find(dict_given_sel_entry['extended_sel']) == -1:
                    if dict_given_sel_entry['extended_sel'].find(dict_error_sel['extended_sel']) == -1:
                        continue
            return 0
        return 1
    
    def check_sel_with_black_list(self, list_given_sel):
        '''
        Edited by Eric
        This function is used to check the target sel with the black sel list.
        Input: SEL list needed to be checked.
        Output: -1 : error
                matched number : the count that matched with black list.
                Example: Return -1, error happens
                         Return 0, no matched with black list
                         Return 1, one sel matched with black list
        '''
        int_given_sel_list_length = len(list_given_sel)
        i = 0
        err_msg = 'Error: Unable to establish IPMI v2 / RMCP+ session'
        while i < int_given_sel_list_length: 
            if list_given_sel[i].strip()==err_msg:
                self.log('WARNING', err_msg)
                i += 1
                continue
            # Extended SEL don't end with 00 00
            if not list_given_sel[i].strip().endswith('00 00'):
                try:
                    list_sel_array = list_given_sel[i].strip().split()
                    int_ext_sel_length = int(list_sel_array[-1] + list_sel_array[-2], 16)
                    if len(list_given_sel[i + 1].strip('\n').split()) != int_ext_sel_length:
                        self.log('WARNING', 'It is not a SEL entry, skip.')
                        i += 1
                        continue
                    else:
                        pass
                except:
                    self.log('WARNING', 'It is not a SEL entry, skip it.')
                    i += 1
                    continue
                list_given_sel[i] = list_given_sel[i] + ' ' + list_given_sel[i + 1]
                list_to_checked_sel = list_given_sel[i].split()
                list_to_checked_sel[0:2] = ['00', '00']
                list_to_checked_sel[3:7] = ['00', '00', '00', '00']
                str_to_checked_sel = ' '.join(list_to_checked_sel)
                if str_to_checked_sel in self.list_normal_sel:
                    i += 2
                    continue
                dict_given_sel_entry = self.parse_general_sel_entry(list_given_sel[i])
                for dict_black_sel_entry in self.list_formatted_black_sel:
                    dict_error_info = {}
                    int_result = self.check_matched_black_sel(dict_given_sel_entry, dict_black_sel_entry)
                    if int_result == 0:
                        continue
                    elif int_result == 1:
                        dict_error_info['raw_sel'] = list_given_sel[i]
                        dict_error_info['gen_id'] = dict_black_sel_entry['generator_id']
                        dict_error_info['source'] = dict_black_sel_entry['source']
                        dict_error_info['description'] = dict_black_sel_entry['event_data_description']
                        self.list_error_warning_sel.append(dict_error_info)
                        self.b_error_warning_sel_occur = True
                        i += 2
                        break
                    else:
                        self.log('ERROR', 'Check matched black sel fail')
                        return -1
                else:
                    list_have_checked_sel = list_given_sel[i].split()
                    list_have_checked_sel[0:2] = ['00', '00']
                    list_have_checked_sel[3:7] = ['00', '00', '00', '00']
                    str_have_checked_sel = ' '.join(list_have_checked_sel)
                    self.list_normal_sel.append(str_have_checked_sel)
                    i += 2
            # Normal SEL end with 00 00
            else:
                list_to_checked_sel = list_given_sel[i].split()
                list_to_checked_sel[0:2] = ['00', '00']
                list_to_checked_sel[3:7] = ['00', '00', '00', '00']
                str_to_checked_sel = ' '.join(list_to_checked_sel)
                if str_to_checked_sel in self.list_normal_sel:
                    i += 1
                    continue
                dict_given_sel_entry = self.parse_general_sel_entry(list_given_sel[i])
                for dict_black_sel_entry in self.list_formatted_black_sel:
                    dict_error_info = {}
                    int_result = self.check_matched_black_sel(dict_given_sel_entry, dict_black_sel_entry)
                    if int_result == 0:
                        continue
                    elif int_result == 1:
                        dict_error_info['raw_sel'] = list_given_sel[i]
                        dict_error_info['gen_id'] = dict_black_sel_entry['generator_id']
                        dict_error_info['source'] = dict_black_sel_entry['source']
                        dict_error_info['description'] = dict_black_sel_entry['event_data_description']
                        self.list_error_warning_sel.append(dict_error_info)
                        self.b_error_warning_sel_occur = True
                        i += 1
                        break
                    else:
                        self.log('ERROR', 'Check matched black sel fail')
                        return -1
                else:
                    list_have_checked_sel = list_given_sel[i].split()
                    list_have_checked_sel[0:2] = ['00', '00']
                    list_have_checked_sel[3:7] = ['00', '00', '00', '00']
                    str_have_checked_sel = ' '.join(list_have_checked_sel)
                    self.list_normal_sel.append(str_have_checked_sel)
                    i += 1
        
        return 0
               
    def dump_sel_with_interval(self):
        try:
            # Check whether the SEL logger quit flag is set.
            while not self.b_quit:
                if not self.b_stop_dump:
                    # Check whether the dump sel flag is set from external
                    if self.b_dump_flag_from_external:
                        self.dump_and_clear_sel_with_black_list_checking()
                        if not self.event_trigger_dump.is_set():
                            self.event_trigger_dump.set()
                            self.b_dump_flag_from_external = False
                            time.sleep(self.int_interval)
                    else:
                        self.dump_and_clear_sel_with_black_list_checking()
                        time.sleep(self.int_interval)
                else:
                    if not self.event_stop_dump_clear_sel.is_set():
                        self.event_stop_dump_clear_sel.set()
                    time.sleep(self.int_interval)
            self.dump_and_clear_sel_with_black_list_checking()
        except:
            msg='Unexpected exception in Sellogger:%s'%traceback.format_exc()
            self.log('ERROR', msg)

    def run(self):
        self.log('INFO', 'SelLogger thread start...')
        self.thread_sellogger = Thread(target = self.dump_sel_with_interval)
        self.thread_sellogger.setDaemon(True)
        self.thread_sellogger.start()
    
    def join(self, int_timeout = 30):
        self.thread_sellogger.join(int_timeout)
    
    def is_alive(self):
        return self.thread_sellogger.isAlive()

    def clear_cached_sel(self):
        '''
        Clear cached SEL(reserved in memory)
        Author: Shark
        '''
        self.list_sel_reserved_in_memory = []

if __name__ == '__main__':
    pass
