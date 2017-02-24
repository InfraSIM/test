#!/usr/bin/env python
"""
This is a utility to accept commandline option and help generate
Vagrantfile to deploy on vSphere.
"""

import jinja2
import os
import sys
import re
from optparse import OptionParser, OptionGroup


# Find template from test/doc/template_Vagrantfile
path_template = os.sep.join(
    # ../doc/template_ansible_inventory
    os.path.abspath(__file__).split(os.sep)[:-2]
    +["doc", "template_Vagrantfile"])

options = None
parser = None


def parse_options():
    global options
    global parser

    usage = 'usage: %prog [option] arg1 arg2'

    parser = OptionParser(usage=usage)

    # General options
    group = OptionGroup(parser, 'General Options')

    group.add_option('-n', '--node_number', action='store',
                     type='int', dest='node_number', default=9,
                     help='Total node number to be deployed, default is 9, '
                          'for InfraSIM now supports 9 node type now')

    group.add_option('-o', '--output', action='store',
                     type='string', dest='output', default='Vagrantfile',
                     help='Output vagrantfile path, default is a Vagrantfile '
                          'in current path')

    parser.add_option_group(group)

    # vSphere options
    group_vsphere = OptionGroup(parser, 'vSphere Options')

    group_vsphere.add_option('', '--host', action='store',
                             type='string', dest='v_center_host', default='',
                             help='[Mandatory] vCenter host name')
    group_vsphere.add_option('-u', '--user', action='store',
                             type='string', dest='v_user', default='',
                             help='[Mandatory] vCenter user name')
    group_vsphere.add_option('-p', '--pass', action='store',
                             type='string', dest='v_pass', default='',
                             help='[Mandatory] vCenter password')
    group_vsphere.add_option('-d', '--datacenter', action='store',
                             type='string', dest='v_datacenter', default='',
                             help='[Mandatory] Target cluster')
    group_vsphere.add_option('-c', '--compute', action='store',
                             type='string', dest='v_compute', default='',
                             help='[Mandatory] Target compute resource name, '
                                  'it can be ESXi host name, or cluster name')
    group_vsphere.add_option('-t', '--template', action='store',
                             type='string', dest='v_template', default='',
                             help='[Mandatory] vSphere template path')
    group_vsphere.add_option('-r', '--resourcepool', action='store',
                             type='string', dest='v_resource_pool', default='',
                             help='[Mandatory] Target resource pool path')
    group_vsphere.add_option('', '--outfolder', action='store',
                             type='string', dest='v_output_folder', default='',
                             help='[Mandatory] Target folder to put computes')
    parser.add_option_group(group_vsphere)

    (options, args) = parser.parse_args()

    return options


def write_vagrantfile():
    global options
    global parser
    global path_template

    is_legal = True
    if not options.v_center_host:
        print 'vCenter host name (--host) is missing'
        is_legal = False
    if not options.v_datacenter:
        print 'Datacenter name (-d) is missing'
        is_legal = False
    if not options.v_compute:
        print 'Compute resource (-c) is missing'
        is_legal = False
    if not options.v_user:
        print 'vCenter user name (-u) is missing'
        is_legal = False
    if not options.v_pass:
        print 'vCenter password (-p) is missing'
        is_legal = False
    if not options.v_template:
        print 'Template file (-t) is missing'
        is_legal = False
    if not options.v_resource_pool:
        print 'Target resource pool (-r) is missing'
        is_legal = False
    if not options.v_output_folder:
        print 'Target folder (--outfolder) is missing'
        is_legal = False
    if not is_legal:
        print 'Fail to write Vagrantfile!'
        exit(-1)

    with open(path_template, "r") as fp:
        vagrantfile_template = fp.read()
    template = jinja2.Template(vagrantfile_template)
    inventory = template.render(node_count=options.node_number,
                                v_host=options.v_center_host,
                                v_datacenter=options.v_datacenter,
                                v_compute=options.v_compute,
                                v_user=options.v_user,
                                v_pass=options.v_pass,
                                v_template=options.v_template,
                                v_resource_pool=options.v_resource_pool,
                                v_output_folder=options.v_output_folder)
    with open(options.output, "w") as fp:
        fp.write(inventory)


if __name__ == "__main__":
    parse_options()
    write_vagrantfile()
