#!/bin/bash

db='../db/versions/6.0/versions.tsv'

wget -O '6.0-release.sqlite.bz2' 'http://mirror.fuel-infra.org/fwm/6.0/centos/os/x86_64/repodata/268fe935dcbb9d78242e1cccc3163392110000a2bfa67a8831699c03cbb9d1c0-primary.sqlite.bz2'
rm '6.0-release.sqlite'
bunzip2 '6.0-release.sqlite.bz2'

packagesdata="$(sqlite3 -separator $'\t' '6.0-release.sqlite' 'select name, epoch, version, release, location_href from packages')"

lastid=$(tail -n 1 $db | cut -f1)
id=$lastid
echo "$packagesdata" | while read l
do
  fn=$(echo "$l" | cut -f5 | cut -c10-)
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
      echo -e "$id\t0\t6.0\trelease\tcentos\t$line" >> $db
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

