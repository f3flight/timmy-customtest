#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import logging
import sys
from timmy import nodes, loadconf
import csv
import sqlite3
import re
import os

# implementation of RPM's rpmvercmp function
# http://rpm.org/wiki/PackagerDocs/Dependencies
# http://rpm.org/api/4.4.2.2/rpmvercmp_8c-source.html#l00015
def rpm_vercmp(a, b):
    a_newer = 1
    b_newer = -1
    equal = 0
    if a == b:
        return equal
    if a and not b:
        return a_newer
    if b and not a:
        return b_newer
    a_epoch = re.match('^(-?\d):', a)
    b_epoch = re.match('^(-?\d):', b)
    if a_epoch:
        if b_epoch:
            if int(a_epoch.groups()[0]) > int(b_epoch.groups()[0]):
                return a_newer
            if int(a_epoch.groups()[0]) < int(b_epoch.groups()[0]):
                return b_newer
        if int(a_epoch.groups()[0]) > 0:
            return a_newer
        if int(a_epoch.groups()[0]) < 0:
            return b_newer
    elif b_epoch:
        if int(b_epoch.groups()[0]) > 0:
            return b_newer
        if int(b_epoch.groups()[0]) < 0:
            return a_newer
    a_list = re.findall('[a-zA-Z]+|[0-9]+', a)
    b_list = re.findall('[a-zA-Z]+|[0-9]+', b)
    for index, value in enumerate(a_list):
        if index > len(b_list):
            return a_newer
        else:
            if value.isdigit():
                if not b_list[index].isdigit():
                    return a_newer
                else:
                    if int(value) > int(b_list[index]):
                        return a_newer
                    if int(value) < int(b_list[index]):
                        return b_newer
            else:
                if b_list[index].isdigit():
                    return b_newer
                else:
                    if value > b_list[index]:
                        return a_newer
                    if value < b_list[index]:
                        return b_newer
    if len(b_list) > len(a_list):
        return b_newer
    return equal

# implementation of Debian version comparison
# https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
# http://dpkg.sourcearchive.com/documentation/1.15.6/vercmp_8c-source.html
def deb_vercmp(a, b):

    def cmp(a, b):

        def order(x):
            if x == '~':
                return -1
            if x.isdigit():
                return int(x)
            if ord(x) in range(ord('A'), ord('Z')+1)+range(ord('a'),ord('z')):
                return x
            else:
                return ord(x) + 256

        ia = 0
        ib = 0 
        iter = -1
        while ia < len(a) or ib < len(b):
            iter += 1
            diff = 0
            # workaround for end of string, add 0 to compare lower then everything except '~'
            # it is impossible that both ia and ib get over string bounds, so no endless loop possibility
            if ia == len(a):
                a += '0'
            if ib == len(b):
                b += '0'
            while (ia < len(a) and not a[ia].isdigit()) or ( ib < len(b) and not b[ib].isdigit()):
                if order(a[ia]) > order(b[ib]):
                    return 1
                if order(a[ia]) < order(b[ib]):
                    return -1
                ia += 1
                ib += 1
            while ia < len(a) and a[ia] == '0':
                ia += 1
            while ib < len(b) and b[ib] == '0':
                ib += 1
            while ia < len(a) and a[ia].isdigit() and ib < len(b) and b[ib].isdigit():
                if not diff:
                    diff = int(a[ia]) - int(b[ib])
                ia += 1
                ib += 1
            if ia < len(a) and a[ia].isdigit():
                return 1
            if ib < len(b) and b[ib].isdigit():
                return -1
            if diff:
                return diff
        return 0

    a_newer = 1
    b_newer = -1
    equal = 0
    if a == b:
        return equal
    if a and not b:
        return a_newer
    if b and not a:
        return b_newer
    a_epoch = re.match('^(\d):', a)
    b_epoch = re.match('^(\d):', b)
    if a_epoch:
        if b_epoch:
            if int(a_epoch.groups()[0]) > int(b_epoch.groups()[0]):
                return a_newer
            if int(a_epoch.groups()[0]) < int(b_epoch.groups()[0]):
                return b_newer
        elif int(a_epoch.groups()[0]) > 0:
            return a_newer
        else:
            b = b[2:]
        a = a[2:]
    elif b_epoch:
        if int(b_epoch.groups()[0]) > 0:
            return b_newer
        b = b[2:]

    a_parts = re.match('^([^-].+?)?(?:-([^-]+))?$', a)
    a_version = a_revision = None
    if a_parts:
        a_version, a_revision = a_parts.groups()
    b_parts = re.match('^([^-].+?)?(?:-([^-]+))?$', b)
    b_version = b_revision = None
    if b_parts:
        b_version, b_revision = b_parts.groups()
    if a_version and not b_version:
        return a_newer
    if b_version and not a_version:
        return b_newer
    vc = cmp(a_version, b_version)
    if vc > 0:
        return a_newer
    if vc < 0:
        return b_newer
    if a_revision and not b_revision:
        return a_newer
    if b_revision and not a_revision:
        return b_newer
    rc = cmp(a_revision, b_revision)
    if rc > 0:
        return a_newer
    if rc < 0:
        return b_newer
    return equal

