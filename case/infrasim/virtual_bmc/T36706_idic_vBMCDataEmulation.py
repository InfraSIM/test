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
        self.enable_ipmi_console()

    def test(self):
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                self.log('INFO', 'Validate data emulation for node {} of rack {} ...'.
                         format(obj_node.get_name(), obj_rack.get_name()))
                obj_bmc = obj_node.get_bmc()

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
                    # Try to find the corresponding sensor id status by product name from JSON file.
                    sensor_dic = self.data[fru['Product Name']]
                    sensor_id = sensor_dic.keys()[0]
                    sensor_status = sensor_dic[sensor_id]

                except KeyError, e:
                    # If product name missing, block this case.
                    self.result(BLOCK,
                    """
                    KeyError: {}.
                    Please supplement product name of node ({}) and the corresponding sensor id in {}.json.
                    For more details, please read the document: https://infrasim.readthedocs.org/en/latest/
                    """
                                .format(e, e, self.__class__.__name__))

                else:
                    expected_sel = "#" + sensor_id + " | Upper Critical going high | Asserted"

                    # Inject sensor fault and validate sel list if sel event get triggered.
                    ipmi_console = obj_node.ssh_ipmi_console
                    ipmi_console.send_command_wait_string(str_command='sensor mode set {} fault {} {}'
                                                          .format(sensor_id, sensor_status, chr(13)),
                                                          wait='IPMI_SIM',
                                                          int_time_out=30,
                                                          b_with_buff=False)

                    str_ret, str_rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('sel list')
                    if not re.search(str(expected_sel), str_rsp):
                        # If failed to set sensor fault
                        self.result(FAIL, 'Node {} on rack {} failed to set sensor {} to mode fault status uc, '
                                          'node vBMC ip is {}, ipmitool return:\n{}'
                                    .format(obj_node.get_name(), obj_rack.get_name(),
                                            sensor_id, obj_bmc.get_ip(), str_rsp))

                    else:
                        self.log('INFO', 'Set sensor mode fault succeed: {}'.format(str_rsp))

                time.sleep(1)

    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)


