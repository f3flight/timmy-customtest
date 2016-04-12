#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
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
from timmy import nodes
from timmy.conf import Conf
import csv
import sqlite3
import re
import os
from time import sleep
import yaml
import argparse


class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

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
        else:
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
        if index >= len(b_list):
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
        a = a[2:]
        b = b[2:]
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

def vercmp(os, a, b):
  if os == 'centos':
      return rpm_vercmp(a, b)
  if os == 'ubuntu':
      return deb_vercmp(a, b)

def load_versions_db(nodes):
    db_dir='db/versions'
    db_files = set()
    output = {}
    for node in [n for n in nodes.nodes.values() if n.status == 'ready' and n.online == True]:
        db_file = os.path.join(db_dir, str(node.release), str(node.os_platform)+'.sqlite')
        if not os.path.isfile(db_file):
            output_add(output, node,
                       'no database found for '
                       +'release '+str(node.release)
                       +', os '+str(node.os_platform)
                       +', this node will be skipped!')
        else:
            db_files.add(db_file)
    db = sqlite3.connect(':memory:')
    dbc = db.cursor()
    dbc.execute('''
        CREATE TABLE versions
        (
            id INTEGER,
            job_id INTEGER,
            release TEXT,
            mu INTEGER,
            os TEXT,
            package_name TEXT,
            package_version TEXT,
            package_filename TEXT
        )''')
    for db_file in db_files:
        import_db = sqlite3.connect(db_file)
        import_dbc = import_db.cursor()
        r = import_dbc.execute('''
            SELECT
                id,
                job_id,
                release,
                mu,
                os,
                package_name,
                package_version,
                package_filename
            FROM versions
            ''')
        for row in r.fetchall():
            dbc.execute('''
            INSERT INTO versions
            (
                id,
                job_id,
                release,
                mu,
                os,
                package_name,
                package_version,
                package_filename
            ) VALUES (?,?,?,?,?,?,?,?)
            ''', row)
    db.commit()
    return db, output

def nodes_init(conf):
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(message)s')
    n = nodes.Nodes(conf=conf,
                    extended=0,
                    cluster=None,
                    destdir='/tmp')
    n.get_node_file_list()
    n.get_release()
    return n    

def output_add(output, node, message, key=None):
    # deunicodize
    # message = str(message)
    if node.cluster == 0:
        if 'fuel' not in output:
            if key:
                output['fuel'] = {}
            else:
                output['fuel'] = []
        if key:
            if key not in output['fuel']:
                output['fuel'][key] = []
            output['fuel'][key].append(message)
        else:
            output['fuel'].append(message)
    else:
        if node.cluster not in output:
            output[node.cluster] = {}
        if node.node_id not in output[node.cluster]:
            if key:
                output[node.cluster][node.node_id] = {'roles':node.roles,'output':{}}
            else:
                output[node.cluster][node.node_id] = {'roles':node.roles,'output':[]}
        if key:
            if key not in output[node.cluster][node.node_id]['output']:
                output[node.cluster][node.node_id]['output'][key] = []
            output[node.cluster][node.node_id]['output'][key].append(message)
        else:
            output[node.cluster][node.node_id]['output'].append(message)
    return output

def output_prepare(output):
    for e_id, env in output.items():
        if e_id == 'fuel':
            if type(env) is list:
                env.sort()
        else:
            output['env '+str(e_id)] = output.pop(e_id)
            for n_id, node in env.items():
                if type(node['output']) is list:
                    node['output'].sort()
                env['node '+str(n_id)
                    + ' ['+', '.join(node['roles'])+']'
                   ] = env.pop(n_id)['output']

def pretty_print(output):
    sys.stdout.write('\n')
    output_prepare(output)
    for line in yaml.dump(output, default_flow_style=False).split('\n'):
        if len(line) > 0:
            if re.match('^ *-', line):
                # force ident for block sequences
                print('    '+line)
            else:
                print('  '+line)

def fstrip(text_file):
    return [line.rstrip('\n') for line in text_file]

