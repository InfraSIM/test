'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import subprocess
import os
import sys
from Logger import CLogger


# Constants
IPMI_RESULT_SUCCESS = 0
IPMI_RESULT_FAIL = -1
IPMI_RESULT_NO_COMMAND = -2
IPMI_RESULT_UNKNOWN = -3


class CIOL(CLogger):
    
    IPMITOOL_PATH = os.path.join(os.path.abspath('.'),
                                 'tool',
                                 'ipmitool',
                                 'ipmitool')
    b_ipmitool_warning = False
    str_ipmitool_warning = "[WARNING][IPMITool]: External tool of ipmitool needed. " \
                           "Make sure the tool is properly installed"
    
    def __init__(self, str_ip='', port=None, str_user='admin', str_password='Password1'):
        CLogger.__init__(self)
        if CIOL.b_ipmitool_warning:
            print CIOL.str_ipmitool_warning
            CIOL.b_ipmitool_warning
        self.str_ip = str_ip
        # RMCP+ udp port used by BMC; by default it is 623.
        if port:
            self.port = port
        else:
            self.port = 623

        self.str_user = str_user
        self.str_password = str_password
        self.str_param = ''
        self.set_ipmitool_command_prefix()
        self.b_create_session_log = True
        self.str_session_log = ''

    def send_ipmi(self, list_request, int_retry_time=3):
        '''
        ************************************************
        [Author  ]: Forrest.Gu@emc.com            
        [Function]: send ipmi command via KCS interface
        [Input   ]: 
                list_request  - a int list of net function, command ID 
                                and request data
        [Output  ]:
                int_result    - a int indicating if this IPMI interaction is finished
                                if the IPMI command is executed and has return data, int_result = 0
                                or int_result = -1  
                list_response - a int list of completion code 
                                and response data
        [History ]:  
        -    Forrest.Gu@emc.com 05/04/2014
            First edition.                                                               
        ************************************************
        '''
        int_result = 0
        list_respond = []
        # if the IP is empty, will return error code with no response data
        if self.str_ip == '':
            self.log('WARNING', 'There is no IP for IPMI IOL')
            return -1, list_respond
        
        str_completion_code = ''
        
        # re-format the IPMI command from hex list to a string
        str_request = ''
        for i in range(len(list_request)):
            str_byte = hex(list_request[i])
            str_byte.lower().strip()  # remove spaces
            str_byte = str_byte.replace('0x', '')
            str_byte = '0x'+str_byte
            if len(str_byte) > 4:
                self.log('WARNING', 'Invalid request data for IOL: %s' % str(list_request))
                return -1, []
            str_request += str_byte + ' '
        
        # Build ipmitool command
        str_command = self.str_ipmitool_command_prefix + ' raw ' + str_request
        # Log request data
        self.add_string_to_session_log(str_command)
        
        # Retry
        int_retry = int_retry_time
        
        for i in range(int_retry):
            # Execute command
            p_run_command = subprocess.Popen(str_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            str_cmd_return = str(p_run_command.communicate()[0])
            # Log response data
            self.add_string_to_session_log(str_cmd_return)
            str_cmd_return_chars_without_space = str_cmd_return.replace(' ', '')
            str_cmd_return_chars_without_space = str_cmd_return_chars_without_space.replace('\n', '')
            # Check if the return value is digital
            b_digital = True
            try:
                int(str_cmd_return_chars_without_space, 16)
            except:
                b_digital = False
            
            # No response data
            if str_cmd_return_chars_without_space == '':
                int_result = IPMI_RESULT_SUCCESS
                str_completion_code = '0x00'
                break
            # Response data get, but not digital
            # elif not str_cmd_return_chars_without_space.isdigit():
            elif not b_digital:
                if str_cmd_return.find('rsp=') >= 0:
                    int_position = str_cmd_return.find('rsp=')
                    int_result = IPMI_RESULT_SUCCESS
                    str_completion_code = str_cmd_return[int_position+4:int_position+8]
                    list_respond = []
                    break
                # Failed to send command, maybe lan issue
                elif str_cmd_return.find('Error:') >= 0:
                    self.log('WARNING', 'Error appear in IOL: %s' % str_cmd_return)
                    int_result = IPMI_RESULT_FAIL
                    str_completion_code = ''
                elif str_cmd_return.find('Close Session command failed') >= 0:
                    self.log('WARNING', 'IOL session in trouble: %s' % str_cmd_return)
                    int_result = IPMI_RESULT_FAIL
                    str_completion_code = ''
                else:
                    self.log('WARNING', 'IOL result not understandable: %s' % str_cmd_return)
                    int_result = IPMI_RESULT_UNKNOWN
                    str_completion_code = ''
                continue
            # Response data digital
            else:
                int_result = IPMI_RESULT_SUCCESS
                str_completion_code = '0x00'
                str_cmd_return = str_cmd_return.strip()
                if str_cmd_return.find(' '):
                    str_cmd_return = '0x' + str_cmd_return
                    str_cmd_return = str_cmd_return.replace(' ', ' 0x')  # add 0x hex back
                    list_respond = str_cmd_return.split(' ')
                else:
                    list_respond = str_cmd_return
                break
                
        # Return int_result and response data
        if int_result == IPMI_RESULT_SUCCESS:
            # Transfer string list to int list and return
            return int_result, [int(i, 0) for i in ([str_completion_code]+list_respond)]
        else:
            return -1, []
            
    def set_session_log(self, str_session_log_file_name):
        # Forrest 10/31/2014
        # For an IOL instance, if it's session log is set before
        # then it won't be changed to a new file
        # This is to avoid duplicated IOL session log for a same SP
        if self.str_session_log == '':
            self.str_session_log = str_session_log_file_name
        return 0
    
    def add_string_to_session_log(self, str_line):
        if self.b_create_session_log is True:
            try:
                with open(self.str_session_log, 'a') as f_log:
                    import datetime
                    str_line = str_line.replace('\n', '\n' + '[' + str(datetime.datetime.now()) + '] ')
                    f_log.writelines(str_line)
                    f_log.writelines('\n')
                    return 0
            except:
                return 1
    
    def add_list_to_session_log(self, list_line):
        for item in list_line:
            self.add_string_to_session_log(item)

    def set_ipmitool_command_prefix(self):
        prefix = '"%s" -I lanplus -H %s -p %s -U %s -P %s -C 3 '\
                 % (self.IPMITOOL_PATH, self.str_ip, self.port,
                    self.str_user, self.str_password)
        self.str_ipmitool_command_prefix = prefix

    def set_ip_address(self, str_ip):
        self.str_ip = str_ip
        self.set_ipmitool_command_prefix()
    
    def set_passwd(self, str_passwd):
        self.str_password = str_passwd
        self.set_ipmitool_command_prefix()
    
    def ipmitool_raw_cmd(self, str_request, args=[]):
        list_respond = []
        # if the IP is empty, will return error code with no response data
        if self.str_ip == '':
            return -1, list_respond
        str_completion_code = ''
        
        # Build Request Data
        str_request = str_request.strip()  # Remove start/end blanks
        str_request = ' '.join([hex(int(b, 16)) for b in str_request.split()])

        # Add arguments if there are
        str_request += ' '
        str_request += ' '.join([hex(int(i, 16)) for i in args])
        if str_request == '':
            int_result = IPMI_RESULT_NO_COMMAND
            return int_result, str_completion_code, list_respond
        
        # Build ipmitool command
        str_command = self.str_ipmitool_command_prefix + 'raw ' + str_request
        self.add_string_to_session_log(str_command)
        
        # Execute command
        p_run_command = subprocess.Popen(str_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        str_cmd_return = str(p_run_command.communicate()[0])
        self.add_string_to_session_log(str_cmd_return)
        str_cmd_return_chars_without_space = str_cmd_return.replace(' ', '')
        str_cmd_return_chars_without_space = str_cmd_return_chars_without_space.replace('\n', '')
        # Check if the return value is digital
        b_digital = True
        try:
            int(str_cmd_return_chars_without_space, 16)
        except:
            b_digital = False
        
        # No response data
        if str_cmd_return_chars_without_space == '':
            int_result = IPMI_RESULT_SUCCESS
            str_completion_code = '0x00'
        # Response data get, but not digital
        # elif not str_cmd_return_chars_without_space.isdigit():
        elif not b_digital:
            if str_cmd_return.find('rsp=') >= 0:
                int_position = str_cmd_return.find('rsp=')
                int_result = IPMI_RESULT_SUCCESS
                str_completion_code = str_cmd_return[int_position+4:int_position+8]
            # Failed to send command, maybe lan issue
            elif str_cmd_return.find('Error:') >= 0:
                int_result = IPMI_RESULT_FAIL
                str_completion_code = ''
            else:
                int_result = IPMI_RESULT_UNKNOWN
                str_completion_code = ''
        # Response data digital
        else:
            int_result = IPMI_RESULT_SUCCESS
            str_completion_code = '0x00'
            str_cmd_return = str_cmd_return.strip()
            if str_cmd_return.find(' '):
                str_cmd_return = '0x' + str_cmd_return
                str_cmd_return = str_cmd_return.replace(' ', ' 0x')  # add 0x hex back
                list_respond = str_cmd_return.split(' ')
            else:
                list_respond = str_cmd_return
                
        return int_result, str_completion_code, list_respond
    
    def ipmitool_standard_cmd(self, str_request):
        
        '''
        ************************************************
        [Author  ]: Forrest.Gu@emc.com
        [Function]: Send standard ipmitool command and get response data
        [Input   ]: str_request - operation request followed after ipmitool
        [Output  ]: str_cmd_return - response string
        [History ]:         
        ********************************************************************
         VERSION      EDITOR                DATE             COMMENT
        ********************************************************************
          V1.0        Forrest.Gu@emc.com    09/18/2013       First edition
        ********************************************************************   
        '''

        # if the IP is empty, will return error code with no response data
        if self.str_ip == '':
            return -1, ''
        # Build ipmitool command
        str_command = self.str_ipmitool_command_prefix + str_request
        self.add_string_to_session_log(str_command)
        # Execute command
        p_run_command = subprocess.Popen(str_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        str_cmd_return = str(p_run_command.communicate()[0])
        int_return = p_run_command.returncode
        self.add_string_to_session_log(str_cmd_return)
        return int_return, str_cmd_return

    def __del__(self):
        pass
    
    def reset(self):
        self.str_session_log = ''


if '__main__' == __name__:
    if len(sys.argv) != 2:
        print("need target BMC ip")
        sys.exit(-1)
    print("send IPMI command to " + sys.argv[1])
    IPMITool = CIOL(sys.argv[1])
#    str_result, str_completion_code, list_respond = IPMITool.cmd('0x30 0x31')
#    print 'Result:', str_result
#    print 'Completion:', str_completion_code
#    print 'Respond:', list_respond
#    ret=IPMITool.ipmitool_standard_cmd('sel list')
#    print ret
#    str_result, str_completion_code, list_respond = IPMITool.ipmitool_raw_cmd('0x00 0x01')
#    print str_result
#    print str_completion_code
#    print list_respond
    ret, lst = IPMITool.ipmitool_standard_cmd('sel raw')
    print ret
    print lst
    print type(lst)
    print lst.splitlines()
