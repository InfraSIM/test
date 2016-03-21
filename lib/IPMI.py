'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: IPMI.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: 
[Contains]: 
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
 V1.0    Bruce Yang        2014/04/21     Initial Version
        - This module is to give a unified interface for IPMI command    
 V1.1    Forrest Gu        2014/04/30     Enrich
        - Change IPMI to a class
        - Modify LIST_CHANNEL to class variable dict_interface
        - Modify register_channel to register_interface
        - Add interface selector in send_ipmi input 
*********************************************************
'''

from Logger import CLogger
import traceback
try:
    from lib.Apps import *
except:
    print '[ERROR][IPMI] Failed to import module: lib.Apps'
    print traceback.format_exc()
    exit()

ERROR_NO_ERROR = 0
ERROR_UNKNOWN_INTERFACE = -1
ERROR_NOT_EXECUTED = -2


class CIPMI(CLogger):
    '''
    ************************************************************************************************************
    [Type    ]: Class
    [Name    ]: CIPMI
    [Author  ]: Forrest Gu(Forrest.Gu@emc.com)
    [Function]: Encapsulate IPMI interaction
    [History ]:
    ************************************************************************************************************
      VERSION        EDITOR          DATE             COMMENT
    ************************************************************************************************************
      R00            Forrest Gu      04/30/2014       Initial version
      R01            Forrest Gu      05/06/2014       Change dict_interface and 
                                                      str_session_log_full_path
                                                      to class variable.
                                                      Add log support.
    ************************************************************************************************************
    '''
    
    # Class variable (know as static variable in C++/Java)
#    dict_interface = {}
    
    def __init__(self):
        CLogger.__init__(self)
        self.obj_logger = None
        self.dict_interface = {}
        
    def reset(self):
        self.obj_logger = None
        self.dict_interface = {}
    
    def clear_interface_list(self):
        '''
        ************************************************
        [Author  ]: Forrest.Gu@emc.com
        [Function]: This function clear dict_interface
        [Output  ]:     
        [History ] 
            - Forrest.Gu@emc.com 05/06/2014
                initial edition
                Add log support for clear interface
        ************************************************
        '''
        self.log('INFO', "Clear interface list.")
        self.dict_interface = {}
        self.log('INFO', 'IPMI interface list cleared')

    def register_interface(self, str_description, obj_interface):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is designed for adding IPMI channel. For each channel being added
            this function will check if the channel has support for sending IPMI. 
        [Input   ]:
            str_description   - interface description: kcs, iol, console, etc...
            obj_interface     - an object via which IPMI command can be send
        [Output  ]:     
            True for success and False for failure
        [History ] 
            - Bruce.Yang@emc.com 04/21/2014
                initial edition
            - Forrest.Gu@emc.com 04/24/2014
                Modify simple priority list to a dict list.
                One dict include description and interface instance.
            - Forrest.Gu@emc.com 05/04/2014
                Modify instance variable to class variable.
                Add log support for interface register
        ************************************************
        '''
        # check if the channel object has send_ipmi method
        self.log('INFO', 'Check if interface (%s) is available then register...' % str_description)
        try:
            int_result, list_response = obj_interface.send_ipmi([0x06, 0x01])
        except Exception, e:
            import traceback
            self.log('WARNING', 'Exception during interface register: \n%s' % traceback.format_exc()) 
            
            return False
        
        # Register interface
        if int_result != 0:
            self.log('WARNING', 'Interface (%s) is not available. Fail to register.' % str_description)
            return False
        else:
            self.log('INFO', "Interface (%s) is available. Register to interface pool." % str_description)
            self.dict_interface[str_description] = obj_interface
            self.log('INFO', 'Register interface (%s) done.' % str_description)
            
            return True
    
    def has_interface(self, str_interface_name):
        if self.dict_interface.has_key(str_interface_name):
            return True
        return False
    
    def send_ipmi(self, hex_ipmi, list_interface=['kcs', 'iol', 'console'], int_retry_time=3):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is designed to provide an unified interface for sending
            IPMI command. 
        [Input   ]:
            hex_ipmi        -    a list consist of hex integer
            list_interface  -    sort interface for priority 
        [Output  ]:   
            int_result      -    an error code to indicate if IPMI session succeeds
        [History ] 
            - Bruce.Yang@emc.com 04/21/2014
                initial edition
            - Forrest.Gu@emc.com 04/24/2014
                Modify input parameter
            - Forrest.Gu@emc.com 05/06/2014
                Modify instance variable to class variable
        ************************************************
        '''
        
        # Initialize int_result and list_response
        int_result=ERROR_NOT_EXECUTED
        list_response=[]
        str_cmd = ' '.join([hex(i) for i in hex_ipmi])
        str_all_interface = ', '.join(list_interface)
        
        # If interface list is empty, raise exception
        if list_interface == []:
            raise Exception('FAIL', 'Interface list is empty for command (%s)' % str_cmd)
        
        # If all interfaces in list are not registered, raise exception
        if not any([self.has_interface(i) for i in list_interface]):
            raise Exception('FAIL', 'All request interface (%s) are not registered' % str_all_interface)
            
        # Send IPMI command
        for str_interface in list_interface:
            
            try:
                self.log('INFO', 'Send IPMI(%s): %s' % (str_interface, str_cmd))
                int_result, list_response = self.dict_interface[str_interface].send_ipmi(hex_ipmi,int_retry_time)
            except KeyError:
                self.log('WARNING', 'Interface: %s is not registered.' % str_interface)
                continue
            
            # If successfully send the command, exit the circulation
            # Else go to the next interface
            
            if int_result == ERROR_NO_ERROR:
                str_rsp = ' '.join([hex(i) for i in list_response])
                self.log('INFO', 'Response: %s' % str_rsp)
                break
            else:
                self.log('WARNING', 'IPMI session fails on: %s' % str_interface)
                
        # Return the response data
        return int_result, list_response


if __name__ == '__main__':
    from IOL import CIOL
    obj_iol = CIOL('192.168.1.152')
    obj_ipmi = CIPMI()
    obj_ipmi.register_interface('iol', obj_iol)
    print obj_ipmi.send_ipmi([0x06, 0x01])
