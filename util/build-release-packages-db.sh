#!/bin/bash

if [ "$#" -ne 1 ]
then
  echo "Please supply release - '6.0' or '6.1' etc, without quotes"
  exit 1
else
  release=$1
fi

#script to scan release ISO, so build id is zero
id=0
mu='release'

#process rpms
os='centos'
while read file
do
  package=$(echo $file | rev | cut -d/ -f1 | rev)
  rpminfo="$(rpm -qpi $file 2> /dev/null)"
  p_name=$(echo "$rpminfo" | grep '^Name' | head -n 1 | perl -pe 's/^Name +: ([^ ]+).*$/\1/')
  p_version_v=$(echo "$rpminfo" | grep '^Version' | head -n 1 | perl -pe 's/^Version +: ([^ ]+).*$/\1/')
  p_version_r=$(echo "$rpminfo" | grep '^Release' | head -n 1 | perl -pe 's/^Release +: ([^ ]+).*$/\1/')
  p_version=${p_version_v}${p_version_r}
  echo -e $id'\t'$release'\t'$mu'\t'$os'\t'$p_name'\t'$p_version'\t'$package
done <<< "$(find /var/www/nailgun/centos/ -name '*.rpm')"

#process debs
os='ubuntu'
while read file
do
 package=$(echo $file | rev | cut -d/ -f1 | rev)
 debinfo="$(dpkg-deb -I $file 2> /dev/null)"
 p_name=$(echo "$debinfo" | grep '^ Package' | head -n 1 | perl -pe 's/^ Package: ([^ ]+).*$/\1/')
 p_version=$(echo "$debinfo" | grep '^ Version' | head -n 1 | perl -pe 's/^ Version: ([^ ]+).*$/\1/')
 echo -e $id'\t'$release'\t'$mu'\t'$os'\t'$p_name'\t'$p_version'\t'$package
done <<< "$(find /var/www/nailgun/ubuntu/ -name '*.deb')"
