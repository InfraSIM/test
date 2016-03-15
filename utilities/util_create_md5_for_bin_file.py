'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
'''
===============================================================================
 [File Name]:util_create_md5_for_bin_file.py
 [Purpose]:This utility is for FFV fixed SerDes register value checking
 [History]:
 08/20/2013 Bruce.Yang@emc.com
     First verion, will create md5 file with the same name with ext of ".md5" for
     each binary file in the folder where the script is located
===============================================================================
'''

import os
import shutil
import hashlib


str_cwd = os.curdir

def all_binary_files_in_current_folder():
    list_files_in_curdir = os.listdir(str_cwd)
    print str_cwd
    list_binary_files = []
    for each_file in list_files_in_curdir:
        str_bin_file_full_path = os.path.join(str_cwd, each_file)
        print str_bin_file_full_path
        if str_bin_file_full_path.endswith('.bin'):
            list_binary_files.append(str_bin_file_full_path)
    return list_binary_files

def generate_md5_file_for_bin_file(str_bin_file_full_path):
        str_dest_folder = os.path.dirname(str_bin_file_full_path)
            
        # read the image content
        try:
            f_read = open(str_bin_file_full_path, 'rb')
        except:
            return False
        
        # create md5 engine and compute the md5 value
        obj_md5_engine = hashlib.md5()
        
        for each_line in f_read:
            obj_md5_engine.update(each_line)
        
        f_read.close()
        
        str_md5_value = '%s *%s' % (obj_md5_engine.hexdigest(), os.path.basename(str_bin_file_full_path))
        
        # create md5 file in the dest folder
        str_md5_file =os.path.join(str_dest_folder + '\\' + os.path.basename(str_bin_file_full_path).replace('.bin', '.md5'))
        try:
            f_write = open(str_md5_file, 'wb')
        except:
            print 'Failed to create MD5 file for image: %s' % str_bin_file_full_path
            return False
        f_write.write(str_md5_value)
        f_write.close()
        return True

if __name__ == '__main__':
    list_images = all_binary_files_in_current_folder()
    if list_images == []:
        print 'No binary file is found in current folder'
    for each_image in list_images:
        print 'Create MD5 file for %s ......' % each_image,
        if generate_md5_file_for_bin_file(each_image):
            print 'SUCCESS'
        else:
            print 'FAIL'
    print 'Done creating MD5 for binaries'