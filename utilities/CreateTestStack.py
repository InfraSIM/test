#!/usr/bin/env python
"""
This is an utility to accept ip inventory as admin
network, then:
- validate SSH on admin network
- analyze node network
- (if necessary, update infrasim code and install)
- (if necessary, define bmc network and qemu network)
- update node yml file
- start infrasim instance
- validate ipmi access
- write stack.json in puffer style
"""


import paramiko
import sys
import traceback
import socket
import json
import subprocess
import time
from ansible import inventory
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader

node_type = [
    "quanta_t41",
    "quanta_d51",
    "s2600kp",
    "s2600tp",
    "s2600wtt",
    "dell_r730xd",
    "dell_r730",
    "dell_r630",
    "dell_c6320"
]
full_group = "virtual_server"
ssh_username = ""
ssh_password = ""
inventory_path = ""
hosts = {}
host_to_bmc = {}


def run_command(cmd="", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        result = ""
        if cmd_result[1] is not None:
            result = cmd + ":" + cmd_result[1]
        else:
            result = cmd
        raise Exception("[FAIL] {}".format(result))
    return 0, cmd_result[0]


def validate_ansible():
    _, rsp = run_command("ansible --version")
    version = rsp.split()[1]
    if version.startswith("1."):
        print "Ansible version: {}, require ansible>=2.0".format(version)
        print "Install ansible>=2.0 needs a PPA, refer to: "
        print "http://docs.ansible.com/ansible/intro_installation.html#latest-releases-via-apt-ubuntu"
        exit(-1)


def scan_inventory(path):
    """
    Given an infrasim inventory path, analyze all host and group in dict.
    """
    dict_group = {}
    for one_type in node_type:
        dict_group[one_type] = []
    global ssh_username
    global ssh_password
    global hosts

    variable_manager = VariableManager()
    loader = DataLoader()

    inv = inventory.Inventory(loader=loader, variable_manager=variable_manager, host_list=path)
    groups = inv.get_groups()
    for g in groups:
        group = groups[g]
        if group.name in node_type:
            hosts = group.get_hosts()
            for host in hosts:
                dict_group[group.name].append(host.name)
        elif group.name == full_group:
            vars = group.get_vars()
            ssh_username = vars["ansible_become_user"]
            ssh_password = vars["ansible_become_pass"]

    hosts = dict_group
    return


def validate_admin_access():
    global hosts
    global host_to_bmc
    global ssh_password

    bmc_cmd = "ifconfig ens192 | awk '/inet addr/{print substr($2,6)}'"

    for node_type in hosts:
        for host in hosts[node_type]:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, username="infrasim", password="infrasim")

            except paramiko.AuthenticationException:
                print 'SSH authentication error, please check username and password'
                return False
            except paramiko.SSHException:
                print 'Error happen in SSH connect: \n{}'.format(traceback.format_exc())
                return False
            except socket.error:
                print 'WARNING', 'Socket error while connection: \n{}'.format(traceback.format_exc())
                return False
            except Exception:
                print 'WARNING', 'Fail to build SSH connection: \n{}'.format(traceback.format_exc())
                return False
            else:
                print "SSH to {} is validated".format(host)

            try:
                # bring all net dev up if they are not
                stdin, stdout, stderr = client.exec_command("ifquery -l")
                while not stdout.channel.exit_status_ready():
                    pass
                str_stdout = ''.join(stdout.readlines())
                str_stderr = stderr.channel.recv_stderr(4096)
                int_exitcode = stdout.channel.recv_exit_status()
                if int_exitcode != 0:
                    raise Exception("Fail to query interfaces list", str_stderr)
                intf_list = str_stdout.split()
                for intf in intf_list:
                    stdin, stdout, stderr = client.exec_command("ifconfig {}".format(intf))
                    while not stdout.channel.exit_status_ready():
                        pass
                    str_stdout = ''.join(stdout.readlines())
                    str_stderr = stderr.channel.recv_stderr(4096)
                    int_exitcode = stdout.channel.recv_exit_status()
                    if int_exitcode != 0:
                        print 'INFO', '{} is not up, trying to bring it up...'.format(intf)
                        stdin, stdout, stderr = client.exec_command("echo {} | sudo -S ifup {}".format(ssh_password, intf))
                        while not stdout.channel.exit_status_ready():
                            pass
                        str_stdout = ''.join(stdout.readlines())
                        str_stderr = stderr.channel.recv_stderr(4096)
                        int_exitcode = stdout.channel.recv_exit_status()
                        if int_exitcode != 0:
                            raise Exception("Fail to ifup {}".format(intf))

                # fetch bmc interface ip
                stdin, stdout, stderr = client.exec_command(bmc_cmd)
                while not stdout.channel.exit_status_ready():
                    pass
                str_stdout = ''.join(stdout.readlines())
                str_stderr = stderr.channel.recv_stderr(4096)
                int_exitcode = stdout.channel.recv_exit_status()

                if int_exitcode != 0 or "error fetching interface information" in str_stderr:
                    raise Exception("Fail to fetch IP of ens192 on node {}".format(host))
                else:
                    host_to_bmc[host] = str_stdout.strip()
            except paramiko.SSHException:
                print 'SSH exception when execute command on remote shell: {}'.format(bmc_cmd)
            finally:
                client.close()

    return True


