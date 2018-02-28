from case.CBaseCase import *
from lib import Env,main

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


class T0006_rackhd_OSInstallRHEL(CBaseCase):
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
        ssh = self.monorail.obj_ssh_agent

        # start testing normally from here
        token = self.monorail.set_rackhd_rest_auth()

        # To do: Case specific config

        # Check if os is mounted
        rsp = ssh.remote_shell("mount")
        if "/ifs/share/infrastructure/nfs-maglev-image/html/static/mirrors" not in rsp["stdout"]:
            self.log(
                "WARNING", "No OS mirror is found in RackHD environment. Going to mount...")
            ssh.remote_shell("echo {} | sudo -S apt-get install nfs-common -y".
			     format(self.monorail.password))

            ssh.remote_shell("echo {} | sudo -S apt-get install sshpass -y".
			     format(self.monorail.password))

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
        install_time_statistics_dic = {}
        node_pend_on_discovery_list = []
        node_os_install_dic = {}
        node_os_install_workflow_inactive_list = []
        node_fail_post_os_install_workflow_list = []
        node_fail_os_install_list = []
        node_bmc_ip = {}
        interval = 60
        retry = 20

        for i in range(retry):
            try:
                node_os_install_dic = self.monorail.get_nodes("compute")
	        if node_os_install_dic:
                    if len(node_os_install_dic) == self.data["node_count"]:
                        break
                    elif len(node_os_install_dic) < self.data["node_count"]:
                        # if the dic is not null means at least one node is up
                        # wait some more time for all nodes up
                        time.sleep(interval)
                        continue
	    except KeyError:
                time.sleep(interval)
                continue

        interval = 60
        retry = 3
        for i in range(retry):
            # if no node has active workflow, break the loop
            count = len(node_os_install_dic)
            for node in node_os_install_dic.values():
                rsp = node.get_workflows(active=True).items()
                if len(rsp) == 0:
                    count = count - 1
            if count == 0:
                self.log('INFO', "No active workflow on any node, ready for OS installation")
                break

            # if any node has active workflow,
            # deal with workflow: cancel installation workflow + sleep for discovery workflow
            has_discover_workflow = False
            for node in node_os_install_dic.values():
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
                                                format(len(rsp), node.id))
                            node_pend_on_discovery_list.append(node.id)
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
            node_bmc_ip[node.id] = node.get_bmc_ip()
            self.monorail.put_node_ipmi_obm(
                node_id=node_id, host=node_bmc_ip[node.id], username="admin", password="admin")
            try:
                node.install_os(self.data["os_name"])
                install_time_statistics_dic[node_id] = {"start": time.time()}
            except Exception, e:
                self.log("WARNING", "Exception in loading or posting OS installation workflow on node ID: {}. \
                         \n Exception message: {}".format(node_id, e.message))
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
        interval = 60
        retry = self.data["timeout"] * 60 / interval
        time.time()
        print("Retry: {}".format(retry))
        for i in range(retry):
            has_os_install_workflow = False
            for node_id, node in node_os_install_dic.iteritems():
                rsp = node.get_workflow_by_id(node_workflow_list[node_id])
                if rsp.status == "running":
                    elapse_run_time = time.time() - install_time_statistics_dic[node_id]["start"]
                    # FIXME:
                    # If os installation is still running, it's likely be stuck in loading os,
                    # workaround is to restart infrasim twice one is around 20 minutes, one is around 23 minutes
                    if (elapse_run_time < 1215 and elapse_run_time > 1185) \
                        or (elapse_run_time < 1395 and elapse_run_time > 1365):
                        self.log('INFO', "InstanceId {} of node id {} for {} workflow may stuck after {} minutes, \
                                 restart infrasim now ...".
                                 format(node_workflow_list[node_id], node_id, self.data["os_name"], elapse_run_time))
                        ssh = self.monorail.obj_ssh_agent
                        ssh.remote_shell("ipmitool -I lanplus -U admin -P admin -H {} chassis power cycle".format(node_bmc_ip[node.id]))

                    if i == retry - 1:
                        node_fail_os_install_list.append(node)
                    self.log('INFO', "InstanceId {} of node id {} for {} workflow status: {}".format(
                             node_workflow_list[node_id], node_id, self.data["os_name"], rsp.status))
                    has_os_install_workflow = True
                elif rsp.status == "succeeded":
                    self.log('INFO', "InstanceId {} of node id {} for {} workflow completed".format(
                             node_workflow_list[node_id], node_id, self.data["os_name"]))
                    if not install_time_statistics_dic[node_id].has_key("stop"):
                          install_time_statistics_dic[node_id]["stop"] = time.time()
                else:
                    self.log('WARNING', "Instance {} of node id {} for {} workflow not success.Status: {}".format(
                             node_workflow_list[node_id], node_id, self.data["os_name"], rsp.status))
                    if node not in node_fail_os_install_list:
                        node_fail_os_install_list.append(node)
            if has_os_install_workflow:
                time.sleep(interval)
            else:
                break

        # Log for test result
        if node_fail_post_os_install_workflow_list or \
           node_fail_os_install_list or \
           node_pend_on_discovery_list or \
           node_os_install_workflow_inactive_list or \
           len(node_os_install_dic) < self.data["node_count"]:
            str_failed = ''
            str_pend = ''
            str_inactive = ''
            str_post_fail = ''
            str_discover_fail = ''
            if node_fail_os_install_list:
                err_msgs = []
                for node in node_fail_os_install_list:
                    node_ohai = node.get_catalog_from_identity("ohai")
                    node_mfg = node_ohai.data["dmi"]["system"]["manufacturer"]
                    node_product = node_ohai.data["dmi"]["system"]["product_name"]
                    msg = "\tNode ID: {node_id}, BMC IP: {bmc_ip}, Type: {node_mfg} {product}".\
                          format(node_id=node.id, bmc_ip=node_bmc_ip[node.id],
                                 node_mfg=node_mfg, product=node_product)
                    err_msgs.append(msg)
                str_failed = "{} node(s) failed {} installation: \n{}".format(
                    len(node_fail_os_install_list), self.data["os_name"], "\n".join(err_msgs))

            if node_pend_on_discovery_list:
                str_pend = "{} node(s) pending on discovery workflow before {} installation: {}".format(
                    len(node_pend_on_discovery_list), self.data["os_name"], node_pend_on_discovery_list)
            if node_os_install_workflow_inactive_list:
                str_inactive = "{} node(s) {} installation workflow inactive: {}".format(len(
                    node_os_install_workflow_inactive_list), self.data["os_name"], node_os_install_workflow_inactive_list)
            if node_fail_post_os_install_workflow_list:
                str_post_fail = "{} node(s) failed in loading or posting {} installation workflow: {}".format(len(
                    node_fail_post_os_install_workflow_list), self.data["os_name"], node_fail_post_os_install_workflow_list)
            if len(node_os_install_dic) < self.data["node_count"]:
                str_discover_fail = "RackHD discovered {} node(s), expect {} node(s)". \
                                     format(len(node_os_install_dic), self.data["node_count"])
            self.result(FAIL, "\n".join([str_failed, str_pend, str_inactive, str_post_fail, str_discover_fail]))

        # Summarize os install statistics
        self.log("INFO", "OS installation elapse time statistics:")
        for node_id, time_dic in install_time_statistics_dic.iteritems():
            if "stop" in time_dic:
                elapse = time_dic["stop"] - time_dic["start"]
                self.log("INFO", "\t\tNode {} install {} elapse time: {}min {}s".
                                 format(node_id, self.data["os_name"], int(elapse) / 60, int(elapse) % 60))


    def deconfig(self):
        # To do: Case specific deconfig
        ssh = self.monorail.obj_ssh_agent
	rsp = ssh.remote_shell("bash +x clean_up.sh ip.txt")
        CBaseCase.deconfig(self)
