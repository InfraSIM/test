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
        self.enable_ipmi_console()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'To try IPMI SIM sensor command accessible for node {}...'.
                         format(obj_node.get_name()))

                bmc_obj = obj_node.get_bmc()

                # Get product name from FRU data.
                ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('fru print 0')
                # Test fail if this nodes ipmi can't response
                if ret != 0:
                    self.result(BLOCK, 'Node {} on rack {} fail to response ipmitool fru print'.
                                format(obj_node.get_name(), obj_rack.get_name()))
                    continue

                fru = {}
                for item in rsp.split('\n'):
                    key = item.split(': ')[0].strip()
                    value = item.split(': ')[-1].strip()
                    fru[key] = value

                try:
                    # Try to find the corresponding sensor id by product name from JSON file.
                    sensor_dic = self.data[fru['Product Name']]
                    sensor_id = sensor_dic.keys()[0]
                    sensor_value_expected = sensor_dic[sensor_id]

                except KeyError, e:
                    # If product name missing, block this case.
                    self.result(BLOCK,
                    """
                    KeyError: {}.
                    Please supplement product name of node ({}) and the corresponding sensor id in {}.json.
                    For more details, please read the document: https://infrasim.readthedocs.org/en/latest/
                    """
                                .format(e, e, self.__class__.__name__))
                    continue

                sensor_value = 1000.00

                ipmi_console = obj_node.ssh_ipmi_console
                str_rsp = ipmi_console.send_command_wait_string(str_command='sensor'+chr(13),
                                                                wait='info mode value',
                                                                int_time_out=30,
                                                                b_with_buff=False)
                if re.search("Available sensor commands", str_rsp) is None:
                    # If sensor command not available
                    self.result(FAIL, 'BMC IPMI_SIM sensor command is not accessible. Rack is {}, '
                                      'Node is {}, BMC IP is: {}'.
                                format(obj_rack.get_name(), obj_node.get_name(), bmc_obj.get_ip()))

                else:
                    str_rsp = ipmi_console.send_command_wait_string(str_command='sensor info'+chr(13),
                                                                    wait='degrees C',
                                                                    int_time_out=10,
                                                                    b_with_buff=False)
                    self.log('INFO', 'Sensor info of node: {}'.format(str_rsp))
                    if not str_rsp:
                        self.result(FAIL,
                                    'Failed to get sensor info by IPMI_SIM. '
                                    'Rack is {}, Node is {}, BMC IP is: {}'.
                                    format(obj_rack.get_name(), obj_node.get_name(), bmc_obj.get_ip()))
                        return

                    # Clear previous ssh stream
                    str_rsp = ipmi_console.send_command_wait_string(str_command=chr(13),
                                                                    wait='IPMI_SIM>',
                                                                    int_time_out=10,
                                                                    b_with_buff=False)
                    # Add 1s sleep to meet lab network latency
                    time.sleep(1)

                    str_rsp = ipmi_console.send_command_wait_string(str_command='sensor value get {} {}'
                                                                    .format(sensor_id, chr(13)),
                                                                    wait='IPMI_SIM>',
                                                                    int_time_out=10,
                                                                    b_with_buff=False)
                    self.log('INFO', 'Sensor (id:{}) value of node: {}'.format(sensor_id, str_rsp))

                    ipmi_console.send_command_wait_string(str_command='sensor value set {} {} {}'
                                                          .format(sensor_id, sensor_value, chr(13)),
                                                          wait='IPMI_SIM>',
                                                          int_time_out=10,
                                                          b_with_buff=False)
                    self.log('INFO', 'Sensor (id:{}) value of node set to: {}'.format(sensor_id, sensor_value))

                    str_rsp = ipmi_console.send_command_wait_string(str_command='sensor value get {} {}'
                                                                    .format(sensor_id, chr(13)),
                                                                    wait='IPMI_SIM>',
                                                                    int_time_out=10,
                                                                    b_with_buff=False)

                    if re.search(str(sensor_value_expected), str_rsp) is not None:
                        self.log('INFO', 'Sensor (id:{}) value of node set to: {} succeed!'
                                 .format(sensor_id, sensor_value))

                    else:
                        self.result(FAIL,
                                    'Failed to set up BMC sensor (id:{}) value through IPMI_SIM. '
                                    'Rack is {}, Node is {}, BMC IP is: {}'.
                                    format(sensor_id, obj_rack.get_name(), obj_node.get_name(), bmc_obj.get_ip()))
                time.sleep(1)

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)


