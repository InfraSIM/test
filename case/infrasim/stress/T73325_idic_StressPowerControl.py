from case.CBaseCase import *
import json

class T73325_idic_StressPowerControl(CBaseCase):
    '''
    [Purpose ]: Stress PDU power on/off node, and check fundamental service
    [Author  ]: forrest.gu@emc.com
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
        self.enable_bmc_ssh()
    
    def test(self):
        self.retry = self.data['retry']
        time_start = time.time()

        for i in range(self.retry):
            self.curr = i
            if not self.power_control_test():
                time_end = time.time()
                self.result(FAIL, 'Stress power control fail at {}/{}, time consumption: {} s'.
                            format(self.curr+1, self.retry, time_end-time_start))
                return

        time_end = time.time()
        self.log('INFO', 'Stress power control {} times finish, time consumption: {} s'.
                 format(self.retry, time_end-time_start))
    
    def deconfig(self):
        for obj_node in self.stack.walk_node():
            obj_node.power_on()
        self.log('INFO', 'Wait 10s for nodes to power on...')
        time.sleep(10)
        CBaseCase.deconfig(self)

    def power_control_test(self):
        # For all nodes, power off node
        for obj_node in self.stack.walk_node():
            obj_node.get_bmc().ssh.disconnect()
            if not obj_node.power_off():
                self.result(FAIL, '[{}/{}] Fail to power off node {}'.
                            format(self.curr+1, self.retry, obj_node.get_name()))
                return False
            else:
                self.log('INFO', '[{}/{}] Power off node {} done'.
                         format(self.curr+1, self.retry, obj_node.get_name()))
            time.sleep(5)

        # For all nodes, power on node
        for obj_node in self.stack.walk_node():
            if not obj_node.power_on():
                self.result(FAIL, '[{}/{}] Fail to power on node {}'.
                            format(self.curr+1, self.retry, obj_node.get_name()))
                return False
            else:
                self.log('INFO', '[{}/{}] Power on node {} done'.
                         format(self.curr+1, self.retry, obj_node.get_name()))
            time.sleep(5)

        # For all nodes, check status
        for obj_node in self.stack.walk_node():
            # Wait until ipmi stack response
            b_ipmi_ready = False
            for i in range(20):
                ret, cc, rsp = obj_node.get_bmc().ipmi.ipmitool_raw_cmd('0x00 0x01')
                # BMC is not on, power on the virtual node in first loop
                if ret != 0:
                    self.log('WARNING', 'Node {} vBMC doesn\'t response, waiting...'.
                             format(obj_node.get_name()))
                    time.sleep(3)
                else:
                    b_ipmi_ready = True
                    break
            if b_ipmi_ready:
                self.log('INFO', 'Node {} ipmi stack is ready'.format(obj_node.get_name()))
            else:
                self.result(FAIL, '[{}/{}] Node {} fail to response IOL command 1 minutes after AC on, '
                                  'ret: {}, completion code: {}, rsp: {}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), ret, cc, rsp))
                return False

            # Remote shell "ps" and check process status
            obj_node.get_bmc().ssh.connect()
            rsp = obj_node.get_bmc().ssh.remote_shell('ps')
            if rsp['exitcode'] != 0:
                self.result(FAIL, '[{}/{}] Node {} fail to response remote shell command, response: \n{}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), json.dumps(rsp, indent=4)))
                return False
            # Check process
            str_output = rsp['stdout']
            str_key = '/usr/bin/vmtoolsd'
            if str_output.find(str_key) < 0:
                self.result(FAIL, '[{}/{}] Node {} process missing: {}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            else:
                self.log('INFO', '[{}/{}] Node {} process found: {}'.
                         format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            str_key = 'python /etc/ipmi/util/ipmi_sim.py'
            if str_output.find(str_key) < 0:
                self.result(FAIL, '[{}/{}] Node {} process missing: {}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            else:
                self.log('INFO', '[{}/{}] Node {} process found: {}'.
                         format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            str_key = '/bin/ipmi_sim'
            if str_output.find(str_key) < 0:
                self.result(FAIL, '[{}/{}] Node {} process missing: {}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            else:
                self.log('INFO', '[{}/{}] Node {} process found: {}'.
                         format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            str_key = '/bin/socat'
            if str_output.find(str_key) < 0:
                self.result(FAIL, '[{}/{}] Node {} process missing: {}'.
                            format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            else:
                self.log('INFO', '[{}/{}] Node {} process found: {}'.
                         format(self.curr+1, self.retry, obj_node.get_name(), str_key))
            b_qemu_found = False
            for i in range(20):
                str_qemu = 'qemu-system-x86_64'
                str_startcmd = '{startcmd} /bin/sh /etc/ipmi/startcmd'
                if str_output.find(str_qemu) >= 0:
                    self.log('INFO', '[{}/{}] Node {} process found: {}'.
                             format(self.curr+1, self.retry, obj_node.get_name(), str_qemu))
                    b_qemu_found = True
                    break
                elif str_output.find(str_startcmd) >= 0:
                    self.log('INFO', '[{}/{}] Node {} process found: {}'.
                             format(self.curr+1, self.retry, obj_node.get_name(), str_startcmd))
                    self.log('INFO', 'Wait until qemu boot ...')
                    time.sleep(3)
                    rsp = obj_node.get_bmc().ssh.remote_shell('ps')
                    str_output = rsp['stdout']
                elif str_output.find(str_qemu) < 0 and str_output.find(str_startcmd) < 0:
                    self.result(FAIL, '[{}/{}] Node {} process missing: {} and {}'.
                                format(self.curr+1, self.retry, obj_node.get_name(), str_qemu, str_startcmd))
                    break
            if not b_qemu_found:
                self.result(FAIL, '[{}/{}] Node {} fail to start {} in 1 minutes'.
                            format(self.curr+1, self.retry, obj_node.get_name(), str_qemu))

        time.sleep(10)
        return True
