'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import types
import re
import math
import json
import hashlib
from functools import wraps
from lib.SSH import CSSH


def convert_short_to_lsb_msb(data):
    str_data_s = '0x%04x' % data
    str_data_lsb = str_data_s[-2:]
    str_data_msb = str_data_s[2:4]
    str_data_lsb = '0x' + str_data_lsb
    str_data_msb = '0x' + str_data_msb
    return str_data_lsb, str_data_msb


def clear_list(list_data): 
    while(list_data != []):
        list_data.pop()
    return list_data


def strip_color_code(str):
    '''
    ************************************************
    [Author  ]: June.Zhou@emc.com
    [Function]: It will strip color code from texttable string, eg. test output from vpdu map list is texttable string.
                usage example: raw_data = strip_color_code(content)
    [Input   ]: str  -  texttable string to strip color code from
    [Output  ]: raw string that with all color code striped
    [History ]
        - June.Zhou@emc.com 03/17/2016
            initial edition
    ************************************************
    '''
    strip_ANSI_escape_sequences_sub = re.compile(r"""
    \x1b     # literal ESC
    \[       # literal [
    [;\d]*   # zero or more digits or semicolons
    [A-Za-z] # a letter
    """, re.VERBOSE).sub
    return strip_ANSI_escape_sequences_sub("", str)


def byte_in_response(list_response, index):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to get byte from list_response.
    [Input   ]:
        list_response  -  an int list
        index          -  an int which make this function return one byte
                       -  an int list which make this function return a list
    [Output  ]:     
        A byte or a list of byte, depending on index
    [History ] 
        - Forrest.Gu@emc.com 05/08/2014
            initial edition
    ************************************************
    '''
    if type(index) is types.IntType:
        return list_response[index]
    elif type(index) is types.StringType:
        return list_response[int(index,0)]
    elif type(index) is types.ListType:
        list_bytes = [0] * len(index)
        for i in range(len(index)):
            list_bytes[i] = byte_in_response(list_response, index[i])
        return list_bytes


def bit_in_response(list_response, byte_index, bit_index):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to get a bit from response data.
    [Input   ]:
        list_response  -  an int list
        byte_index     -  byte index to read
        bit_index      -  bit index in the byte
    [Output  ]:     
        0 | 1
        raise Exception in case of failure.
    [History ] 
        - Forrest.Gu@emc.com 05/08/2014
            initial edition
    ************************************************
    '''
    byte = 0
    
    # byte_index validity check
    if type(byte_index) is types.StringType:
        byte = list_response[int(byte_index, 0)]
    elif type(byte_index) is types.IntType:
        byte = list_response[byte_index]
    else:
        raise Exception('unrecognized type of byte index: %s'%type(byte_index))
        
    # bit_index validity check
    if type(bit_index) is types.StringType:
        bit_index = int(bit_index, 0)
        if bit_index < 0 or bit_index > 7:
            raise Exception('Bit index out of range')
        else:
            return byte >> bit_index & 1
    elif type(byte_index) is types.IntType:
        if bit_index < 0 or bit_index > 7:
            raise Exception('Bit index out of range')
        else:
            return byte >> bit_index & 1
    else:
        raise Exception('unrecognized type of bit_index: %s'%type(bit_index))


def int_to_byte(int_a, str_format = 'lsb', int_byte_length = 2):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to transfer int to MSB or LSB list.
    [Input   ]:
        int_a           -  an integer
        str_format      -  'lsb' or 'msb', not case sensitive
        int_byte_length -  target LSB/MSB list length
    [Output  ]:     
        list_byte       -  A list of hex integer number
    [History ] 
        - Forrest.Gu@emc.com 05/14/2014
            initial edition
    ************************************************
    '''
    
    # format validity check
    if str_format.lower() == 'lsb':
        index = 0
        index_step = 1
    elif str_format.lower() == 'msb':
        index = -1
        index_step = -1
    else:
        print "Not a valid format."
        return []
    
    # input validity check
    if type(int_a) is not types.IntType:
        print "Not a valid integer."
        return []
    else:
        list_byte = [0] * int_byte_length
        for i in range(int_byte_length):
            list_byte[index] = int_a % 256
            int_a /= 256 
            index += index_step
        if int_a != 0:
            print "Warning: int overflow!"
        return list_byte


def byte_to_int(list_byte, str_format = 'lsb'):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to transfer 
                MSB or LSB byte list to an integer.
    [Input   ]:
        list_byte       -  A list of hex integer number
        str_format      -  'lsb' or 'msb', not case sensitive
        int_byte_length -  target LSB/MSB list length
    [Output  ]:     
        int_a           -  an integer
    [History ] 
        - Forrest.Gu@emc.com 07/07/2014
            First edition
    ************************************************
    '''
    # format validity check
    if str_format.lower() == 'lsb':
        index = -1
        index_step = -1
    elif str_format.lower() == 'msb':
        index = 0
        index_step = 1
    else:
        print "Not a valid format."
        return []
    
    # input validity check
    for i in list_byte:
        if type(i) is not types.IntType:
            print "Not a valid integer."
            return []
    
    # sum
    int_a = 0
    for i in range(len(list_byte)):
        int_a = int_a * 256 + list_byte[index]
        index += index_step
    
    return int_a
    
    
