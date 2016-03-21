'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: KCS.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: This module is to add support connection to host OS via JSON-RPC
    protocal. This Linux OS will be a platform for sending IPMI via KCS
[Contains]: 
    -class CKCS
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
V1.0    Bruce.Yang@emc.com 09/23/2014    Initial Version
*********************************************************
'''
import traceback
try:
    from Logger import CLogger
except:
    print '[ERROR] Failed to import CLogger'
    
try:
    from jsonrpclib.jsonrpc import ServerProxy
except:
    print '[ERROR] Failed to import ServerProxy. Make sure jsonrpclib is installed'
    raw_input('Hit enter to exit')
    exit()
    
_KEY_ATRAGON_RETURN_VALUE = 'return_value'
_KEY_ATRAGON_EXECUTE_RESULT = 'execute_result'
_DEFAULT_ATRAGON_PORT = 9009

class CKCS(CLogger):
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: This class is for supporting KCS interface to IPMI. Is is using
        KCS implemented in Atragon
    [Methods]:    
        - is_valid - check if the interface is valid
        - connect - connect to a target host OS(Atragon)
        - send_ipmi - standard method for IPMI interface
        - log - event logging method
    [History]:                                                                 
    ************************************************  
    Version    Editor      Date        Comments
    ************************************************
    V1.0     Bruce Yang 03/21/2013     First Version                          
    ************************************************
    '''
    def __init__(self, str_ip = None, int_port = _DEFAULT_ATRAGON_PORT):
        CLogger.__init__(self)
        self.obj_json_client = None
        self.str_ip = str_ip
        self.int_port = int_port
    
    def is_valid(self):
        '''
        [Function]:
            Check the validity of the KCS interface. Checking include:
                - If the JSON RPC client is initialized
        [Input   ]: NA
        [Output  ]:
            True - if valid
            False - if invalid
        '''
        if self.obj_json_client is None: # The "is" here cannot be replaced by "="
            return False
        return True
    
    def is_connected(self):
        return self.is_valid()
    
    def get_ip(self):
        return self.str_ip
    
    def set_ip(self, str_ip):
        self.str_ip = str_ip
        
    def get_port(self):
        return self.int_port
    
    def set_port(self, int_port):
        self.int_port = int_port
    
    def connect(self, str_ip = None, int_port = None):
        '''
        [Function]:
            Used to bind the KCS instance to a certain port. This method can also be used to
            change the IP or port of the KCS interface. And it can even be used to connect to
            another KCS
        [Input   ]:
            str_ip - the IP address of the host OS
            int_port - the JSON RPC port which the target host OS is using. Default is 9009
        [Output  ]:     
            Initialize/Re-initialize the RPC client
        '''
        if str_ip:
            self.str_ip = str_ip
        if int_port:
            self.int_port = int_port 
        self.obj_json_client = ServerProxy('http://%s:%s' % (self.str_ip, self.int_port))

    def reconnect(self, str_ip = None, int_port = _DEFAULT_ATRAGON_PORT):
        '''
        [Function]:
            Duplicate of connect for compatibility.
        [Input   ]:
            str_ip - the IP address of the host OS(Atragon)
            int_port - the JSON RPC port which the target host OS(Atragon) is using. Default is 9009
        [Output  ]:     
            Initialize/Re-initialize the RPC client
        '''
        return self.connect(str_ip, int_port)
    
    def send_ipmi(self, list_request, int_retry = 3):
        '''         
        [Function]: send ipmi command via KCS interface
        [Input   ]: 
                list_request  - a list of integrates including: 
                                net function, command ID and request data
        [Output  ]:
                int_result    - an integrate indicating if this IPMI interaction is finished
                                if the IPMI command is executed and has return data, int_result = 0
                                or int_result = -1  
                list_response - a list of integrate including:
                                completion code and response data
        '''
        # check if the KCS interface is valid
        if not self.is_valid():
            self.log('WARNING', 'Trying to send IPMI while the interface is not valid')
            return -1, []
        # send command
        try:
            for i in range(int_retry):
                dict_atragon_return = self.obj_json_client.ipmi(list_request)
                if dict_atragon_return[_KEY_ATRAGON_EXECUTE_RESULT] != 0:
                    continue
                # the return value of the "ipmi" method in host OS(Atragon) is a dictionary in which the value
                # for "execute_result" is the execution result and the value for "return_value" is the 
                # return data of the IPMI command
                # dict_atragon_return = {'execute_result':##, 'return_value':[]}
                return dict_atragon_return[_KEY_ATRAGON_EXECUTE_RESULT], dict_atragon_return[_KEY_ATRAGON_RETURN_VALUE]
            
            # If fail with all retries, return int_result with an empty list
            return -1, []
        except:
            self.log('WARNING', 'Failed to send JSONRPC command to RPC server: \n%s' % traceback.format_exc())
            return -1, []
        
    def log(self, str_level, str_message):
        '''
        [Function]: 
            Add KCS prefix before pass the message to the Logger class
        [Input   ]:
            str_level - the log level
            str_message - the log information
        [Output  ]:     
            Will write log in to log file
        '''
        str_message = '(KCS: %s)%s' % (self.str_ip, str_message)
        return CLogger.log(self, str_level, str_message)
    
if __name__ == '__main__':
    obj_kcs = CKCS('192.168.1.22', 9009)
    print obj_kcs.send_ipmi([0x06, 0x01])