def solve_arp_flux():
    global full_group
    global inventory_path
    global ssh_password
    dl_cmd = "ansible {} -i {} -m shell -a \"wget " \
          "https://raw.githubusercontent.com/InfraSIM/tools/master/diag_arp_flux/diag_arp_flux.py\"".\
        format(full_group, inventory_path, ssh_password)
    run_command(dl_cmd)
    install_cmd = "ansible {} -i {} -m shell -a \"echo {} | sudo -S pip install netifaces\"".\
        format(full_group, inventory_path, ssh_password)
    run_command(install_cmd)
    route_cmd = "ansible {} -i {} -m shell -a \"echo {} | sudo -S python diag_arp_flux.py\"".\
        format(full_group, inventory_path, ssh_password)
    run_command(route_cmd)


def clear_node():
    global full_group
    global inventory_path
    global hosts
    global ssh_password
    cmd = "ansible {} -i {} -m shell -a \"echo {} | " \
          "sudo -S ipmi-console stop\"".\
        format(full_group, inventory_path, ssh_password)
    _, rsp = run_command(cmd)
    print rsp
    # Verify operations on all nodes are successful
    for hosts_of_this_kind in hosts.values():
        for host in hosts_of_this_kind:
            if "{} | SUCCESS | rc=0 >>".format(host) in rsp:
                print "ipmi-console on {} is stopped".format(host)
            else:
                raise Exception("ipmi-console on {} fail to stop".format(host))

    cmd = "ansible {} -i {} -m shell -a \"echo {} | " \
          "sudo -S infrasim node stop\"".\
        format(full_group, inventory_path, ssh_password)
    _, rsp = run_command(cmd)
    print rsp
    # Verify operations on all nodes are successful
    for hosts_of_this_kind in hosts.values():
        for host in hosts_of_this_kind:
            if "{} | SUCCESS | rc=0 >>".format(host) in rsp:
                print "infrasim node instance on {} is stopped".format(host)
            else:
                raise Exception("infrasim node instance on {} fail to stop".format(host))


def update_node_type():
    global inventory_path
    global hosts
    global ssh_password
    for node_type in hosts:
        cmd = "ansible {0} -i {1} -b -m shell -a \"echo {2} | " \
              "sudo -S sed -i 's/^\(type: \).*/\\1{0}/' ~/.infrasim/.node_map/default.yml\"".\
            format(node_type, inventory_path, ssh_password)
        _, rsp = run_command(cmd)
        print rsp
        for host in hosts[node_type]:
            if "{} | SUCCESS | rc=0 >>".format(host) in rsp:
                print "default.yml on {} is updated to {}".format(host, node_type)
            else:
                raise Exception("default.yml on {} fail to be updated to {}".format(host, node_type))


def start_node():
    global full_group
    global inventory_path
    global hosts
    global ssh_password

    cmd = "ansible {} -i {} -m shell -a \"echo {} | " \
          "setsid sudo -S infrasim node start\"".\
        format(full_group, inventory_path, ssh_password)
    _, rsp = run_command(cmd)
    print rsp
    # Verify operations on all nodes are successful
    for hosts_of_this_kind in hosts.values():
        for host in hosts_of_this_kind:
            if "{} | SUCCESS | rc=0 >>".format(host) in rsp:
                print "infrasim node instance on {} is started".format(host)
            else:
                raise Exception("infrasim node instance on {} fail to start".format(host))

    cmd = "ansible {} -i {} -m shell -a \"echo {} | " \
          "setsid sudo -S ipmi-console start\"".\
        format(full_group, inventory_path, ssh_password)
    _, rsp = run_command(cmd)
    print rsp
    # Verify operations on all nodes are successful
    for hosts_of_this_kind in hosts.values():
        for host in hosts_of_this_kind:
            if "{} | SUCCESS | rc=0 >>".format(host) in rsp:
                print "ipmi-console on {} is started".format(host)
            else:
                raise Exception("ipmi-console on {} fail to start".format(host))


