'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Apr 29, 2015

This module is implement for external automation tools to talk with TestRail
via the RestAPIs provided by TestRail

The APIClient class and the APIError class is provide by TestRail. A little customization
may be added to the two modules. If there are updates from TestRail about the two classes,
we need to be careful of the customization part

@author: Bruce.Yang@emc.com
*********************************************************
'''

import requests
import json
import traceback
from requests.packages import urllib3
from Logger import CLogger

class APIClient(CLogger):
    def __init__(self, verify=False, 
                 username='', 
                 password='', 
                 session_log=True,
                 headers={'Content-Type': 'application/json'}):
        CLogger.__init__(self)
        self.str_session_log = ''
        self.b_verify = verify
        self.username = username
        self.password = password
        self.b_session_log = session_log
        self.http_header = headers
        urllib3.disable_warnings()

    def send_get(self, uri, rest_stat=200, rest_payload=None, timeout=None, retry=3):
        '''
        Send Get
        Issues a GET request (read) to the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. get_case/1)
        '''
        return self.restful(uri, 'get', rest_stat, rest_payload, timeout, retry)

    def send_post(self, uri, data, rest_stat=200, timeout=None, retry=3):
        '''
        Send POST
        Issues a POST request (write) to the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. add_case/1)
            data            The data to submit as part of the request (as
                            Python dict, strings must be UTF-8 encoded)
        '''
        return self.restful(uri, 'post', rest_stat, data, timeout, retry)

    def send_put(self, uri, data, rest_stat=200, timeout=None, retry=3):
        '''
        Send PUT
        Issues a PUT request (write) to the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. add_case/1)
            data            The data to submit as part of the request (as
                            Python dict, strings must be UTF-8 encoded)
        '''
        return self.restful(uri, 'put', rest_stat, data, timeout, retry)

    def send_delete(self, uri, rest_stat=200, rest_payload=None, timeout=None, retry=3):
        '''
        Send Delete
        Issues a Delete request to the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. get_case/1)
        '''
        return self.restful(uri, 'delete', rest_stat, rest_payload, timeout, retry)

    def send_patch(self, uri, data, rest_stat=200, timeout=None, retry=3):
        '''
        Send Patch
        Issues a Patch request to the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. get_case/1)
            data            The data to submit as part of the request (as
                            Python dict, strings must be UTF-8 encoded)
        '''
        return self.restful(uri, 'patch', rest_stat, data, timeout, retry)

    # This routine executes a rest API call to the host
    # the default success value for a rest call is 200.  If you expect a 'failure' pass in
    # a value for rest_status, this needs to be implemented further, not quite working
    def restful(self, url_command, rest_action, rest_stat=200, rest_payload=None, timeout=None, retry=3):
        result_data = None

        # Perform rest request
        for i in range(retry):
            self.log('DEBUG', '[Retry:{}/{}][{}][{}]'.
                     format(i+1, retry, rest_action, url_command))
            try:
                if rest_action == "get":
                    result_data = requests.get(url_command, 
                                               timeout=timeout,
                                               verify=self.b_verify,
                                               auth=(self.username, self.password),
                                               headers=self.http_header)
                if rest_action == "delete":
                    result_data = requests.delete(url_command, 
                                                  timeout=timeout,
                                                  verify=self.b_verify,
                                                  auth=(self.username, self.password),
                                                  headers=self.http_header)
                if rest_action == "put":
                    result_data = requests.put(url_command,
                                              data=json.dumps(rest_payload),
                                              timeout=timeout,
                                              verify=self.b_verify,
                                              auth=(self.username, self.password),
                                              headers=self.http_header)
                if rest_action == "post":
                    result_data = requests.post(url_command,
                                               data=json.dumps(rest_payload),
                                               timeout=timeout,
                                               verify=self.b_verify,
                                               auth=(self.username, self.password),
                                               headers=self.http_header)
                if rest_action == "patch":
                    result_data = requests.patch(url_command,
                                                 data=json.dumps(rest_payload),
                                                 timeout=timeout,
                                                 verify=self.b_verify,
                                                 auth=(self.username, self.password),
                                                 headers=self.http_header)
            except requests.exceptions.Timeout:
                if i < retry - 1:
                    continue
                else:
                    msg_timeout = 'Retry {0} times and all timeout ({1}s each)'\
                                .format(retry, timeout)
                    self.log('WARNING', msg_timeout)
                    rsp = {'json':'', 
                            'text':msg_timeout,
                            'status':0,
                            'headers':'',
                            'timeout':True}
                    if self.b_session_log:
                        self.add_string_to_session_log('{} {}\n{}\n'.
                            format(rest_action, url_command, str(rsp)))
                    return rsp
            else:
                break
        try:
            result_data.json()
        except ValueError:
            self.log('WARNING', 'ValueError during jsonify REST response data')
            rsp = {'json':[], 
                    'text':result_data.text, 
                    'status':result_data.status_code,
                    'headers':result_data.headers.get('content-type'),
                    'timeout':False}
            if self.b_session_log:
                self.add_string_to_session_log('{} {}\n{}\n'.
                    format(rest_action, url_command, str(rsp)))
            return rsp
        else:
            rsp = {'json':result_data.json(), 
                    'text':result_data.text,
                    'status':result_data.status_code,
                    'headers':result_data.headers.get('content-type'),
                    'timeout':False}
            if self.b_session_log:
                self.add_string_to_session_log('{} {}\n{}\n'.
                    format(rest_action, url_command, str(rsp)))
            return rsp
    
    def disable_verify(self):
        # Disable certificate verification
        self.b_verify = False
    
    def enable_verify(self):
        # Enable certificate verification
        self.b_verify = True
        
    def set_headers(self, dict_header):
        self.headers = dict_header
            
    def set_session_log(self, str_session_log_file_name):
        # For an REST agent instance, if it's session log is set before
        # then it won't be changed to a new file
        # This is to avoid duplicated REST session log for a same instance
        
        if self.str_session_log == '':
            self.str_session_log = str_session_log_file_name
            
        return 0
    
    def get_session_log(self):
        return self.str_session_log

    def disable_log(self):
        self.b_session_log = False

    def enable_log(self):
        self.b_session_log = True
    
    def add_string_to_session_log(self, str_line):
        try:
            with open(self.str_session_log, 'a') as f_log:
                import datetime
#                 str_line = str_line.replace('\n', '\n' + '[' + str(datetime.datetime.now()) + '] ')
                f_log.writelines('[{}] {}'.format(str(datetime.datetime.now()), str_line))
                f_log.writelines('\n')
                return 0
        except Exception, e:
            print traceback.format_exc()
            return 1
    
    def reset(self):
        self.str_session_log = ''
            
class APIError(Exception):
    pass


if __name__=='__main__':
    
    uri_test = "https://10.62.59.33:443/login"
    obj_rest = APIClient(session_log=False)
    dict_test = {"email":"admin", "password":"admin123"}
    print "#####################" + str(uri_test)
    print "#####################" + str(dict_test)
    response = obj_rest.restful(str(uri_test), 'post', rest_payload=dict_test)
    print str(response)