def split_list(list_a, int_len):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to split a long list into 
                small segments in same size (except the last one).
    [Input   ]:
        list_a          -  input list
        int_len         -  segment length
    [Output  ]:     
        list_b          -  output list contains splited list
    [History ] 
        - Forrest.Gu@emc.com 05/22/2014
            initial edition
    ************************************************
    '''
    int_l=int(math.ceil(len(list_a)/float(int_len)))
#    print int_l
    list_b = [0]*int_l
    
    for i in range(int_l):
        list_b[i] = list_a[i*int_len:(i+1)*int_len]
        
    return list_b


def str_to_ascii(str_a):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is designed to transfer a string to
                a ASCII list.
    [Input   ]: str_a -  input string
    [Output  ]: list_a -  ASCII code in list
    [Exception]:
            'FAIL', 'Input parameter is not a valid string'
    [History ] 
        - Forrest.Gu@emc.com 08/06/2014
            initial edition
    ************************************************
    '''
    if type(str_a) is types.StringType:
        return map(lambda a:ord(a), str_a)
    else:
        raise Exception('FAIL', 'Input parameter is not a valid string')


def tolerance(num_a, num_refer, num_diff, str_type = 'absolute'):
    '''
    ************************************************
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is to judge if num_a is in the tolerance with
                defined reference and diff.
    [Input   ]: num_a -  the number to judge, should be int or float
                num_refer - reference
                num_diff - tolerance from reference
                str_type - 'absolute'|'percent'
                            For 'percent' type, num_diff should be the percentage
                            e.g. num_diff = 5 means 5%
    [Output  ]: True - num_a is in the tolerance range
                False - num_a is out of tolerance range
    [Exception]:
            'FAIL', 'args[0] is not int, float or long'
            'FAIL', 'args[1] is not int, float or long'
            'FAIL', 'args[2] is not int, float or long'
            'FAIL', 'args[2] is out of range as a percentage'
            'FAIL', 'args[3] type should be absolute or percent'
    [History ] 
        - Forrest.Gu@emc.com 11/05/2014
            initial edition
    ************************************************
    '''
    # Type check
    if type(num_a) not in [types.IntType, types.FloatType, types.LongType]:
        raise Exception('FAIL', 'args[0] is not int, float or long')
    if type(num_refer) not in [types.IntType, types.FloatType, types.LongType]:
        raise Exception('FAIL', 'args[1] is not int, float or long')
    if type(num_diff) not in [types.IntType, types.FloatType, types.LongType]:
        raise Exception('FAIL', 'args[2] is not int, float or long') 
    if str_type not in ['absolute', 'percent']:
        raise Exception('FAIL', 'args[3] type should be absolute or percent')
    
    if str_type == 'percent':
        if num_diff < -100 or num_diff > 100:
            raise Exception('FAIL', 'args[2] is out of range as a percentage')
    
    num_diff = abs(num_diff)
    
    if str_type == 'absolute':
        if num_a >= num_refer - num_diff and num_a <= num_refer + num_diff:
            return True
        else:
            return False
    if str_type == 'percent':
        absolute_diff = num_a * float(num_diff) / 100
        if num_a >= num_refer - absolute_diff and num_a <= num_refer + absolute_diff:
            return True
        else:
            return False


def ascii_to_char(int_ascii_code):
    '''
    ************************************************
    [Author  ]: eric.wang5@emc.com
    [Function]: This function is designed to translate 
                an ASCII code to a character.
    [Input   ]: int_ascii_code
    [Output  ]: str_char
    [Exception]:
            "FAIL", "Input parameter is not a valid ASCII code."
    [History ] 
        - eric.wang5@emc.com 12/17/2014
            initial edition
    ************************************************
    '''
    if type(int_ascii_code) is not types.IntType:
        raise Exception("FAIL", "The input parameter is not an integer type.")
    if int_ascii_code < 0 or int_ascii_code > 127:
        raise Exception("FAIL", "Tbe input paramter is out of range (0-127).")
    return chr(int_ascii_code)


