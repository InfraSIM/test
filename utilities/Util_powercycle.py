'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
str_new_file_content = '''
from APC import CAPC 
import time
str_port_name = \'#PORTNAME#\'
str_port_number = \'#PORTNUMBER#\'
str_apc_ip = \'#APCIP#\'
print \'Powercycle: APCIP-%s, PortName-%s, PortNumbers-%s\' % (str_apc_ip, str_port_name, str_port_number)
# Access APC
if str_port_name != \'\':
    # By port name
    obj_apc = CAPC(str_apc_ip)
    obj_apc.power_cycle([str_port_name,], 10)
else:
    # By port number
    str_port_number = str_port_number.replace(\' \', \'\')
    if str_port_number != \'\':
        list_port_number = str_port_number.split(\',\')
        obj_apc = CAPC(str_apc_ip)
        obj_apc.power_cycle(list_port_number, 10)
print \'Completed\'
print \'Exit\'
time.sleep(2)
'''
if __name__ == '__main__':
    from optparse import OptionParser
    import time
    usage = "usage: %prog [options] arg1 arg2"
    parser = OptionParser(usage = usage)
    parser.add_option("-n", "--name", action = "store", \
                      type = "string", dest = "str_port_name" , default = "", help = "The port name. If this is assigned, the port number will be ignored")
    parser.add_option("-p", "--port", action = "store", \
                      type = "string", dest = "str_port_number", default = "", help = "The port number to be controlled. Separated by \',\'")
    parser.add_option("-i", "--ip", action = "store", \
                      type = "string", dest = "str_apc_ip", default = "", help = "The APC IP")
    
    (options, args) = parser.parse_args()
    from APC import CAPC
    str_apc_ip = options.str_apc_ip
    str_port_name = options.str_port_name
    str_port_number = options.str_port_number
    
    if str_apc_ip == '':
        # No APC IP, user input
        str_apc_ip = raw_input('Input APC IP (e.g. 192.168.1.201): ')
    if str_port_name == '':
        if str_port_number == '':
            str_choose = ''
            while 1:
                str_choose = raw_input("Choose 1(input port name) or 2(input port numbers) or q(quit): ")
                # No port name or port number, User input
                if str_choose == '1':
                    str_port_name = raw_input('Input port name: ')
                    if str_port_name != '':
                        break
                if str_choose == '2':
                    str_port_number = raw_input('Input port numbers(separate with \',\':')
                    str_port_number = str_port_number.replace(' ', '')
                    if str_port_number != '':
                        break
                if str_choose == 'q':
                    break
    # Access APC
    if str_port_name != '':
        # By port name
        obj_apc = CAPC(str_apc_ip)
        obj_apc.power_cycle([str_port_name,], 10)
    else:
        # By port number
        str_port_number = str_port_number.replace(' ', '')
        if str_port_number != '':
            list_port_number = str_port_number.split(',')
            obj_apc = CAPC(str_apc_ip)
            obj_apc.power_cycle(list_port_number, 10)
    print 'Completed'
    print
    str_choose = raw_input('Save script(y/n)?')
    if str_choose == 'y':
        str_file_full_path = raw_input('Input file name:')
        try:
            f_write = open(str_file_full_path,'w')
        except:
            print 'Failed to create new script'
            print 'Exit'
            time.sleep(2)
        str_new_file_content = str_new_file_content.replace('#PORTNUMBER#', str_port_number)
        str_new_file_content = str_new_file_content.replace('#PORTNAME#', str_port_name)
        str_new_file_content = str_new_file_content.replace('#APCIP#', str_apc_ip)
        f_write.write(str_new_file_content)
        print 'Success'
        f_write.close()
    print 'Exit'
    time.sleep(2)
        