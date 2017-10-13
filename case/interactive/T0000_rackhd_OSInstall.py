from case.CBaseCase import *

sources_list = "This is a Xenial sources.list you can use:\n" \
               "\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial main restricted\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial-updates main restricted\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial universe\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial-updates universe\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial multiverse\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial-updates multiverse\n" \
               "deb http://mirror.rackspace.com/ubuntu/ xenial-backports main restricted universe multiverse\n" \
               "deb http://security.ubuntu.com/ubuntu xenial-security main restricted\n" \
               "deb http://security.ubuntu.com/ubuntu xenial-security universe\n" \
               "deb http://security.ubuntu.com/ubuntu xenial-security multiverse\n"


class T0000_rackhd_OSInstall(CBaseCase):
    '''
    [Purpose ]: Trigger RackHD 2.0 workflow to install OS for all nodes under management.
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 21
    [Tickets ]: HWSIM-747
    '''

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config

        ssh = self.monorail.obj_ssh_agent

        # Check if os is mounted
        rsp = ssh.remote_shell("mount")
        if "/ifs/share/infrastructure/nfs-maglev-image/html/static/mirrors" not in rsp["stdout"]:
            self.log(
                "WARNING", "No OS mirror is found in RackHD environment. Going to mount...")
            ssh.remote_shell("echo {} | sudo -S mkdir "
                             "-p /opt/monorail/static/http".
                             format(self.monorail.password))
            rsp = ssh.remote_shell("echo {} | sudo -S mount -t nfs "
                                   "-o rw,rsize=8192,wsize=8192,timeo=14,intr "
                                   "192.168.127.32:/ifs/share/infrastructure/nfs-maglev-image/html/static/mirrors "
                                   "/opt/monorail/static/http".
                                   format(self.monorail.password))
            if "mount: wrong fs type" in rsp["stderr"]:
                self.result(BLOCK, "Please install nfs-common in RackHD environment, then run this test again:\n"
                                   "- Write a valid /etc/apt/sources.list\n"
                                   "- sudo apt-get update\n"
                                   "- sudo apt-get install nfs-common\n"
                                   "\n"
                                   "{}".format(sources_list))
                return
            if "mount.nfs: access denied by server" in rsp["stderr"]:
                self.result(BLOCK, "Please install cifs-utils in RackHD environment, then "
                                   "mount the share folder with cifs protocol")
                return
            if "mount.nfs: Connection timed out" in rsp["stderr"]:
                self.result(BLOCK, "Server is inaccessible, please find another mirror server to mount.")
                return

    def test(self):
        # Check if any node has any active OS install workflows
        # If active workflow is for discovery, we will just wait
        node_os_install_list = []
        node_pend_on_discovery_list = []
        node_fail_os_install_list = []
        interval = 6
        retry = 30
        nodes = self.monorail.get_nodes("compute").items()
        node_os_install_list = self.monorail.get_nodes("compute").items()

        for i in range(retry):
            # if no nodes' has active workflow, break the 'for' loop
            count = len(nodes)
            for node_id, node in nodes:
                rsp = node.get_workflows(active=True).items()
                if len(rsp) == 0:
                    count = count - 1
            if count == 0:
                self.log('INFO', "No active workflow on any node, ready for OS installation")
                break
            # if any node has active workflow,
            # deal with workflow: cancel installation workflow + sleep for discovery workflow
            sleep_f = False
            for node_id, node in nodes:
                rsp = node.get_workflows(active=True).items()
                if len(rsp) != 0:
                    workflow_obj = rsp[0][1]
                    workflow_instance_id = workflow_obj.instanceId
                    self.log('INFO', "InstanceId {} workflow for {} is still active". format(
                             workflow_instance_id, workflow_obj.injectableName))
                    if "Install" in workflow_obj.injectableName:
                        workflow_obj.cancel()
                        self.log('INFO', "InstanceId {} workflow is cancelled". format(
                                 workflow_instance_id, workflow_obj.injectableName))
                    else:
                        if i == retry - 1:
                            self.log("WARNING", "There is {0} active workflow(s) on node {1}."
                                                "Will not continue with OS installtion on this node\n".
                                        format(len(rsp), node_id))
                            node_info = (node_id, node)
                            node_os_install_list.remove(node_info)
                            node_pend_on_discovery_list.append(node_id)
                        sleep_f = True

        # Block test if no node ready for OS installation due to incomplete discovery workflow
        if not node_os_install_list:
            self.result(BLOCK, "All nodes are pending on discovery workflow."
                        "Will not preceed with OS installation")
            return

        # Start workflow to install OS
        for node_id, node in node_os_install_list:
            # for node_id, node in self.monorail.get_nodes("compute").items():
            node_bmc_ip = node.get_bmc_ip()
            self.monorail.put_node_ipmi_obm(
                node_id=node_id, host=node_bmc_ip, username="admin", password="admin")
            node.install_os(self.data["os_name"])
            self.log(
                'WARNING', 'Installation on node {} starts, please open VNC to check'.format(node_id))
            time.sleep(120)

        # Verify os install succeeded
        for i in range(retry):
            retry = 60
            interval = float(30)
            sleep_f = False
            for node_id, node in node_os_install_list:
                rsp = node.get_workflows(active=True).items()
                if len(rsp) != 0:
                    workflow_obj = rsp[0][1]
                    workflow_instance_id = workflow_obj.instanceId
                rsp = node.get_workflow_by_id(workflow_instance_id)
                if rsp.status != "succeeded":
                    if i == retry - 1:
                        time_in_min = float(retry * interval / 60)
                        node_fail_os_install_list.append(node_id)
                    self.log('INFO', "InstanceId {} workflow for {} status: {}".format(
                        workflow_instance_id, workflow_obj.injectableName, rsp.status))
                    sleep_f = True
                elif rsp.status == "succeeded":
                    self.log('INFO', "InstanceId {} workflow completed".format(
                        workflow_instance_id))
                    break
            if sleep_f:
                time.sleep(interval)
        if node_fail_os_install_list or node_pend_on_discovery_list:
            str_failed = ''
            str_pend = ''
            if node_fail_os_install_list:
                str_failed = "Node(s) failed OS installation): {}\n".format(node_fail_os_install_list)
            if node_pend_on_discovery_list:
                str_pend =  "Node(s) pending on discovery workflow: {}\n".format(node_pend_on_discovery_list)
            self.result(FAIL, "{}{}".format(str_failed, str_pend))

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
