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
from timmy.conf import load_conf
from timmy.tools import interrupt_wrapper
import urllib2
import hashlib
import csv
import sqlite3
import re
import os
import yaml
import argparse
from vercmp import vercmp


class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def load_versions_dict(conf, nm):
    def fetch(url):
        try:
            return urllib2.urlopen(url).read()
        except:
            return None

    def online(release, os_platform, ext):
        url = ('http://mirror.fuel-infra.org/mcv/mos/%s/'
               '%s-latest.%s' % (release, os_platform, ext))
        return fetch(url)

    def update_db(db_file, release, os_platform):
        ext_db = online(release, os_platform, 'sqlite')
        if ext_db:
            open(db_file, 'w').write(ext_db)
        else:
            return False
        return True

    msg_newer_ok = ('a newer versions db for MOS %s %s was found online '
                    'and successfully downloaded.')
    msg_newer_unkn = ('could not check for versions db updates for '
                      'MOS %s %s online, using local copy.')
    msg_newer_fail = ('a newer verisons db for MOS %s %s was found online '
                      'but download failed, using an older local copy.')
    msg_nodb_ok = ('versions db for MOS %s %s was not present but was '
                   'successfully downloaded from an online mirror.')
    msg_nodb_fail = ('no versions db found for MOS %s %s and could not '
                     'download from a mirror - this node will be skipped!')
    db_dir = os.path.join(conf['customtest_db_dir'], 'versions')
    dbs = {}
    db_files = set()
    output = {}
    for node in nm.nodes.values():
        r = node.release
        p = node.os_platform
        if not r or not p:
            output_add(output, node,
                       ('could not determine release or os, this node will'
                        'be skipped! Release: %s, OS: %s') % (r, p))
            continue
        if r not in dbs:
            dbs[r] = {}
        if p not in dbs[r]:
            dbs[r][p] = {}
        if 'nodes' not in dbs[r][p]:
            dbs[r][p]['nodes'] = []
        dbs[r][p]['nodes'].append(node)
        if 'dir' not in dbs[r][p]:
            dbs[r][p]['dir'] = os.path.join(db_dir, r)
        if 'file' not in dbs[r][p]:
            dbs[r][p]['file'] = os.path.join(db_dir, r, '%s.sqlite' % p)
    for r in dbs:
        for p in dbs[r]:
            d = dbs[r][p]['dir']
            f = dbs[r][p]['file']
            if not os.path.isdir(d):
                os.makedirs(d)
            if f in db_files:
                continue
            if os.path.isfile(f):
                ext_md5 = online(r, p, 'md5')
                if ext_md5:
                    ext_md5 = ext_md5.rstrip('\n')
                    int_db = open(f, 'rb').read()
                    int_md5 = hashlib.md5(int_db).hexdigest()
                    if ext_md5 != int_md5:
                        if update_db(f, r, p):
                            for n in dbs[r][p]['nodes']:
                                output_add(output, n, msg_newer_ok % (r, p))
                        else:
                            for n in dbs[r][p]['nodes']:
                                output_add(output, n, msg_newer_fail % (r, p))
                else:
                    for n in dbs[r][p]['nodes']:
                        output_add(output, n, msg_newer_unkn % (r, p))
                db_files.add(f)
            else:
                if update_db(f, r, p):
                    for n in dbs[r][p]['nodes']:
                        output_add(output, n, msg_nodb_ok % (r, p))
                    db_files.add(f)
                else:
                    for n in dbs[r][p]['nodes']:
                        output_add(output, n, msg_nodb_fail % (r, p))
    versions_dict = {}
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
            ORDER BY package_name ASC, mu DESC
            ''')
        for row in r.fetchall():
            release = row[2]
            mu = row[3]
            os_platform = row[4]
            p_name = row[5]
            p_version = row[6]
            if release not in versions_dict:
                versions_dict[release] = {}
            vdr = versions_dict[release]
            if os_platform not in vdr:
                vdr[os_platform] = {}
            if p_name not in vdr[os_platform]:
                vdr[os_platform][p_name] = {}
            p_dict = vdr[os_platform][p_name]
            if 'mu' not in p_dict:
                p_dict['mu'] = set()
            p_dict['mu'].add(mu)
            if 'versions' not in p_dict:
                p_dict['versions'] = {}
            if p_version not in p_dict['versions']:
                p_dict['versions'][p_version] = set()
            if 'max_version' not in p_dict:
                p_dict['max_version'] = p_version
            else:
                r = vercmp(os_platform, p_version, p_dict['max_version'])
                max_v_mus = p_dict['versions'][p_dict['max_version']]
                if r > 0 and mu not in max_v_mus:
                    '''Should never happen since the MU order is DESC.
                    If this happens then it means that package version was
                    lowered in a subsequent MU, which is against our policy as
                    of Feb 2016.'''
                    logging.warning('Downgrade detected in release '
                                    '%s, os %s, %s to %s, package %s - '
                                    "version '%s' was downgraded to '%s'\n"
                                    % (release, os_platform, print_mu(mu),
                                       print_mu(min(max_v_mus)), p_name,
                                       p_version, p_dict['max_version']))
                elif r > 0:
                    p_dict['max_version'] = p_version
            p_dict['versions'][p_version].add(mu)
    return versions_dict, output


def node_manager_init(conf):
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')
    nm = nodes.NodeManager(conf=conf)
    return nm


def output_add(output, node, message, key=None):
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
        if node.id not in output[node.cluster]:
            if key:
                output[node.cluster][node.id] = {
                    'roles': node.roles,
                    'output': {}}
            else:
                output[node.cluster][node.id] = {
                    'roles': node.roles,
                    'output': []}
        if key:
            if key not in output[node.cluster][node.id]['output']:
                output[node.cluster][node.id]['output'][key] = []
            output[node.cluster][node.id]['output'][key].append(message)
        else:
            output[node.cluster][node.id]['output'].append(message)
    return output


def output_prepare(output):
    for e_id, env in output.items():
        if e_id == 'fuel':
            if type(env) is list:
                env.sort()
        else:
            env_str = 'env %s' % (str(e_id),)
            output[env_str] = output.pop(e_id)
            for n_id, node in env.items():
                if type(node['output']) is list:
                    node['output'].sort()
                node_str = 'node %s [%s]' % (str(n_id),
                                             ', '.join(node['roles']))
                env[node_str] = env.pop(n_id)['output']


def pretty_print(output, pre_indent=4):
    sys.stdout.write('\n')
    output_prepare(output)
    for line in yaml.safe_dump(output, default_flow_style=False).split('\n'):
        if len(line) > 0:
            if re.match('^ *-', line):
                # force ident for block sequences
                line = '  ' + line
            print(' ' * pre_indent + line)


def fstrip(text_file):
    return [line.rstrip('\n') for line in text_file]


def verify_versions(node, versions_dict, output=None):
    if (node.release not in versions_dict or (node.os_platform not in
                                              versions_dict[node.release])):
        return output_add(output, node,
                          ('the database does not have any data for MOS '
                           'release %s for %s!' % (str(node.release),
                                                   str(node.os_platform))))
    vd = versions_dict[node.release][node.os_platform]
    command = 'packagelist-' + node.os_platform
    if command not in node.mapscr:
        return output_add(output, node, 'versions data was not collected!')
    if not os.path.exists(node.mapscr[command]):
        return output_add(output, node, 'versions data output file missing!')
    if os.stat(node.mapscr[command]).st_size == 0:
        return output_add(output, node,
                          'versions data empty, you may want to re-run!')
    with open(node.mapscr[command], 'r') as packagelist:
        reader = csv.reader(packagelist, delimiter='\t')
        if not hasattr(node, 'custom_packages'):
            node.custom_packages = {}
        for p_name, p_version in reader:
            if p_name in vd:
                if p_version not in vd[p_name]['versions']:
                    if p_name not in node.custom_packages:
                        node.custom_packages[p_name] = {}
                        node.custom_packages[p_name]['reasons'] = set()
                    node.custom_packages[p_name]['version'] = p_version
                    if 0 not in vd[p_name]['mu']:
                        node.custom_packages[p_name]['reasons'].add('upstream')
                    else:
                        node.custom_packages[p_name]['reasons'].add('version')
    return output


def verify_md5_builtin_show_results(conf, node, output=None):
    command = 'packages-md5-verify-'+node.os_platform
    if command not in node.mapscr:
        return output_add(output, node, 'builtin md5 data was not collected!')
    if not os.path.exists(node.mapscr[command]):
        return output_add(output, node,
                          'builtin md5 data output file missing!')
    ex_filename = os.path.join(conf['customtest_db_dir'],
                               'md5/%s/%s.filter' % (node.release,
                                                     node.os_platform))
    # value-less dict
    ex_list = []
    if os.path.isfile(ex_filename):
        with open(ex_filename, 'r') as ex_file:
            for line in fstrip(ex_file):
                ex_list.append(line)
    if os.stat(node.mapscr[command]).st_size > 0:
        with open(node.mapscr[command], 'r') as md5_file:
            for line in fstrip(md5_file):
                excluded = False
                for ex_regexp in ex_list:
                    if re.match(ex_regexp, line):
                        excluded = True
                        break
                if excluded:
                    continue
                p_name, p_version, details = line.split('\t')
                if not hasattr(node, 'custom_packages'):
                    node.custom_packages = {}
                if p_name not in node.custom_packages:
                    node.custom_packages[p_name] = {}
                    node.custom_packages[p_name]['reasons'] = set()
                node.custom_packages[p_name]['version'] = p_version
                node.custom_packages[p_name]['reasons'].add('builtin-md5')
                output_add(output, node,
                           str(details).strip(),
                           '%s %s' % (str(p_name), str(p_version)))
    return output


def print_mu(mu):
    return 'MU'+str(mu) if mu > 0 else 'GA'


def get_reasons_string(reasons_list):
    if 'upstream' in reasons_list:
        return 'upstream'
    else:
        return 'custom ['+', '.join(reasons_list)+']'


def mu_safety_check(node, versions_dict, output=None):

    def _compare_with_mvd(vd_package, p_name, p_data):
        p_version = p_data['version']
        p_reasons = get_reasons_string(p_data['reasons'])
        r = vercmp(node.os_platform, vd_package['max_version'], p_version)
        mu = min(vd_package['versions'][vd_package['max_version']])
        if r > 0 and p_reasons != 'upstream':
            output_add(
                output,
                node,
                str("%s %s '%s' will be overwritten by %s version '%s'" % (
                    p_reasons, p_name, p_version, print_mu(mu),
                    vd_package['max_version'])))
        elif r < 0 or (r == 0 and p_reasons == 'upstream'):
            # case in brackets is highly unlikely
            if p_reasons == 'upstream':
                message = ("%s %s '%s' needs to be downgraded to %s version "
                           "'%s', please ensure repo priorities or disable "
                           'upstream repos')
            else:
                message = ("%s %s '%s' may prevent %s version '%s' from "
                           'being installed')
            output_add(output, node,
                       str(message % (p_reasons, p_name, p_version,
                                      print_mu(mu),
                                      vd_package['max_version'])))

    if hasattr(node, 'custom_packages'):
        for p_name, p_data in node.custom_packages.items():
            if node.release in versions_dict:
                if node.os_platform in versions_dict[node.release]:
                    vd = versions_dict[node.release][node.os_platform]
                    if p_name in vd:
                        vd_p = vd[p_name]
                        if max(vd_p['mu']) > 0:
                            _compare_with_mvd(vd_p, p_name, p_data)
    return output


def update_candidates(node, versions_dict, output=None):
    # shortening fucntion name for pep8's sake...
    grs = get_reasons_string
    if (node.release not in versions_dict or (node.os_platform not in
                                              versions_dict[node.release])):
            return output_add(output, node,
                              ('the database does not have any data for MOS '
                               'release %s, os %s!' % (str(node.release),
                                                       str(node.os_platform))))
    vd = versions_dict[node.release][node.os_platform]
    command = 'packagelist-'+node.os_platform
    if command not in node.mapscr:
        return output_add(output, node, 'versions data was not collected!')
    if not os.path.exists(node.mapscr[command]):
        return output_add(output, node, 'versions data output file missing!')
    if os.stat(node.mapscr[command]).st_size == 0:
        return output_add(output, node,
                          'versions data empty, you may want to re-run!')
    with open(node.mapscr[command], 'r') as packagelist:
        reader = csv.reader(packagelist, delimiter='\t')
        for p_name, p_version in reader:
            if p_name in vd:
                vd_package = vd[p_name]
                r = vercmp(node.os_platform, vd_package['max_version'],
                           p_version)
                p_state = ''
                if (hasattr(node, 'custom_packages') and
                        p_name in node.custom_packages):
                    p_state = ('%s ' %
                               (grs(node.custom_packages[p_name]['reasons'])))
                if p_version in vd_package['versions']:
                    p_mu = min(vd_package['versions'][p_version])
                    if p_mu:
                        print_p_mu = 'MU%s' % (p_mu)
                    else:
                        print_p_mu = 'GA'
                else:
                    print_p_mu = 'N/A'
                if r > 0 or (r < 0 and p_state == 'upstream '):
                    mus = vd_package['versions'][vd_package['max_version']]
                    mu = min(mus)
                    output_add(output, node,
                               {'%s%s' % (p_state, p_name): str(
                                   "%s to %s (from '%s' to '%s')" %
                                   (print_p_mu,
                                    print_mu(mu),
                                    p_version,
                                    vd_package['max_version']))})
    return output


def perform(description, function, nm, args, ok_message):
    sys.stdout.write(description+': ')
    output = {}
    if not args:
        args = {}
    for node in nm.nodes.values():
        args['node'] = node
        args['output'] = output
        function(**args)
    if output:
        pretty_print(output)
    else:
        print(ok_message)


@interrupt_wrapper
def main(argv=None):
    sys.stdout = Unbuffered(sys.stdout)
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fake',
                        help=("Do not perform remote commands, use already "
                              "collected data"),
                        action="store_true")
    parser.add_argument('-c', '--config',
                        help=('Config file to use to override default '
                              'configuration. Default: /usr/share/'
                              'timmy-customtest/timmy-config-default.yaml '
                              '(if present, else ./timmy-config.yaml)'),
                        default=('/usr/share/timmy-customtest/'
                                 'timmy-config-default.yaml'))
    if argv is None:
        argv = sys.argv
    args = parser.parse_args(argv[1:])
    if not os.path.isfile(args.config):
        args.config = './timmy-config.yaml'
    print('Initialization:')
    sys.stdout.write('  Getting node list: ')
    conf = load_conf(args.config)
    nm = node_manager_init(conf)
    print('DONE')
    sys.stdout.write('  Loading necessary databases: ')
    versions_dict, output = load_versions_dict(conf, nm)
    if not versions_dict:
        print('Aborting.')
        return 1
    if not output:
        print('DONE')
    else:
        pretty_print(output)
    print('Data collection:')
    sys.stdout.write('  Collecting data from %d nodes: ' % len(nm.nodes))
    nm.run_commands(conf['outdir'], fake=args.fake)
    print('DONE')
    print('Results:')
    perform('  Versions verification analysis', verify_versions, nm,
            {'versions_dict': versions_dict}, 'OK')
    perform('  Built-in md5 verification analysis',
            verify_md5_builtin_show_results, nm, {'conf': conf}, 'OK')
    perform('  MU safety analysis', mu_safety_check, nm,
            {'versions_dict': versions_dict}, 'OK')
    perform('  Potential updates', update_candidates, nm,
            {'versions_dict': versions_dict}, 'ALL NODES UP-TO-DATE')
    return 0


if __name__ == '__main__':
    exit(main(sys.argv))
