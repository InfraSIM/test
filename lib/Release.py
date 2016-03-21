'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
[Filename]: Release.py
[Author  ]: Bruce.Yang@emc.com
[Purpose ]: Implementation for FW release folder
[Contains]: 
            CRelease - class
[History ]:
********************************************************************
 VERSION      EDITOR                DATE             COMMENT
********************************************************************
  V1.0        Bruce.Yang@emc.com    09/12/2013       First edition
********************************************************************
'''

#imports
from Image import CImage
import os

bReleaseDebug = False


def ReleaseDebugPrint(str_msg):
    if bReleaseDebug:
        print str_msg


class CRelease():
    '''
    ************************************************
    [Author]: Bruce.Yang@emc.com
    [Description]: 
    [Methods]:    
    [History]:                                                                 
    ************************************************
    '''
    STATUS_UNKNOWN = -1
    STATUS_READY = 0
    STATUS_IMAGE_NOT_READY = 1
    STATUS_NOT_FOR_TARGET_PLATFORM = 2
    FILE_FW_SET = 'FW_SET.txt'
    FILE_FWQA_START = 'FWQA_START.txt'

    # Release check 
    # 1 - The trigger process agreed by FWQA and PM
    # 2 - Parse the images and check if all the images are ready    
    RELEASE_CHECK_STYLE = 1
    
    def __init__(self, str_folder_full_path, str_platform='', int_release_check_style=0):
        self.str_full_path = str_folder_full_path
        self.str_platform = str_platform
        self.int_release_check_style = int_release_check_style
        self.__parse_info()
    
    def __parse_info(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Parse the folder information
        [Input   ]: NA
        [Output  ]: NA 
        [History ]:                  
        ************************************************
        '''
        self.str_name = ''
        self.str_folder_base_path = ''
        self.str_image_zip_package_full_path = ''
        self.list_images = []

        # these two dicts are only used in XF where only four images
        # with known type are needed
        self.__dict_image_not_ready = {}
        self.__dict_image_ready = {}

        self.int_image_ready_count = 0
        self.int_status = CRelease.STATUS_UNKNOWN
        self.str_creator = ''
        self.str_create_date = ''
        self.str_branch = ''
        self.int_priority = 0
        self.list_customers = []
        
        if not self.__exist__():
            return
        self.str_folder_base_path = os.path.basename(self.str_full_path)
        
        # information parse and status check
        if self.int_release_check_style == 0:
            # Didn't define self level, use global level
            if CRelease.RELEASE_CHECK_STYLE == 1:
                if not self.parse_fw_start_file():
                    self.int_status = CRelease.STATUS_NOT_FOR_TARGET_PLATFORM
                    return
                if not self.parse_fw_set_file():
                    self.int_status = CRelease.STATUS_NOT_FOR_TARGET_PLATFORM
                    return
                self.__dict_image_not_ready = {}
            if CRelease.RELEASE_CHECK_STYLE == 2:
                self.fetch_images()
        else:
            if self.int_release_check_style == 1:
                if not self.parse_fw_start_file():
                    self.int_status = CRelease.STATUS_NOT_FOR_TARGET_PLATFORM
                    return
                if not self.parse_fw_set_file():
                    self.int_status = CRelease.STATUS_NOT_FOR_TARGET_PLATFORM
                    return
                self.__dict_image_not_ready = {}
            if self.int_release_check_style == 2:
                self.fetch_images()
        # Update status
        self.check_status()
        
        return

    def __exist__(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Check if the folder exists
        [Input   ]: NA
        [Output  ]: ret0 - boolean, exists or not  
        [History ]:                  
        ************************************************
        '''
        if not os.path.isdir(self.str_full_path):
            ReleaseDebugPrint('Full path not found')
            return False
        return True
    
    def base_folder_name(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is an interface to access the base folder of the 
                    release folder
        [Input   ]: NA
        [Output  ]:  
        [History ]:                  
        ************************************************
        '''
        return self.str_folder_base_path
    
    def full_path(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function is an interface to the full path of the release folder
        [Input   ]: NA
        [Output  ]:  
        [History ]:                  
        ************************************************
        '''
        return self.str_full_path
    
    def images(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provides the images ready in the folder
        [Input   ]: NA
        [Output  ]: ret0 - list, image objects   
        [History ]:                  
        ************************************************
        '''
        return self.list_images
    
    def name(self): 
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provide the release name
        [Input   ]: NA
        [Output  ]: ret0 - string, release name  
        [History ]                                              
        ************************************************
        '''
        return self.str_name
    
    def status(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provides the release status
        [Input   ]: NA
        [Output  ]: ret0 - int, status  
        [History ]                                              
        ************************************************
        '''
        return self.int_status
    
    def branch(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provides the branch name
        [Input   ]: NA
        [Output  ]: ret0 - string, branch name  
        [History ]                                              
        ************************************************
        '''
        return self.str_branch
    
    def customers(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provides the custormers of the release
        [Input   ]: NA
        [Output  ]: ret0 - list, customer list  
        [History ]                                              
        ************************************************
        '''
        return self.list_customers
    
    def creator(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Provides the creator of the release
        [Input   ]: NA
        [Output  ]: ret0 - string, creator name  
        [History ]                                              
        ************************************************
        '''
        return self.str_creator
    
    def copy_to(self, str_dest_folder):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: copy the images to a given folder
        [Input   ]: NA
        [Output  ]: ret0 - boolean, action result 
        [History ]                                              
        ************************************************
        '''
        if self.int_status != CRelease.STATUS_READY:
            return False
        
        b_result = True
        # copy all images to dest folder
        for each_image in self.list_images:
            if not each_image.copy_to(str_dest_folder):
                b_result = False
        if not os.path.isdir(str_dest_folder):
            try:
                os.makedirs(str_dest_folder)
            except:
                b_result = False
        # copy trigger file and the image zip file if there is
        import shutil
        try:
            shutil.copy(self.str_fw_set_file, os.path.join(str_dest_folder, CRelease.FILE_FW_SET))
            shutil.copy(self.str_fw_start_file, os.path.join(str_dest_folder, CRelease.FILE_FWQA_START))
            if self.str_image_zip_package_full_path != '':  # copy the image zip file, for moons
                ReleaseDebugPrint('Copy the image zip file')
                shutil.copy(self.str_image_zip_package_full_path,
                            os.path.join(str_dest_folder,
                                         os.path.basename(self.str_image_zip_package_full_path)))
            else:
                ReleaseDebugPrint('No image zip file')
        except Exception:
            ReleaseDebugPrint('Runtime error happen when copy image')
            b_result = False
            
        # update the release properties
        self.str_full_path = str_dest_folder
        self.__parse_info()
        
        return b_result        
    
    def create_md5_files(self, str_dest_folder=''):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Create md5 files to a given folder, create in current
                    folder if no dest folder is specified
        [Input   ]: NA
        [Output  ]: ret0 - boolean, action result
        [History ]                                              
        ************************************************
        '''
        b_result = True
        for each_image in self.list_images:
            if not each_image.create_md5_file(str_dest_folder):
                b_result = False
        return b_result
    
    def parse_fw_set_file(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Parse the FW_SET.txt file which is defined
                    between FFV and PM
        [Input   ]: NA
        [Output  ]: ret0 - boolean, action result
        [History ]                                              
        ************************************************
        '''
        ReleaseDebugPrint('parse FW set file')
        self.str_fw_set_file = os.path.join(self.str_full_path, CRelease.FILE_FW_SET)
        
        #check if the fw_set file exists
        if not os.path.isfile(self.str_fw_set_file):
            ReleaseDebugPrint('FW set file not found')
            return False
        try:
            fRead = open(self.str_fw_set_file, 'r')
        except:
            ReleaseDebugPrint('Failed to open FW set file')
            return False
        
        #fetch fw_set info for all platforms
        str_fw_set_info_all_platforms = fRead.read() # Read FW set info
        fRead.close()
        str_fw_set_info_all_platforms = str_fw_set_info_all_platforms.replace('\t', '') #remove tabs
        list_fw_set_info_all_platforms = str_fw_set_info_all_platforms.split('\n')
        
        # check if there is fw_set info for target platform
        str_target_fw_set_info = ''
        for each_fw_set in list_fw_set_info_all_platforms:
            each_fw_set = each_fw_set.strip()
            if each_fw_set.lower().startswith(self.str_platform):
                str_target_fw_set_info = each_fw_set
                break
        if str_target_fw_set_info == '':
            ReleaseDebugPrint('No FW set for target platform')
            return False
        
        #parse the fw_set info for target platform
        list_target_fw_set_info = str_target_fw_set_info.split(';')
        int_length_target_fw_set_info = len(list_target_fw_set_info)
        if int_length_target_fw_set_info < 3:
            return False
        
        # parse the release name
        self.str_name = list_target_fw_set_info[1].strip().replace(' ', '_')
        
        list_images_in_fw_set_file = list_target_fw_set_info[2:int_length_target_fw_set_info - 1]
        # for transformer
        if str_target_fw_set_info.lower().find('.zip') == -1:
            ReleaseDebugPrint('this release is for XF')
            for each_image in list_images_in_fw_set_file:
                each_image = each_image.strip().lower()
                str_image_full_path = os.path.join(self.str_full_path, each_image)
                # add image to the release image poor
                obj_image_add = CImage(str_image_full_path)
                if obj_image_add.b_is_fw_image:
                    self.list_images.append(obj_image_add)
        # for moons
        else:
            ReleaseDebugPrint('this release is for Moons')
            for each_image in list_images_in_fw_set_file:
                each_image = each_image.strip()
                str_image_full_path = os.path.join(self.str_full_path, each_image)
                if each_image.endswith('.zip'):
                    # get the image zip file
                    self.str_image_zip_package_full_path = str_image_full_path
                    break
        # if there is no image info(either image files or zip file), mark the FW set file invalid
        if self.list_images == [] and self.str_image_zip_package_full_path == '':
            return False
        
        str_priority = list_target_fw_set_info[int_length_target_fw_set_info - 1].strip().lower()
        try:
            if str_priority.startswith('priority:'):
                self.int_priority = int(str_priority[str_priority.find(':') + 1:], 10)
        except:
            self.int_priority = 0
        return True
        
    def parse_fw_start_file(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Parse the FW_START.txt file which is defined
                    between FFV and PM
        [Input   ]: NA
        [Output  ]: ret0 - boolean, action result
        [History ]                                              
        ************************************************
        '''
        self.str_fw_start_file = os.path.join(self.str_full_path, CRelease.FILE_FWQA_START)
        # check if the fwqa_start file exists
        if not os.path.isfile(self.str_fw_start_file):
            return False
        try:
            fRead = open(self.str_fw_start_file, 'r')
        except:
            return False
        
        # fetch the start info
        str_fw_start_info = fRead.readline().lower().replace(' ', '')
        list_fw_start_info = str_fw_start_info.split(';')
        self.str_creator = list_fw_start_info[0]
        try:
            self.str_create_date = list_fw_start_info[1]
        except:
            print list_fw_start_info
        
        return True
        
    def fetch_images(self, str_image_folder = None):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: Fetch all images in the release folder
        [Input   ]: NA
        [Output  ]: ret0 - boolean, action result
        [History ]                                              
        ************************************************
        '''
        if str_image_folder is None:
            str_image_folder = self.str_full_path
        
        list_files_in_folder = os.listdir(str_image_folder)
        for each_file in list_files_in_folder:
            obj_image = CImage(os.path.join(str_image_folder, each_file))
            if not obj_image.is_for_platform(self.str_platform):
                continue
            if self.list_images.count(obj_image) == 0:
                self.list_images.append(obj_image)
                
    def image_files_full_path(self):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function will parse the image list in the release folder and
                    provide a list of the full path of all images
        [Input   ]: 
        [Output  ]: 
        [History ]                                              
        ************************************************
        '''
        list_image_file_full_path = []
        for each_image in self.list_images:
            list_image_file_full_path.append(each_image.full_file_path())
        return list_image_file_full_path
            
    def get_image_by_type(self, str_type):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: This function will try to find a target type of image. If the image
                    is found, it will return the image object. Otherwise, it
                    will return None
        [Input   ]: str_type, legal types are cut out from image name:
                        1. Remove header
                        2. Remove version ending
        [Output  ]: 
        [History ]                                              
        ************************************************
        '''
        for each_image in self.list_images:
            if each_image.type().startswith(str_type):
                return each_image
        return None
    
    def unzip_image_package(self, str_dest_folder = None):
        '''
        ************************************************
        [Author  ]: Bruce.Yang@emc.com
        [Function]: In moons platform, all the images will be packaged in a 
                    zip file. This function is used to unzip the image package
                    to release all image files
        [Input   ]: 
        [Output  ]: 
        [History ]                                              
        ************************************************
        '''
        if self.int_status != CRelease.STATUS_READY:
            return -1
        
        # check if the zip file exists
        if not os.path.isfile(self.str_image_zip_package_full_path):
            ReleaseDebugPrint('No image zip or zip file(%s) not found' % self.str_image_zip_package_full_path)
            return -1
        
        # if dest folder is not set, extract to the release folder
        if str_dest_folder is None:
            str_dest_folder = self.str_full_path
            
        # extract image files
        from zipfile import ZipFile as ZF
        zip_image = ZF(self.str_image_zip_package_full_path)
        zip_image.extractall(str_dest_folder)
        
        # check the results
        if not os.path.isdir(os.path.join(str_dest_folder, 'EMC')):
            return -1
        
        # update list_image
        self.fetch_images(os.path.join(str_dest_folder, 'EMC'))
        
        return 0
                
if __name__ == '__main__':
    objRelease = CRelease('D:\\workspace\\Forrest\\Release', 'abc')
    list_image_full_path = objRelease.image_files_full_path()
    for each_image_full_path in list_image_full_path:
        print 'Image: %s' % each_image_full_path
    print 'full path: %s' % objRelease.str_full_path
    print 'image zip: %s' % objRelease.str_image_zip_package_full_path
    print 'status: %s' % objRelease.status()
    print 'creator: %s' % objRelease.creator()
    print 'branch: %s' % objRelease.branch()
    print 'name: %s' % objRelease.name()
    print 'priority: %s' % str(objRelease.int_priority)
    objRelease.create_md5_files()
    
    print '\nAfter copy'
    objRelease.copy_to('C:\\Users\\yangb10\\Desktop\\DEST')
    list_image_full_path = objRelease.image_files_full_path()
    for each_image_full_path in list_image_full_path:
        print 'Image: %s' % each_image_full_path
    print 'full path: %s' % objRelease.str_full_path
    print 'image zip: %s' % objRelease.str_image_zip_package_full_path
    print 'status: %s' % objRelease.status()
    print 'creator: %s' % objRelease.creator()
    print 'branch: %s' % objRelease.branch()
    print 'name: %s' % objRelease.name()
    print 'priority: %s' % str(objRelease.int_priority)
    
    print '\nAfter unzip'
    objRelease.unzip_image_package()
    list_image_full_path = objRelease.image_files_full_path()
    for each_image_full_path in list_image_full_path:
        print 'Image: %s' % each_image_full_path
    print 'full path: %s' % objRelease.str_full_path
    print 'image zip: %s' % objRelease.str_image_zip_package_full_path
    print 'status: %s' % objRelease.status()
    print 'creator: %s' % objRelease.creator()
    print 'branch: %s' % objRelease.branch()
    print 'name: %s' % objRelease.name()
    print 'priority: %s' % str(objRelease.int_priority)

