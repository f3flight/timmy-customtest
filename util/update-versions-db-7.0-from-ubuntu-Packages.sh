#!/bin/bash

db='../db/versions/7.0/versions.tsv'

#packagesdata="$(wget -O - http://mirror.fuel-infra.org/fwm/7.0/ubuntu/dists/mos7.0/main/binary-amd64/Packages)"
packagesdata="$(cat Packages)"

lastid=$(tail -n 1 $db | cut -f1)
id=$lastid

echo "$packagesdata" | ./parse-Packages.pl | while read line
do
  fn=$(echo "$line" | cut -f3)
  if [ $(grep -c "$line" $db) -eq 0 ]
  then
    if [ $(grep -c "$fn" $db) -eq 0 ]
    then
      id=$((id+1))
      echo -e "$id\t0\t7.0\trelease\tubuntu\t$line" >> $db
    else
      for n in $(grep -n "	$fn" $db | cut -d: -f1)
      do
        l="$(sed -n "${n}p" $db)"
        part="$(echo "$l" | cut -f-5)"
        sed -i "${n}s/.*/${part}\t${line}/" $db
      done
    fi
  fi
done

