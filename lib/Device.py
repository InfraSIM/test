'''
*********************************************************
 Copyright 2013 EMC Inc.

[Filename]: 
[Author  ]: 
[Purpose ]: 
[Contains]: 
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
1.0     Bruce.Yang@emc.com  2013/12/18    First Edition
*********************************************************
'''

from Logger import CLogger
from lib.IPMI import CIPMI
from lib.Apps import *
import time
import traceback

class CDevice(CLogger):
    list_type = []
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: This is the top level class which will be inherit by all device
                   classes.
    [Methods]:    
        has_sub_device -
        sub_device - get all the sub-device of a certain type
        build - this is virtual function which will always be overwritten by child
                class. it is designed to build the device based on the source device
                or the father device
    [History]:                                                                 
    ************************************************
    '''
    
    def __init__(self, str_sub_type = '' , obj_xmlnode_runtime = None, obj_device_parent = None):
        CLogger.__init__(self)
        # for the device tree
        self.str_sub_type = str_sub_type
        self.obj_device_parent = obj_device_parent
        self.obj_xmlnode_runtime = obj_xmlnode_runtime
        self.dict_device_children = {}
        self.str_device_type = None
        self.str_device_name = None
        # the interfaces
        self.obj_rest_agent = None
        # for runtime
        self.obj_logger = None
        # flags
        self.b_valid = True # this flag is set to True by default. It will be set to false
                            # when a error appeared, which means the device is not OK to
                            # be used
        self.b_build = False # device built
        self.b_logger_set = False # logger set or not
        self.b_interface_set = False # interfaces set or not
        CDevice.list_type.append(self.str_device_type)
        
        self.uri = ''
            
    def is_valid(self):
        return self.b_valid & self.b_build
    
    def has_sub_device(self, str_device_type):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: check if this device has a certain kind of sub-device
        [Input   ]: 
            str_device_type - the target device type
        [Output  ]:
            True if this device has the target kind of device
        [History ]                                              
        ************************************************
        '''
        if self.dict_device_children.has_key(str_device_type):
            return True
        return False
    
    def sub_device(self, str_device_type):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: get a certain type of sub_device
        [Input   ]: 
            str_device_type - the target device type
        [Output  ]:
            a sub device dict: key - index, value - device object
        [History ]                                              
        ************************************************
        '''
        if self.has_sub_device(str_device_type):
            return None
        return self.dict_device_children[str_device_type]
    
    def build(self):
        # create interface
        if self.b_build == True:
            self.log('WARNING', 'Device has been built before')
            return 0
        self.b_build = True
        self.set_logger()
        self.log('INFO', 'Start building device(%s, %s)' % (self.str_device_type, self.str_sub_type))
        self.build_upon_spec()
        self.load_runtime_config()
        self.build_sub_devices()
        self.build_sensors()
        self.add_actions()
        if self.b_valid:
            self.b_build = True
            self.log('INFO', 'Build finished')
            return 0
        self.log('ERROR', 'Build finished with error')
        return -1 
    
    def build_sensors(self):
        #=======================================================================
        # This function have to be override by sub-class
        # if the device has sensors
        #=======================================================================
        pass
    
    def build_upon_spec(self):
        pass
    
    def load_runtime_config(self):
        pass
        
    def build_sub_devices(self):
        pass
        
    def _validate_sub_device(self, obj_sub_device):
        if not obj_sub_device.b_valid:
            self.b_valid = False
            self.log('ERROR', 'Invalid %s found' % obj_sub_device.str_device_type)
            return -1
        self.dict_device_children[obj_sub_device.str_device_type] = obj_sub_device
        return 0
    
    def validate(self):
        return False
    
    def set_logger(self, obj_logger = None, obj_rest_logger = None):
        # if the obj_logger is set, use this as the device log of this device
        if obj_logger != None:
            self.obj_logger = obj_logger
            self.b_logger_set = True
        # if the obj_logger is not set, use the logger of the parent
        # as the logger of this device
        elif self.obj_device_parent != None and \
                self.obj_device_parent.b_logger_set == True:
            self.obj_logger = self.obj_device_parent.obj_logger
            self.b_logger_set = True
        else:
            return -1
                
        return 0
    
    # Set Interface
    def set_rest_agent(self, obj_rest_agent):
        # register rest_logger
        if obj_rest_agent != None:
            self.obj_rest_agent = obj_rest_agent
            self.rest_get = self.obj_rest_agent.send_get
            self.rest_put = self.obj_rest_agent.send_put
            self.rest_post = self.obj_rest_agent.send_post
            self.rest_delete = self.obj_rest_agent.send_delete
            self.rest_patch = self.obj_rest_agent.send_patch
            return True
        else:
            return False
        
    def log(self, str_level, str_message):
        str_message = '(%s) %s' % (self.str_sub_type, str_message)
        CLogger.log(self, str_level, str_message)
        return 0

    def add_actions(self):
        pass
    
    def get(self, key=''):
        '''
        Get the value of corresponding key from the device's on_data
        @param key: the key of the return value in the raw on_data
        '''
        return self.on_data['json'].get(key, None)

    def get_mon(self, key=''):
        '''
        Get the value of corresponding key from the device's mon_data
        @param key: the key of the return value in the raw on_data
        '''
        return self.mon_data['json'].get(key, None)

if __name__ == '__main__':
    print 'device module not runnable'