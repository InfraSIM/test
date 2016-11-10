from case.CBaseCase import *
import gevent
import re


class T72404_idic_IPMIConsoleSensorAutoMode(CBaseCase):
    '''
    [Purpose ]: Verify ipmi-console can set sensor to auto mode
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        self.enable_ipmi_console()
    
    def test(self):
        print json.dumps(self.data, indent=4)
        gevent.joinall([gevent.spawn(self.test_auto_mode, obj_node)
                        for obj_node in self.stack.walk_node()])
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def test_auto_mode(self, obj_node):

        str_ret, str_rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('fru print 0')

        fru = {}
        for item in str_rsp.split('\n'):
            key = item.split(': ')[0].strip()
            value = item.split(': ')[-1].strip()
            fru[key] = value

        print "node:", obj_node.get_name()
        print json.dumps(fru, indent=4)

        # If ipmitool not response as expected, key shall be lost
        # and this test shall be blocked on this node
        if 'Product Name' not in fru:
            self.result(BLOCK, 'Node {} fail to get fru print information, '
                               'response of ipmitool is:\n{}'.
                        format(self.test_node.get_name(), str_rsp))
            return

        test_sensor = self.data[fru['Product Name']]

        ipmi_console = obj_node.ssh_ipmi_console

        # Set sensor to auto mode
        rsp = ipmi_console.send_command_wait_string(str_command="sensor mode set {} auto".
                                                    format(test_sensor)+chr(13),
                                                    wait="IPMI_SIM>")
        p = re.compile(r"Sensor [\w\-_] changed to auto")
        m = p.match(rsp)
        if m:
            self.log('INFO', 'Node {} sensor {} is set to auto mode via ipmi-console'.
                     format(obj_node.get_name(), test_sensor))
        else:
            self.result(FAIL, 'Node {} sensor {} fails to be set to auto mode via '
                              'ipmi-console:\n{}'.
                        format(obj_node.get_name(), test_sensor, rsp))

        # Set sensor back to user mode
        rsp = ipmi_console.send_command_wait_string(str_command="sensor mode set {} user".
                                                    format(test_sensor)+chr(13),
                                                    wait="IPMI_SIM>")
        p = re.compile(r"Sensor [\w\-_] changed to user")
        m = p.match(rsp)
        if m:
            self.log('INFO', 'Node {} sensor {} is set back to user mode via ipmi-console'.
                     format(obj_node.get_name(), test_sensor))
        else:
            self.result(FAIL, 'Node {} sensor {} fails to be set back to user mode via '
                              'ipmi-console:\n{}'.
                        format(obj_node.get_name(), test_sensor, rsp))
