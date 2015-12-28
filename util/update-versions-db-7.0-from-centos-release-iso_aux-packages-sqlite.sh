#!/bin/bash

db='../db/versions/7.0/versions.tsv'

wget -O '7.0-release-iso_aux.sqlite.bz2' 'http://mirror.fuel-infra.org/fwm/7.0-release/centos/os/x86_64/repodata/ac1d1a570081b586105151f293cf7ea63cf919223368afcfa0fa2758b2dbef54-primary.sqlite.bz2'
rm '7.0-release-iso_aux.sqlite'
bunzip2 '7.0-release-iso_aux.sqlite.bz2'

packagesdata="$(sqlite3 -separator $'\t' '7.0-release-iso_aux.sqlite' 'select name, epoch, version, release, location_href from packages')"

lastid=$(tail -n 1 $db | cut -f1)
id=$lastid
echo "$packagesdata" | while read l
do
  #skip source packages
  if [ "$(echo "$l" | grep -c '\.src\.rpm$')" -eq 1 ]
  then
    continue
  fi
  fn=$(echo "$l" | cut -f5 | rev | cut -d/ -f1 | rev)
  n=$(echo "$l" | cut -f1)
  e=$(echo "$l" | cut -f2 | sed 's/$/:/' | grep -v '^0:$')
  v=$(echo "$l" | cut -f3)
  r=$(echo "$l" | cut -f4)
  line="$(echo -e "$n\t$e$v-$r\t$fn")"
  if [ $(grep -c "$line" $db) -eq 0 ]
  then
    if [ $(grep -c "$fn" $db) -eq 0 ]
    then
      id=$((id+1))
      echo -e "$id\t0\t7.0\trelease\tcentos\t$line" >> $db
    else
      for n in $(grep -n "	$fn" $db | cut -d: -f1)
      do
        ln="$(sed -n "${n}p" $db)"
        part="$(echo "$ln" | cut -f-5)"
        sed -i "${n}s/.*/${part}\t${line}/" $db
      done
    fi
  fi
done