def validate_ipmiconsole_access():
    global hosts

    for node_type in hosts:
        for host in hosts[node_type]:
            cmd = "ansible {} -i {} -m shell -a \"netstat -anp | grep 9300\"".format(node_type, inventory_path)
            while True:
                try:
                    run_command(cmd)
                    break
                except Exception as e:
                    time.sleep(0.5)
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, username="", password="", port=9300)

            except paramiko.AuthenticationException:
                print 'SSH authentication error, please check username and password'
                return False
            except paramiko.SSHException:
                print 'Error happen in SSH connect: \n{}'.format(traceback.format_exc())
                return False
            except socket.error:
                print 'WARNING', 'Socket error while connection: \n{}'.format(traceback.format_exc())
                return False
            except Exception:
                print 'WARNING', 'Fail to build SSH connection: \n{}'.format(traceback.format_exc())
                return False
            else:
                print "SSH to {} -p 9300 is validated".format(host)

            try:
                v_shell = client.invoke_shell()
                v_shell.send('help\n')
                time.sleep(1)
                str_output= ''.join(v_shell.recv(2048))
                if "quit/exit" not in str_output:
                    print "WARNING", "Fail to get correct output from ipmi-console"
                    return False

            except paramiko.SSHException:
                print 'SSH exception when execute command on remote shell: {}'.format(cmd)
            finally:
                client.close()

    return True


def validate_bmc_access():
    global hosts
    global host_to_bmc
    global inventory_path

    for node_type in hosts:
        for host in hosts[node_type]:
            cmd = "ansible {} -i {} -m shell -a \"netstat -anp | grep 623\"".format(node_type, inventory_path)
            while True:
                try:
                    run_command(cmd)
                    break
                except Exception as e:
                    time.sleep(0.5)

    for host, bmc in host_to_bmc.items():
        run_command('ipmitool -I lanplus -U admin -P admin -H {} user list'.format(bmc))


def write_stack(path):
    global hosts
    global host_to_bmc

    stack = {
        "vRacks": [
            {
                "name": "vRack1",
                "vPDU": [],
                "vSwitch": [],
                "vNode": []
            }
        ]
    }

    for node_type in hosts:
        for host in hosts[node_type]:
            node = {}
            node["name"] = "{}_{}".format(node_type, host)
            node["admin"] = {
                "ip": host,
                "username": "infrasim",
                "password": "infrasim"
            }
            node["bmc"] = {
                "ip": host_to_bmc[host],
                "username": "admin",
                "password": "admin"
            }
            node["power"] = []
            stack["vRacks"][0]["vNode"].append(node)

    with open(path, 'w') as fp:
        json.dump(stack, fp, indent=4)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "./CreateTestStack.py [ansible_inventory_path] [target_stack_path]"
        exit(-1)

    inventory_path = sys.argv[1]
    stack_path = sys.argv[2]

    print '-'*40
    print '[Validate ansible version]'
    validate_ansible()

    print '-'*40
    print '[Scan inventory file {}]'.format(inventory_path)
    scan_inventory(inventory_path)
    print json.dumps(hosts, indent=4)

    print '-'*40
    print '[Validate SSH connection]'
    if not validate_admin_access():
        sys.exit(1)

    print '-'*40
    print '[Stop running instances]'
    clear_node()

    print '-'*40
    print '[Solve arp flux]'
    solve_arp_flux()

    print '-'*40
    print '[Update node type in yml]'
    update_node_type()

    print '-'*40
    print '[Start infrasim instances]'
    start_node()

    time.sleep(2)

    print '-'*40
    print '[Validate ipmi-console access]'
    if not validate_ipmiconsole_access():
        sys.exit(1)

    print '-'*40
    print '[Validate BMC access]'
    validate_bmc_access()

    print '-'*40
    print '[Export stack description file to {}]'.format(stack_path)
    write_stack(stack_path)
