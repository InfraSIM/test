'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from Serial import CSerial
from Telnet import CTelnet
from Logger import CLogger

class Connect(CLogger):
    '''
    Abstraction of real connection type: serial and telnet.
    '''
    TELNET='telnet'
    SERIAL='serial'

    def __init__(self, connect_type, para, session_log = ''):
        CLogger.__init__(self)

        connect_type = connect_type.lower()

        if connect_type == self.TELNET:
            if type(para[1]) != int:
                para[1] = int(para[1], 10)

            self._connection = CTelnet(para, session_log)
            self.int_port = para[1]

        elif connect_type == self.SERIAL:
            if type(para[0]) != int:
                para[0] = int(para[0], 10)
            if type(para[1]) != int:
                para[1] = int(para[1], 10)

            self._connection = CSerial(para, session_log)
            self.int_port = para[0] - 1

        else:
            raise Exception('Interface type not supported(%s)' % connect_type)

    def __del__(self):
        self._connection.disconnect()

    def __getattr__(self, attr):
        if hasattr(self._connection, attr):
            return getattr(self._connection, attr)
        raise AttributeError, '%s instance has no attribute \'%s\'' \
                                % (self.__class__.__name__, attr)

    def set_logger(self, obj_logger):
        CLogger.set_logger(self, obj_logger)
        self._connection.set_logger(obj_logger)

    def reset(self):
        self._connection.reset()
        self._connection.disconnect()

    def raw_log_file(self):
        return self._connection.get_raw_log_file()