def load_versions_database(sqlite_db):
    '''
       fields:
       0 - line number
       1 - job id
       2 - release number
       3 - mu
       4 - os
       5 - package name
       6 - package version
       7 - package filename
    '''

    sqlite_db_cursor = sqlite_db.cursor()
    sqlite_db_cursor.execute('''
        CREATE TABLE versions
        (
            id INTEGER,
            job_id INTEGER,
            release TEXT,
            mu TEXT,
            os TEXT,
            package_name TEXT,
            package_version TEXT,
            package_filename TEXT
        )''')
    db_dir='db/versions'
    databases = [os.path.join(db_dir,release,'versions.tsv') for release in os.listdir(db_dir) if os.path.isdir(os.path.join(db_dir,release))]
    for db_filename in databases:
        with open(db_filename,'r') as db:
            csv_reader = csv.reader(db, delimiter='\t')
            sqlite_db_cursor.executemany('''
                INSERT INTO versions (id, job_id, release, mu, os, package_name, package_version, package_filename)
                VALUES (?,?,?,?,?,?,?,?)''', csv_reader)
            sqlite_db.commit()

def nodes_init():
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(message)s')
    conf = loadconf.load_conf('config.yaml')
    n = nodes.Nodes(conf=conf,
                    extended=0,
                    cluster=None,
                    destdir='/tmp')
    n.get_node_file_list()
    n.get_release()
    return n    

def verify_versions(versions_db_cursor, nodes, node):
    db_has_release = versions_db_cursor.execute('''
        SELECT COUNT(*) FROM versions WHERE release = ?
        ''', (node.release,)).fetchall()
    if db_has_release[0][0] == 0:
        print('node-'+str(node.node_id)+' - sorry, the database does not have any data for Fuel release '+str(node.release)+'!')
        return
    command = '.packagelist-'+node.os_platform
    if command not in node.mapcmds:
        print('node '+str(node.node_id)+': versions data was not collected!')
        return
    if not os.path.exists(node.mapcmds[command]):
        print('node-'+str(node.node_id)+': versions data output file is missing!')
        return
    with open(node.mapcmds[command],'r') as packagelist:
        reader = csv.reader(packagelist, delimiter='\t')
        if not hasattr(node,'custom_packages'):
             node.custom_packages = {}
        for p_name, p_version in reader:
            match = versions_db_cursor.execute('''
                SELECT * FROM versions
                WHERE release = ?
                    AND os = ?
                    AND package_name = ?
                    AND package_version = ?''', (node.release, node.os_platform, p_name, p_version)).fetchall()
            if not match:
                # try all versions for current release
                match = versions_db_cursor.execute('''
                SELECT * FROM versions
                WHERE release = ?
                    AND os = ?
                    AND package_name = ?''', (node.release, node.os_platform, p_name)).fetchall()
                if match:
                    node.custom_packages[p_name] = p_version
                    print('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +': package version not in db - '+p_name
                        +', version '+str(p_version))
                    continue
                ## try all releases - disabled for now because of lack of upstream data in db for newer releases
                # match = versions_db_cursor.execute('''
                #     SELECT * FROM versions
                #     WHERE os = ?
                #         AND package_name = ?
                #         AND package_version = ?''', (node.os_platform, p_name, p_version)).fetchall()
                # if match:
                #     print('env '+str(node.cluster)
                #         +', node '+str(node.node_id)
                #         +': package from a different release - '+p_name
                #         +', version '+str(p_version)
                #         +', found in release '+match[0][2])
                #     continue
                ## Package with a different version might still be found 
                ## in a different release but such details are not interesting
                ## so just fail with a message.
                ## Commenting out this section for now
                ## since db for the most part does not contain
                ## upstream packages and this will result in
                ## false positives
                # print('env '+str(node.cluster)
                #     +', node '+str(node.node_id)
                #     +': package not in db - '+p_name
                #     +' (installed version - '+str(p_version)+')')
                continue

def verify_md5_builtin_show_results(nodes, node):
    ignored_packages = [ 'vim-tiny' ]
    command = '.packages-md5-verify-'+node.os_platform
    if command not in node.mapcmds:
        print('node '+str(node.node_id)+': builtin md5 data was not collected!')
        return
    if not os.path.exists(node.mapcmds[command]):
        print('node-'+str(node.node_id)+': builtin md5 data output file is missing!')
        return
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5errorlist:
            reader = csv.reader(md5errorlist, delimiter='\t')
            for p_name, p_version, details in reader:
                if p_name not in ignored_packages:
                    if not hasattr(node,'custom_packages'):
                        node.custom_packages = {}
                    node.custom_packages[p_name] = p_version
                    print ('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +': '+str(p_name)
                        +', version '+str(p_version)
                        +' - '+str(details))
 
