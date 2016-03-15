'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import telnetlib
import time
import traceback

from threading import Thread, Lock, Event

from LogTool import CLogTool
from Logger import CLogger

_DEFAULT_TIMEOUT_VALUE = 120


class CTelnet(CLogger, CLogTool):
    '''
    Class for a telnet connection; contains telnet action including read/write.
    '''
    def __init__(self, para, str_session_log = None):
        CLogger.__init__(self)
        CLogTool.__init__(self, str_session_log)
        
        # telnet ip address
        self._str_ip_addr = para[0]
        # telnet port
        self._int_port = int(para[1])
        # telnet connection
        self.h_telnet = telnetlib.Telnet()
        
        # used in read_until_strings, indicating which string is found
        self._int_match_index = 0
        # indicate if the port is connected
        self._b_connected = False
        # size of recv buffer
        self._int_buffer_size = 1024*4
        # the recv buffer used for searching, will be cleared in flush_buffer
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
        '''
        connect to the telnet port. Set the connected flag to true
        will refuse the second connection
        '''
        self.log('INFO', 'Connecting Telnet port(%s:%s)' % (self._str_ip_addr,
                                                            str(self._int_port)))
        self._lock_connection.acquire()
        
        if not self.h_telnet:
            raise Exception('h_telnet is None when trying to connect.')
        if not self._b_connected:
            try:
                self.h_telnet.open(self._str_ip_addr, self._int_port)
            except:
                '''
                This except sentence is to handle the case where the Telnet
                 port is currently occupied by others.
                '''
                self.log('WARNING', 'Error happen in Telnet connect: %s'
                         % traceback.format_exc())
                self._b_connected = False
            else:
                self._b_connected = True
                
        self._lock_connection.release()  
        
        if not self.thread_read.is_alive():
            self.thread_read = Thread(target=self.read_data)
            self.thread_read.setDaemon(True)
            self.thread_read.start()
        
        return self._b_connected        
    
    def disconnect(self):
        self.log('INFO', 'Disconnect Telnet port(%s:%s)'
                 % (self._str_ip_addr, str(self._int_port)))
        self._lock_connection.acquire()
        if self._b_connected:
            self.h_telnet.close()   
            self._b_connected = False
        self._lock_connection.release()
    
    def is_connected(self):
        return self._b_connected  
    
    def send_command(self, str_command=''):
        if not self.is_connected():
            return
        try:
            self.h_telnet.write(str_command)
        except:
            self.log('DEBUG', 'Exception happened in send_command: %s'
                     % traceback.format_exc())
            self.h_telnet.open(self._str_ip_addr, self._int_port)
            self.h_telnet.write(str_command)
        
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
        self._lock_buffer.acquire()
        self._str_buffer = ''
        self._lock_buffer.release()
       
    def read_until_strings(self, wait, int_time_out=_DEFAULT_TIMEOUT_VALUE, b_continue=False):
        '''
        check the console output until one of the target string in wait appears
        the self._int_match_index will indicate which string is got. if self._int_match_index is
        0, it means no target string appears in the given time
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
            raise Exception('FAIL', 'Type(%s) not supported in read_until_string' % type(wait))
        
        # flush buffer if needed
        if not b_continue:
            self.flush_buffer()

        int_start = time.clock()
        pos_start = 0
        pos_find = -1
        # detect if the timeout value is reached
        while int_time_out == 0 or time.clock() - int_start < int_time_out:
            
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
    
    def read_data(self): 
        '''
        function run in thread to read from serial port in a loop.
        '''    
        while True:
            try:
                
                str_read = ''  # cache data of every try of read
                                     
                # if quit single is received, quit the thread
                if self.event_thread_quit.is_set():
                    break
                self._lock_connection.acquire()
                
                # skip the reading if not connected
                if not self.is_connected():
                    self._lock_connection.release()
                    continue
                
                # read data
                try:
                    str_read = self.h_telnet.read_very_eager()
                except EOFError:
                    if self._b_connected:
                        self.log('INFO', 'Telnet connection closed: %s' % traceback.format_exc())
                        self.log('INFO', 'Trying to re-connect')
                        self.h_telnet.open(self._str_ip_addr, self._int_port)
                except:
                    self.log('WARNING', 'Error appear in read_data in CTelnet:\n %s' % traceback.format_exc())
                
                # add data to buffer
                if self._b_checking:
                    self._lock_buffer.acquire()
                    self._str_buffer += str_read
                    self._lock_buffer.release()
                elif self._str_buffer:
                    self.flush_buffer()
                
                # add data to user cache
                if self._b_caching:
                    self._str_cache += str_read
                    
                self._lock_connection.release()
                self.add_string_to_raw_log(str_read)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.log('ERROR', '(Telnet)Exception got in read_data: %s' % traceback.format_exc())
                exit()
        self.log('WARNING', '(Telnet: %s) read data thread exit' % self._int_port)  
        
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
        self._int_port = int_port
        
    def get_port(self):
        return self._int_port

    def get_match_index(self):
        '''
        used for user to check which string is got when checking the console output in
        read_until_strings or any other function which invoked the function of
        read_until_strings, such as send_command_wait_string
        '''
        return self._int_match_index
    
    def is_port_alive(self, timeout=600):
        '''
        [Function]: Checking if the telnet port is getting output
        [Input   ]: timeout.
        [Output  ]:
            True - if the connected port is giving output
            False - if there is no output from the connected port
        '''
        
        b_original_buffering_status = self._b_checking
        str_original_buffer = self._str_buffer
        self._b_checking = True
        
        # check for 5 minutes to see if there is output from the port
        time_now = time.clock()
        while time.clock() - time_now < timeout:
            if self._str_buffer != str_original_buffer:
                self._b_checking = b_original_buffering_status
                return True
            
        self._b_checking = b_original_buffering_status
        return False