def verify_versions(db, node, output=None):
    versions_db_cursor = db.cursor()
    db_has_release = versions_db_cursor.execute('''
        SELECT COUNT(*) FROM versions WHERE release = ? and os = ?
        ''', (node.release, node.os_platform)).fetchall()
    if db_has_release[0][0] == 0:
        return output_add(output, node, 
            'the database does not have any data for MOS release '
            +str(node.release)
            +' for '+str(node.os_platform)+'!')
    command = '.packagelist-'+node.os_platform
    if command not in node.mapcmds:
        return output_add(output, node, 'versions data was not collected!')
    if not os.path.exists(node.mapcmds[command]):
        return output_add(output, node, 'versions data output file is missing!')
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
                    if p_name not in node.custom_packages:
                        node.custom_packages[p_name] = {}
                        node.custom_packages[p_name]['reasons'] = set()
                    node.custom_packages[p_name]['version'] = p_version
                    # check if this is a divergent package introduced in MUs only
                    match = versions_db_cursor.execute('''
                        SELECT * FROM versions
                        WHERE release = ?
                        AND os = ?
                        AND package_name = ?
                        AND mu = 0''', (node.release, node.os_platform, p_name)).fetchall()
                    if match:
                        node.custom_packages[p_name]['reasons'].add('version')
                        output_add(output, node,
                            "package version not in db - %s, version '%s'" % (
                                p_name, str(p_version)))
                    else:
                        # divergent package - skipping
                        node.custom_packages[p_name]['reasons'].add('upstream')
                        # output_add(output, node,
                        #     'installed upstream %s has a divergent version in MU, consider updating' % (
                        #         p_name,))
                        pass
                else:
                    # unknown package, nothing to compare with, so skipping.
                    pass
    return output

def verify_md5_builtin_show_results(node, output=None):
    command = '.packages-md5-verify-'+node.os_platform
    if command not in node.mapcmds:
        return output_add(output, node, 'builtin md5 data was not collected!')
    if not os.path.exists(node.mapcmds[command]):
        return output_add(output, node, 'builtin md5 data output file is missing!')
    ex_filename = 'db/md5/%s/%s.filter' % (node.release, node.os_platform)
    # value-less dict
    ex_list = []
    if os.path.isfile(ex_filename):
        with open(ex_filename, 'r') as ex_file:
            for line in fstrip(ex_file):
              ex_list.append(line)
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5_file:
            for line in fstrip(md5_file):
                excluded = False
                for ex_regexp in ex_list:
                    if re.match(ex_regexp, line):
                        excluded = True
                        break
                if excluded:
                    continue
                p_name, p_version, details = line.split('\t')
                if not hasattr(node,'custom_packages'):
                    node.custom_packages = {}
                if p_name not in node.custom_packages:
                    node.custom_packages[p_name] = {}
                    node.custom_packages[p_name]['reasons'] = set()
                node.custom_packages[p_name]['version'] = p_version
                node.custom_packages[p_name]['reasons'].add('builtin-md5')
                output_add(output, node,
                    str(details).strip(),
                    str(p_name)+' '+str(p_version))
    return output

def verify_md5_with_db_show_results(node, output=None):
    return
    #needs rewriting
    ignored_packages = [ 'vim-tiny' ]
    command = '.packages-md5-db-verify-'+node.os_platform
    if command not in node.mapcmds:
        return output_add(output, node, 'db md5 data was not collected!') 
    if not os.path.exists(node.mapcmds[command]):
        if not output:
            sys.stdout.write('\n')
        return output_add(output, node, 'db md5 data output file is missing!')
    if os.stat(node.mapcmds[command]).st_size > 0:
        with open(node.mapcmds[command], 'r') as md5errorlist:
            reader = csv.reader(md5errorlist, delimiter='\t')
            for id, p_name, p_version, details in reader:
                if p_name not in ignored_packages:
                    if not hasattr(node,'custom_packages'):
                        node.custom_packages = {}
                    node.custom_packages[p_name] = p_version
                    output_add(output, node,
                        +'package_id '+str(id)
                        +', '+str(p_name)
                        +', version '+str(p_version)
                        +' - '+str(details))
    return output