def verify_md5_with_db_show_results(nodes, node):
    ignored_packages = [ 'vim-tiny' ]
    command = '.packages-md5-db-verify-'+node.os_platform
    if command not in node.mapcmds:
        print('node '+str(node.node_id)+': db md5 data was not collected!')
        return
    if not os.path.exists(node.mapcmds[command]):
        print('node-'+str(node.node_id)+': db md5 data output file is missing!')
        return
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5errorlist:
            reader = csv.reader(md5errorlist, delimiter='\t')
            for id, p_name, p_version, details in reader:
                if p_name not in ignored_packages:
                    if not hasattr(node,'custom_packages'):
                        node.custom_packages = {}
                    node.custom_packages[p_name] = p_version
                    print ('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +', package_id '+str(id)
                        +': '+str(p_name)
                        +', version '+str(p_version)
                        +' - '+str(details))

def max_versions_dict(versions_db):
    versions_db_cursor = versions_db.cursor()
    data = versions_db_cursor.execute('''
        SELECT release, os, package_name, package_version
        FROM versions
        ''').fetchall()
    max_version = {}
    for el in data:
        if el[0] not in max_version:
            max_version[el[0]] = {}
        if el[1] not in max_version[el[0]]:
            max_version[el[0]][el[1]] = {}
        if el[2] not in max_version[el[0]][el[1]]:
            max_version[el[0]][el[1]][el[2]] = el[3]
        else:
            if el[1] == 'centos':
                if rpm_vercmp(el[3], max_version[el[0]][el[1]][el[2]]) > 0:
                    max_version[el[0]][el[1]][el[2]] = el[3]
            if el[1] == 'ubuntu':
                if deb_vercmp(el[3], max_version[el[0]][el[1]][el[2]]) > 0:
                    max_version[el[0]][el[1]][el[2]] = el[3]
    return max_version

def mu_safety_check(node, mvd):
    if hasattr(node, 'custom_packages'):
        for p_name, p_version in node.custom_packages.items():
            if node.release in mvd:
                if node.os_platform in mvd[node.release]:
                    if p_name in mvd[node.release][node.os_platform]:
                        if node.os_platform == 'centos':
                            if rpm_vercmp(mvd[node.release][node.os_platform][p_name],p_version) > 0:
                                print('env '+str(node.cluster)
                                    +', node '+str(node.node_id)
                                    +': custom package '+ str(p_name)
                                    +' version '+str(p_version)
                                    +' will be overwritten by MU version '+str(mvd[node.release][node.os_platform][p_name]))
                            else:
                                print('env '+str(node.cluster)
                                    +', node '+str(node.node_id)
                                    +': custom package '+ str(p_name)
                                    +' version '+str(p_version)
                                    +' will prevent (MU or release) version '+str(mvd[node.release][node.os_platform][p_name])
                                    +' from being installed')
                        elif node.os_platform == 'ubuntu':
                            if deb_vercmp(mvd[node.release][node.os_platform][p_name],p_version) > 0:
                                print('env '+str(node.cluster)
                                    +', node '+str(node.node_id)
                                    +': custom package '+ str(p_name)
                                    +' version '+str(p_version)
                                    +' will be overwritten by MU version '+str(mvd[node.release][node.os_platform][p_name]))
                            else:
                                print('env '+str(node.cluster)
                                    +', node '+str(node.node_id)
                                    +': custom package '+ str(p_name)
                                    +' version '+str(p_version)
                                    +' will prevent (MU or release) version '+str(mvd[node.release][node.os_platform][p_name])
                                    +' from being installed')

def main(argv=None):
    n = nodes_init()
    n.launch_ssh(n.conf['out-dir'])
    
    versions_db = sqlite3.connect(':memory:')
    load_versions_database(versions_db)
    versions_db_cursor = versions_db.cursor()
    
    print('versions verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            verify_versions(versions_db_cursor, n, node)

    print('built-in md5 verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            verify_md5_builtin_show_results(n, node)

    print('database md5 verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            verify_md5_with_db_show_results(n, node)

    print('MU safety analysis...')
    mvd = max_versions_dict(versions_db)
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            mu_safety_check(node, mvd)

    print('possible update ')
    mvd = max_versions_dict(versions_db)
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            mu_safety_check(node, mvd)

    return 0

if __name__ == '__main__':
    exit(main(sys.argv))