def is_valid_ip(ip):
    '''
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is to judge if ip is a valid IP, in str or int list
    [Input   ]: ip - the IP to judge, should be string or list
    [Output  ]: True - ip is valid
                False - ip is not valid
    '''
    
    if type(ip) in [types.StringType, types.UnicodeType]:
        p = re.search('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', ip)
        if p:
            for i in range(1,5):
                if int(p.group(i),0) not in range(0,256):
                    return False
            return True
        else:
            return False
    elif type(ip) is types.ListType:
        if len(ip) != 4:
            return False
        else:
            for i in range(4):
                if type(ip[i]) is not types.IntType:
                    return False
                elif ip[i] not in range(0,256):
                    return False
            return True
    else:
        return False


def ip_str(ip):
    '''
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is to translate IP into a string like
                e.g. '192.168.1.1'
    [Input   ]: ip - the IP to transfer
    [Output  ]: str_ip - IP in string
    '''
    
    if not is_valid_ip(ip):
        raise Exception('FAIL', 'Import IP is not valid: %s' % str(ip))
    
    if type(ip) is types.StringType:
        str_ip = ip
    elif type(ip) is types.ListType:
        str_ip = '.'.join([str(i) for i in ip])
        
    return str_ip


def ip_digit_list(ip):
    '''
    [Author  ]: Forrest.Gu@emc.com
    [Function]: This function is to translate IP into a digit list
                e.g. [192,168,1,1]
    [Input   ]: ip - the IP to transfer
    [Output  ]: lst_ip - IP in digit list
    [Exception]:
            'FAIL', 'Import IP is not valid: %s'
    '''
    
    if not is_valid_ip(ip):
        raise Exception('FAIL', 'Import IP is not valid: %s' % str(ip))
    
    if type(ip) is types.StringType:
        lst_ip = [int(i,0) for i in ip.split('.')]
    elif type(ip) is types.ListType:
        lst_ip = ip
    
    return lst_ip


class SEL():
    @classmethod
    def sel(self, gen_id=None, \
                   sensor_type=None, \
                   sensor_num=None, \
                   event_type=None, \
                   event_data=[None, None, None], \
                   ext_data=None):
        '''
        Return a dict representing a sel:
        '''
        _sel={'gen_id':gen_id, \
             'sensor_type':sensor_type, \
             'sensor_num':sensor_num, \
             'event_type':event_type, \
             'event_data':event_data, \
             'ext_data':ext_data
             }
        return _sel


    @classmethod
    def sel_check_match_entry(self, source_sel, dest_sel):
        '''
        check if two given sel dict match and reture True/False.
        dest_sel must be a dict following the format defined in _sel().
        '''

        return self.sel_check_match_field(source_sel ,\
                dest_sel['gen_id'], \
                dest_sel['sensor_type'], \
                dest_sel['sensor_num'], \
                dest_sel['event_type'], \
                dest_sel['event_data'], \
                dest_sel['ext_data'], \
                )


    @classmethod
    def sel_check_match_field(self, source_sel, \
                            gen_id=None, \
                            sensor_type=None, \
                            sensor_num=None, \
                            event_type=None, \
                            event_data=[None, None, None], \
                            ext_data=None \
                            ):
        '''
        Compare SEL with given fields;
        None in a field means we don't care this field.
        '''

        if gen_id is not None:
            gen_id=gen_id.lower()
            #provide multiple alternatives to compare:
            if source_sel['GenId'] not in gen_id.split():
                return False

        if sensor_type is not None:
            sensor_type=sensor_type.lower()
            #provide multiple alternatives to compare:
            if source_sel['SensorType'] not in sensor_type.split():
                return False

        if sensor_num is not None:
            sensor_num=sensor_num.lower()
            #provide multiple alternatives to compare:
            if source_sel['SensorNo'] not in sensor_num.split():
                return False

        if event_type is not None:
            event_type=event_type.lower()
            #provide multiple alternatives to compare:
            if source_sel['EventDirType'] not in event_type.split():
                return False

        t_list=source_sel['EvtData'].split()
        for i in range(3):
            if event_data[i] is not None:
                #if event_data[i].lower() != t_list[i].lower():
                if event_data[i] != t_list[i]:
                    return False

        # do fuzzy search for extended data;
        # if the string given is found in sel extended data,
        # we regard this as "Matched".

        if ext_data is not None:
            if source_sel['string_ext_data'].find(ext_data) == -1:
                return False

        return True


