#!/usr/bin/python

import sys
import argparse
import urllib2
import sqlite3
import os

releases = ['5.1',
            '5.1.1',
            '6.0',
            '6.1',
            '7.0',
            '8.0',
           ]

def main(argv=None):

    def verify_args():
        if not args.updates_source:
            if not args.release:
                return 'Release not specified.'
            if args.release not in releases:
                return 'Specified release "'+args.release+'" is unknown.'
            if not args.release_source:
                return 'Release source not specified.'
        else:
            if not args.mu_number:
                return 'MU file provided but MU number not specified.'
            if not args.database:
                return 'MU file provided but database not specified.'
        if not args.output:
            return 'Output file not specified.'
        try:
            open(args.output, 'w')
        except Exception:
            return 'Cannot write to the output file '+args.output

    def fetch(sources):
        fetched = {}
        for source in sources:
            try:
                request = urllib2.urlopen(source)
            except Exception:
                sys.stderr.write('Error: Could not access '
                                 +str(source)+'\n')
                return 1
            fetched[source] = request.read()
        return fetched

    def dbgen(sources, mu=0, job_id=-1):
        db = sqlite3.connect(args.output)
        dbc = db.cursor()
        if os.stat(args.output).st_size == 0:
            #empty file -> new db, creating tables
            dbc.execute('''
                CREATE TABLE sources
                (
                    id INTEGER PRIMARY KEY,
                    source TEXT
                )''')
            dbc.execute('''
                CREATE TABLE versions
                (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER,
                    job_id INTEGER,
                    release TEXT,
                    mu TEXT,
                    os TEXT,
                    package_name TEXT,
                    package_version TEXT,
                    package_filename TEXT
                )''')
        for source, data in sources.items():
            r = dbc.execute('''
                SELECT rowid FROM sources WHERE source = ?
                ''', (source,)).fetchall()
            if len(r) == 0:
                dbc.execute('''
                    INSERT INTO sources (source) VALUES (?)
                    ''', (source,))
                r = dbc.execute('''
                        SELECT rowid FROM sources
                        WHERE source = ? 
                    ''', (source,)).fetchall()
            source_id = r[0][0]
            packagedata = data.split('\n\n')
            for pd in packagedata:
                if len(pd) == 0:
                    continue
                package = {}
                lines = pd.split('\n')
                for line in lines:
                    unpacked = line.split(': ', 1)
                    if len(unpacked) > 1:
                        package[unpacked[0]] = unpacked[1]
                package['Filename'] = package['Filename'].split('/')[-1]
                r = dbc.execute('''
                    SELECT rowid FROM versions
                    WHERE release = ?
                          AND mu = ?
                          AND os = 'ubuntu'
                          AND package_name = ?
                          AND package_version = ?
                          AND package_filename = ?
                    ''', (args.release,
                          mu,
                          package['Package'],
                          package['Version'],
                          package['Filename']))
                if len(r.fetchall()) > 0:
                    print('Duplicate package '+str(package)+', skipping...')
                else:
                    dbc.execute('''
                        INSERT INTO versions
                        (
                            source_id,
                            job_id,
                            release,
                            mu,
                            os,
                            package_name,
                            package_version,
                            package_filename
                        ) VALUES (?,?,?,?,?,?,?,?)
                        ''', (source_id,
                              job_id,
                              args.release,
                              mu,
                              'ubuntu',
                              package['Package'],
                              package['Version'],
                              package['Filename']))
        db.commit()

    # validating arguments
    if not argv:
        sys.stderr.write('Error: no parameters specified.\n')
        return 1
    else:
        parser = argparse.ArgumentParser(description='Build the deb database')
        parser.add_argument('-r', '--release',
                            help=('Mandatory. '
                                  'Release version (example: 6.1).'
                                 ))
        parser.add_argument('-g', '--release-source', nargs='+',
                            help=('Mandatory when GA is processed. '
                                  'URL(s) to GA Packages file(s). '
                                  'Local files are supported via '
                                  'file://<abs-path>. '
                                  'You must provide all URLs at once, like '
                                  'so: -g http://... file://... file://...'
                                 ))
        parser.add_argument('-d', '--database',
                            help=('Mandatory when MU is processed. '
                                  'URL (only one) to a most updated '
                                  'database previously built by this '
                                  'tool for the specified release. '
                                  'See help for -g for more details.'
                                 ))
        parser.add_argument('-u', '--updates-source', nargs='+',
                            help=('Mandatory when MU is processed. '
                                  'URL(s) to MU update Packages file(s). '
                                  'See help for -g for more details.'
                                 ))
        parser.add_argument('-n', '--mu-number',
                            help=('Mandatory when MU is processed. '
                                  'integer ID of the MU update.'
                                 ))
        parser.add_argument('-o', '--output',
                            help=('Mandatory. '
                                  'Path (not URL) to the output database '
                                  'file. Must not be the same file as -d '
                                  'because output file is cleaned before '
                                  'opening the database.'
                                 ))

        args = parser.parse_args(argv[1:])
        args_check_error = verify_args()
        if args_check_error:
            sys.stderr.write('Error: '+args_check_error+'\n')
            return 1
    # database generation / update
    if not args.updates_source:
        #GA db generation
        print('GA -> db generation...')
        release_source = fetch(args.release_source)
        dbgen(release_source)
    else:
        #MU db update
        print('MU -> db update...')
        updates_source = fetch(args.updates_source)
        updates_db = fetch([args.database])[args.database]
        with open(args.output,'w') as file:
            file.write(updates_db)
        dbgen(updates_source, args.mu_number)

if __name__ == '__main__':
    exit(main(sys.argv))

