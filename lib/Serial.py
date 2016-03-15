'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import time
import traceback
import platform
from threading import Event, Thread, Lock
from serial import Serial
from LogTool import CLogTool
from Logger import CLogger

    
_DEFAULT_TIMEOUT_VALUE = 120


class CSerial(CLogger, CLogTool):
    '''
    Class for serial connection, managing serial port operation including read
     and write.
    '''
    
    def __init__(self, para, str_session_log = None):
        # for event log
        CLogger.__init__(self)
        # for console output logging
        CLogTool.__init__(self, str_session_log)
        
        self._int_port = para[0]-1
        self._int_baudrate = para[1]        
        self.h_serial = Serial()
        server_platform=platform.system()

        # support cygwin;
        # in cygwin, we should use device name instead of port number in int;
        # in Windows and Linux, pyserial could get device by port number automatically;
        # However in cygwin it will try to find /dev/com32 if we only provide 32.
        if 'CYGWIN' in server_platform:
            self.h_serial.port = '/dev/ttyS%d' % self._int_port
        elif server_platform == 'Windows':
            self.h_serial.port = self._int_port
        elif server_platform == 'Linux':
            self.h_serial.port = '/dev/ttyr%02x' % self._int_port
        else:
            raise Exception('Unsupported platform: %s' % server_platform)

        self.h_serial.baudrate = self._int_baudrate
        
        # used in read_until_strings, indicating which string is found
        self._int_match_index = 0
        # indicate if the port is connected
        self._b_connected = False
        # size of searching buffer
        self._int_buffer_size = 1024*4
        # the output buffer, will be cleared in flush_buffer
        self._str_buffer = ''
        # Lock for buffer change
        self._lock_buffer = Lock()
        # used by user to request caching the output
        self._b_caching = False
        # used by user to cache the output
        self._str_cache = ''
        # used to prevent the port from being disconnected when reading data
        self._lock_connection = Lock()
        # used to track if user is checking the buffer
        self._b_checking = False
        
        # used to terminate reading thread
        self.event_thread_quit = Event()
        self.event_thread_quit.clear()

        self.thread_read = Thread(target=self.read_data)
        self.thread_read.setDaemon(True)
        self.thread_read.start()
        
    def __del__(self):
        self.disconnect()
        self.event_thread_quit.set()
        if self.thread_read.is_alive:
            self.thread_read.join()        
            
    def connect(self):
        self.log('INFO', 'Connect serial port(%s)' % str(self.get_port()))
        if not self.h_serial:
            raise Exception('h_serial is None when trying to connect.')
        if not self.h_serial.isOpen():
            try:
                self.h_serial.open()
            except:
                return False
            
        if not self.thread_read.is_alive():
            self.thread_read = Thread(target=self.read_data)
            self.thread_read.setDaemon(True)
            self.thread_read.start()
            
        return True
    
    def disconnect(self):
        self.log('INFO', 'Disconnect serial port(%s)' % str(self.get_port()))
        self._lock_connection.acquire()
        if self.is_connected():
            self.h_serial.close()
        self._lock_connection.release()
        
    def is_connected(self):
        return self.h_serial.isOpen()
    
    def send_command(self, str_command=''):
        '''
        Should always use in pair with read_until_strings().
        '''
        if not self.is_connected():
            raise Exception('FAIL', 'Serial port not connected in send_command.')
        ret = self.h_serial.write(str_command)
        if ret == 0 and str_command != '':
            raise Exception('FAIL', 'serial write fail; 0 bytes written.')
       
    def read_until_strings(self, wait, int_time_out=_DEFAULT_TIMEOUT_VALUE, b_continue=False):
        '''
        check the console output until one of the target string in wait appears
         the self._int_match_index will indicate which string is got.
        If self._int_match_index is 0, it means no target string appears
         in the given time
        '''
        self._int_match_index = 0
        if not self.is_connected():
            return ''

        self._b_checking = True
        
        # get the max length of the target strings 
        int_length = 0
        if isinstance(wait, list) or isinstance(wait, tuple):
            for str_wait in wait:
                if int_length < len(str_wait):
                    int_length = len(str_wait)
        elif isinstance(wait, basestring):
            int_length = len(wait)
        else:
            msg = 'Type(%s) not supported in read_until_string' % type(wait)
            raise Exception('FAIL', msg)
        
        # flash buffer if needed
        if not b_continue:
            self.flush_buffer()

        int_start = time.time()
        pos_start = 0
        pos_find = -1
        # detect if the timeout value is reached
        while int_time_out == 0 or time.time() - int_start < int_time_out:
            t_buffer = self._str_buffer
            
            len_buffer = len(t_buffer)
            if isinstance(wait, basestring):
                # only 1 target string
                pos_find = t_buffer.find(wait, pos_start)
                if pos_find != -1:     
                    # found:
                    self._int_match_index = 1
                    self._b_checking = False
                    return t_buffer[:pos_find] + wait
                    
            elif isinstance(wait, list) or isinstance(wait, tuple):
                # a list of target strings
                for str_wait in wait:
                    pos_find = t_buffer.find(str_wait, pos_start)
    
                    if pos_find != -1:
                        # any string found
                        self._int_match_index = wait.index(str_wait) + 1
                        self._b_checking = False
                        return t_buffer[:pos_find] + str_wait
            
            if len_buffer > int_length:              # string not found
                pos_start = len_buffer - int_length
                
        self._b_checking = False
        return ''
    
    def send_command_wait_string(self,
                                 str_command='',
                                 wait=None,
                                 int_time_out=_DEFAULT_TIMEOUT_VALUE,
                                 b_continue=False):
        '''
        write str_command to the port and wait until one of the target strings in wait 
        appears in the output or timer expired
        '''
        str_result = ''
        self._b_checking = True
        
        if not b_continue:
            self.flush_buffer()
            
        if str_command != '':
            self.send_command(str_command)
            
        if wait is not None:
            str_result = self.read_until_strings(wait, int_time_out, b_continue=True)
        
        self._b_checking = False
        return str_result
      
    def flush_buffer(self):
        '''
        Clear serial read buffer; have an impact on waiting for strings action.
        '''
        self._lock_buffer.acquire()
        self._str_buffer = ''
        self._lock_buffer.release()
        
    def read_data(self):
        '''
        function run in thread to read from serial port in a loop.
        '''
        while True:         
            try:
                               
                str_read = ''
                
                # if quit single is received, quit the thread
                if self.event_thread_quit.is_set():
                    break
                
                self._lock_connection.acquire()
                
                if not self.is_connected():
                    self._lock_connection.release()
                    continue
    
                int_length = self.h_serial.inWaiting()
                if int_length > 0:
                    str_read = self.h_serial.read(int_length)
                    
                if self._b_checking:
                    self._lock_buffer.acquire()
                    self._str_buffer += str_read
                    self._lock_buffer.release()
                else:
                    self.flush_buffer()
                    
                self._lock_connection.release()
                
                # add data to user cache
                if self._b_caching:
                    self._str_cache += str_read
                
                self.add_string_to_raw_log(str_read)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.log('ERROR', '(Serial)Exception got in read_data: %s' % traceback.format_exc())
                exit()
        self.log('INFO', '(Serial:%s) Read data thread exit' % self._int_port)

    def get_match_index(self):
        '''
        used for user to check which string is got when checking the console output in
        read_until_strings or any other function which invoked the function of
        read_until_strings, such as send_command_wait_string
        '''
        return self._int_match_index
    
    def is_port_alive(self, timeout=600):
        '''
        [Function]: This function is checking if the serial port is getting
            output from the device which is connected.
        [Input   ]: NA
        [Output  ]:
            True - if the connected port is giving output
            False - if there is no outpu from the connected port
        '''
        
        b_original_buffering_status = self._b_checking
        str_original_buffer = self._str_buffer
        self._b_checking = True
        
        # check for 5 minutes to see if there is output from the port
        time_now = time.time()
        while time.time() - time_now < timeout:
            if self._str_buffer != str_original_buffer:
                self._b_checking = b_original_buffering_status
                return True
            
        self._b_checking = b_original_buffering_status
        return False
        
    def set_logging_flag(self):
        '''
        will rename to start_caching
        used for user to cache the output of the port
        '''
        self._b_caching = True
        
    def get_log(self):
        '''
        will rename to get_cache
        used for user to get the console output since invoking the set_logging_flag/start_caching
        
        when this function is invoked, the cache will be cleared and the caching flag will be erased
        '''
        self._b_caching = False
        str_cache = self._str_cache
        self._str_cache = ''
        return str_cache
        
    def set_port(self, int_port):
        # should consider that the ReadThread may be using the port if the port is connected.
        self._int_port = int_port - 1
        self.h_serial.set_port(self._int_port)
        return 0
    
    def get_port(self):
        '''
        return the actual port number, which is 1+ port number used py pyserial.
        device number used by pyserial is -1 of com number we saw in
         device manager.
        For example, for com32 we actually pass 31 to pyserial as port num.
        So we need to +1 to get the port number we are familar with.
        '''
        return self._int_port + 1

