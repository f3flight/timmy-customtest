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
        for p_name, p_version in reader:
            match = versions_db_cursor.execute('''
                SELECT * FROM versions
                WHERE release = ?
                    AND os = ?
                    AND package_name = ?
                    AND package_version = ?''', (node.release, node.os_platform, p_name, p_version)).fetchall()
            if not match:
                # try all releases
                match = versions_db_cursor.execute('''
                    SELECT * FROM versions
                    WHERE os = ?
                        AND package_name = ?
                        AND package_version = ?''', (node.os_platform, p_name, p_version)).fetchall()
                if match:
                    print('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +': package from a different release - '+p_name
                        +', version '+str(p_version)
                        +', found in release:'+match.fetchone()[2])
                    continue
                # try all versions for current release
                match = versions_db_cursor.execute('''
                SELECT * FROM versions
                WHERE release = ?
                    AND os = ?
                    AND package_name = ?''', (node.release, node.os_platform, p_name)).fetchall()
                if match:
                    print('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +': package version not in db - '+p_name
                        +', version '+str(p_version))
                    continue
                # package with a different version might still be found 
                # in a different release but such details are not interesting
                # so just fail
                print('env '+str(node.cluster)
                    +', node '+str(node.node_id)
                    +': package not in db - '+p_name
                    +' (installed version - '+str(p_version)+')')
                continue

def verify_md5_builtin_show_results(nodes, node):
    ignored_packages = [ 'vim-tiny' ]
    command = '.packages-md5-verify-'+node.os_platform
    if command not in node.mapcmds:
        print('node '+str(node.node_id)+': versions data was not collected!')
        return
    if not os.path.exists(node.mapcmds[command]):
        print('node-'+str(node.node_id)+': versions data output file is missing!')
        return
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5errorlist:
            reader = csv.reader(md5errorlist, delimiter='\t')
            for package, details in reader:
                if package not in ignored_packages:
                    print ('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +': '+str(package)
                        +' - '+str(details))
 
def verify_md5_with_db_show_results(nodes, node):
    ignored_packages = [ 'vim-tiny' ]
    command = '.packages-md5-db-verify-'+node.os_platform
    if command not in node.mapcmds:
        print('node '+str(node.node_id)+': versions data was not collected!')
        return
    if not os.path.exists(node.mapcmds[command]):
        print('node-'+str(node.node_id)+': versions data output file is missing!')
        return
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5errorlist:
            reader = csv.reader(md5errorlist, delimiter='\t')
            for id, package, version, details in reader:
                if package not in ignored_packages:
                    print ('env '+str(node.cluster)
                        +', node '+str(node.node_id)
                        +', package_id '+str(id)
                        +': '+str(package)
                        +', version '+str(version)
                        +' - '+str(details))



def main(argv=None):
    n = nodes_init()
    n.launch_ssh(n.conf['out-dir'])
    
    versions_db = sqlite3.connect(':memory:')
    load_versions_database(versions_db)
    versions_db_cursor = versions_db.cursor()
    
    print('versions verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready':
            verify_versions(versions_db_cursor, n, node)

    print('built-in md5 verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready':
            verify_md5_builtin_show_results(n, node)

    print('database md5 verification analysis...')
    for node in n.nodes.values():
        if node.status == 'ready':
            verify_md5_with_db_show_results(n, node)

    return 0

if __name__ == '__main__':
    exit(main(sys.argv))
