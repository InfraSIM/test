'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *
import re

class T36706_idic_vBMCDataEmulation(CBaseCase):


    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        self.enable_ipmi_sim()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Validate data emulation for node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                obj_bmc = obj_node.get_bmc()

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

                    #Set sensor value and then validate
                    bmc_ssh = obj_bmc.ssh_ipmi_sim
                    bmc_ssh.send_command_wait_string(str_command = 'sensor value set {} {} {}'.format(sensor_id, sensor_value,chr(13)), wait = 'IPMI_SIM', int_time_out = 3, b_with_buff = False)
                    str_rsp = bmc_ssh.send_command_wait_string(str_command = 'sensor value get {} {}'.format(sensor_id, chr(13)), wait = 'IPMI_SIM', int_time_out = 3, b_with_buff = False)

                    if not re.search(str(sensor_value), str_rsp):
                        #If failed to set sensor value
                        self.result(FAIL, 'Node {} on rack {} failed to set sensor value to {}, '
                                    'ipmitool return:\n{}'.
                                    format(obj_node.get_name(), obj_rack.get_name(), sensor_value, str_rsp))

                    else:
                        self.log('INFO', 'Set sensor value succeed: {}'.format(str_rsp))

                time.sleep(1)

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)


