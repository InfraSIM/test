'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import types
import re
import math
from functools import wraps


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
