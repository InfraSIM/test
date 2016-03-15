'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
'''
Created on Sep 7, 2015

@author: Forrest Gu
'''
import paramiko
import traceback
import time
import socket
from LogTool import CLogTool
from Logger import CLogger
from threading import Thread, Lock, Event

_DEFAULT_TIMEOUT_VALUE = 120
_DEFAULT_READ_CADENCE = 10.0


class CSSH(CLogger, CLogTool):

    def __init__(self, ip, username, password, str_session_log=None, port=22):

        # Log tool init
        CLogger.__init__(self)
        CLogTool.__init__(self, str_session_log)

        # ssh host IP
        self.ip = ip
        self.port = port
        # ssh host username
        self.username = username
        # ssh host password
        self.password = password
        # ssh connection
        self.h_ssh = paramiko.SSHClient()
        self.h_chan = None

        # used in read_until_strings, indicating which string is found
        self._int_match_index = 0
        # indicate if the port is connected
        self._b_connected = False
        # size of recv buffer
        self._int_buffer_size = 1024 * 4
        # the recv buffer used for searching, will be cleared in flush_buffer
        self._str_buffer = ''
        # Lock for buffer change
        self._lock_buffer = Lock()
        # used by user to request caching the output
        self._b_caching = False
        # used by user to cache the output
        self._str_cache = ''
        # used to keep cache
        self._lock_cache = Lock()
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

    def connect(self):
        """
        Connect to SSH host. Set the connected flag to true
        will refuse the second connection
        """
        self.log('INFO', 'Connecting SSH: {0}@{1}:{2}'.format(self.username, self.ip, self.port))

        if not self.h_ssh:
            raise Exception('h_ssh is None when trying to connect.')
        if not self._b_connected:
            self._lock_connection.acquire()
            try:
                self.h_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.h_ssh.connect(self.ip, port=self.port, username=self.username, password=self.password)
                self.h_chan = self.h_ssh.invoke_shell()
                self.h_chan.settimeout(_DEFAULT_READ_CADENCE)
            except paramiko.AuthenticationException:
                self.log('WARNING', 'SSH authentication error, please check username and password')
                self._b_connected = False
            except paramiko.SSHException:
                self.log('WARNING', 'Error happen in SSH connect: \n{}'.format(traceback.format_exc()))
                self._b_connected = False
            except socket.error:
                self.log('WARNING', 'Socket error while connection: \n{}'.format(traceback.format_exc()))
                self._b_connected = False
            except Exception:
                self.log('WARNING', 'Fail to build SSH connection: \n{}'.format(traceback.format_exc()))
                self._b_connected = False
            else:
                self._b_connected = True
            finally:
                self._lock_connection.release()

        if not self.thread_read.is_alive():
            self.thread_read = Thread(target=self.read_data)
            self.thread_read.setDaemon(True)
            self.thread_read.start()

        return self._b_connected

    def disconnect(self):
        self.log('INFO', 'Disconnect SSH ({0}@{1}:{2})'.format(self.username, self.ip, self.port))
        if self._b_connected:
            self._lock_connection.acquire()
            try:
                self.h_chan.close()
                self.h_ssh.close()
                self._b_connected = False
            finally:
                self._lock_connection.release()

    def is_connected(self):
        return self._b_connected

    def read_data(self):
        """
        Function run in thread to read from SSH in a loop.
        """
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
                    str_read = self.h_chan.recv(self._int_buffer_size)
                except EOFError:
                    if self.is_connected():
                        self.log('WARNING', 'SSH connection is unexpectedly closed:\n%s'
                                 % traceback.format_exc())
                        self.log('INFO', 'Trying to re-connect...')
                        self.h_chan.close()
                        self.h_ssh.close()
                        self.h_ssh.connect(self.ip, username=self.username,
                                           password=self.password, port=self.port)
                        self.h_chan = self.h_ssh.invoke_shell()
                        self.h_chan.settimeout(_DEFAULT_READ_CADENCE)
                        self.log('INFO', 'Re-connect done')
                except socket.timeout:
                    # Comment this for it's noisy if test maintain a bunch of
                    # SSH sessions
                    # self.log('DEBUG', 'SSH heartbeat {} s'.
                    #          format(_DEFAULT_READ_CADENCE))
                    pass
                except:
                    self.log('WARNING', 'Error appear in read_data in CSSH:\n%s'
                             % traceback.format_exc())
                finally:
                    self._lock_connection.release()
                    time.sleep(0.1)

                # add data to buffer
                if self._b_checking:
                    self._lock_buffer.acquire()
                    self._str_buffer += str_read
                    self._lock_buffer.release()
                elif self._str_buffer:
                    self.flush_buffer()

                # add data to user cache
                if self._b_caching:
                    self._lock_cache.acquire()
                    self._str_cache += str_read
                    self._lock_cache.release()

                self.add_string_to_raw_log(str_read)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.log('ERROR', '(SSH)Exception got in read_data: %s' % traceback.format_exc())
                exit()
        self.log('WARNING', '(SSH: {0}@{1}) read data thread exit'.format(self.username, self.ip))

    def flush_buffer(self):
        self._lock_buffer.acquire()
        self._str_buffer = ''
        self._lock_buffer.release()

    def send_command(self, str_command=''):
        if not self.is_connected():
            return
        try:
            self.h_chan.send(str_command)
        except socket.timeout:
            self.log('WARNING', 'Timeout to send command: {} to {}@{}'.
                     format(str_command, self.username, self.ip))
        except Exception:
            self.log('WARNING', 'Exception happened in send_command: {}'.
                     format(traceback.format_exc()))

    def send_command_wait_string(self, str_command='', wait=None,
                                 int_time_out=_DEFAULT_TIMEOUT_VALUE,
                                 b_with_buff=False):
        """
        Write str_command to the session and wait until one of the target strings in wait
        appears in the output or timer expired
        @param str_command: command to send in string
        @param wait: keyword in string that you would like to wait and return
        @param int_time_out: time in int that if wait string doesn't appear, this function
            shall time out
        @param b_with_buff: bool, if response shall take previous buffer together
        @return: ssh buffer string till (and including) the first "wait" keyword,
            or empty string '' if timeout.
        """
        str_result = ''
        self._b_checking = True

        if not b_with_buff:
            self.flush_buffer()

        if str_command != '':
            self.send_command(str_command)

        if wait:
            str_result = self.read_until_strings(wait, int_time_out, b_with_buff=True)

        self._b_checking = False

        return str_result

    def read_until_strings(self, wait, int_time_out=_DEFAULT_TIMEOUT_VALUE,
                           b_with_buff=False):
        """
        Check the session output until one of the target string in wait appears
        the self._int_match_index will indicate which string is got. if self._int_match_index is
        0, it means no target string appears in the given time
        @param wait: keyword in string that you would like to wait and return
        @param int_time_out: time in int that if wait string doesn't appear, this function
            shall time out
        @param b_with_buff: bool, if response shall take previous buffer together
        @return: ssh buffer string till (and including) the first "wait" keyword,
            or empty string '' if timeout.
        """
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
        if not b_with_buff:
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

            if len_buffer > int_length:
                # string not found
                pos_start = len_buffer - int_length

        self._b_checking = False
        return ''

    def start_cache(self):
        """
        Used by user to set the cache point and cache the following output
        """
        self._lock_cache.acquire()
        self._b_caching = True
        self._lock_cache.release()

    def get_cache(self):
        """
        Used for user to get the session output since invoking the start_caching
        When this function is invoked, the cache will be cleared and the caching
        flag will be erased
        """
        self._lock_cache.acquire()
        self._b_caching = False
        str_cache = self._str_cache
        self._str_cache = ''
        self._lock_cache.release()
        return str_cache

    def get_match_index(self):
        """
        Used for user to check which string is got when checking the console output in
        read_until_strings or any other function which invoked the function of
        read_until_strings, such as send_command_wait_string
        """
        return self._int_match_index

    def is_port_alive(self, timeout=600):
        """
        Checking if the session is getting output
        Return:
            True - if the connected port is giving output
            False - if there is no output from the connected port
        @param timeout: expiration time
        """

        b_original_buffering_status = self._b_checking
        str_original_buffer = self._str_buffer
        self._b_checking = True

        # check for a certain time to see if there is output from the port
        time_now = time.clock()
        while time.clock() - time_now < timeout:
            if self._str_buffer != str_original_buffer:
                self._b_checking = b_original_buffering_status
                return True

        self._b_checking = b_original_buffering_status
        return False

    def remote_shell(self, shell_cmd):
        """
        Hack original test_common.sshinit
        Build a standalone ssh session (temp_chan) to
        execute the command.
        """
        self.log('DEBUG', '$ {}'.format(shell_cmd))

        # skip the command if not connected
        if not self.is_connected():
            return {'stdout': '', 'exitcode': -1}

        try:
            stdin, stdout, stderr = self.h_ssh.exec_command(shell_cmd)
        except paramiko.SSHException:
            self.log('ERROR', 'SSH exception when execute command on remote shell: {}'.
                     format(shell_cmd))

        self.add_string_to_raw_log('$ '+shell_cmd+'\n')
        list_stdout_lines = stdout.readlines()
        for line in list_stdout_lines:
            self.add_string_to_raw_log(line)

        str_stdout = ''.join(list_stdout_lines)
        str_stderr = stderr.channel.recv_stderr(4096)
        int_exitcode = stdout.channel.recv_exit_status()

        self.log('DEBUG', str_stdout)

        return {
            'stdout': str_stdout,
            'stderr': str_stderr,
            'exitcode': int_exitcode
        }


