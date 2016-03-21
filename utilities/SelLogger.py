'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: SelLogger.py
[Author  ]: Eric Wang(eric.wang5@emc.com)
[Purpose ]: Implementation for SEL log dump by SSH
[Contains]: 
        
[History ]:
*********************************************************
 VERSION    EDITOR          DATE            COMMENT
*********************************************************
 R00        Eric Wang       10/22/2013      First Edition
*********************************************************
'''
import time
import os
import Env
from threading import Thread
from lib.IPMISend import *
from test.test_threading_local import target

class CSelLogger():
    '''
    #*****************************************************
    # [Author     ]: Eric Wang(eric.wang5@emc.com)           
    # [Description]: Provide a class to polling sel log
    # [Method     ]: 
    # [History    ]: First edition by Eric Wang
    #*****************************************************
    '''
    def __init__(self, str_case_name, \
                 str_enclosure_id, \
                 str_case_start_time, \
                 str_sel_log_path, \
                 int_interval = 2, \
                 obj_ipmi_iol = None, \
                 str_sp_side = 'a'):
        
        self.str_sel_log_name = 'SEL' + '_' + str_case_name + '_' + str_enclosure_id + str_sp_side + '_' + str_case_start_time + '.log'
        self.str_sel_log_path = str_sel_log_path
        self.str_sel_log_full_path = os.path.join(self.str_sel_log_path, self.str_sel_log_name)
        self.int_interval = int_interval        #The SEL log polling interval
        self.b_quit = False         # Sel logger thread quit flag
        self.b_valid = True
        self.obj_ipmi_iol = obj_ipmi_iol
        self.str_sel_log_data = ''
        self.lst_full_sel_log = []        #every entry of this array is a dict of a whole SEL log include the extended log
        self.arr_log_entry = ('Record', 'Time', 'Next Record', 'Record Type', 'Record Revision', 'Generator', 'Sensor', \
                         'Sensor Type', 'Event', 'Event Data', 'Extended Revision', 'Extended Size', 'Extended Log')
        self.lst_matched_black_sel = []
        self.lst_matched_white_sel = []
        self.lst_matched_warning_sel = []
        self.int_matched_num = 0
        self.lst_matched_data = []
        self.__parse_info__()
        
    def __parse_info__(self):
        if not os.path.isdir(self.str_sel_log_path):
            self.b_valid = False
        if self.obj_ipmi_kcs == None:
            self.b_valid = False
            
    def get_sel_info(self):
        pass
    
    def clear_sel(self):
        if self.obj_ipmi_kcs.sel_command('SEL_CLEAR') != 0:
            time.sleep(2)
            return False
        else:
            time.sleep(2)
            return True
    
    def dump_sel_log(self):
        if self.obj_ipmi_kcs.sel_command('SEL_LIST') != 0:
            return False
        else:
            try:
                with open(self.str_sel_log_full_path, 'a') as f_log:
                    f_log.writelines('\n'.join(self.obj_ipmi_kcs.list_return))
                    f_log.writelines('\n')
                    return True
            except:
                return False
            
    def dump_sel_log_with_interval(self):
        self.clear_sel()
        while not self.b_quit:
            b_result = self.dump_sel_log()
            if not b_result:
                continue    # If one time dump sel fail, don't clear, and dump again.
            else:
                self.clear_sel()    # Dump success, clear sel.
                time.sleep(self.int_interval)   # Interval
        if not self.dump_sel_log():
            self.dump_sel_log()
        self.clear_sel()
        
    def dump_and_check_sel_log_with_interval(self):
        self.clear_sel()
        while not self.b_quit:
            b_result = self.dump_sel_log()
            if not b_result:
                continue    # If one time dump sel fail, don't clear, and dump again.
            else:
                # Place holder: Need to add check sel listed in black list
                self.clear_sel()    # Dump success, clear sel.
                time.sleep(self.int_interval)   # Interval
        if not self.dump_sel_log():
            self.dump_sel_log()
        self.clear_sel()
    
    def read_sel_log_file(self):
        try:
            with open(self.str_sel_log_full_path, 'r') as f_log:
                lst_sel_log = f_log.readlines()
                return True, lst_sel_log
        except:
            return False, []
        
    def parse_sel_log(self, lst_sel_log):
        lst_sel_log_formatted = []
        for entry in lst_sel_log:
            dict_sel_elem = {}
            lst_sel_elem = entry.strip('\n').split('|')
            if len(lst_sel_elem) != 6:
                continue
            dict_sel_elem['sel_id'] = lst_sel_elem[0].strip()
            dict_sel_elem['time'] = lst_sel_elem[1].lstrip(' ').rstrip(' ')
            dict_sel_elem['sensor_num'] = lst_sel_elem[2].strip()
            dict_sel_elem['sensor_type'] = lst_sel_elem[3].lstrip(' ').rstrip(' ')
            dict_sel_elem['event'] = lst_sel_elem[4].lstrip(' ').rstrip(' ')
            dict_sel_elem['event_data'] = lst_sel_elem[5].strip('\n').lstrip(' ').rstrip(' ')
            lst_sel_log_formatted.append(dict_sel_elem)
        return True, lst_sel_log_formatted
    
    def check_event_data_with_mask(self, str_resp_data, str_event_data, str_mask):
        '''
        #************************************************
        # [Author  ]: Eric Wang(eric.wang5@emc.com)        
        # [Function]: Check whether the response event data is expected
        # [Input   ]: Response event data, expected event data, event mask
        # [Output  ]: The return value
        # [History ]: First edition by Eric Wang
        #************************************************
        '''
        if (int(str_resp_data, 16) & int(str_mask, 16)) == int(str_event_data, 16):
            return True
        else:
            return False
    
    def check_matched_sel(self, str_sensor_num, \
                          lst_event_data_and_mask, \
                          str_time_start = ''):
        '''
        #***************************************************************************
        # [Author  ]: Eric Wang(eric.wang5@emc.com)        
        # [Function]: Check the matched sel log
        # [Input   ]: Sensor number, [event data[0], mask[0], ...]
        #             start time(09/22/2013 15:51:53), end time(09/22/2013 15:51:53)
        # [Output  ]: Matched number, matched list
        # [History ]: First edition by Eric Wang
        #***************************************************************************
        '''

        lst_all_sel_log_formatted = []
        self.int_matched_num = 0
        
        if not self.dump_sel_log():     #Dump before read, insure that the SEL log in the log file is the latest.
            return False
            
        b_result, lst_result = self.read_sel_log_file()
        if not b_result:
            return False
        else:
            b_result, lst_result = self.parse_sel_log(lst_result)
            if not b_result:
                return False
            else:
                lst_all_sel_log_formatted = lst_result
            
        str_event_data0 = lst_event_data_and_mask[0]
        str_event_mask0 = lst_event_data_and_mask[1]
        str_event_data1 = lst_event_data_and_mask[2]
        str_event_mask1 = lst_event_data_and_mask[3]
        str_event_data2 = lst_event_data_and_mask[4]
        str_event_mask2 = lst_event_data_and_mask[5]
        
        int_length = len(lst_all_sel_log_formatted)
        for i in range(int_length):
            if str_time_start != '':        # Check the SEL log after the time: str_time_start
                if self.lst_all_sel_log_formatted[i]['time'] >= str_time_start:
                    if int(self.lst_all_sel_log_formatted[i]['sensor_num'], 16) == int(str_sensor_num, 16):
                        lst_event_data = lst_all_sel_log_formatted[i]['event_data'].split(' ')
                        if len(lst_event_data) != 3:
                            continue
                        str_resp_event_data0 = lst_event_data[0]
                        str_resp_event_data1 = lst_event_data[1]
                        str_resp_event_data2 = lst_event_data[2]
                        if self.check_event_data_with_mask(str_resp_event_data0, str_event_data0, str_event_mask0) \
                            and self.check_event_data_with_mask(str_resp_event_data1, str_event_data1, str_event_mask1) \
                            and self.check_event_data_with_mask(str_resp_event_data2, str_event_data2, str_event_mask2):
                            self.int_matched_num += 1
                            self.lst_matched_data.append(lst_all_sel_log_formatted[i])
                    else:
                        continue
                else:
                    continue
            else:       # Check all of the SEL log
                if int(lst_all_sel_log_formatted[i]['sensor_num'], 16) == int(str_sensor_num, 16):
                    lst_event_data = lst_all_sel_log_formatted[i]['event_data'].split(' ')
                    if len(lst_event_data) != 3:
                        continue
                    str_resp_event_data0 = lst_event_data[0]
                    str_resp_event_data1 = lst_event_data[1]
                    str_resp_event_data2 = lst_event_data[2]
                    if self.check_event_data_with_mask(str_resp_event_data0, str_event_data0, str_event_mask0) \
                        and self.check_event_data_with_mask(str_resp_event_data1, str_event_data1, str_event_mask1) \
                        and self.check_event_data_with_mask(str_resp_event_data2, str_event_data2, str_event_mask2):
                        self.int_matched_num += 1
                        self.lst_matched_data.append(lst_all_sel_log_formatted[i])
                else:
                    continue
                
        return True
    
    def for_test(self):
        #self.create_logger()
        print 'wait 10 seconds'
        time.sleep(10)
        int_result = self.obj_ipmi_kcs.sel_command('SEL_LIST')
        print self.obj_ipmi_kcs
        print int_result
        print self.obj_ipmi_kcs.list_return
    
    def run(self):
        #self.thread_sellogger = Thread(target = self.dump_sel_log_with_interval)
        self.thread_sellogger = Thread(target = self.dump_sel_log_with_interval)
        self.thread_sellogger.start()
        
if __name__=='__main__':
    obj_test = CSelLogger('01', '01', '01', '01', '01', '01', '01', '01', '01', '01')
    b_result, lst_result = obj_test.check_matched_sel('0x00', ['0x80', '0xff', '0x05', '0xff', '0xff', '0xff'])
    print b_result
    print lst_result