def print_mu(mu):
    return 'MU'+str(mu) if mu > 0 else 'GA'

def max_versions_dict(versions_db):
    # returns a dict hierarchy containing package names and their highest
    # available versions
    # structure is max_version[release][os][package_name] = {'version', 'mu'}
    
    def put(version, mu, element=None):
        if not element:
            element = {}
        element['version'] = version
        element['mu'] = mu
        return element

    versions_db_cursor = versions_db.cursor()
    data = versions_db_cursor.execute('''
        SELECT release, os, package_name, package_version, mu
        FROM versions
        ORDER BY package_name ASC, mu DESC
        ''').fetchall()
    max_version = {}
    for el in data:
        release = el[0]
        os = el[1]
        p_name = el[2]
        p_ver = el[3]
        mu = el[4]
        if release not in max_version:
            max_version[release] = {}
        if os not in max_version[release]:
            max_version[release][os] = {}
        if p_name not in max_version[release][os]:
            max_version[release][os][p_name] = put(p_ver, mu)
        else:
            element = max_version[release][os][p_name]
            result = vercmp(os, p_ver, element['version'])
            if result > 0:
                # Should never happen since the MU order is DESC.
                # If this happens then it means that package version was
                # lowered in a subsequent MU, which is against our policy as
                # of Feb 2016.
                if element['mu'] != mu:
                    sys.stderr.write('WARNING! Downgrade detected in release %s,' 
                                     ' os %s, %s to %s, package %s - version'
                                     " '%s' was downgraded to '%s'\n" % (
                                         release, os, print_mu(mu), print_mu(element['mu']),
                                         p_name, p_ver, element['version']))
                put(p_ver, mu, max_version[release][os][p_name])
            elif result == 0 and mu < element['mu']:
                # update MU to show in which MU this version was introduced first
                put(p_ver, mu, max_version[release][os][p_name])
                
    return max_version

def get_reasons_string(reasons_list):
    if 'upstream' in reasons_list:
        return 'upstream'
    else:
        return 'custom ['+', '.join(reasons_list)+']'


def mu_safety_check(node, mvd, output=None):
    if hasattr(node, 'custom_packages'):
        for p_name, p_data in node.custom_packages.items():
            p_version = p_data['version']
            p_reasons = get_reasons_string(p_data['reasons'])
            if node.release in mvd:
                if node.os_platform in mvd[node.release]:
                    if p_name in mvd[node.release][node.os_platform]:
                        mvd_package = mvd[node.release][node.os_platform][p_name]
                        if mvd_package['mu'] != 'GA':
                            r = vercmp(node.os_platform, mvd_package['version'], p_version)
                            if r > 0 and p_reasons != 'upstream':
                                output_add(
                                    output,
                                    node,
                                    str("%s %s '%s' will be overwritten by %s version '%s'" % (
                                        p_reasons,
                                        p_name,
                                        p_version,
                                        print_mu(mvd[node.release][node.os_platform][p_name]['mu']),
                                        mvd[node.release][node.os_platform][p_name]['version'])))
                            elif r < 0 or (r == 0 and p_reasons == 'upstream'): #second case highly unlikely
                                if p_reasons == 'upstream':
                                    message = ("%s %s '%s' needs to be downgraded to %s version '%s',"
                                               ' please ensure repo priorities or disable upstream repos')
                                else:
                                    message = "%s %s '%s' may prevent %s version '%s' from being installed"
                                output_add(
                                    output,
                                    node,
                                    str(message % (
                                        p_reasons,
                                        p_name,
                                        p_version,
                                        print_mu(mvd[node.release][node.os_platform][p_name]['mu']),
                                        mvd[node.release][node.os_platform][p_name]['version'])))
    return output

