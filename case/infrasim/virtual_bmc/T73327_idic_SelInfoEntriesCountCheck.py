'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T73327_idic_SelInfoEntriesCountCheck(CBaseCase):
    '''
    [Purpose ]: Verify virtual BMC's SEL Entries count
    [Author  ]: arys.lu@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Check node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                obj_node.get_bmc().ipmi.ipmitool_standard_cmd('sel clear')
                time.sleep(3)
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('sel info')
                self.log('INFO', 'ret: {}'.format(ret))
                self.log('INFO', 'rsp: \n{}'.format(rsp))

                if not re.search('Entries(\s)*:(\s)*0', rsp):
                    self.log('INFO', 'The Entries is not 0 accurately.')
                else:
                    self.result(FAIL, 'Failure: The Entreis is 0.')


    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)