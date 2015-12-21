#!/usr/bin/python

import csv
import sqlite3
import os

db = sqlite3.connect(':memory:')
cur = db.cursor()

with open('timmy-virgintest/db/versions/6.0/versions.tsv','r') as file:
    reader = csv.reader(file, delimiter='\t')
    cur.execute('''
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
    cur.executemany('''
        INSERT INTO versions (id, job_id, release, mu, os, package_name, package_version, package_filename)
        VALUES (?,?,?,?,?,?,?,?)''', reader)
    db.commit()


for file in os.listdir('md5'):
    with open('md5/'+file,'r') as f2:
        if file[-11:-8] == 'deb':
            match = cur.execute('''
                SELECT * FROM versions
                WHERE job_id = 0
                    AND release = '6.0'
                    AND mu = 'release'
                    AND os = 'ubuntu'
                    AND package_filename = ?
                ORDER BY id
                LIMIT 1
                ''', (file[:-8],)).fetchall()
            if match:
                with open('md5.tsv','a+') as outfile:
                    try:
                        outfile.writelines([''.join([str(match[0][0]), l.rstrip(), '\n']) for l in f2.readlines()])
                    except:
                        print(file)
            else:
                print('problem with finding '+file[:-8]+' in the database')
            pass
        elif file[-11:-8] == 'rpm':
            match = cur.execute('''
                SELECT * FROM versions
                WHERE job_id = 0
                    AND release = '6.0'
                    AND mu = 'release'
                    AND os = 'centos'
                    AND package_filename = ?
                ORDER BY id
                LIMIT 1
                ''', (file[:-8],)).fetchall()
            if match:
                with open('md5.tsv','a+') as outfile:
                    try:
                        outfile.writelines([''.join([str(match[0][0]), l.rstrip(), '\n']) for l in f2.readlines()])
                    except:
                        print(file)
            else:
                print('problem with finding '+file[:-8]+' in the database')
            pass
