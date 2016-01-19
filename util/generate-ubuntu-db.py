#!/usr/bin/python

import sys
import argparse
import urllib2
import sqlite3

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
            return 'Cannot write to the output file.'

    # declaring variables
    release_source = {}
    updates_source = {}
    in_database = None
    out_database = None
    # validating arguments
    if not argv:
        sys.stderr.write('Error: no parameters specified.\n')
        return 1
    else:
        parser = argparse.ArgumentParser(description='Build the deb database')
        parser.add_argument('-r', '--release',
                            help='release version (example: 6.1)')
        parser.add_argument('-g', '--release-source', nargs='+',
                            help=('this option is mandatory when GA is '
                                  'processed, it should be a URL to GA '
                                  'Packages file(s). Local files are '
                                  'supported via file://<abs-path>. '
                                  'Provide all URLs at once, like so: '
                                  '-g http://... file://... file://...'
                                 ))
        parser.add_argument('-d', '--database',
                            help=('this option is mandatory when MU is '
                                  'processed, it should be a URL '
                                  'to a most updated previously built '
                                  'database for this release. Local files '
                                  'are supported by supplying a file link '
                                  'like so: file://<absolute-path-here>. '
                                  'Example: -d file:///tmp/database.sqlite'
                                 ))
        parser.add_argument('-u', '--updates-source', nargs='+',
                            help='path to MU update Packages file(s)')
        parser.add_argument('-n', '--mu-number',
                            help='integer ID of the MU update')
        parser.add_argument('-o', '--output',
                            help='path to the output database file')

        args = parser.parse_args(argv[1:])
        args_check_error = verify_args()
        if args_check_error:
            sys.stderr.write('Error: '+args_check_error+'\n')
            return 1
    # database generation / update
    if not args.updates_source:
        #GA db generation
        print('GA -> db generation...')
        for source in args.release_source:
            try:
                request = urllib2.urlopen(source)
            except Exception:
                sys.stderr.write('Error: Could not access '
                                 +str(source)+'\n')
                return 1
            release_source[source] = request.read()
        db = sqlite3.connect(args.output)
        dbc = db.cursor()
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
        for source, data in release_source.items():
            dbc.execute('''
                INSERT INTO sources (source) VALUES (?)
                ''', (source,))
            r = dbc.execute('''
                SELECT rowid FROM sources
                WHERE source = ? 
                ''', (source,))
            source_id = r.fetchone()[0]
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
                          AND mu = 0
                          AND os = 'ubuntu'
                          AND package_name = ?
                          AND package_version = ?
                          AND package_filename = ?
                    ''', (args.release,
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
                              -1,
                              args.release,
                              0,
                              'ubuntu',
                              package['Package'],
                              package['Version'],
                              package['Filename']))
        db.commit()
    else:
        #MU db update
        print('MU -> db update...')
        try:
            request = urllib2.urlopen(args.database)
        except Exception:
            sys.stderr.write('Error: Could not access the database\n')
            return 1
        in_database = request.read()
        print(in_database)
            

if __name__ == '__main__':
    exit(main(sys.argv))

