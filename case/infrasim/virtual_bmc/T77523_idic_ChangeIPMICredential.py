from case.CBaseCase import *
from lib.IOL import CIOL
import gevent


class T77523_idic_ChangeIPMICredential(CBaseCase):
    '''
    [Purpose ]: Change IPMI credential and verify IPMI access
    [Author  ]: forrest.gu@emc.com
    [Sprint  ]: Lykan Sprint 
    [Tickets ]: SST-
    '''
    def __init__(self):
        CBaseCase.__init__(self, self.__class__.__name__)
    
    def config(self):
        CBaseCase.config(self)
        # To do: Case specific config
    
    def test(self):
        gevent.joinall([gevent.spawn(self.test_ipmi_credential_change, obj_node)
                        for obj_node in self.stack.walk_node()])
    
    def deconfig(self):
        # To do: Case specific deconfig
        CBaseCase.deconfig(self)

    def test_ipmi_credential_change(self, obj_node):
        obj_bmc = obj_node.get_bmc()
        bmc_ip = obj_bmc.get_ip()
        bmc_username = obj_bmc.get_username()

        bmc_password = obj_bmc.get_password()
        iol_origin = CIOL(str_ip=bmc_ip,
                          str_user=bmc_username,
                          str_password=bmc_password)

        bmc_password_new = bmc_password+"_new"
        iol_new = CIOL(str_ip=bmc_ip,
                       str_user=bmc_username,
                       str_password=bmc_password_new)

        ###################
        # Update and test #
        ###################

        # Update password
        self.log('INFO', 'Update node {} BMC password to "{}"...'.
                 format(obj_node.get_name(), bmc_password_new))
        ret, rsp = iol_origin.ipmitool_standard_cmd("user set password 2 {}".
                                                    format(bmc_password_new))
        if ret != 0:
            self.result(FAIL, 'Fail to set node {} BMC password to "{}"'.
                        format(obj_node.get_name(), bmc_password_new))
        else:
            self.log('INFO', 'Node {} BMC password is set to "{}"'.
                     format(obj_node.get_name(), bmc_password_new))

        # Try new password is workable
        # At the same time, original password is invalid now
        ret, rsp = iol_origin.ipmitool_standard_cmd("sensor list")
        if ret == 0:
            self.result(FAIL, 'Node {} original password "{}" is expected to be '
                              'invalid after password updated to "{}", but it '
                              'is still working now'.
                        format(obj_node.get_name(), bmc_password, bmc_password_new))
        else:
            self.log('INFO', 'Node {} original password "{}" is invalid now, as expected'.
                     format(obj_node.get_name(), bmc_password))

        ret, rsp = iol_new.ipmitool_standard_cmd("sensor list")
        if ret != 0:
            self.result(FAIL, 'Node {} new password "{}" is invalid'.
                        format(obj_node.get_name(), bmc_password_new))
        else:
            self.log('INFO', 'Node {} new password "{}" is valid now, as expected'.
                     format(obj_node.get_name(), bmc_password_new))

        ####################
        # Recover and test #
        ####################

        # Update password back
        self.log('INFO', 'Update node {} BMC password back to "{}"...'.
                 format(obj_node.get_name(), bmc_password))
        ret, rsp = iol_new.ipmitool_standard_cmd("user set password 2 {}".
                                                 format(bmc_password))
        if ret != 0:
            self.result(FAIL, 'Fail to set node {} BMC password back to "{}"'.
                        format(obj_node.get_name(), bmc_password))
        else:
            self.log('INFO', 'Node {} BMC password is set back to "{}"'.
                     format(obj_node.get_name(), bmc_password))

        # Try original password is workable
        # At the same time, test password is invalid now
        ret, rsp = iol_new.ipmitool_standard_cmd("sensor list")
        if ret == 0:
            self.result(FAIL, 'Node {} test password "{}" is expected to be '
                              'invalid after password updated back to "{}", but it '
                              'is still working now'.
                        format(obj_node.get_name(), bmc_password_new, bmc_password))
        else:
            self.log('INFO', 'Node {} test password "{}" is invalid now, as expected'.
                     format(obj_node.get_name(), bmc_password_new))

        ret, rsp = iol_origin.ipmitool_standard_cmd("sensor list")
        if ret != 0:
            self.result(FAIL, 'Node {} original password "{}" is invalid'.
                        format(obj_node.get_name(), bmc_password))
        else:
            self.log('INFO', 'Node {} original password "{}" is valid now, as expected'.
                     format(obj_node.get_name(), bmc_password))

