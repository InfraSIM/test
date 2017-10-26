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
        node_pend_on_discovery_list = []
        node_os_install_workflow_inactive_list = []
        node_fail_post_os_install_workflow_list = []
        node_fail_os_install_list = []
        interval = 6
        retry = 30
        node_os_install_dic = self.monorail.get_nodes("compute")

        for i in range(retry):
            # if no node has active workflow, break the loop
            count = len(node_os_install_dic)
            for node_id, node in node_os_install_dic.iteritems():
                rsp = node.get_workflows(active=True).items()
                if len(rsp) == 0:
                    count = count - 1
            if count == 0:
                self.log('INFO', "No active workflow on any node, ready for OS installation")
                break

            # if any node has active workflow,
            # deal with workflow: cancel installation workflow + sleep for discovery workflow
            has_discover_workflow = False
            for node_id, node in node_os_install_dic.iteritems():
                rsp = node.get_workflows(active=True).items()
                if len(rsp) != 0:
                    workflow_obj = rsp[0][1]
                    workflow_instance_id = workflow_obj.instanceId
                    self.log('INFO', "InstanceId {} workflow for {} is still active". format(
                             workflow_instance_id, workflow_obj.injectableName))
                    if "Install" in workflow_obj.injectableName:
                        workflow_obj.cancel()
                        self.log('INFO', "InstanceId {} workflow for {} is cancelled". format(
                                 workflow_instance_id, workflow_obj.injectableName))
                    else:
                        if i == retry - 1:
                            self.log("WARNING", "There is {0} active workflow(s) on node {1}."
                                                "Will not continue with OS installtion on this node\n".
                                        format(len(rsp), node_id))
                            node_pend_on_discovery_list.append(node_id)
                        has_discover_workflow = True
            if has_discover_workflow:
                time.sleep(interval)
            else:
                break

        for node_id in node_pend_on_discovery_list:
            del(node_os_install_dic[node_id])

        # Block test if no node ready for OS installation due to incomplete discovery workflow
        if not node_os_install_dic:
            self.result(BLOCK, "All nodes are pending on discovery workflow."
                        "Will not preceed with OS installation")
            return

        # Start workflow to install OS
        install_interval = 120
        node_workflow_list = {}
        for node_id, node in node_os_install_dic.iteritems():
            node_bmc_ip = node.get_bmc_ip()
            self.monorail.put_node_ipmi_obm(
                node_id=node_id, host=node_bmc_ip, username="admin", password="admin")
            try:
                node.install_os(self.data["os_name"])
            except Exception as e:
                self.log("WARNING", "Exception in loading or posting OS installation workflow on node ID: {}".format(node_id))
                node_fail_post_os_install_workflow_list.append(node_id)
            self.log(
                'INFO', 'Installation on node {} starts, please open VNC to check'.format(node_id))
            rsp = node.get_workflows(active=True).items()
            if len(rsp) != 0:
                workflow_obj = rsp[0][1]
                if "Install" in workflow_obj.injectableName:
                    workflow_instance_id = workflow_obj.instanceId
                    node_workflow_list[node_id] = workflow_instance_id
            else:
                node_os_install_workflow_inactive_list.append(node_id)
                self.log("WARNING", "OS installation workflow is not active on node ID: {}".format(node_id))
            time.sleep(install_interval)

        for node_id in node_fail_post_os_install_workflow_list:
            del(node_os_install_dic[node_id])

        # Verify os install succeeded
        retry = 60
        interval = float(30)
        for i in range(retry):
            has_os_install_workflow = False
            for node_id, node in node_os_install_dic.iteritems():
                rsp = node.get_workflow_by_id(node_workflow_list[node_id])
                if rsp.status != "succeeded":
                    if i == retry - 1:
                        time_in_min = float(retry * interval / 60)
                        node_fail_os_install_list.append(node_id)
                    self.log('INFO', "InstanceId {} of NodeId {} for {} workflow status: {}".format(
                        node_workflow_list[node_id], node_id, self.data["os_name"], rsp.status))
                    has_os_install_workflow = True
                elif rsp.status == "succeeded":
                    self.log('INFO', "InstanceId {} of nodeId {} for {} workflow completed".format(
                        node_workflow_list[node_id], node_id, self.data["os_name"]))
            if has_os_install_workflow:
                time.sleep(interval)
            else:
                break

        # Log for test result
        if node_fail_os_install_list or node_pend_on_discovery_list or node_os_install_workflow_inactive_list:
            str_failed = ''
            str_pend = ''
            str_inactive = ''
            str_post_fail = ''
            if node_fail_os_install_list:
                str_failed = "Node(s) failed {} installation: {}\n".format(self.data["os_name"], node_fail_os_install_list)
            if node_pend_on_discovery_list:
                str_pend =  "Node(s) pending on discovery workflow before {} installation: {}\n".format(self.data["os_name"], node_pend_on_discovery_list)
            if node_os_install_workflow_inactive_list:
                str_inactive = "Node(s) {} installation workflow inactive: {}\n".format(self.data["os_name"], node_os_install_workflow_inactive_list)
            if node_fail_post_os_install_workflow_list:
                str_post_fail = "Node(s) failed in loading or posting {} installation workflow: {}\n".format(self.data["os_name"], node_fail_post_os_install_workflow_list)
            self.result(FAIL, "{}{}{}{}".format(str_failed, str_pend, str_inactive, str_post_fail))


    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
