'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import re
from case.CBaseCase import *


class T216342_idic_WarEnclosure(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_chassis_ssh()
        # To do: Case specific config

    def test(self):
        for obj_chassis in self.stack.walk_chassis():
            self.war_chassis_access(obj_chassis)
            self.war_chassis_ipmi_cmd(obj_chassis)
            self.war_verify_smbios_data(obj_chassis)
            self.war_pcie_topo(obj_chassis)
            self.war_nvme_drives_count(obj_chassis)
            self.war_chassis_shared_data(obj_chassis)
            self.war_nic_scheme(obj_chassis)
            self.war_ses(obj_chassis)

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)
        # to set nvme temp to default
        set_temp_cmd = "'sudo nvme set-feature /dev/nvme0n1 -f 4 -v 0x14d'"
        for obj_chassis in self.stack.walk_chassis():
            for node in obj_chassis.get_node_list():
                obj_chassis.send_command_to_guest(node, set_temp_cmd)

    def war_chassis_access(self, chassis):
        # Verify both nodes (node_a and node_b) can be access in war chassis
        chassis_instance_name, node_ins_a, node_ins_b = chassis.get_instance_name()
        self.log("INFO", "Chassis runtime instance name: {}, node_a: {}, node_b: {}".format(chassis_instance_name,
                                                                                            node_ins_a,
                                                                                            node_ins_b))
        for node in chassis.get_node_list():
            if chassis.guest_access(node):
                self.log("INFO", "Guest OS on node: {} is started ".format(node.ip))

    def war_chassis_ipmi_cmd(self, chassis):
        # verify ipmitool command response is correct:
        # 'lan print', 'fru print'
        for node in chassis.get_node_list():
            lan_rsp = chassis.ipmi_lan_print(node)
            if "Auth Type" in lan_rsp:
                self.log('INFO', 'ipmitool lan print info is correct, response info \n: {}'.format(lan_rsp))
            else:
                self.result(FAIL, 'ipmitool lan print info is incorrect,\n response info \n: {}!!'.format(lan_rsp))

            fru_rsp = chassis.ipmi_fru_print(node)
            if "Builtin FRU Device (ID 0)" in fru_rsp:
                self.log('INFO', 'ipmitool fru info on node: {} is correct, response info \n: {}'.
                         format(node.name, fru_rsp))
            else:
                self.result(FAIL, 'ipmitool fru info on node: {} is incorrect,\n response info \n: {}!!'.
                         format(node.name, fru_rsp))

    def war_verify_smbios_data(self, chassis):
        # Verify smbios info is correct
        for node in chassis.get_node_list():
            dmi_cmd = "sudo dmidecode -t1"
            rsp_dict = chassis.send_command_to_guest(node, dmi_cmd)
            if "900-564-061" in rsp_dict.get("stdout"):
                self.log('INFO', 'smbios data on node: {} is verified'.format(node.name))
            else:
                self.result(FAIL, 'smbios data on node: {} is incorrect'.format(node.name))

    def war_pcie_topo(self, chassis):
        # Verify network (eno1) bdf is correct
        for node in chassis.get_node_list():
            pci_cmd = "lspci -s bd:00.0"
            rsp_dict = chassis.send_command_to_guest(node, pci_cmd)
            if "82540EM" in rsp_dict.get("stdout"):
                self.log('INFO', 'Network Topo on node: {} is verified'.
                         format(node.name))
            else:
                self.result(FAIL, 'PCIE Topo on node: {} is incorrect, stdout: {}'.
                         format(node.name, rsp_dict.get("stdout")))

    def war_nvme_drives_count(self, chassis):
        '''
        Verify nvme drive count is correct:
        Intel model(0a54) : 23
        PMC model(8606) : 2
        '''
        for node in chassis.get_node_list():
            nvme1_cmd = "lspci |grep -c 0a54"
            rsp1_dict = chassis.send_command_to_guest(node, nvme1_cmd)
            if "23" in rsp1_dict.get("stdout"):
                self.log('INFO', 'NVME drive (Intel model) count on node: {} is verified'.
                         format(node.name))
            else:
                self.result(FAIL, 'NVME drive (Intel model) count on node: {} is incorrect, stdout: {}'.
                         format(node.name, rsp1_dict.get("stdout")))

            nvme2_cmd = "lspci |grep -c 8606"
            rsp2_dict = chassis.send_command_to_guest(node, nvme2_cmd)
            if "2" in rsp1_dict.get("stdout"):
                self.log('INFO', 'NVME drive (Intel model) count on node: {} is verified'.
                         format(node.name))
            else:
                self.result(FAIL, 'NVME drive (Intel model) count on node: {} is incorrect, \n stdout: {}'.
                                  format(node.name, rsp2_dict.get("stdout")))

    def war_chassis_shared_data(self, chassis):
        # Use nvme set-feature/get-feature to verify chassis shared data
        node_list = chassis.get_node_list()
        get_temp_cmd = "sudo nvme get-feature /dev/nvme0n1 -f 4 -s 0"
        set_temp_cmd = "sudo nvme set-feature /dev/nvme0n1 -f 4 -v 0xbef"
        get_a_rsp = chassis.send_command_to_guest(node_list[0], get_temp_cmd)
        get_b_rsp = chassis.send_command_to_guest(node_list[1], get_temp_cmd)
        if get_a_rsp.get("stdout") == get_b_rsp.get("stdout"):
            self.log('INFO', 'Temp value is the same before set-feature on node_a and node_b')

        chassis.send_command_to_guest(node_list[0], set_temp_cmd)
        get_a_rsp_after_set = chassis.send_command_to_guest(node_list[0], get_temp_cmd)
        get_b_rsp_after_set = chassis.send_command_to_guest(node_list[1], get_temp_cmd)
        if get_a_rsp_after_set.get("stdout") == get_b_rsp_after_set.get("stdout"):
            self.log('INFO', 'Temp value is the same after setting on node_a and node_b')
        else:
            self.result(FAIL, 'Temp value did not set successfully, rsp: \n'
                                'node_a: {} \n node_b: {} \n'.format(get_a_rsp_after_set.get("stdout"),
                                                                     get_b_rsp_after_set.get("stdout")))

    def war_nic_scheme(self, chassis):
        # There are total 12 NIC ports have different names
        for node in chassis.get_node_list():
            nic_cmd = "ifconfig -a"
            nic_rsp = chassis.send_command_to_guest(node, nic_cmd)
            nicnum = nic_rsp.get("stdout").strip().split().count("HWaddr")
            if nicnum == 12:
                self.log('INFO', 'NIC number on node: {} is expected'.format(node.name))
            else:
                self.result(FAIL, 'NIC number on node: {} is incorrect, \n rsp: {}'.format(node.name,
                                                                                          nic_rsp.get("stdout")))

    def war_ses(self, chassis):
        # Verify the SCSI inquiry and SES pages 0x02 info
        for node in chassis.get_node_list():
            scsi_inq = "sudo test_eses -e 0 -q std"
            inq_rsp = chassis.send_command_to_guest(node, scsi_inq)
            if "ESES Enclosure" in inq_rsp.get("stdout"):
                self.log('INFO', 'SCSI inquiry std command passed on node: {}'.format(node.name))
            else:
                self.result(FAIL, 'Cannot get the SCSI std inquiry info, rsp: {}'.format(inq_rsp.get("stdout")))

            ses_cmd = "sudo test_eses -e 0 -g 02"
            ses_rsp = chassis.send_command_to_guest(node, ses_cmd)
            rst = ses_rsp.get("stdout")
            if re.search("Temperature Sensor Status elements(.*)4", rst) and \
                    re.search("Enclosure Services Controller Electronics elements(.*)4", rst) and \
                    re.search("Enclosure Status elements(.*)6", rst) and \
                    re.search("Array Device Slot Status elements(.*)26", rst) and \
                    re.search("SAS Expander Status elements(.*)4", rst) and \
                    re.search("SAS Connector Status elements(.*)49", rst) and \
                    re.search("Expander Phy Status elements(.*)48", rst):
                self.log('INFO', 'SES Page(02) info correct on node: {}'.format(node.name))
            else:
                self.result(FAIL, 'SES Page(02) info on node: () is not correct,\n rsp: {}'.
                         format(node.name, ses_rsp.get("stdout")))
