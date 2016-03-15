'''
*********************************************************
 Copyright 2013 EMC Inc.

[Filename]: Interface.py
[Author  ]: Eric Wang
[Purpose ]: Provide a base class for the interfaces
[Contains]: 
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
1.0     eric.wang@emc.com  2013/12/25    First Edition
1.1     Bruce.Yang@emc.com 2014/01/13    Add set_logger action
*********************************************************
'''

class CLogger():
    '''
    '''
    def __init__(self):
        self.obj_logger = None
        
    def log(self, str_level, str_message):
        str_xmlnode_eventlog = '''
        <event_log>
            <source />
            <level />
            <time />
            <message />
        </event_log>
        '''
        if self.obj_logger == None:
            return
        import xml.etree.ElementTree as ET
        import datetime
        obj_xmlnode_eventlog = ET.fromstring(str_xmlnode_eventlog)
        obj_xmlnode_eventlog.find('source').text = self.obj_logger.name
        obj_xmlnode_eventlog.find('level').text = str_level
        obj_xmlnode_eventlog.find('time').text = str(datetime.datetime.now())
        obj_xmlnode_eventlog.find('message').text = str_message
        self.obj_logger.info(ET.tostring(obj_xmlnode_eventlog)) 
    
    def set_logger(self, obj_logger):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Set the logger object of the interface
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        self.obj_logger = obj_logger
    