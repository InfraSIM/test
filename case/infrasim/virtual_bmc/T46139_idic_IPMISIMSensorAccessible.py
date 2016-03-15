'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T46139_idic_IPMISIMSensorAccessible(CBaseCase):

    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_sim()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO','To try IPMI SIM sensor command accessible for each node of rack...')

                bmc_obj = obj_node.get_bmc()

                #Get product name from FRU data.
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('fru print')

                fru = {}
                for item in rsp.split('\n'):
                    key = item.split(': ')[0].strip()
                    value = item.split(': ')[-1].strip()
                    fru[key] = value

                try:
                    #Try to find the corresponding sensor id by product name from JSON file.
                    sensor_id = self.data[fru['Product Name']]

                except KeyError, e:
                    #If product name missing, block this case.
                    self.result(BLOCK,
                    """
                    KeyError: {}.
                    Please supplement product name of node ({}) and the corresponding sensor id in {}.json.
                    For more details, please read the document: https://infrasim.readthedocs.org/en/latest/
                    """
                                .format(e, e, self.__class__.__name__))
                else:

                    sensor_value = 1000.00

                    bmc_ssh = bmc_obj.ssh_ipmi_sim
                    str_rsp = bmc_ssh.send_command_wait_string(str_command = 'sensor'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)

                    if re.search("Available sensor commands", str_rsp) == None:
                        #If sensor command not available
                        self.result(FAIL, 'BMC IPMI_SIM sensor command of a node not accessible. Rack is {}, Node is {}, BMC IP is: {}'.
                                    format(obj_rack.get_name(),obj_node.get_name(), bmc_obj.get_ip()))

                    else:

                        str_rsp = bmc_ssh.send_command_wait_string(str_command = 'sensor info'+chr(13), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                        self.log('INFO', 'Sensor info of node: {}'.format(str_rsp))

                        str_rsp = bmc_ssh.send_command_wait_string(str_command = 'sensor value get {} {}'.format(sensor_id, chr(13)), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                        self.log('INFO', 'Sensor (id:{}) value of node: {}'.format(sensor_id, str_rsp))

                        bmc_ssh.send_command_wait_string(str_command = 'sensor value set {} {} {}'.format(sensor_id, sensor_value, chr(13)), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)
                        self.log('INFO', 'Sensor (id:{}) value of node set to: {}'.format(sensor_id, sensor_value))

                        str_rsp = bmc_ssh.send_command_wait_string(str_command = 'sensor value get {} {}'.format(sensor_id, chr(13)), wait = 'IPMI_SIM',int_time_out =3, b_with_buff = False)

                        if re.search(str(sensor_value), str_rsp) != None:
                            self.log('INFO', 'Sensor (id:{}) value of node set to: {} succeed!'.format(sensor_id, sensor_value))

                        else:
                            self.result(FAIL, 'Failed to set up BMC sensor (id:{}) value through IPMI_SIM. Rack is {}, Node is {}, BMC IP is: {}'.
                                    format(sensor_id, obj_rack.get_name(),obj_node.get_name(), bmc_obj.get_ip()))

                time.sleep(1)

    def deconfig(self):

        CBaseCase.deconfig(self)

