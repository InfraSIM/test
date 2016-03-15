'''
 Copyright 2013 EMC Inc.
'''
import xml.etree.ElementTree as ET
import datetime
import ctypes
import platform
PLATFORM=platform.system()

LOG_LEVEL_WARNING = 'WARNING'
LOG_LEVEL_ERROR = 'ERROR'
LOG_LEVEL_INFO = 'INFO'
LOG_LEVEL_DEBUG = 'DEBUG'


class Color:
    '''
    See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    for information on Windows APIs.
    '''
    #color for Windows
    STD_OUTPUT_HANDLE = -11

    FOREGROUND_BLACK = 0x0
    FOREGROUND_BLUE = 0x01 # text color contains blue.
    FOREGROUND_GREEN = 0x02 # text color contains green.
    FOREGROUND_RED = 0x04 # text color contains red.
    FOREGROUND_INTENSITY = 0x08 # text color is intensified.

    BACKGROUND_BLUE = 0x10 # background color contains blue.
    BACKGROUND_GREEN = 0x20 # background color contains green.
    BACKGROUND_RED = 0x40 # background color contains red.
    BACKGROUND_INTENSITY = 0x80 # background color is intensified.

    #color for linux
    DARKGRAY = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


    def set_cmd_color(self, color):
        '''
        (color) -> bit
        Example: set_cmd_color(self.FOREGROUND_RED | self.FOREGROUND_GREEN \
                                | self.FOREGROUND_BLUE | self.FOREGROUND_INTENSITY)
        '''
        if PLATFORM=='Windows':
            handle = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
            bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
        elif PLATFORM=='Linux':
            #do nothing for linux for the moment.
            return True
        elif 'CYGWIN' in PLATFORM:
            #do nothing for cygwin for the moment.
            return True
        else:
            raise Exception('Unsupported platform: %s'%PLATFORM)
        return bool


    def reset_color(self):
        white=self.FOREGROUND_RED | self.FOREGROUND_GREEN | self.FOREGROUND_BLUE
        self.set_cmd_color(white)


    def print_red_text(self, print_text):
        if PLATFORM == 'Linux' or 'CYGWIN' in PLATFORM:
            print '%s%s%s'%(self.RED, print_text, self.ENDC)
        elif PLATFORM == 'Windows':
            intense_red=self.FOREGROUND_RED | self.FOREGROUND_INTENSITY
            self.set_cmd_color(intense_red)
            print print_text
            self.reset_color()


    def print_yellow_text(self, print_text):
        if PLATFORM == 'Linux' or 'CYGWIN' in PLATFORM:
            print '%s%s%s'%(self.YELLOW, print_text, self.ENDC)
        elif PLATFORM == 'Windows':
            yellow = self.FOREGROUND_GREEN | self.FOREGROUND_RED
            intense_yellow = yellow | self.FOREGROUND_INTENSITY
            self.set_cmd_color(intense_yellow)
            print print_text
            self.reset_color()


    def print_cyan_text(self, print_text):
        if PLATFORM == 'Linux' or 'CYGWIN' in PLATFORM:
            print '%s%s%s'%(self.CYAN, print_text, self.ENDC)
        elif PLATFORM == 'Windows':
            cyan=self.FOREGROUND_GREEN | self.FOREGROUND_BLUE
            self.set_cmd_color(cyan)
            print print_text
            self.reset_color()

    def print_default_text(self, print_text):
        print print_text


class CLogger():
    '''
    print log to screen and save log to file.
    '''
    LIST_LOG_LEVEL_SUPPORT = (LOG_LEVEL_DEBUG, \
                              LOG_LEVEL_ERROR, \
                              LOG_LEVEL_INFO, \
                              LOG_LEVEL_WARNING)


    def __init__(self):
        self.obj_logger = None
        self.b_print = True


    def log(self, str_level, str_message):

        str_log_time = str(datetime.datetime.now())

        # Check level
        str_level = str_level.upper()
        if str_level not in self.LIST_LOG_LEVEL_SUPPORT:
            str_level = LOG_LEVEL_INFO

        # print to console when the b_print switch is open
        if self.b_print:
            clr = Color()
            if self.obj_logger:
                str_log_origin = self.obj_logger.name
            else:
                str_log_origin = 'puffer'
            # make shorter case name
            if '_' in str_log_origin:
                lst_origin_section = str_log_origin.split('_')
                if lst_origin_section[1] in ['uefi', 'bmc']:
                    str_log_origin = '_'.join([lst_origin_section[0][1:], lst_origin_section[2]])
            if len(str_log_origin) > 20:
                str_log_origin = str_log_origin[0:17] + '...'
            # filling tailing zero if millisecond is all zeros and truncated by o/s
            if len(str_log_time) < 26:
                str_log_time = str_log_time + '.000000'
            str_out = '%12s  %20s:  %s' % (str_log_time[11:23], str_log_origin, str_message)
            if str_level == LOG_LEVEL_INFO:
                clr.print_default_text(str_out)
            elif str_level == LOG_LEVEL_ERROR:
                clr.print_red_text(str_out)
            elif str_level == LOG_LEVEL_WARNING:
                clr.print_yellow_text(str_out)
            elif str_level == LOG_LEVEL_DEBUG:
                clr.print_cyan_text(str_out)

        if self.obj_logger == None:
            return

        # remove non-ASCII code
        str_message = str_message.decode('ascii', 'ignore')

        # Logging
        str_xmlnode_eventlog = '''
        <event_log>
            <source />
            <level />
            <time />
            <message />
        </event_log>
        '''

        obj_xmlnode_eventlog = ET.fromstring(str_xmlnode_eventlog)
        obj_xmlnode_eventlog.find('source').text = self.obj_logger.name
        obj_xmlnode_eventlog.find('level').text = str_level
        obj_xmlnode_eventlog.find('time').text = str_log_time
        obj_xmlnode_eventlog.find('message').text = str_message
        self.obj_logger.info(ET.tostring(obj_xmlnode_eventlog))

    def set_logger(self, obj_logger):
        '''
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Set the logger object of the interface
        [Input   ]:
        [Output  ]:
        '''
        self.obj_logger = obj_logger


if __name__ == '__main__':
    raise Exception('This module is not callable.')

