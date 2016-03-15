'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from telnetlib import Telnet
from threading import Lock
import os
import time

#constant
KEY_ENTER = chr(13)
KEY_ESC = chr(27)
PROMPT_USER = 'User Name :'
PROMPT_PSW = 'Password  :'
PROMPT_INPUT = '> '

ACTION_IMMEDIATE_ON = 1
ACTION_IMMEDIATE_OFF = 2
ACTION_IMMEDIATE_REBOOT = 3
ACTION_DELAY_ON = 4
ACTION_DELAY_OFF = 5
ACTION_DELAY_REBOOT = 6


b_apc_debug_print = True
def apc_debug_print(str_msg):
    if b_apc_debug_print == True:
        print str_msg
        
class CAPC():
    
    def __init__(self, str_ip, int_port = 23, str_user = "apc", str_pwd = "apc"):
        self.str_ip = str_ip
        while self.str_ip.find('.0')>-1:
            apc_debug_print(self.str_ip)
            self.str_ip = self.str_ip.replace('.0', '.')
        self.int_port = int_port
        self.str_user = str_user
        self.str_pwd = str_pwd
        try:
            self.obj_telnet = Telnet(self.str_ip, self.int_port)
        except:
            print '[ERROR][APC]: Failed to connect to the APC server'
            self.obj_telnet = None
        self.lock_occupied = Lock()
        self.list_control_menu = ['Device Manager', \
                            'Outlet Management', \
                            'Outlet Control/Configuration']
        self.list_control_index = ['1','2','1','','1']
        self.b_log = False
        self.str_log_file = ''
        self.str_log_mode = 'w'
        self.b_print = False
        self.int_find = -1
        
    def __del__(self):
        pass
    
    def back_to_root(self):
        int_try = 0
        while(1):
            self.send_command(KEY_ESC)
            str_result = self.read_until(PROMPT_INPUT, 3)
            if str_result.find('Control Console'):
                break
            else:
                int_try +=1
                if int_try > 100:
                    return False
        return True
    
    def connect(self):
        while(1):
            self.obj_telnet.open(self.str_ip, self.int_port)      
            self.send_command(KEY_ENTER)
            #self.read_until([PROMPT_INPUT, PROMPT_PSW, PROMPT_USER], 3)
            try:
                self.read_until([PROMPT_INPUT, PROMPT_PSW, PROMPT_USER], 3)
            except:
                continue
            break
        return True
    
    def send_command(self, str_command):
        self.obj_telnet.write(str_command)
    
    def read_until(self, list_wait, int_time_out = None):
        str_get = ''
        res = [-1, None, '']
        if str(type(list_wait)) == "<type 'str'>":
            res =  self.obj_telnet.read_until(list_wait, int_time_out)
            if not res.find(list_wait):
                str_get = ''
                self.int_find = -1
            str_get = res
            self.int_find = 1    
        elif str(type(list_wait)) == "<type 'list'>":
            res =  self.obj_telnet.expect(list_wait, int_time_out)
            self.int_find = res[0] + 1
            str_get = res[2]
        if self.b_log:
            if not os.path.isdir(self.str_log_file):
                while(1):
                    try:
                        f_log = open(self.str_log_file,self.str_log_mode)
                    except:
                        print '[WARNING][CAPC][READUNTIL]: can not open log file(%s)' %self.str_log_file
                        self.b_log = False
                        break
                    f_log.write(str_get)
                    break
        if self.b_print:
            print str_get
        return str_get
        
    def log_on(self, str_user = 'apc', str_psw = 'apc'):
        self.connect()
        self.send_command(KEY_ENTER)
        while(1):     
            try:
                self.read_until([PROMPT_INPUT, PROMPT_PSW, PROMPT_USER], 3)
            except:
                return False
            if self.int_find == 1:
                break
            elif self.int_find == 2:
                self.send_command(str_psw + KEY_ENTER)
            elif self.int_find == 3:
                self.send_command(str_user + KEY_ENTER)
            else:
                pass
        return True
    
    def power_cycle(self, list_port, int_delay):
        self.power_control(list_port, ACTION_IMMEDIATE_OFF)
        time.sleep(int_delay)
        self.power_control(list_port, ACTION_IMMEDIATE_ON)
    
    def power_control(self, list_port, int_action):
        if int_action < 1 or int_action > 6:
            self.disconnect()
            return False
        b_by_port_number = True
        for str_entry in list_port:
            if not str(str_entry).isdigit():
                b_by_port_number = False
        self.log_on()
        self.goto_control_page()
        if b_by_port_number == True:
            for str_entry in list_port:
                str_entry  = str(str_entry)
                self.send_command(str_entry + KEY_ENTER)
                self.read_until(PROMPT_INPUT, 3)
                self.send_command('1' + KEY_ENTER)
                self.read_until(PROMPT_INPUT, 3)
                self.send_command(str(int_action) + KEY_ENTER)
                self.read_until('<ENTER> to cancel :', 3)
                self.send_command('yes'+KEY_ENTER)
                self.read_until('continue...', 3)
                self.send_command(KEY_ENTER)
                self.send_command(KEY_ESC)
                self.read_until(PROMPT_INPUT, 3)
                self.send_command(KEY_ESC)
                self.read_until(PROMPT_INPUT, 3)
        else:
            b_find = False
            if str(type(list_port)) == "<type 'str'>":
                list_port = [list_port, '']
            for str_entry in list_port:
                if str_entry  == '':
                    continue
                self.send_command(KEY_ENTER)
                str_result = self.read_until(PROMPT_INPUT, 3)
                while(1):
                    str_menu_index = self.get_menu_index(str_result, str_entry)
                    if str_menu_index == '':
                        if b_find == False:
                            self.disconnect()
                            return False
                        else:
                            break
                    else:
                        b_find = True
                    self.send_command(str_menu_index + KEY_ENTER)
                    self.read_until(PROMPT_INPUT, 3)
                    self.send_command('1' + KEY_ENTER)
                    self.read_until(PROMPT_INPUT, 3)
                    self.send_command(str(int_action) + KEY_ENTER)
                    self.read_until('<ENTER> to cancel :', 3)
                    self.send_command('yes'+KEY_ENTER)
                    self.read_until('continue...', 3)
                    self.send_command(KEY_ENTER)
                    self.send_command(KEY_ESC)
                    self.read_until(PROMPT_INPUT, 3)
                    self.send_command(KEY_ESC)
                    self.read_until(PROMPT_INPUT, 3)
                    pos = str_result.find(str_entry)
                    str_result = str_result[pos+len(str_entry)+1:]
        return True   
                
    def goto_control_page(self):
        while(1):
            self.back_to_root()
            str_result = self.read_until(PROMPT_INPUT, 3)
            int_pos = 0
            for str_entry in self.list_control_menu:
                if str_result.find(str_entry):
                    break
            b_find = True
            while(int_pos < len(self.list_control_menu)):
                str_menu_index = self.get_menu_index(str_result, self.list_control_menu[int_pos])
                if str_menu_index == '':
                    b_find = False
                    break
                self.send_command(str_menu_index + KEY_ENTER)
                str_result = self.read_until(PROMPT_INPUT, 3)
                int_pos += 1
            if b_find == True:
                break
        pass
    
    def get_menu_index(self, str_page, str_menu):
        str_page = str_page.lower()
        str_menu = str_menu.lower()
        ## find position of str_menu in str_page
        if str_page.find(str_menu)== -1:
            return ''
        int_pos = str_page.index(str_menu)
        ## get out MenuIndes if find
        if int_pos:
            str_index = str_page[int_pos - 4 : int_pos]
            str_index = str_index.replace(" ", "")
            str_index = str_index.replace(")", "")
            str_index = str_index.replace("-", "")
            return str_index
        else:
            return ''  
    
    def disconnect(self):
        if self.obj_telnet != None:
            self.obj_telnet.close()
        
    def check_port_name(self, list_port, list_name):
        pass
    
    def set_log(self, b_log = True, str_log_file = '', b_append = True):
        self.b_log = b_log
        self.str_log_file = str_log_file
        if b_append == True:
            self.str_log_mode = 'a'
        else:
            self.str_log_mode = 'w'
        return 0
    
    
if __name__ == '__main__':
    apc_debug_print('CAPC')
    apc = CAPC('192.168.001.202')
    apc.set_log(True, 'd:\\bruce\\apclog.txt', True)
    apc.b_print = True
    apc.power_cycle('N/A', 10)
