'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T33258_idic_vPDUBasicInfo(CBaseCase):
    '''
    [Purpose ]: Verify vPDU basic information can be got by snmp command
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 25
    [Tickets ]: SST-628
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        self.result(BLOCK, 'No PDU for infrasim-compute at all')
        return
        try:
            self.stack.walk_pdu().next()
        except StopIteration:
            self.result(BLOCK, 'No PDU in stack at all')
    
    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_pdu in obj_rack.get_pdu_list():
                if obj_pdu.self_check():
                    self.log('INFO', 'PDU {} pass basic information check'.
                             format(obj_pdu.get_name()))
                else:
                    self.result(FAIL, 'PDU {} fail basic information check'.
                                format(obj_pdu.get_name()))
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
