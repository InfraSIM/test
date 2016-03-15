'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *

class T36713_idic_ControlNodePower(CBaseCase):
    '''
    [Purpose ]: Control node power via snmp to PDU
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 25
    [Tickets ]: SST-628
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        try:
            self.stack.walk_pdu().next()
        except StopIteration:
            self.result(BLOCK, 'No PDU in stack at all')
    
    def test(self):
        for obj_rack in self.stack.get_rack_list():
            obj_hyper = self.stack.hypervisors[obj_rack.get_hypervisor()]
            for obj_node in obj_rack.get_node_list():

                if not obj_node.power:
                    self.log('WARNING', 'Node {} power is not managed by any PDU'.
                             format(obj_node.get_name()))
                    continue

                # Power off
                obj_node.power_off()
                self.log('INFO', 'Wait 5 seconds for power off ...')
                time.sleep(5)
                str_power_status = self.stack.rest_get_node_power_status(
                    obj_hyper.get_ip(),
                    obj_node.get_name()
                )
                if str_power_status != 'Off':
                    self.result(FAIL, 'Node {} power status is {} after power off'.
                                format(obj_node.get_name(), str_power_status))
                else:
                    self.log('INFO', 'Node {} power off done'.format(obj_node.get_name()))

                # Power on
                obj_node.power_on()
                self.log('INFO', 'Wait 5 seconds for power on ...')
                time.sleep(5)
                str_power_status = self.stack.rest_get_node_power_status(
                    obj_hyper.get_ip(),
                    obj_node.get_name()
                )
                if str_power_status != 'On':
                    self.result(FAIL, 'Node {} power status is {} after power on'.
                                format(obj_node.get_name(), str_power_status))
                else:
                    self.log('INFO', 'Node {} power on done'.format(obj_node.get_name()))
    
    def deconfig(self):
        # To do: Case specific deconfig
        self.log('INFO', 'Wait 30s for all nodes to boot ...')
        time.sleep(30)
        CBaseCase.deconfig(self)
