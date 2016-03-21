'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 22, 2015

@author: Tony Su
*********************************************************
'''

from lib.Device import CDevice
from lib.SNMP import CSNMP
from lib.SSH import CSSH
from lib.Apps import with_connect

OID_CHECK_LIST = {
    "INV_PROD_FORMAT_VER": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 2, 0),
    "INV_PROD_SIGNATURE": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 1, 0),
    "INV_MANUF_CODE": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 3, 0),
    "INV_UNIT_NAME": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 7, 0),
    "INV_SERIAL_NUM": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 11, 0),
    "INV_FW_REVISION": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 10, 0),
    "INV_HW_REVISION": (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 99, 9, 0),
}
OID_PDU_OUT_ON_ROOT = (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 7, 2, 3, 1, 5)
OID_PDU_OUT_PWD_ROOT = (1, 3, 6, 1, 4, 1, 3711, 24, 1, 1, 7, 2, 3, 1, 6)
INT_PDU_OUT_ON = 1
INT_PDU_OUT_OFF = 2

class CPDU(CDevice):
    def __init__(self, dict_pdu):

        CDevice.__init__(self, 'vPDU')

        self.dict_config = dict_pdu

        self.ip = self.dict_config.get('ip', '')
        self.name = self.dict_config.get('name', '')
        self.community = self.dict_config.get('community', '')

        # Build outlet mapping
        self.outlet = {}
        for str_outlet, str_password in self.dict_config.get('outlet', {}).items():
            self.outlet[str_outlet] = {
                'node': None,
                'password': str_password
            }

        self.snmp = CSNMP(self.ip, self.community)
        self.ssh_vpdu = CSSH(ip=self.ip, username='', password='', port=20022)

    def get_config(self):
        return self.dict_config

    def get_ip(self):
        return self.ip

    def get_name(self):
        return self.name

    def get_community(self):
        return self.community

    def connect(self, obj_node, str_outlet):
        '''
        Connect a node to certain outlet
        :param obj_node: virtual node instance of idic.stack.Node.CNode
        :param str_outlet: a string of "<pdu#>.<port#>", e.g. "1.1", "3.2"
        :return: True | False
            True is successfully connect PDU and node
            False is fail to connect PDU and node
        '''
        if str_outlet not in self.outlet:
            raise KeyError('Outlet {} is not defined in PDU {}'.format(str_outlet, self.name))
        if self.outlet[str_outlet]['node']:
            self.log('WARNING', '{} outlet {} is occupied by node {}, fail to connect'.
                     format(self.name, str_outlet, self.outlet[str_outlet]['node'].get_name()))
            return False
        else:
            # Some operation on SSH

            self.outlet[str_outlet]['node'] = obj_node
            if (self, str_outlet) not in obj_node.power:
                obj_node.power.append((self, str_outlet))
            self.log('INFO', 'Connect PDU {} outlet {} to node {} DONE'.
                     format(self.name, str_outlet, obj_node.get_name()))
            return True

    def disconnect(self, str_outlet):
        '''
        Disconnect an outlet
        :param str_outlet: a string of "<pdu#>.<port#>", e.g. "1.1", "3.2"
        :return: True | False
            True is successfully disconnect PDU and node
            False is fail to disconnect PDU and node
        '''
        if str_outlet not in self.outlet:
            raise KeyError('Outlet {} is not defined in PDU {}'.format(str_outlet, self.name))
        if not self.outlet[str_outlet]['node']:
            self.log('INFO', '{} outlet {} is not connected'.format(self.name, str_outlet))
            return True
        else:
            # Some operation on SSH

            obj_node = self.outlet[str_outlet]['node']
            if (self, str_outlet) in obj_node.power:
                obj_node.power.remove((self, str_outlet))
            self.outlet[str_outlet]['node'] = None
            return True

    def self_check(self):
        list_fail_item = []
        for str_check_item, oid in OID_CHECK_LIST.items():
            err_indicator, err_status, err_index, var_binds = self.snmp.get(oid)
            if err_indicator or err_status or err_index:
                self.log('ERROR', "{} (IP: {}) fail on {} check:\n"
                                  "Error indicator: {}\n"
                                  "Error status: {}\n"
                                  "Error index: {}".
                         format(self.name, self.ip, str_check_item,
                                str(err_indicator), err_status, err_index))
                list_fail_item.append(str_check_item)
            else:
                self.log('INFO', "{} check {} is done".
                         format(self.name, str_check_item))

        if list_fail_item:
            self.log('ERROR', 'Fail items: {}'.format(str(list_fail_item)))
            return False
        else:
            return True

    def get_outlet_password(self, str_outlet):
        if str_outlet not in self.outlet:
            raise KeyError('Outlet {} is not defined in PDU {}'.format(str_outlet, self.name))
        return self.outlet[str_outlet].get('password', '')

    @with_connect('ssh_vpdu')
    def set_outlet_password(self, str_outlet, str_password):
        # Some operation on SSH
        pass

    def match_outlet_password(self, str_outlet, str_password=''):
        '''
        Match a password on a certain outlet before power on/off operation
        :param str_outlet: a string of "<pdu#>.<port#>", e.g. "1.1", "3.2"
        :param str_password: password in string
        '''
        oid = OID_PDU_OUT_PWD_ROOT + tuple(str_outlet.split('.'))
        if not str_password:
            str_password = self.get_outlet_password(str_outlet)

        err_indicator, err_status, err_index, var_binds = self.snmp.set(oid, 'OctetString', str_password)
        if err_indicator or err_status or err_index:
            self.log('ERROR', "{} (IP: {}) fail to match password \"{}\" on outlet {}:\n"
                              "Error indicator: {}\n"
                              "Error status: {}\n"
                              "Error index: {}".
                     format(self.name, self.ip, str_password, str_outlet,
                            str(err_indicator), err_status, err_index))
            return False
        else:
            self.log('INFO', "{} match password on outlet {}: {} is done".
                     format(self.name, str_outlet, str_password))
            return True

    def power_on(self, str_outlet):
        '''
        Power on a certain outlet
        :param str_outlet:  a string of "<pdu#>.<port#>", e.g. "1.1", "3.2"
        '''
        oid = OID_PDU_OUT_ON_ROOT + tuple(str_outlet.split('.'))
        err_indicator, err_status, err_index, var_binds = self.snmp.set(oid, 'Integer', INT_PDU_OUT_ON)
        if err_indicator or err_status or err_index:
            self.log('ERROR', "{} (IP: {}) fail to power on outlet {}:\n"
                             "Error indicator: {}\n"
                             "Error status: {}\n"
                             "Error index: {}".
                     format(self.name, self.ip, str_outlet,
                            str(err_indicator), err_status, err_index))
            return False
        else:
            self.log('INFO', "{} power on outlet {} is done".
                     format(self.name, str_outlet))
            return True

    def power_off(self, str_outlet):
        '''
        Power off a certain outlet
        :param str_outlet:  a string of "<pdu#>.<port#>", e.g. "1.1", "3.2"
        '''
        oid = OID_PDU_OUT_ON_ROOT + tuple(str_outlet.split('.'))
        err_indicator, err_status, err_index, var_binds = self.snmp.set(oid, 'Integer', INT_PDU_OUT_OFF)
        if err_indicator or err_status or err_index:
            self.log('ERROR', "{} (IP: {}) fail to power off outlet {}:\n"
                             "Error indicator: {}\n"
                             "Error status: {}\n"
                             "Error index: {}".
                     format(self.name, self.ip, str_outlet,
                            str(err_indicator), err_status, err_index))
            return False
        else:
            self.log('INFO', "{} power off outlet {} is done".
                     format(self.name, str_outlet))
            return True
