'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
'''
Created on Dec 30, 2015

@author: Forrest Gu
'''

from LogTool import CLogTool
from Logger import CLogger
from pysnmp.entity.rfc3413.oneliner import cmdgen

DEFAULT_SNMP_PORT = 161

class CSNMP(CLogger, CLogTool):

    def __init__(self, ip, community, port=DEFAULT_SNMP_PORT):
        self.ip = ip
        self.community = community
        self.port = port

    def get_ip(self):
        return self.ip

    def set_ip(self, str_ip):
        self.ip = str_ip

    def get_port(self):
        return self.port

    def set_port(self, port):
        if isinstance(port, int):
            self.port = port
        elif isinstance(port, str):
            self.port = int(port, 0)

    def get_community(self):
        return self.community

    def set_community(self, str_community):
        self.community = str_community

    def get(self, oid, community=''):
        '''
        Perform SNMP GET request and return a response or error indication.
        :param oid: a tuple of id in int or symbol in string
        :param community: community that can be customized to inject fault
        :return errorIndicator, errorStatus, errorIndes, varBinds:
            refer to getCmd() for detail:
            http://ports.gnu-darwin.org/net-mgmt/py-snmp4/work/pysnmp-4.1.7a/docs/pysnmp-tutorial.html
        '''
        if not community:
            community = self.community

        return cmdgen.CommandGenerator().getCmd(
            cmdgen.CommunityData(community),
            cmdgen.UdpTransportTarget((self.ip, self.port)),
            oid
        )

    def set(self, oid, value_type, value, community=''):
        '''
        Perform SNMP SET request and return a response or error indicator.
        :param oid: a tuple of id in int or symbol in string
        :param value_type: refer to pysnmp.proto.rfc1902.__all__, valid value_type are:
            ['Opaque', 'TimeTicks', 'Bits', 'Integer', 'OctetString',
           'IpAddress', 'Counter64', 'Unsigned32', 'Gauge32', 'Integer32',
           'ObjectIdentifier', 'Counter32']
        :param value: value to set
        :return errorIndicator, errorStatus, errorIndes, varBinds:
            refer to setCmd() for detail:
            http://ports.gnu-darwin.org/net-mgmt/py-snmp4/work/pysnmp-4.1.7a/docs/pysnmp-tutorial.html
        '''
        if not community:
            community = self.community

        module = __import__('pysnmp.proto.rfc1902', globals(), locals(), ['value_type'], -1)
        class_ = getattr(module, value_type)

        return cmdgen.CommandGenerator().setCmd(
            cmdgen.CommunityData(community),
            cmdgen.UdpTransportTarget((self.ip, self.port)),
            (oid, class_(value))
        )