class with_connect(object):
    '''
    This is a decorator to detect if an interface has been connected
    The connection instance MUST have an interface is_connectedS()

    There are 2 usages:

    1. This decorator can be used for interface instance as class variable,
    which is passed in as a string, the variable's name.
    e.g.
    @with_connect('conn_ssh'),
    then the decorator shall help you check if instance's conn_ssh is connected
    decorator shall treat first arg as self.

    2. If you pass something else rather than a string, the decorator shall
    check if it has an attribute is_connected and do fn().
    '''
    def __init__(self, conn):
        self._conn = conn

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Usage 1
            if type(self._conn) is str:
                obj_self = args[0]
                obj_conn = getattr(obj_self, self._conn)
                if obj_conn.is_connected():
                    return fn(*args, **kwargs)
                else:
                    raise OSError('Interface {} of instance {} is not connected'.
                                  format(self._conn, obj_self))
            # Usage 2
            else:
                if hasattr(self._conn, 'is_connected'):
                    if self._conn.is_connected():
                        return fn(*args, **kwargs)
                    else:
                        raise OSError('Interface {} is not connected'.format(self._conn))
                else:
                    raise AttributeError('Object {} has no function is_connected'.format(self._conn))
        return wrapper


def arp_query_ip(server, username, password, mac):
    '''
    Get IP address according to the MAC address, from target
    server, wich credential username:password
    :param server: server name
    :param username: server username
    :param password: server password
    :param mac: MAC address of the target node
    :return: IP address of the target node
    '''
    conn = CSSH(ip=server,
                username=username,
                password=password)
    if not conn.connect():
        raise Exception('Fail to connect to server {} to query IP'.format(server))

    rsp = conn.remote_shell('arp -an | grep {}'.format(mac))
    if rsp['exitcode'] != 0:
        conn.disconnect()
        raise Exception('Fail to get response from server {} to query IP\n{}'.
                        format(server, json.dumps(rsp, indent=4)))

    p_ip = r'\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)'
    list_info = rsp['stdout'].split('\n')
    list_ip = []
    for each_info in list_info:
        p = re.search(p_ip, each_info)
        if p:
            if is_valid_ip(p.group(1)):
                list_ip.append(p.group(1))
    if len(list_ip) != 1:
        conn.disconnect()
        raise Exception('MAC conflict for IP: {}'.format(list_ip))
    else:
        conn.disconnect()
        return list_ip[0]


def dhcp_query_ip(server, username, password, mac):
    '''
    Get IP address according to the MAC address, from target
    server, wich credential username:password
    :param server: server name
    :param username: server username
    :param password: server password
    :param mac: MAC address of the target node
    :return: IP address of the target node
    '''
    conn = CSSH(ip=server,
                username=username,
                password=password)
    if not conn.connect():
        raise Exception('Fail to connect to server {} to query IP'.format(server))

    rsp = conn.remote_shell('grep -A 2 -B 7 "{}" /var/lib/dhcp/dhcpd.leases | grep "lease" | tail -n 1'.format(mac))
    if rsp['exitcode'] != 0:
        conn.disconnect()
        raise Exception('Fail to get response from server {} to query IP\n{}'.
                        format(server, json.dumps(rsp, indent=4)))
    if not rsp['stdout']:
        conn.disconnect()
        raise Exception('Find no DHCP lease information for MAC: {}'.format(mac))

    p_ip = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    p = re.search(p_ip, rsp['stdout'])
    if p:
        if is_valid_ip(p.group(1)):
            conn.disconnect()
            return p.group(1)


def md5(fname):
    '''
    Caculate md5 sum for a file
    :param fname: file path
    :return: md5 sum in string
    '''
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def has_option(config, *args):
    """
    Check if config has these option chains
    :param config: a python dict
    :param args: a list of option chains, e.g.
    if config is:
    {
        "a": {"b": 1}
    }
    has_option(config, "a", "b") returns True
    has_option(config, "b") returns False
    has_option(config, "a", "c") returns False
    """
    if len(args) == 0:
        raise Exception(has_option.__doc__)
    section = config
    for option in args:
        try:
            iter(section)
        except TypeError:
            return False
        if option in section:
            section = section[option]
        else:
            return False
    return True


def update_option(config, payload, *args):
    """
    Update payload to config's target option, the option can be a key chains
    :param config: a python dict
    :param payload: target value to update
    :param args: a list of option chains, e.g.
    if config is:
    {
        "a": {"b": 1}
    }
    update_option(config, 2, "a", "b") updates config to {"a":{"b":2}}
    update_option(config, 2, "b") raises exception since no key "b" for this dict
    update_option(config, 2, "a") updates config to {"a":2}
    """
    if len(args) == 0:
        raise Exception(update_option.__doc__)
    if not has_option(config, *args):
        raise KeyError("Target object has no key chain like: {}".format(' > '.join(args)))

    target = config
    for i in range(len(args)-1):
        target = target[args[i]]
    target[args[-1]] = payload
