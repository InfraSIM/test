from case.CBaseCase import *

class T33270_idic_vPDUSetPassword(CBaseCase):
    '''
    [Purpose ]: 
    [Author  ]: June.Zhou@emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        try:
            self.stack.walk_pdu().next()
        except StopIteration:
            self.result(BLOCK, 'No PDU in stack at all')
        self.enable_vpdu_shell()
    
    def test(self):
        #verify map add, list, delete, update, and pdu restart
        self.log('INFO', 'Start Test...')

        fail_flag = False
        for obj_rack in self.stack.get_rack_list():
            for obj_pdu in obj_rack.get_pdu_list():
                #verify pdu password set. password set, and password list commands are tested.
                if not obj_pdu.verify_password_set():
                    fail_flag = True
                    self.result(FAIL, 'vPDU password set test fails. PDU is {} {}'
                                .format(obj_pdu.get_ip(), obj_pdu.get_name()))

        if fail_flag == False:
            self.log('INFO', 'Map port test success!')
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)