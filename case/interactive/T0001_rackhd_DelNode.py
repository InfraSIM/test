from case.CBaseCase import *


class T0001_rackhd_DelNode(CBaseCase):
    '''
        [Purpose ]: Trigger RackHD 2.0 workflow to delete all nodes under management.
        [Author  ]: julie.jiang@emc.com
        [Sprint  ]: Lykan Sprint 29
        [Tickets ]: HWSIM-1241
    '''

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)

    def test(self):
        for node_id, node in self.monorail.get_nodes("compute").items():
            rsp = node.get_workflows(active=True).items()
            if len(rsp) != 0:
                workflow_obj = rsp[0][1]
                workflow_obj.cancel()
            try:
                node.delete()
            except:
                # If fails in deleting node due to active workflow unable to be canceled, remove workflow from rackhd mongodb
                ssh = self.monorail.obj_ssh_agent
                rsp = ssh.remote_shell("echo 'db.graphobjects.remove({\"node\": " + "ObjectId(\"{0}\")".format(node_id) + "})' | mongo pxe")
                node.delete()
        for enclosure_id, enclosure in self.monorail.get_nodes("enclosure").items():
            enclosure.delete()

    def deconfig(self):
        CBaseCase.deconfig(self)
