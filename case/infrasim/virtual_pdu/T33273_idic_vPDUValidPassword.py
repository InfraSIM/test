'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from case.CBaseCase import *


class T33273_idic_vPDUValidPassword(CBaseCase):
    '''
    [Purpose ]: 
    [Author  ]: june.zhou@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)

    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        self.result(BLOCK, 'No PDU for infrasim-compute at all')
        return
        try:
            self.stack.walk_pdu().next()
        except StopIteration:
            self.result(BLOCK, 'No PDU in stack at all')

    def test(self):
        self.log('INFO', 'Start Test...')
        # power off
        for obj_rack in self.stack.get_rack_list():
            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    pdu_pwd = power_unit[0].get_outlet_password(power_unit[1])
                    power_unit[0].match_outlet_password(power_unit[1], pdu_pwd)
                    if not power_unit[0].power_off(power_unit[1]):
                        self.result(FAIL, 'Node failed powering off with correct '
                                          'PDU outlet password. Node is {}, '
                                          'outlet is {}.'.
                                    format(obj_node.get_name(), power_unit[1]))
                    else:
                        self.log('INFO', 'Node succeed in powering off with correct '
                                         'PDU outlet password. Node is {}, '
                                         'outlet is {}'.
                                 format(obj_node.get_name(), power_unit[1]))

                self.log('INFO', 'Wait 10 seconds for power off ...')
                time.sleep(10)

        # power on
        for obj_rack in self.stack.get_rack_list():
            obj_hyper = self.stack.hypervisors[obj_rack.get_hypervisor()]
            for obj_node in obj_rack.get_node_list():
                for power_unit in obj_node.power:
                    pdu_pwd = power_unit[0].get_outlet_password(power_unit[1])
                    power_unit[0].match_outlet_password(power_unit[1], pdu_pwd)
                    if not power_unit[0].power_on(power_unit[1]):
                        self.result(FAIL, 'Node failed powering on with correct PDU '
                                          'outlet password. Node is {}, outlet is {}.'.
                                    format(obj_node.get_name(), power_unit[1]))
                    else:
                        self.log('INFO', 'Node succeed in powering on with correct PDU '
                                         'outlet password. Node is {}, outlet is {}'.
                                 format(obj_node.get_name(), power_unit[1]))

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

        self.log('INFO', 'End Test...')

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
                    self.log('WARNING', 'Node {} vBMC doesn\'t response, retry...'.
                             format(obj_node.get_name()))
                    time.sleep(int_gap)
                    continue
                # System power is not on, do ipmi power on
                elif rsp[0] != '0x01':
                    ret, rsp = obj_node.get_bmc().ipmi.ipmitool_standard_cmd('chassis power on')
                    if ret == 0:
                        continue
                    else:
                        self.result(FAIL, 'Node {} system fail to do chassis power on after T33273, '
                                          'ret: {}, completion code: {}, response data: {}'.
                                    format(obj_node.get_name(), ret, cc, rsp))
                        break
                else:
                    b_bmc_ready = True
                    break

            if b_bmc_ready:
                continue
            else:
                self.result(FAIL, 'Node {} in unexpected status after T33273'.format(obj_node.get_name()))

        CBaseCase.deconfig(self)
