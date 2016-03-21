'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: Image.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: Implementation for FW image file validation
[Contains]: 
        CImage - class
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        Bruce.Yang@emc.com    09/12/2013       First edition
********************************************************************
'''

# imports
import os
import shutil
import hashlib
import re

# constants
LIST_IMAGE_TYPE = ('fw_a', 'fw_b', 'fw_c')
LIST_PLATFORM_SUPPORTED = ('platform_a', 'platform_b', 'platform_c')
PATTERN_NAME = r'*(.+)_([0-9-\.]+)\.bin'


class CImage():
    '''
    ************************************************
    [Author  ]: Bruce.Yang@emc.com
    [Description]: Implement of FW image. The class provides validation of a
                given file to see if it is a FW image. Also, the class implements 
                interfaces of the image properties such as type, version, etc
    [Methods]: is_fw_image - tells if the file is a FW image
               is_for_platform - tells if the image is suitable for the given platform
               type - the image type
               version - the image version
               copy_to - copy the image to a given folder
               create_md5_file - create md5 file and copy to a given folder
    [History ]:                                                                 
    ************************************************
    '''
    def __init__(self, str_file):
        self.str_file_full_path = str_file
        self.str_file_name = ''
        self.b_is_fw_image = False
        self.b_has_emc_header = False
        self.str_platform = ''  # empty is for all platforms
        self.str_version = '0000'
        self.str_type = ''  # empty is for unknown image type
        self.__parse__info__()
    
    def __parse__info__(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Parse info from the given file path
        [Input   ]: NA
        [Output  ]: NA
        [History ]:                                             
        ************************************************
        '''
        self.b_is_fw_image = False
        if not self.exists():
            return
        fn = os.path.basename(self.str_file_full_path).lower()

        ret = re.match(PATTERN_NAME, fn)
        if not ret:
            raise Exception('FAIL', 'Not an expected firmware file: %s', fn) 

        self.str_file_name = fn

        self.str_type = ret.group(2).lower()

        rev = ret.group(3)
        if len(rev) == 4:
            rev = '%s.%s' % (rev[0:2], rev[2:4])

        self.str_version = rev

        # parsing platform
        for platform in LIST_PLATFORM_SUPPORTED:
            if platform in self.str_type:
                self.str_platform = platform
                break
 
        # set the b_is_fw_image flag to True if no error is found
        self.b_is_fw_image = True
    
    def exists(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Tells if the file exists
        [Input   ]: NA
        [Output  ]: ret0 - boolean, tells if the file exists or not
        [History ]:                                             
        ************************************************
        '''
        if os.path.isfile(self.str_file_full_path):
            return True
        else:
            return False
        
    def full_file_path(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: return the full path of the image file
                    e.g. c:\images\abc_2020.bin
        [Input   ]: 
        [Output  ]: 
        [History ]:                                             
        ************************************************
        '''
        return self.str_file_full_path
    
    def base_file_name(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: return the full path of the image file. E.g.  for image with full 
                    path of c:\images\abc_2020.bin, this function will
                    return abc_2020.bin
        [Input   ]: 
        [Output  ]: 
        [History ]:                                             
        ************************************************
        '''
        return self.str_file_name
    
    def is_fw_image(self): 
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Tells if the file is a image file
        [Input   ]: NA
        [Output  ]: ret0 - boolean, tells if the file is a image or not
        [History ]:                                             
        ************************************************
        '''
        return self.b_is_fw_image
    
    def is_for_platform(self, str_platform):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Tells if the image is suitable for a given platform
                If the platform information in file name match the target platform or
                there is no platform information in file name.
                The function will return True
        [Input   ]: NA
        [Output  ]: ret0 - boolean, tells if the image is for the platform or not
        [History ]:                                             
        ************************************************
        '''
        if self.str_platform == str_platform or self.str_platform == '':
            return True
        else:
            return False
        
    def type(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Tells the FW type of the image
        [Input   ]: NA
        [Output  ]: ret0 - string, image type  
        [History ]:                                             
        ************************************************
        '''
        return self.str_type
    
    def platform(self):
        '''
        ************************************************
        [Author  ]: Forrest.Gu@emc.com
        [Function]: Tells the platform of the image
        [Input   ]: NA
        [Output  ]: ret0 - string, image type  
        [History ]:                                             
        ************************************************
        '''
        return self.str_platform
    
    def version(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Tells the FW version of the image
        [Input   ]: NA
        [Output  ]: ret0 - string, image version  
        [History ]:                                             
        ************************************************
        '''
        return self.str_version
    
    def copy_to(self, str_dest_folder):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: copy the image to a given folder
        [Input   ]: str_dest_folder - the destination folder
        [Output  ]: ret0 - boolean, if the action succeeds
        [History ]                                              
        ************************************************
        '''
        if not os.path.isdir(str_dest_folder):
            try:
                os.makedirs(str_dest_folder)
            except:
                return False
        try:
            shutil.copy(self.str_file_full_path, os.path.join(str_dest_folder, self.str_file_name))
        except:
            return False
        return True
            
    def create_md5_file(self, str_dest_folder=''):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Create the md5 value of the image and put the file 
                    to a given folder
        [Input   ]: str_dest_folder - the destination folder
        [Output  ]: ret0 - boolean, if the action succeeds
        [History ]                                              
        ************************************************
        '''
        # if no dest folder given, create in current folder
        if str_dest_folder == '':
            str_dest_folder = os.path.dirname(self.str_file_full_path)
            
        # read the image content
        try:
            f_read = open(self.str_file_full_path, 'rb')
        except:
            return False
        
        # check the dest folder
        if not os.path.isdir(str_dest_folder):
            try:
                os.makedirs(str_dest_folder)
            except: 
                f_read.close()
                return False
        
        # create md5 engine and compute the md5 value
        obj_md5_engine = hashlib.md5()
        
        for each_line in f_read:
            obj_md5_engine.update(each_line)
        
        f_read.close()
        
        str_md5_value = '%s *%s' % (obj_md5_engine.hexdigest(), self.str_file_name)
        
        # create md5 file in the dest folder
        str_md5_file = os.path.join(str_dest_folder, self.str_file_name.replace('.bin', '.md5'))
        try:
            f_write = open(str_md5_file, 'wb')
        except:
            return False
        f_write.write(str_md5_value)
        f_write.close()
        return True
    
if __name__ == '__main__':
    print 'Image module is not runnable'