if __name__ == "__main__":
    import logging

    ip = '192.168.13.131'
    username = 'root'
    password = 'root'
    str_session_log = 'C:\\Users\\guf1\\Desktop\\ssh_session.txt'
    str_event_log = 'C:\\Users\\guf1\\Desktop\\event.txt'

    obj_logger = logging.getLogger(str_event_log)
    obj_logger.setLevel(20)
    str_formater = '%(message)s'
    log_formater = logging.Formatter(str_formater)
    log_handler_file = logging.FileHandler(str_event_log, 'a')
    log_handler_file.setFormatter(log_formater)
    log_handler_file.setLevel(logging.INFO)
    obj_logger.addHandler(log_handler_file)

    obj_ssh = CSSH(ip, username, password, str_session_log)
    obj_ssh.set_logger(obj_logger)
    obj_ssh.set_log(1, True, True)
    print 'connected:', obj_ssh.connect()
    print '-' * 40
    obj_ssh.send_command_wait_string(chr(13), '$', b_with_buff=False)
    obj_ssh.send_command_wait_string('pwd' + chr(13), '~$', b_with_buff=False)
    obj_ssh.send_command_wait_string('ls' + chr(13), '~$', b_with_buff=False)
    obj_ssh.send_command_wait_string('mkdir abc' + chr(13), '~$', b_with_buff=False)
    obj_ssh.send_command_wait_string('cd abc' + chr(13), '~/abc$', b_with_buff=False)
    obj_ssh.send_command_wait_string('touch afile' + chr(13), '~/abc$', b_with_buff=False)
