'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import datetime
import sys
import os

if __name__ == '__main__':
    str_utility_path = sys.path[0]
    str_name = raw_input('Case name: ')
    str_py_name = os.path.join(str_utility_path, '..', 'case', 'probation', str_name + '.py')
    str_json_name = os.path.join(str_utility_path, '..', 'case', 'probation', str_name + '.json')
    f_py = open(str_py_name, "a")
    f_json = open(str_json_name, "a")
    
    
    str_py_file = "from case.CBaseCase import *\n\n\
class "+str_name+"(CBaseCase):\n\
    '''\n\
    [Purpose ]: \n\
    [Author  ]: @emc.com\n\
    [Sprint  ]: Lykan Sprint \n\
    [Tickets ]: SST-\n\
    '''\n\
    def __init__(self):\n\
        CBaseCase.__init__(self, self.__class__.__name__)\n\
    \n\
    def config(self):\n\
        CBaseCase.config(self)\n\
        # To do: Case specific config\n\
    \n\
    def test(self):\n\
        pass\n\
    \n\
    def deconfig(self):\n\
        # To do: Case specific deconfig\n\
        CBaseCase.deconfig(self)\n\
"

    str_json_file = \
"[\n\
    {}\n\
]\n\
"
    
    f_py.writelines(str_py_file)
    f_json.writelines(str_json_file)
    f_py.close()
    f_json.close()

    print 'Now your case is available as:\n' \
          '<puffer>/case/probation/{0}.py\n' \
          '<puffer>/case/probation/{0}.json'.format(str_name)
