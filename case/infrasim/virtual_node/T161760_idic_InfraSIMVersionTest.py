from case.CBaseCase import *
import gevent

PROMPT_GUEST = "root@localhost"
CONF = {}
class T161760_idic_InfraSIMVersionTest(CBaseCase):
    '''
    [Purpose ]: Send infrasim version commands. Display the node version
    [Author  ]: bin.yan@dell.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        self.enable_node_ssh()
    
    def test(self):
        gevent.joinall([gevent.spawn(self.send_infrasim_version_cmd, obj_node)
                       for obj_node in self.stack.walk_node()])

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def send_infrasim_version_cmd(self, node):
        # Send infrasim version command
        print node.ssh.send_command_wait_string(str_command="sudo infrasim version"+chr(13), wait="~$")
        return
