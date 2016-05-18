from case.CBaseCase import *

class T73329_idic_StressIPMISIM(CBaseCase):
    '''
    [Purpose ]: Stress test with long duration, big amount IPMI traffic.
    [Author  ]: forrest.gu@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
    
    def test(self):
        retry = self.data['retry']
        time_start = time.time()
        gevent.joinall([gevent.spawn(self.ipmi_test, obj_node, retry)
                        for obj_node in self.stack.walk_node()])
        time_end = time.time()
        self.log('INFO', 'Stress ipmitool "0x06 0x01" {} times finish, time consumption: {} s'.
                 format(retry, time_end-time_start))
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def ipmi_test(self, obj_node, retry):
        for i in range(retry):
            ret, cc, _ = obj_node.get_bmc().ipmi.ipmitool_raw_cmd('0x06 0x01')
            if ret != 0:
                self.result(FAIL, 'Node {} ipmitool 0x06 0x01 fail at {}/{}, ret: {}'.
                            format(obj_node.get_name(), i+1, retry, ret))
                return
            elif cc != '0x00':
                self.result(FAIL, 'Node {} ipmitool 0x06 0x01 fail at {}/{}, completion code: {}'.
                            format(obj_node.get_name(), i+1, retry, ret))
                return
            else:
                self.log('INFO', 'Node {} ipmitool 0x06 0x01 pass at {}/{}'.
                         format(obj_node.get_name(), i+1, retry))
