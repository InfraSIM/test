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
                self.log('INFO', 'Wait 10 seconds for power off ...')
                time.sleep(10)
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
                self.log('INFO', 'Wait 10 seconds for power on ...')
                time.sleep(10)

        # Wait for node boot, 60s after last node boot
        self.log('INFO', 'Wait 60 seconds after last node power on to get IP ...')
        time.sleep(60)
        self.env_stack_verify()

        for obj_rack in self.stack.get_rack_list():
            obj_hyper = self.stack.hypervisors[obj_rack.get_hypervisor()]
            for obj_node in obj_rack.get_node_list():
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
        for obj_node in self.stack.walk_node():

            # Wait until vBMC's IPMI start to response
            # Retry every 3 seconds for 40 times
            b_bmc_ready = False
            int_retry = 40
            int_gap = 3
            for i in range(int_retry):
                ret, cc, rsp = obj_node.get_bmc().ipmi.ipmitool_raw_cmd('0x00 0x01')
                # BMC is not on, power on the virtual node in first loop
                if ret != 0:
                    self.log('WARNING', 'Node {} vBMC doesn\'t response, ret: {}, retry...'.
                             format(obj_node.get_name(), ret))
                    time.sleep(int_gap)
                    continue
                # System power is not on, do ipmi power on
                elif rsp[0] != '0x01':
                    ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis power on')
                    if ret == 0:
                        continue
                    else:
                        self.result(FAIL, 'Node {} system fail to do chassis power on after T36713, '
                                          'ret: {}, completion code: {}, response data: {}'.
                                    format(obj_node.get_name(), ret, cc, rsp))
                        break
                else:
                    b_bmc_ready = True
                    break

            if b_bmc_ready:
                continue
            else:
                self.result(FAIL, 'Node {} in unexpected status after T36713, last ipmitool retry ret: {}'.
                            format(obj_node.get_name(), ret))

        CBaseCase.deconfig(self)
