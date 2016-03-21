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

from restapi import APIClient
import urllib2
import base64
import json

class TestRailClient:

    def __init__(self, str_server_addr, str_user, str_password):
        self.str_user = str_user
        self.str_password = str_password
        self.str_server_addr = str_server_addr
    
    def user(self):
        return self.str_user
    
    def server_addr(self):
        return self.str_server_addr
    
    def get_case(self, int_case_id):
        str_rest_uri = '{0}/get_case/{1}'.\
            format(self.server_addr(), int_case_id)
        return self.send_get(str_rest_uri)

    def get_cases(self, project_id, case_filter=None):
        str_rest_uri = '{0}/get_cases/{1}{2}'.\
            format(self.server_addr(), project_id, case_filter)
        return self.send_get(str_rest_uri)

    def get_test_run(self, test_run_id):
        str_rest_uri = '{0}/get_run/{1}'.\
            format(self.server_addr(), test_run_id)
        return self.send_get(str_rest_uri)

    def update_test_run(self, test_run_id, fields=None):
        """
        fields is dict including fields of the testrun to update.
        """
        str_rest_uri = '{0}/update_run/{1}'.\
            format(self.server_addr(), test_run_id)
        return self.send_post(str_rest_uri, fields)

    def add_test_run(self, int_project_id,
                     str_name,
                     list_case_id=[],
                     int_test_suite=None,
                     str_description=None,
                     int_milestone=None,
                     int_assign_to_user_id=None):
        str_rest_uri = '{0}/add_run/{1}'.\
            format(self.server_addr(), int_project_id)
        dict_data = {'suite_id': int_test_suite,
                     'name': str_name,
                     'description': str_description,
                     'milestone_id': int_milestone,
                     'assignedto_id': int_assign_to_user_id,
                     'include_all': True if list_case_id == [] else False,
                     'case_ids': list_case_id
                     }
        return self.send_post(str_rest_uri, dict_data)
    
    def delete_test_run(self, int_test_run_id):
        str_rest_uri = '{0}/delete_run/{1}'.\
            format(self.server_addr(), int_test_run_id)
        dict_data = {}
        return self.send_post(str_rest_uri, dict_data)
    
    def close_test_run(self, int_test_run_id):
        str_rest_uri = '{0}/close_run/%{1}'.\
            format(self.server_addr(), int_test_run_id)
        dict_data = {}
        return self.send_post(str_rest_uri, dict_data)
    
    def add_test_plan(self, int_project_id, str_name, list_test_run=[],
                      str_description=None, int_milestone_id=None):
        str_rest_uri = '{0}/add_plan/{1}'.\
            format(self.server_addr(), int_project_id)
        dict_data = {
            'name': str_name,
            'description': str_description,
            'milestone_id': int_milestone_id,
            'entries': list_test_run
        }
        return self.send_post(str_rest_uri, dict_data)
        
    def add_plan_entry(self, int_test_plan_id,
                       int_suite_id,
                       list_case_ids=[],
                       list_config_ids=[],
                       list_test_runs=[],
                       int_assign_user_id=None):
        str_rest_uri = '{0}/add_plan_entry/{1}'.\
            format(self.server_addr(), int_test_plan_id)
        dict_data = {
            'suite_id': int_suite_id,
            'assinedto_id': int_assign_user_id,
            'include_all': False if list_case_ids else True,
            'config_ids': list_config_ids,
            'case_ids': list_case_ids,
            'runs': []
        }
        for each_test_run in list_test_runs:
            if type(each_test_run) != list or \
               len(each_test_run) != 3:
                continue
            list_case_ids_test_run = each_test_run[0]
            list_config_ids_test_run = each_test_run[1]
            int_assign_user_id_test_run = each_test_run[2]
            dict_data_test_run = {
                'include_all': False if list_case_ids_test_run else True,
                'case_ids': list_case_ids_test_run,
                'assignedto_id': int_assign_user_id_test_run,
                'config_ids': list_config_ids_test_run
            }
            dict_data['runs'].append(dict_data_test_run)
            
        return self.send_post(str_rest_uri, dict_data)
    
    def get_test_plan(self, int_test_plan_id):
        str_rest_uri = '{0}/get_plan/{1}'.\
            format(self.server_addr(), int_test_plan_id)
        return self.send_get(str_rest_uri)
        
    def delete_test_plan(self, int_test_plan_id):
        str_rest_uri = '{0}/delete_plan/{1}'.\
            format(self.server_addr(), int_test_plan_id)
        dict_data = {}
        return self.send_post(str_rest_uri, dict_data)
    
    def close_test_plan(self, int_test_plan_id):
        str_rest_uri = '{0}/close_plan/{1}'.format(self.server_addr(), int_test_plan_id)
        dict_data = {}
        return self.send_post(str_rest_uri, dict_data)
    
    def add_case_result(self, int_test_run_id, int_test_case_id,
                        int_status, str_comment=None, str_duration_time=''):
        str_rest_uri = '{0}/add_result_for_case/{1}/{2}'.\
            format(self.server_addr(), int_test_run_id, int_test_case_id)
        dict_data = {
            'status_id': int_status,
            'comment': str_comment,
            'elapsed': str_duration_time
        }
        return self.send_post(str_rest_uri, dict_data)
    
    def get_case_result(self):
        pass

    def send_get(self, uri, retry=0):
        """
        Send Get
        Issues a GET request (read) against the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. get_case/1)
        """
        return self.__send_request('GET', uri, None, retry)

    def send_post(self, uri, data, retry=0):
        """
        Send POST
        Issues a POST request (write) against the API and returns the result
        (as Python dict).
        Arguments:
            uri             The API method to call including parameters
                            (e.g. add_case/1)
            data            The data to submit as part of the request (as
                            Python dict, strings must be UTF-8 encoded)
        """
        return self.__send_request('POST', uri, data, retry)

    def __send_request(self, method, uri, data, retry=3):
        request = urllib2.Request(uri)
        if method == 'POST':
            request.add_data(json.dumps(data))
        auth = base64.encodestring('%s:%s' % (self.str_user, self.str_password)).strip()
        request.add_header('Authorization', 'Basic %s' % auth)
        request.add_header('Content-Type', 'application/json')

        all_error = ''
        for i in range(1 + retry):
            try:
                response = urllib2.urlopen(request).read()
                result = json.loads(response)
                return result
            except urllib2.HTTPError as e:
                response = e.read()
                result = json.loads(response)
                if result and 'error' in result:
                    error = 'HTTP {0}: "{1}"'.format(e.code, result['error'])
                else:
                    error = 'No additional error message received'

                if i != retry:
                    print '{}; retrying'.format(error)
                    all_error += error
                else:
                    raise APIError('TestRail API returned HTTP error:({})'.format(all_error))

class APIError(Exception):
    pass

if __name__ == '__main__':
    raise Exception('This module is not callable.')
