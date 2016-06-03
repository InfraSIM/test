'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
Created on Dec 22, 2015

@author: Tony Su
*********************************************************
'''
from lib.Device import CDevice
from lib.SSH import CSSH
from lib.Apps import with_connect
import re


class CHypervisor(CDevice):
    def __init__(self, dict_hypervisor):

        CDevice.__init__(self, 'hypervisor')

        self.dict_config = dict_hypervisor

        self.name = self.dict_config.get('name', '')
        self.type = self.dict_config.get('type', '')
        self.ip = self.dict_config.get('ip', '')
        self.username = self.dict_config.get('username', '')
        self.password = self.dict_config.get('password', '')

        self.ssh = CSSH(self.ip, username=self.username, password=self.password, port=22)

    def get_config(self):
        return self.dict_config

    def get_name(self):
        return self.name

    def get_ip(self):
        return self.ip

    def set_ip(self, ip):
        self.ip = ip

    def get_username(self):
        return self.username

    def set_username(self, username):
        self.username = username

    def get_password(self):
        return self.password

    def set_password(self, password):
        self.password = password

    @with_connect('ssh')
    def get_all_vmid(self):
        '''
        Get all vm information into a dict
        :return: a dict, e.g.
        {
            "vm1": "3180",
            "vm2": "3181"
        }
        '''
        dict_vms = {}

        rsp = self.ssh.remote_shell("vim-cmd vmsvc/getallvm")
        vms = rsp['stdout'].split("\n")
        for vm in vms:
            # The line define vm has datastore name in []
            if '[' not in vm:
                continue
            prefix = vm.split('[')[0]
            vm_id = prefix.split()[0].strip()
            vm_name = prefix.split(' ', 1)[1].strip()
            dict_vms[vm_name] = vm_id

        return dict_vms
    
    @with_connect('ssh')
    def get_vmid(self, dtstore, vm_name):
        rsp = self.ssh.remote_shell("vim-cmd vmsvc/getallvm")
        vms = rsp['stdout'].split("\n")
        for vm in vms:
            if vm.find(vm_name) > 0 and vm.find(dtstore) > 0:
                return vm.split(" ")[0]

    @with_connect('ssh')
    def power_on(self, vmid):
        self.log('INFO', 'Power on VM, ID: {} ...'.format(vmid))
        rsp = self.ssh.remote_shell("vim-cmd vmsvc/power.on {0}".format(vmid))
        if rsp['exitcode'] == 0:
            self.log('INFO', 'Power on VM, ID: {} is done'.format(vmid))
        else:
            self.log('WARNING', 'Fail to power on VM, ID: {}\nExit code: {}\nstdout:\n{}\nstderr:\n{}'.
                     format(vmid, rsp['exitcode'], rsp['stdout'], rsp['stderr']))

        return

    @with_connect('ssh')
    def power_off(self, vmid):
        self.log('INFO', 'Power off VM, ID: {} ...'.format(vmid))
        rsp = self.ssh.remote_shell("vim-cmd vmsvc/power.off {0}".format(vmid))
        if rsp['exitcode'] == 0:
            self.log('INFO', 'Power off VM, ID: {} is done'.format(vmid))
        else:
            self.log('WARNING', 'Fail to power off VM, ID: {}\nExit code: {}\nstdout:\n{}\nstderr:\n{}'.
                     format(vmid, rsp['exitcode'], rsp['stdout'], rsp['stderr']))

        return

    @with_connect('ssh')
    def drive_delete_all(self, dtstore, vm_name):
        vmid = self.get_vmid(dtstore, vm_name)

        self.log('INFO', 'Delete all drive of VM {} ID {} on datastore {}...'.format(vm_name, vmid, dtstore))

        rsp = self.ssh.remote_shell("ls /vmfs/volumes/{0}/{1}/{1}_*.vmdk".format(dtstore, vm_name))
        disks = rsp['stdout'].split('\n')
        disk_to_remove = []
        for disk in disks:
            if disk.endswith('vmdk') and 'flat' not in disk:
                disk_to_remove.append(disk)

        for disk in disk_to_remove:
            rsp = self.ssh.remote_shell("vim-cmd vmsvc/device.diskremove {0} 0 1 {1}".format(vmid, disk))

            disk_index = disk.split(vm_name)[-1].split('.')[0]

            if rsp['exitcode'] == 0:
                self.log('INFO', 'VM {} ID {} on datastore {} disk {} is deleted'.
                         format(vm_name, vmid, dtstore, disk_index))
            elif rsp['exitcode'] == 255:
                self.log('INFO', 'VM {} ID {} on datastore {} disk {} is not found'.
                         format(vm_name, vmid, dtstore, disk_index))
            else:
                self.log('WARNING', 'VM {} ID {} on datastore {} disk {} delete fail\n'
                                    'Exit code: {}\nstdout:\n{}\nstderr:\n{}'.
                         format(vm_name, vmid, dtstore, disk_index,
                                rsp['exitcode'], rsp['stdout'], rsp['stderr']))

        return

    @with_connect('ssh')
    def drive_delete(self, dtstore, vm_name, controller=0, unit=1):
        vmid = self.get_vmid(dtstore, vm_name)

        self.log('INFO', 'Delete drive {}.{} of VM {} ID {} on datastore {}...'.
                 format(controller, unit, vm_name, vmid, dtstore))

        rsp = self.ssh.remote_shell("vim-cmd vmsvc/device.diskremove {} {} {} true".
                                    format(vmid, controller, unit))

        if rsp['exitcode'] == 0:
            self.log('INFO', 'VM {} ID {} on datastore {} disk {}.{} is deleted'.
                     format(vm_name, vmid, dtstore, controller, unit))
        elif rsp['exitcode'] == 255:
            self.log('INFO', 'VM {} ID {} on datastore {} disk {} is not found'.
                     format(vm_name, vmid, dtstore, controller, unit))
        else:
            self.log('WARNING', 'VM {} ID {} on datastore {} disk {} delete fail\n'
                                'Exit code: {}\nstdout:\n{}\nstderr:\n{}'.
                     format(vm_name, vmid, dtstore, controller, unit,
                            rsp['exitcode'], rsp['stdout'], rsp['stderr']))

        return

    @with_connect('ssh')
    def drive_add(self, dtstore, vm_name, new_vmdk, controller=0, unit=1):
        vmid = self.get_vmid(dtstore, vm_name)

        self.log('INFO', 'Add drive on scsi {}.{} for VM ID {}, image: {} ...'.
                 format(controller, unit, vmid, new_vmdk))
        rsp = self.ssh.remote_shell("vim-cmd vmsvc/device.diskaddexisting {0} {1} {2} {3}".
                                    format(vmid, new_vmdk, controller, unit))
        if rsp['exitcode'] == 0:
            self.log('INFO', 'VM {} ID {} on datastore {} add disk {} on scsi {}.{} is done'.
                     format(vm_name, vmid, dtstore, new_vmdk, controller, unit))
        else:
            self.log('WARNING', 'VM {} ID {} on datastore {} add disk {}  on scsi {}.{} fail\n'
                                'Exit code: {}\nstdout:\n{}\nstderr:\n{}'.
                     format(vm_name, vmid, dtstore, new_vmdk, controller, unit,
                            rsp['exitcode'], rsp['stdout'], rsp['stderr']))
        return

    @with_connect('ssh')
    def search_datastore(self, name):
        rsp = self.ssh.remote_shell("find /vmfs/volumes -type f -name {}".format(name))
        if rsp['exitcode'] == 0:
            return rsp['stdout'].split('\n')
        else:
            self.log('WARNING', 'Fail to query {} on hypervisor {}'.format(name, self.get_name()))
            return None

    @with_connect('ssh')
    def get_vm_ip(self, vmid):
        p_ip = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'

        self.log('INFO', 'Get IP address for VM ID {}'.format(vmid))
        rsp = self.ssh.remote_shell("vim-cmd vmsvc/get.summary {} | grep ipAddress".format(vmid))
        if rsp['exitcode'] == 0:
            p = re.search(p_ip, rsp['stdout'])
            if p:
                self.log('INFO', 'VM ID {} IP is {}'.format(vmid, p.group(1)))
                return p.group(1)
        else:
            self.log('WARNING', 'Fail to get VM ID {}\'s IP'.format(vmid))
            return None
