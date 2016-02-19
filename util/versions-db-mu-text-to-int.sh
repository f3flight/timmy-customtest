sqlite3 $1 'drop table vtemp'
sqlite3 $1 'create table vtemp (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    job_id INTEGER,
    release TEXT,
    mu INTEGER,
    os TEXT,
    package_name TEXT,
    package_version TEXT,
    package_filename TEXT
);'
sqlite3 $1 'insert into vtemp select id, source_id, job_id, release, cast(mu as int), os, package_name, package_version, package_filename from versions'
sqlite3 $1 'drop table versions'
sqlite3 $1 'alter table vtemp rename to versions'
