'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Jan 4th, 2016
This module is used to manipulate nodes, vPDU and vSwitch
@author: Payne.Wang@emc.com
*********************************************************
'''

import sys
import json
import re
import time
import os
import argparse

sys.path.append("../")
from lib.restapi import APIClient

# set the args
parser = argparse.ArgumentParser(description="Set the deploy parameters")
parser.add_argument("-f", dest="conf_file", default="stack_requirement.json", type=str,
                    help="Set the config file (default: stack_requirement.json)")
parser.add_argument("-l", dest="ova_file", default=[], nargs='+',
                    help="Set the ova list (default: [])")
parser.add_argument("-d", dest="delay_time", default=20,
                    help="Set the duration time (default: 20)", )
parser.add_argument("-n", dest="nodes_network", default="VM Network", type=str,
                    help="Set the nodes network (default: \"VM Network)\")")
args = parser.parse_args()
CONF_FILE = args.conf_file
OVA_FILE = args.ova_file
DELAY_TIME = args.delay_time
NODES_NETWORK = args.nodes_network
CONF_DATA = None
VRACKSYSTEM_INFO = {}
URI_PRE = None
OBJ_REST = None
HYPERVISORS = []
GEN_CONF = {
    "vRackSystem": {},
    "available_HyperVisor": [],
    "vRacks": []
}
NODES_TYPE = ["quanta_t41", "quanta_d51", "s2600kp",
              "dell_c6320", "dell_r630", "vnode"]
PDU_CONFIG = {
    "hawk": {
        "name": "hawk",
        "database": "ipia.db",
        "snmpdata": "hawk"
    },
    "sentry": {
        "name": "SENTRY",
        "database": "sentry3.db",
        "snmpdata": "sentry"
    }
}
SHOULD_DEL = True


def exit_func(e):
    print "ERROR: {}".format(str(e))
    print "####################################################"
    print json.dumps(GEN_CONF, indent=4)
    exit(1)


def conf_parse():
    print "\033[93m[Parse Requirement]\033[0m"
    global CONF_DATA
    global VRACKSYSTEM_INFO
    global GEN_CONF
    conf_file_path = "../configure/{}".format(CONF_FILE)
    try:
        with open(conf_file_path) as configure:
            CONF_DATA = json.load(configure)
            VRACKSYSTEM_INFO = CONF_DATA["vRackSystem"]
            GEN_CONF["vRackSystem"] = CONF_DATA["vRackSystem"]

    except IOError, e:
        exit_func(e)
    except KeyError, e:
        exit_func(e)


def set_rest_obj():
    print "\033[93m[Build vRackSystem Access]\033[0m"
    global URI_PRE
    global OBJ_REST
    if not CONF_DATA:
        print "WARNING: configure file has not been parased, " \
              "will call conf_parse func first"
        conf_parse()

    try:
        OBJ_REST = APIClient(username=VRACKSYSTEM_INFO["username"],
                             password=VRACKSYSTEM_INFO["password"],
                             session_log=False)
        URI_PRE = "{}://{}:{}{}/".format(VRACKSYSTEM_INFO["protocol"],
                                         VRACKSYSTEM_INFO["ip"],
                                         VRACKSYSTEM_INFO["port"],
                                         VRACKSYSTEM_INFO["root"])
    except KeyError, e:
        exit_func(e)


def rest_api(target=None, action="get", payload=None, expect_status=200):
    url = "{}{}".format(URI_PRE, target)
    response = OBJ_REST.restful(url_command=url,
                                rest_action=action,
                                rest_payload=payload)
    if response["status"] != expect_status:
        error_msg = "can't get the response correctly by issuing the api: \n" \
                    "[{}]{} " \
                    "HTTP status: {}\n" \
                    "Payload:\n{}". \
            format(action, url, response["status"],
                   json.dumps(payload, indent=4))
        exit_func(error_msg)

    try:
        rest_api_data = json.loads(response["json"])
    except TypeError:
        rest_api_data = response["json"]
    except ValueError:
        rest_api_data = response["json"]
    return rest_api_data


def get_expect_esxi(raw_data, expect_esxi):
    try:
        esxi_info = raw_data
        for esxi in esxi_info:
            if esxi["esxiIP"] == expect_esxi:
                return esxi
    except KeyError, e:
        exit_func(e)


def get_hypervisor():
    print "\033[93m[Traverse Hypervisor]\033[0m"
    global HYPERVISORS
    global GEN_CONF
    esxi_data = rest_api(target="esxi")
    try:
        hypervisors = CONF_DATA["available_HyperVisor"]
    except KeyError, e:
        exit_func(e)

    for hypervisor_key, hypervisor in hypervisors.items():
        hypervisor_name = re.match("(.*)(\d+)", hypervisor_key).groups()
        hypervisor_credential = re.match("(.*)/(.*)@(.*)", hypervisor).groups()
        hypervisor_username = hypervisor_credential[0]
        hypervisor_pwd = hypervisor_credential[1]
        hypervisor_ip = hypervisor_credential[2]

        GEN_CONF["available_HyperVisor"].append(
            {"name": "hyper" + hypervisor_name[1],
             "type": hypervisor_name[0],
             "ip": hypervisor_ip,
             "username": hypervisor_username,
             "password": hypervisor_pwd}
        )

        esxi = get_expect_esxi(esxi_data, hypervisor_ip)

        if esxi:
            HYPERVISORS.append(esxi)
            esxi["name"] = "hyper" + hypervisor_name[1]
        else:
            payload = {"esxiIP": hypervisor_ip,
                       "username": hypervisor_username,
                       "password": hypervisor_pwd}
            rest_api(target="esxi/", action="post",
                     payload=payload, expect_status=201)
            time.sleep(10)
            esxi_data = rest_api(target="esxi")
            esxi = get_expect_esxi(esxi_data, hypervisor_ip)
            if esxi:
                HYPERVISORS.append(esxi)
                esxi["name"] = "hyper" + hypervisor_name[1]
            else:
                error_msg = "can't get the added esxi by issuing the api"
                exit_func(error_msg)

    print "get the hypervisors:"
    print json.dumps(HYPERVISORS, indent=4)


def get_datastore():
    print "\033[93m[Traverse Datastore]\033[0m"
    global HYPERVISORS
    for hypervisor in HYPERVISORS:
        hypervisor_id = hypervisor["id"]
        datastores = rest_api(target="esxi/{}/datastores".
                              format(str(hypervisor_id)))
        hypervisor["datastores"] = datastores
        print "datastores {} are found for hypervisor {}". \
            format(datastores, hypervisor_id)
    print "datastores are added for each hypervisor:"
    print json.dumps(HYPERVISORS, indent=4)


def get_vms(esxi_id):
    vms = list(rest_api(target="esxi/{}/getvms".format(esxi_id)))
    for vm in vms:
        if "dhcp" in vm["name"].lower():
            vms.remove(vm)
    return vms


def delete_all_vms(esxi_id):
    vms = get_vms(esxi_id)
    for vm in vms:
        vm_name = vm["name"]
        if "dhcp" in vm_name.lower():
            continue
        rest_api(target="esxi/{}/destroyvm".format(esxi_id),
                 action="post",
                 payload={"name": vm_name},
                 expect_status=200)


def deploy_node(esxi_id, datastore, power, nodetype, ova, network):
    url = "esxi/{}/deploy".format(esxi_id)
    payload = {"datastore": datastore,
               "power": power,
               "count": "1",
               "nodetype": nodetype,
               "controlnetwork": network,
               "duration": DELAY_TIME
               }
    if ova:
        payload["ova"] = ova
    return rest_api(target=url, action="post", payload=payload)


def operate_node(esxi_id, vm_name, operation):
    print "start to {} vm {} on {}".format(operation, vm_name, esxi_id)
    operation = "{}vm".format(operation)
    rest_api(target="esxi/{}/{}".format(esxi_id, operation),
             action="post", payload={"name": vm_name})


def vpdu_restart(esxi_id, vpdu_ip):
    print "start to restart vpdu for {} on {}".format(vpdu_ip, esxi_id)
    rest_api(target="esxi/{}/vpdurestart".format(esxi_id),
             action="post", payload={"ip": vpdu_ip})


def vpdu_config_update(esxi_id, vpdu_ip, vpdu_type):
    print "start to update the vpdu config info"
    if vpdu_type not in PDU_CONFIG:
        exit_func("type of vpdu {} is not supported".format(vpdu_type))
    config_info = PDU_CONFIG[vpdu_type]
    rest_api(target="esxi/{}/vpdusetpduinfo".format(esxi_id),
             action="post",
             payload={
                 "ip": vpdu_ip, "name": config_info["name"],
                 "database": config_info["database"],
                 "snmpdata": config_info["snmpdata"]
             })


def vpdu_mapping(esxi_id, esxi_name, vpdu_list, node_list):
    if not vpdu_list:
        print "there is no vpdu, no need to map"
        return

    print "\033[93m> set vPDU ...\033[0m"
    global GEN_CONF
    # add vPDU ESXi host configuration information
    vpdu_dict = {}
    vms = get_vms(esxi_id)
    for i in range(len(vpdu_list)):
        vpdu = vpdu_list[i]
        for vm in vms:
            if vpdu == vm["name"]:
                vpdu_type = vm["name"].split('_')[1]
                vpdu_admin_ip = vm["ip"][0]
                try:
                    vpdu_control_ip = vm["ip"][1]
                except IndexError:
                    print "There is no control network for the vPDU"
                    vpdu_control_ip = vpdu_admin_ip
                vpdu_config_update(esxi_id, vpdu_control_ip, vpdu_type)
                vpdu_dict[vpdu] = {}
                vpdu_dict[vpdu]['admin'] = vpdu_admin_ip
                vpdu_dict[vpdu]['control'] = vpdu_control_ip
                GEN_CONF["vRacks"][-1]["vPDU"][i]["ip"] = vpdu_control_ip
                GEN_CONF["vRacks"][-1]["vPDU"][i]["outlet"] = {}
                rest_api(target="esxi/{}/vpduhostadd".format(esxi_id),
                         action="post", payload={"ip": vpdu_control_ip})
                break

    # mapping the nodes
    node_count = len(node_list)
    loops = (node_count + 143) / 144

    for loop in range(loops):
        vpdu = vpdu_list[loop]
        vpdu_admin_ip = vpdu_dict[vpdu]['admin']
        vpdu_control_ip = vpdu_dict[vpdu]['control']

        for i in range(1, 7):
            for j in range(1, 25):
                try:
                    node_name = node_list.pop(0)
                except IndexError:
                    vpdu_restart(esxi_id, vpdu_control_ip)
                    return
                pos_key = "{}.{}".format(i, j)
                rest_api(target="esxi/{}/vpdupwdadd".format(esxi_id),
                         action="post",
                         payload={"ip": vpdu_control_ip,
                                  "pdu": i, "port": j,
                                  "password": "idic"})
                GEN_CONF["vRacks"][-1]["vPDU"][loop]["outlet"][pos_key] = "idic"

                for vm in vms:
                    if node_name == vm["name"]:
                        datastore = vm["datastore"]
                        rest_api(target="esxi/{}/vpdumapadd".format(esxi_id),
                                 action="post",
                                 payload={"ip": vpdu_control_ip,
                                          "dt": datastore,
                                          "name": node_name,
                                          "pdu": i, "port": j})
                        node_info = {}
                        node_info["name"] = node_name
                        node_info["datastore"] = datastore
                        node_info["power"] = [{"vPDU": vpdu,
                                               "outlet": pos_key}]
                        node_info["network"] = []
                        node_info["bmc"] = {
                            "ip": vm["ip"][0] if vm["ip"] else "",
                            "username": "admin",
                            "password": "admin"}
                        node_info["hypervisor"] = esxi_name
                        GEN_CONF["vRacks"][-1]["vNode"].append(node_info)
        vpdu_restart(esxi_id, vpdu_control_ip)


def deploy_vrack(vpdu_num, vswitch_num, vnodes):
    global GEN_CONF
    total_nodes = 0
    pdu_list = []
    node_list = []
    for vnode in vnodes:
        total_nodes += vnodes[vnode]
    if vpdu_num and (total_nodes + 143) / 144 > vpdu_num:
        error_msg = "ERROR: {} vpdu(s) to be deployed are not enough to " \
                    "manage {} nodes".format(vpdu_num, total_nodes)
        return error_msg
    for hypervisor in HYPERVISORS:
        # should add the resource check here, if not satified, continue
        GEN_CONF["vRacks"][-1]["hypervisor"] = hypervisor["name"]
        GEN_CONF["vRacks"][-1]["vPDU"] = []
        GEN_CONF["vRacks"][-1]["vSwitch"] = []
        GEN_CONF["vRacks"][-1]["vNode"] = []

        hypervisor_id = hypervisor["id"]
        if SHOULD_DEL:
            print "WARNING: delete all the nodes in ESXi {}".format(
                hypervisor_id)
            delete_all_vms(hypervisor_id)

        print '\033[93m> deploy vpdu ...\033[0m'
        # deploy vpdu
        if vpdu_num != 0:
            pdu_ova = None
            download_pdu_ova = rest_api(target="ova/list",
                                        action="post",
                                        payload={"type": "pdu"})
            print "downloaded pdu ova: {}".format(download_pdu_ova)
            if not download_pdu_ova:
                error_msg = "ERROR: there is no downloaded vpdu ova"
                exit_func(error_msg)

            for ova in OVA_FILE:
                if "vpdu" in ova:
                    print "vpdu {} ova is transferred by user".format(ova)
                    pdu_ova = ova
                    OVA_FILE.remove(pdu_ova)
                    break

            if pdu_ova and pdu_ova not in download_pdu_ova:
                error_msg = "ERROR: expected vpdu ova {} has " \
                            "not been downloaded".format(pdu_ova)
                exit_func(error_msg)
            for i in range(vpdu_num):
                pdu_name = deploy_node(hypervisor_id,
                                       hypervisor["datastores"][0],
                                       "on", "pdu", pdu_ova, 0)
                pdu_list.append(pdu_name)
                GEN_CONF["vRacks"][-1]["vPDU"].append(
                    {"hypervisor": hypervisor["name"],
                     "name": pdu_name,
                     "datastore": hypervisor["datastores"][0],
                     "community": "ipia"}
                )
            print pdu_list

        if vswitch_num != 0:
            pass

        if not vnodes:
            # for CI
            print "INFO: the default number for CI test is 2"
            vnode = {}
            for node_ova in OVA_FILE:
                try:
                    node_type = re.match("vbmc_(.*)_\w+\.ova", node_ova).group(
                        1)
                    vnodes[node_type] = 2
                except AttributeError:
                    error_msg = "ERROR: the ova file {} is not " \
                                "expected".format(node_ova)
                    exit_func(error_msg)

            if not vnodes:
                print "CI don't provide the OVA file"
                for node_type in NODES_TYPE:
                    download_node_ova = rest_api(target="ova/list",
                                                 action="post",
                                                 payload={"type": node_type})
                    if download_node_ova:
                        vnodes[node_type] = 2
            if not vnodes:
                print "WARNING: there is no ova available for CI node deployment"

        print '\033[93m> deploy vnodes ...\033[0m'
        for node_type, build_count in vnodes.items():
            download_node_ova = rest_api(target="ova/list",
                                         action="post",
                                         payload={"type": node_type})
            if not download_node_ova:
                error_msg = "ERROR: there is no downloaded {} ova".format(
                    node_type)
                exit_func(error_msg)

            for node_ova in OVA_FILE:
                if node_type in node_ova:
                    print "ova is provided by user for {} deployment".format(
                        node_type)
                    break
            else:
                node_ova = None

            if node_ova and node_ova not in download_node_ova:
                error_msg = "ERROR: expected vpdu ova {} has " \
                            "not been downloaded".format(node_ova)
                exit_func(error_msg)

            for i in range(build_count):
                print '{} {} ...'.format(node_type, node_ova)
                node_name = deploy_node(hypervisor_id,
                                        hypervisor["datastores"][0],
                                        "on", node_type, node_ova,
                                        NODES_NETWORK)
                node_list.append(node_name)
            del vnodes[node_type]
        print node_list
        time.sleep(30)
        if vnodes:
            error_msg = "ERROR: there is no ova transferred for the nodes: " \
                        "{}".format(vnodes.keys())
            exit_func(error_msg)
        time.sleep(30)
        vpdu_mapping(hypervisor_id, hypervisor["name"], pdu_list, node_list)
        vms = get_vms(hypervisor_id)
        for vm in vms:
            vm_name = vm["name"]
            operate_node(hypervisor_id, vm_name, "poweron")
    return "successfully"


def deploy_vracks():
    print "\033[93m[Deploy vRack]\033[0m"
    global GEN_CONF
    try:
        vracks = CONF_DATA["vRacks"]
    except KeyError, e:
        exit_func(e)
    for key, vrack in vracks.items():
        GEN_CONF["vRacks"].append({})
        GEN_CONF["vRacks"][-1]["name"] = key
        try:
            vpdu_num = vrack["vPDU"]
            vswitch_num = vrack["vSwitch"]
            vnodes = vrack["vNode"]
            for node in vnodes.keys():
                if node.lower() not in NODES_TYPE:
                    error_msg = "node type {} is not expected".format(node)
                    raise KeyError(error_msg)
        except KeyError, e:
            print "ERROR: the info of vrack {} is wrong, " \
                  "because: {}".format(key, str(e))
            continue
        message = deploy_vrack(vpdu_num, vswitch_num, vnodes)
        if "ERROR" in message:
            print message
            continue


def set_conf():
    print "\033[93m[Write Config to JSON]\033[0m"
    try:
        str_path = "../../test.json"
        with open("../../test.json", "w") as result_conf:
            result_conf.write(json.dumps(GEN_CONF, indent=4))
        print 'Configuration can be found at {}'.format(
            os.path.abspath(str_path))
    except IOError:
        error_msg = "ERROR: can't generate the configure file"
        exit_func(error_msg)


if __name__ == '__main__':
    conf_parse()
    set_rest_obj()
    get_hypervisor()
    get_datastore()
    deploy_vracks()
    set_conf()
