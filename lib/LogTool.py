'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import datetime

class CLogTool():
    
    RAW_LOG_FILE_NOT_FOUND = 1
    RAW_LOG_FILE_OPEN_ERROR = 2
    FORMATTED_LOG_FILE_NOT_FOUND = 3
    FORMATTED_LOG_FILE_OPEN_ERROR = 4
    
    def __init__(self, str_console_log_file=None):
        self._str_console_log_file = str_console_log_file
        self._b_console_logging = False

    def reset(self):
        self._b_console_logging = False
        self._str_console_log_file = None
        
    def is_working(self):
        '''
        Track if the logging tool is working
        '''
        return self._b_console_logging
        
    def add_string_to_raw_log(self, str_line):
        '''
        used to add data in buffer into log file
        '''
        if not self._str_console_log_file:
            return 0
        if not self._b_console_logging:
            return 0
        if os.path.isfile(self._str_console_log_file) == False:
            f_raw_log = open(self._str_console_log_file, 'w')
        else:
            try:
                f_raw_log = open(self._str_console_log_file, 'ab')
            except:
                return CLogTool.RAW_LOG_FILE_OPEN_ERROR
        str_line = str_line.decode('ascii', 'ignore')
        str_line = str_line.replace('\n', '\n' + '[' + str(datetime.datetime.now()) + '] ')
        f_raw_log.write(str_line)
        f_raw_log.close()
        return 0

    def set_raw_log_file(self, str_raw_log_file_name):
        self._str_console_log_file = str_raw_log_file_name
        return 0

    def get_raw_log_file(self):
        return self._str_console_log_file
    
    def set_log(self, int_log_type = 3, b_enable = True, b_append = False):
        '''
        ##        int_log_type = 1 - Raw Logging configuration
        ##                       2 - Formatted Logging configuration
        ##                       3 - Both

        We have decided that only raw logging is supported
        
        So please only set the int_log_type to 1
        '''
        if int_log_type & 1 == 1:
            self._b_console_logging = b_enable
            if b_enable == True and b_append == False:
                if os.path.isfile(self._str_console_log_file):
                    return self.RAW_LOG_FILE_NOT_FOUND
                try:
                    f_raw_log_file = open(self._str_console_log_file, 'wb')
                except:
                    return self.RAW_LOG_FILE_OPEN_ERROR
                f_raw_log_file.close()
        return 