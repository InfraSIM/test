'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Jul 30, 2015
@author: wuy1

Currently user need to input the password during the installation in Linux. In the future when integration with Jenkins, we will develop the feature to let user input the password and rend it in a configure file. Then it will automatically write the password during installation.
*********************************************************
'''

import os
import ctypes, sys
import commands

def pip_install():
    """
        Install the pip module if cannot import pip successfully. 
        If the system is Windows, it will install pip by running python get-pip.py
        If the system is Linux, it will install pip by running "sudo apt-get install python-pip"
    """   
    try:
        import pip
        print "PIP already installed"
    except ImportError:
        print "Start to install PIP"
        # nt represent windows OS
        if os.name == 'nt':
            os.system("python get-pip.py")
        # posix represent Linux/Unix OS
        elif os.name == 'posix':
            os.system("sudo apt-get install -y python-pip")
        else:
            return "System not supported"
   
def install_in_linux():
    """
        Install the python-dev module in linux system
    """  
    try:
        os.system("sudo apt-get -y install build-essential libssl-dev libffi-dev python-dev")
    except:
        e = sys.exc_info()[0]
        print e
            
def install_and_import(package):
    """
        Install third class python modules using pip 
        If the system is Windows, it will install pip by running pip install <package>
        If the system is Linux, it will install pip by running "sudo pip install <package>"
    """ 
    import importlib
    try:
        if package == "pyserial":
            import serial
            print "pyserial already installed"
        elif package == "requests":
            import requests
            print "Start to upgrade requests"
            if os.name == 'nt':
                micmd = "pip install -U "+str(package)
                output = os.popen(micmd)
            elif os.name == 'posix':
                os.system("sudo pip install -U "+str(package))
            print "requests upgrade successfully"
        else:
            importlib.import_module(package)
            print "{0} already installed".format(package)
    except ImportError:
        try:
            if os.name == 'nt':
                micmd = "pip install -U "+str(package)
                output = os.popen(micmd)
                info = output.readlines()
                str_c_compiler_error = "unable to find vcvarsall.bat"
                str_all = ""
                for line in info:
                    line = line.strip('\r\n')
                    print line
                    if str(line).lower().find(str_c_compiler_error) != -1:
                        error_message = "To solve the \"unable to find vcvarsall.bat\" error in Windows environment, please go to http://www.microsoft.com/en-us/download/details.aspx?id=44266, download and install Microsoft Visual C++ Compiler for Python 2.7 first, then try to install the package again."
                        print 
                        
                        STD_INPUT_HANDLE = -10
                        STD_OUTPUT_HANDLE = -11
                        STD_ERROR_HANDLE = -12

                        FOREGROUND_RED = 0x0c # red.
                        FOREGROUND_GREEN = 0x0a # green.
                        FOREGROUND_BLUE = 0x09 # blue.
                        std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
                        ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, FOREGROUND_RED)
                        sys.stdout.write(error_message.encode('gb2312'))
                        ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE)
                        
                        print
                        return
            # posix represent Linux/Unix OS
            elif os.name == 'posix':
                os.system("sudo pip install -U "+str(package))
            print "Successfully install {0} package".format(package)
        except:
            print "Fail to install {0} package".format(package)
        
#Main test function
if __name__ == '__main__':
    pip_install()
    
    if os.name =='nt':
        # Add python path to the environment path. If not, pip install package will fail.
        path = sys.executable
        PythonPath = path[0:path.rfind(os.sep)]
        envPath = PythonPath + "\\;"+PythonPath+"\\Scripts\\"
        os.environ['PATH']=envPath
        #print os.environ['PATH']
        
    if os.name == 'posix':
        install_in_linux()
        
    install_and_import('pyserial')
    install_and_import('gevent')
    install_and_import('jsonrpclib')
    install_and_import('cryptography')
    install_and_import('paramiko')
    install_and_import('requests')
    install_and_import('six')
    install_and_import('pysnmp')
    install_and_import('jinja2')
