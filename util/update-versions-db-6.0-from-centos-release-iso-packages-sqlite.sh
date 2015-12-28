#!/bin/bash

db='../db/versions/6.0/versions.tsv'

bunzip2 '6c871095dafc9dfc34b862c0b240cb198e2a657d6500919090ef11507ced2480-primary.sqlite.bz2'

packagesdata="$(sqlite3 -separator $'\t' '6c871095dafc9dfc34b862c0b240cb198e2a657d6500919090ef11507ced2480-primary.sqlite' 'select name, epoch, version, release, location_href from packages')"

lastid=$(tail -n 1 $db | cut -f1)
id=$lastid
echo "$packagesdata" | while read l
do
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

