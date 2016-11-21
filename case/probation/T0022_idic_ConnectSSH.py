from case.CBaseCase import *


class T0022_idic_ConnectSSH(CBaseCase):
    '''
    [Purpose ]: 
    [Author  ]: @emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        self.enable_node_ssh()
        self.enable_ipmi_console()
    
    def test(self):
        pass
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

