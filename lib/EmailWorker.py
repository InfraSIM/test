'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: EmailWorker.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: 
[Contains]: 
[History ]:
**********************************************************
 VERSION    EDITOR          DATE            COMMENT
**********************************************************
 V1.0    Bruce Yang        2014/03/20     First Version
 V1.1    Bruce Yang        2014/03/21     Add EmailTemplate Module
 V1.2    Bruce Yang        2014/04/01     Add support in CEmailTemplate
                                            - For Qual Start
                                            - For Qual Complete
*********************************************************
'''

# imports
import os
import datetime
import time
import smtplib
from email import Encoders
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from threading import Thread, Lock
import email
import shutil

# constants
default_email_to_list = []
default_email_cc_list = []
default_email_from = 'puffer <forrest.gu@emc.com>'
list_key_qual_initialized = ['$RELEASE_NAME', '$TIME', '$PLATFORM', '$FWA_VERSION',\
                             '$FWB_VERSION', '$FW-BUNDLE_VERSION', '$FWC_VERSION', '$VERSION']
list_key_qual_start = ['$TITLE', '$RELEASE_NAME', '$VERSION']
list_key_qual_complete = ['$TITLE', '$RELEASE_NAME', '$START_TIME', '$END_TIME', '$VERSION']
str_full_path_email_template_folder = 'doc'
list_failed_description = ['false', '0', 'no']
str_puffer_version = '2.0'

SUBJECT_QUAL_INITIALIZED = 'Qual Initialized'
SUBJECT_QUAL_START = 'Qual Start'
SUBJECT_QUAL_COMPLETE = 'Qual Complete'

def _log(str_level, str_info):
    return 0 # disable print
    print '[%s]:%s' % (str_level, str_info)

class CEmail():
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: The email data structure. Contains all information of an email
    [Methods]:    
    [History]:                                                                 
    ************************************************
    '''
    def __init__(self):
        self.str_body = ''
        self.str_from = ''
        self.list_to = []
        self.list_cc = []
        self.str_subject = ''
        self.list_attachments = []
        self.obj_MIMEMultipart = None
        self.str_file_name = '' # this is to store the email
        
    def to_string(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Transform the email information to string
            - If the obj_MIMEMultipart is not None, call the as_string method to transform the MIMEMultipart to string
            - If the obj_MIMEMultipart is None, transform the CEmail object to string
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        if self.obj_MIMEMultipart != None:
            return self.obj_MIMEMultipart.as_string()
        
        str_email = '[From]%s;[To]%s;[Cc]%s;[Subject]%s' % (self.str_from,\
                                                            ' '.join(self.list_to),\
                                                            ' '.join(self.list_cc),\
                                                            self.str_subject)
        return str_email
    
    def from_file(self, str_email_file):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Update the email information with content of a given file.
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        if not os.path.isfile(str_email_file):
            _log('WARNING', 'The email file to be parsed doesn\'t exist')
            return -1
        
        self.str_file_name = str_email_file
        print self.str_file_name
        
        try:
            self.obj_MIMEMultipart = email.message_from_file(file(self.str_file_name))
        except Exception,e: 
            print e
            return -1
        
        if self.obj_MIMEMultipart is None:
            _log('WARNING', 'Failed to parse the email file')
            return -1
        
        self.str_from = self.obj_MIMEMultipart['From']
        self.list_to = self.obj_MIMEMultipart['To'].split(';')
        try:
            self.list_cc = self.obj_MIMEMultipart['CC'].split(';')
        except:
            pass
        self.str_subject = self.obj_MIMEMultipart['Subject']
        
        return 0
                
    def save_to(self, str_directory_full_path):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Save the email information into a file
            - the file is named: #subject_#timepint.html
            - the file will be created in the given path
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        if self.obj_MIMEMultipart is None:
            return -1
        
        # check if the directory exists
        if not os.path.isdir(str_directory_full_path):
            try:
                os.makedirs(str_directory_full_path)
            except Exception, e:
                print e
                return -1

        # build file full path
        self.str_file_name = '%s_%s.html' % (self.str_subject, \
                                             datetime.datetime.strftime(datetime.datetime.now(),\
                                             '%Y%m%d%H%M%S%f'))
        self.str_file_name = os.path.join(str_directory_full_path, self.str_file_name)
        # save to file
        try:
            f_Write = open(self.str_file_name, 'w')
        except Exception, e:
            print e
            return -1
        f_Write.write(self.obj_MIMEMultipart.as_string())
        
        return 0
    
    def build(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function will be used if the email information is not get from a file or a string
            - It will create a MIMEMultipart instance, collect information from the instance and then
              update the MIMEMultipart object with the information
        [Input   ]:
        [Output  ]:     
        [History ]:                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        if self.str_from == '':
            _log('ERROR', 'No from address')
            return -1

        if self.list_to == []:
            _log('ERROR', 'No to list')
            return -1

        if self.str_subject == '':
            _log('WARNING', 'No subject')
        
        if self.list_cc == [] and self.list_to == []:
            _log('ERROR', 'Neither \'to\' or \'cc\' list are set')
            return -1
        
        #make outer
        outer                    = MIMEMultipart()
        
        if self.list_to != []:
            outer['To']                = ';'.join(self.list_to)
        outer['From']            = self.str_from
        if self.list_cc != []:
            outer['CC']                = ';'.join(self.list_cc)
        outer['Subject']        = self.str_subject
        
        # add body  
        mtext = MIMEText(self.str_body,'html')
        outer.attach(mtext)
        
        # add attachments
        for str_attachment in self.list_attachments:
            if os.path.isfile(str_attachment) == False:
                _log('WARNING', 'Attachment(%s) not found' % str_attachment)
                continue
            filename = os.path.basename(str_attachment)
            att_build_result = MIMEBase('application','plain')
            att_build_result.set_payload(open(str_attachment,'rb').read())
            Encoders.encode_base64(att_build_result)
            att_build_result.add_header('Content-Disposition', 'attachment; filename=%s' %filename)
            outer.attach(att_build_result)
        
        self.obj_MIMEMultipart = outer
        
        return 0
    
    def is_valid(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: An email object will be invalid until the MIMEMultipart object is initialized
        [Input   ]:
        [Output  ]:     
        [History ]                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        if self.obj_MIMEMultipart == None:
            return False
        return True
    
    def subject(self):
        return self.str_subject
    
class CEmailTemplate():
    
    dict_subject_keylist = {SUBJECT_QUAL_INITIALIZED: list_key_qual_initialized,\
                            SUBJECT_QUAL_START: list_key_qual_start,\
                            SUBJECT_QUAL_COMPLETE: list_key_qual_complete}
    
    def __init__(self):
        # key property
        self.str_subject = '' # Bruce 06/20: This is the email type. Qual complete/Qual start or else.
        
        # template information
        
        self.str_email_body_file_folder = str_full_path_email_template_folder
        self.str_body_file = ''
        self.str_email_title = '' # this is the title of the email
        self.str_from = default_email_from
        self.list_to = default_email_to_list[:]
        self.list_cc = default_email_cc_list[:]
        self.list_key = []
        self.dict_subject_update_method = {SUBJECT_QUAL_START:self.update_info_qual_start,\
                                           SUBJECT_QUAL_COMPLETE:self.update_info_qual_complete,\
                                           SUBJECT_QUAL_INITIALIZED:self.update_info_qual_initialized}
        
        self.b_enabled = False
        self.reset()
        
    def reset(self):
        self.str_body = ''
        self.list_attachments = []
        self.list_key_replacements = []
        
    def read_body_from_file(self):
        str_template_full_path = os.path.join(self.str_email_body_file_folder, self.str_body_file)
        try:
            self.str_body = open(str_template_full_path, 'r').read()
        except Exception, e:
            print e
            _log('ERROR', 'The template file(%s) for template(%s) not found or cannot be open.' % (self.str_body_file, self.str_subject))
            return -1 
        return 0
    
    def update_key_information(self):
        
        if not self.is_valid():
            _log('ERROR', 'Update key information for invalid template')
            return -1
        
        int_key_length = len(self.list_key)
            
        if len(self.list_key_replacements) != int_key_length:
            _log('ERROR', 'No enough key information: expect %d, get %d' % (int_key_length, len(self.list_key_replacements)))
            return -1
        
        for i in range(int_key_length):
            str_key = self.list_key[i]
            str_key_replacement = self.list_key_replacements[i]
            if self.str_body.find(str_key) == -1:
                _log('ERROR', 'Key(%s) not found for event(%s)' % (str_key, self.str_subject))
                return -1
            self.str_body = self.str_body.replace(str_key, str_key_replacement)
            
        return 0
    
    def update_info_qual_start(self, list_image_file):
        str_image_line = '''<p class=MsoNormal style='text-indent:36.0pt'><span style='font-size:14.0pt;
mso-bidi-font-size:11.0pt;mso-ascii-font-family:Calibri;mso-hansi-font-family:
Calibri'>$IMAGE<o:p></o:p></span></p>\n'''
        str_image_list_part_in_email_body = ''
        _log('INFO', 'Update the image list in the qual start email body')
        for each_image_file in list_image_file:
            str_image_list_part_in_email_body += str_image_line.replace('$IMAGE', each_image_file)
            
        self.str_body = self.str_body.replace('$IMAGE_LIST', str_image_list_part_in_email_body)
        
        self.str_email_title = 'Puffer Test Start - %s' % self.list_key_replacements[0]
        return 0
    
    def update_info_qual_initialized(self):
        self.str_email_title = 'Puffer Test Initialized - %s' % self.list_key_replacements[0]
        return 0
    
    def update_info_qual_complete(self, str_report_file):
        str_report_file = str_report_file[0]
        int_pass_case_number = 0
        int_fail_case_number = 0
        int_skip_case_number = 0
        int_block_case_number = 0
        str_case_result_table = ''
        # read report file
        try:
            list_line_in_report_file = open(str_report_file).readlines()
        except:
            _log('ERROR', 'Failed to read report file(%s)' % str_report_file)
            return -1
        
        # parse information in report file
        for each_line in list_line_in_report_file:
            if each_line.find('>pass<') >-1:
                int_pass_case_number += 1
            elif each_line.find('>fail<') >-1:
                int_fail_case_number += 1
                str_case_result_table += each_line + '\n'
            elif each_line.find('>skip<') >-1:
                int_skip_case_number += 1
            elif each_line.find('>block<') >-1:
                int_block_case_number += 1
                str_case_result_table += each_line + '\n'
        
        # update email body
        self.str_body = self.str_body.replace('$NUM_PASS', str(int_pass_case_number))
        self.str_body = self.str_body.replace('$NUM_FAIL', str(int_fail_case_number))
        self.str_body = self.str_body.replace('$NUM_SKIP', str(int_skip_case_number))
        self.str_body = self.str_body.replace('$NUM_BLOCK', str(int_block_case_number))
        self.str_body = self.str_body.replace('$RESULT_TABLE', str_case_result_table)
        
        self.str_email_title = 'Puffer Test Completed - %s' % self.list_key_replacements[0]
        
        return 0
        
    def to_email(self, list_information):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Create an email object
        [Input   ]:
            str_subject - the subject of the email.
            list_information - key information in the email body. They will be used
                    to update the email body. Including two parts
                    a. Key information replacement. E.g. release_name
                    b. Information to create table. E.g. test result table
        [Output  ]:  
            email object - if the information given is valid and supported
            None         - if the information given is not valid or supported
        [History ]                                              
        ************************************************
        '''
        if len(list_information) < 3:
            _log('ERROR', 'Not enough information to create an email object')
            self.reset()
            return None
        
        try:
            self.list_key = CEmailTemplate.dict_subject_keylist[self.str_subject]
        except:
            _log('WARNING', 'Template subject not supported')
        
        self.list_key_replacements = list_information[0]
        self.list_attachments = list_information[2]

        if self.read_body_from_file() != 0:
            self.reset()
            return None
        
        if self.update_key_information() != 0:
            self.reset()
            return None
        
        if self.dict_subject_update_method.has_key(self.str_subject):
            if self.dict_subject_update_method[self.str_subject](list_information[1]) != 0:
                return None

        obj_email = CEmail()
        obj_email.str_subject = self.str_email_title
        obj_email.str_body = self.str_body
        obj_email.str_from = self.str_from
        obj_email.list_to = self.list_to[:]
        obj_email.list_cc = self.list_cc[:]
        obj_email.list_attachments = self.list_attachments[:]
        obj_email.build()
        
        if not obj_email.is_valid():
            self.reset()
            return None
        
        self.reset()
        return obj_email
    
    def from_xml_node(self, obj_xmlnode_template):
        # get subject
        try:
            self.str_subject = obj_xmlnode_template.find('subject').text 
            self.str_body_file = obj_xmlnode_template.find('template').text
        except:
            _log('ERROR', 'No subject or template in xmlnode')
            return -1
        # get to list
        try:
            str_to_list = obj_xmlnode_template.find('to_list').text
            if str_to_list.find(',') >= 0:
                self.list_to = str_to_list.split(',')
            else:
                self.list_to = [str_to_list, ]
        except:
            _log('WARNING', 'Failed to get \'to\' information in xmlnode')
            self.list_to = []
        # get cc list
        try:  
            str_cc_list = obj_xmlnode_template.find('cc_list').text
            if str_cc_list.find(',') >= 0:
                self.list_cc = str_cc_list.split(',')
            else:
                self.list_cc = [str_cc_list, ]
        except:
            self.list_cc = []
        # get switch status
        try:
            if obj_xmlnode_template.find('enabled').text.lower() in list_failed_description:
                self.b_enabled = False
            else:
                self.b_enabled = True
        except:
            pass
        return 0        
    
    def subject(self):
        return self.str_subject
    
    def is_valid(self):
        if self.str_from == '':
            return False
        if self.str_body_file == '':
            return False
        return True
    
class CEmailBuilder():
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: Support
        - Create an email based on subject and information
        - Has a library which contains a series of email template indexed by subject
          , of which each will have pre-defined information
        - Can add a template based on a xml node
    [Methods]:    
    [History]:                                                                 
    ************************************************
    '''
    def __init__(self):
        self.str_full_path_template_folder = ''
        self.dict_subject_emailevent = {}
    
    def create_email(self, str_subject, list_information):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Interface for other modules to create email from template
        [Input   ]:
            str_subject - the subject of the email.
            list_information - key information in the email body. They will be used
                    to update the email body. Including two parts
                    a. Key information replacement. E.g. release_name
                    b. Information to create table. E.g. test result table
        [Output  ]:  
            email object - if the information given is valid and supported
            None         - if the information given is not valid or supported
        [History ]                                              
        ************************************************
        '''
        if not self.dict_subject_emailevent.has_key(str_subject):
            _log('WARNING', 'Create email with unsupported subject(%s)' % str_subject)
            return None
        
        obj_template = self.dict_subject_emailevent[str_subject]
        
        obj_email = obj_template.to_email(list_information)
        
        return obj_email
    
    def add_template_xml(self, obj_xmlnode_template):
        obj_template = CEmailTemplate()
        obj_template.from_xml_node(obj_xmlnode_template)
        
        if not obj_template.is_valid():
            _log('ERROR', 'XML node for template is invalid')
            return -1
        
        if self.dict_subject_emailevent.has_key(obj_template.subject()):
            _log('WARNING', 'Email template with subject(%s) already exist' % obj_template.subject())
            return 0
        
        _log('INFO', 'Add notification event: %s' % obj_template.subject())
        self.dict_subject_emailevent[obj_template.subject()] = obj_template
        
        return 0

class CEmailServer(Thread):
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: 
        - Support adding email to email queue waiting to be sent out
        - A thread keep sending queued email out
        - Keep all email request in file so that puffer quit will not cause
            data loss
        - The local record(file) should be moved to sent box after the email is sent out
    [Methods]:    
    [History]:                                                                 
    ************************************************
    '''
    def __init__(self):
        super(CEmailServer, self).__init__()
        self.str_full_path_out_box = os.path.join('email_box', 'out_box')
        self.str_full_path_sent_box = os.path.join('email_box', 'sent_box')
        self.list_email_queued = []
        self.str_SMTP_host_address = ''
        self.obj_email_builder = CEmailBuilder()
        self.obj_email_sender = CEmailSender()
        self.b_accepting_request = False
        self.b_quit = False
        self.lock_list_email_queued = Lock()  
        
    def start(self):
        self.b_accepting_request = True
        self.setDaemon(True)
        Thread.start(self)  
        
    def stop(self):
        self.b_accepting_request = False    
    
    def raise_email_request(self, str_subject, list_information):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This is interface for external module to raise email request.
            - If the str_subject and list_information can match a pair in the Email Builder
              a email will be created and added to the out box and the sending queue
        [Input   ]:
        [Output  ]:
        [History ]
        ************************************************
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version
        ************************************************
        '''
        if not self.b_accepting_request:
            _log('WARNING', 'Email request service not started yet')
            return -1
        # create email
        obj_email = self.obj_email_builder.create_email(str_subject, list_information)
        if obj_email == None or obj_email.is_valid() == False:
            _log('WARNING', 'Failed to create email: %s' % str_subject)
            return -1
        
        # add to out box and email queue
        if not os.path.isdir(self.str_full_path_out_box):
            try:
                os.makedirs(self.str_full_path_out_box)
            except:
                _log('ERROR', 'Failed to create the out_box')
                return -1
        obj_email.save_to(self.str_full_path_out_box)
        self.add_email_to_sending_queue(obj_email)
        return 0
    
    def add_email_to_sending_queue(self, obj_email):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Add a email to the sending queue
        [Input   ]:
        [Output  ]:     
        [History ]                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        self.lock_list_email_queued.acquire()
        if self.list_email_queued.count(obj_email) == 0:
            self.list_email_queued.append(obj_email)
            self.lock_list_email_queued.release()
            return 0
        self.lock_list_email_queued.release()
        return 1
    
    def remove_email_from_sending_queue(self, obj_email):
        # move the email from out box to sent box
        if not os.path.isdir(self.str_full_path_sent_box):
            try:
                os.makedirs(self.str_full_path_sent_box)
            except:
                _log('ERROR', 'Sent box not found and failed to be created')
                exit(1)
        try:
            shutil.move(obj_email.str_file_name, \
                        os.path.join(self.str_full_path_sent_box, \
                                os.path.basename(obj_email.str_file_name)))
        except:
            _log('INFO', 'Failed to remove email(%s) from out box to sent box' % obj_email.str_file_name)
            
        
        # remove the email from the sending queue
        try:
            self.list_email_queued.remove(obj_email)
        except Exception, e:
            print e
            _log('INFO', 'Runtime error when remove email from sending queue')
        return 0
    
    def add_all_emails_in_out_box_to_sending_queue(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function will be called in the start up process of the Email server. It will
            - Convert all the email files in out box to email objects
            - Add all the email objects to sending queue of the server
        [Input   ]:
        [Output  ]:     
        [History ]:                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        _log('INFO', 'Add all emails in out box to sending queue')
        
        if not os.path.isdir(self.str_full_path_out_box):
            return 0
        
        list_email_file = os.listdir(self.str_full_path_out_box)
        for each_email_file in list_email_file:
            
            if not each_email_file.endswith('.html'):
                continue
            
            each_email_file = os.path.join(self.str_full_path_out_box, \
                                           each_email_file)
            
            obj_email = CEmail()
            obj_email.from_file(each_email_file)
            
            if not obj_email.is_valid():
                _log('INFO', '')
                continue
            
            self.add_email_to_sending_queue(obj_email)
            
            _log('INFO', 'Email found: %s' % obj_email.subject())
        
        _log('INFO', 'All emails in outbox queued')
        
        return 0
    
    def run(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: The running body of the server. It one after another will:
            - 1. Convert all emails in out box into email objects and put them into sending queue
            - 2. Start the email request service
            - 3. Start the email sending process
        [Input   ]:
        [Output  ]:     
        [History ]                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        _log('INFO', 'Email server start')
        self.add_all_emails_in_out_box_to_sending_queue()
        
        while not self.b_quit:
            if not self.list_email_queued:
                continue
            obj_email = self.list_email_queued[0]
            self.obj_email_sender.send_email(obj_email)
            self.remove_email_from_sending_queue(obj_email)
            
        _log('INFO', 'Email server quit')
        return
    
    def is_idle(self):
        if self.list_email_queued:
            return False
        return True
    
    def set_SMPT_address(self, str_SMTP_host_address):
        return self.obj_email_sender.set_SMTP_host_address(str_SMTP_host_address)
    
    def quit(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Stop the server from running
        [Input   ]:
        [Output  ]:     
        [History ]                                                                    
        ************************************************  
        Version    Editor      Date        Comments
        ************************************************
        V1.0     Bruce Yang 03/21/2013     First Version                          
        ************************************************
        '''
        self.b_accepting_request = False
        self.b_quit = True

class CEmailSender():
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: 
    [Methods]:    
    [History]:                                                                 
    ************************************************
    '''
    def __init__(self, str_SMTP_host_address = ''):
        self.str_SMTP_host_address = str_SMTP_host_address
        
    def set_SMTP_host_address(self, str_SMTP_host_address):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Set the SMTP server for sending email
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        self.str_SMTP_host_address = str_SMTP_host_address
    
    def send_email(self, obj_email):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Used to send a single email
        [Input   ]:
        [Output  ]:     
        [History ]                                              
        ************************************************
        '''
        if self.str_SMTP_host_address == '':
            _log('INFO', 'Host address not set')
            return -1
        
        if obj_email == None or \
           isinstance(obj_email, CEmail) == False:
            _log('WARNING', 'Sending an non CEmail object')
            return -1
        
        if not obj_email.is_valid():
            _log('WARNING', 'Found a invalid email: %s' % obj_email.to_string())
            return -1
        
        _log('INFO', 'Sending email: %s' % obj_email.subject())
        
        try:
            self.email_server = smtplib.SMTP(self.str_SMTP_host_address)
            self.email_server.sendmail(obj_email.str_from,\
                                       obj_email.list_to + obj_email.list_cc,\
                                       obj_email.obj_MIMEMultipart.as_string())
            self.email_server.quit()
        except Exception,e:
            print e
            _log('ERROR', 'Failed to send email: %s' % obj_email.str_subject)
            return -1
        
        _log('INFO', 'Email Sent: (To) %s, (Subject) %s' % (' '.join(obj_email.list_to), obj_email.str_subject))
        
        return 0
    
def set_default_from_address(str_from_address):
    global default_email_from
    default_email_from = str_from_address
    
def set_default_to_address(list_to_address):
    global  default_email_to_list
    default_email_to_list = list_to_address[:]
    
def set_default_cc_address(list_cc_address):
    global default_email_cc_list
    default_email_cc_list = list_cc_address[:]
    
if __name__ == '__main__':
    pass