def update_candidates(db, node, mvd, output=None):
    versions_db_cursor = db.cursor()
    db_has_release = versions_db_cursor.execute('''
        SELECT COUNT(*) FROM versions WHERE release = ? and os = ?
        ''', (node.release, node.os_platform)).fetchall()
    if db_has_release[0][0] == 0:
            return output_add(output, node,
                'the database does not have any data for MOS release '+str(node.release)
                +', os '+str(node.os_platform)+'!')
    command = '.packagelist-'+node.os_platform
    if command not in node.mapcmds:
        return output_add(output, node, 'versions data was not collected!')
    if not os.path.exists(node.mapcmds[command]):
        return output_add(output, node, 'versions data output file is missing!')
    with open(node.mapcmds[command],'r') as packagelist:
        reader = csv.reader(packagelist, delimiter='\t')
        for p_name, p_version in reader:
            if p_name in mvd[node.release][node.os_platform]:
                mvd_package = mvd[node.release][node.os_platform][p_name]
                r = vercmp(node.os_platform, mvd_package['version'], p_version)
                p_state = ''
                if hasattr(node, 'custom_packages') and p_name in node.custom_packages:
                    p_state = get_reasons_string(node.custom_packages[p_name]['reasons'])+' '
                p_known_mu = versions_db_cursor.execute('''
                    SELECT mu FROM versions WHERE 
                        release = ?
                        and os = ?
                        and package_name = ?
                        and package_version = ?
                    ORDER BY mu
                    LIMIT 1
                    ''', (node.release, node.os_platform, p_name, p_version)).fetchone()
                if p_known_mu:
                    print_p_mu = 'GA' if p_known_mu[0] == 0 else 'MU%s' % (p_known_mu[0])
                else:
                    print_p_mu = 'N/A'
                if r > 0 or (r < 0 and p_state == 'upstream '):
                    output_add(
                        output,
                        node,
                        { '%s%s' % (p_state, p_name): str("%s to %s (from '%s' to '%s')" % (
                            print_p_mu,
                            print_mu(mvd_package['mu']),
                            p_version,
                            mvd_package['version']))}
                    )
    return output

def perform(description, function, n, args, ok_message):
    sys.stdout.write(description+': ')
    output = {}
    if not args:
        args = {}
    for node in n.nodes.values():
        if node.status == 'ready' and node.online == True:
            args['node'] = node
            args['output'] = output
            function(**args)
    if output:
        pretty_print(output)
    else:
        print(ok_message)
    sleep(1)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fake',
        help="Do not perform remote commands, use already collected data",
        action="store_true")
    parser.add_argument('-c', '--config',
        help="Config file to use to override default configuration. When not specified - config.yaml is used.",
        default='config.yaml')
    args = parser.parse_args(argv[1:])
    sys.stdout.write('Getting node list: ')
    conf = Conf()
    if args.config:
        conf = Conf.load_conf(args.config)
    n = nodes_init(conf)
    print('DONE')
    sys.stdout.write('Loading necessary databases: ')
    versions_db, output = load_versions_db(n)
    if not versions_db:
        print('Aborting.')
        return 1
    if not output:
        print('DONE')
    else:
        pretty_print(output)
    sys.stdout.write('Collecting data from the nodes: ')
    n.launch_ssh(n.conf.outdir, fake=args.fake)
    print('DONE')
    perform('Versions verification analysis', verify_versions, n, {'db':versions_db}, 'OK')
    perform('Built-in md5 verification analysis', verify_md5_builtin_show_results, n, None, 'OK')
    perform('[WIP] Database md5 verification analysis', verify_md5_with_db_show_results, n, None, 'SKIPPED')
    mvd = max_versions_dict(versions_db)
    perform('MU safety analysis', mu_safety_check, n, {'mvd':mvd}, 'OK')
    perform('Potential updates', update_candidates, n, {'db':versions_db,'mvd':mvd}, 'ALL NODES UP-TO-DATE')
    return 0

if __name__ == '__main__':
    exit(main(sys.argv))
