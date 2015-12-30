#!/bin/bash

db='../db/versions/6.1/versions.tsv'

bunzip2 '1f231bad38cd1781e7431df1fb2023df458dc3aefb31a0a4c8bb4d2a7c7a3e9b-primary.sqlite.bz2'

packagesdata="$(sqlite3 -separator $'\t' '1f231bad38cd1781e7431df1fb2023df458dc3aefb31a0a4c8bb4d2a7c7a3e9b-primary.sqlite' 'select name, epoch, version, release, location_href from packages')"

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
      echo -e "$id\t0\t6.1\trelease\tcentos\t$line" >> $db
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

