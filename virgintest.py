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


import argparse
import logging
import sys
from timmy import nodes, loadconf
from subprocess import Popen,PIPE
import csv
import sqlite3
import re
import os


def load_versions_database(sqlite_db, db_filename=None):
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
    if db_filename == None:
        db_filename='db/versions.tsv'

    with open(db_filename,'r') as db:
        csv_reader = csv.reader(db, delimiter='\t')
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

        sqlite_db_cursor.executemany('''
            INSERT INTO versions (id, job_id, release, mu, os, package_name, package_version, package_filename)
            VALUES (?,?,?,?,?,?,?,?)''', csv_reader)
        sqlite_db.commit()

def collect():
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(message)s')
    conf = loadconf.load_conf('config.yaml')
    n = nodes.Nodes(conf=conf,
                    extended=0,
                    cluster=None,
                    destdir='/tmp')
    n.get_node_file_list()
    n.launch_ssh(conf['out-dir'])
    return n    

def main(argv=None):
    n = collect()

    versions_db = sqlite3.connect(':memory:')
    load_versions_database(versions_db)
    versions_db_cursor = versions_db.cursor()

    release_cmd = Popen(['grep release /etc/fuel/version.yaml | cut -d\'"\' -f2'], stdout=PIPE, shell=True)    
    (release, err) = release_cmd.communicate()
    release = release.rstrip()
    db_has_release = versions_db_cursor.execute('''
        SELECT COUNT(*) FROM versions WHERE release = ?
        ''', (release,)).fetchall()
    if db_has_release[0][0] == 0:
        print('Sorry, the database does not have any data for this Fuel release!')
        exit(0)
    
    print('versions verification analysis...')
    file_list_cmd = Popen(['find', n.conf['out-dir'], '-name', '*.packagelist-*'], stdout=PIPE)
    (file_list, err) = file_list_cmd.communicate()
    for file in file_list.rstrip().splitlines():
        if re.search('-ubuntu$', file):
            node_os = 'ubuntu'
        elif re.search('-centos$', file):
            node_os = 'centos'
        else:
            print('env '+cluster_id+', node '+node_id+': unknown os, skipping data file %s' %(file))
            continue

        cluster_id = re.search('/cluster-(\d+)/', file).groups()[0]
        node_id = re.search('/node-(\d+)/', file).groups()[0]
        with open(file,'r') as packagelist:
            reader = csv.reader(packagelist, delimiter='\t')
            for p_name, p_version in reader:
                match = versions_db_cursor.execute('''
                    SELECT * FROM versions
                    WHERE release = ?
                        AND os = ?
                        AND package_name = ?
                        AND package_version = ?''', (release, node_os, p_name, p_version)).fetchall()
                if not match:
                    # try all releases
                    match = versions_db_cursor.execute('''
                        SELECT * FROM versions
                        WHERE os = ?
                            AND package_name = ?
                            AND package_version = ?''', (node_os, p_name, p_version)).fetchall()
                    if match:
                        print('env '+cluster_id
                            +', node '+node_id
                            +': package from a different release - '+p_name
                            +', version '+p_version
                            +', found in release:'+match.fetchone()[2])
                        continue
                    # try all versions for current release
                    match = versions_db_cursor.execute('''
                    SELECT * FROM versions
                    WHERE release = ?
                        AND os = ?
                        AND package_name = ?''', (release, node_os, p_name)).fetchall()
                    if match:
                        print('env '+cluster_id
                            +', node '+node_id
                            +': package version not in db - '+p_name
                            +', version '+p_version)
                        continue
                    # package with a different version might still be found 
                    # in a different release but such details are not interesting
                    # so just fail
                    print('env '+cluster_id
                        +', node '+node_id
                        +': package not in db - '+p_name
                        +' (version '+p_version+')')
                    continue

    print('built-in md5 verification analysis...')
    ignored_packages = [ 'vim-tiny' ]
    file_list_cmd = Popen(['find', n.conf['out-dir'], '-name', '*.packages-md5-verify-*'], stdout=PIPE)
    (file_list, err) = file_list_cmd.communicate()
    for file in file_list.rstrip().splitlines():
        cluster_id = re.search('/cluster-(\d+)/', file).groups()[0]
        node_id = re.search('/node-(\d+)/', file).groups()[0]
        if os.stat(file).st_size > 0:
            with open(file, 'r') as md5errorlist:
                reader = csv.reader(md5errorlist, delimiter='\t')
                for package, details in reader:
                    if package not in ignored_packages:
                        print ('env '+cluster_id+', node '+node_id+': '+package+' - '+details)

    return 0

if __name__ == '__main__':
    exit(main(sys.argv))
