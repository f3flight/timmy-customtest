#!/bin/bash

rm -r tmp-deb
rm -r md5
mkdir md5

files="$(find /var/www/nailgun/ubuntu/ -name '*.deb')"
for file in $files
do
  dpkg -x $file tmp-deb 2> /dev/null
  if [ "$?" -eq 0 ]
  then
    package_filename=$(echo $file | rev | cut -d/ -f1 | rev)
    cd tmp-deb
    for dir in $(ls -d */ | grep -v 'etc\|root\|home\|mnt\|proc\|sys\|tmp\|dev\|run')
    do
      find $dir -type f -exec md5sum {} + >> ../md5/${package_filename}.md5sums 2> /dev/null
    done
    cd ..
    rm -r tmp-deb
  fi
done

rm -r tmp-rpm

files="$(find /var/www/nailgun/centos/ -name '*.rpm')"
for file in $files
do
  mkdir tmp-rpm
  cd tmp-rpm
  rpm2cpio $file | cpio -id
  if [ "$?" -eq 0 ]
  then
    package_filename=$(echo $file | rev | cut -d/ -f1 | rev)
    for dir in $(ls -d */ | grep -v 'etc\|root\|home\|mnt\|proc\|sys\|tmp\|dev\|run')
    do
      find $dir -type f -exec md5sum {} + >> ../md5/${package_filename}.md5sums 2> /dev/null
    done
  fi
  cd ..
  rm -r tmp-rpm
done

# check for packages for which md5 was not generated - these should be inspected (virtual package or error)
while read line
do
  job_id=$(echo "$line" | cut -f2)
  if [ "$job_id" -eq 0 ]
  then
    id=$(echo "$line" | cut -f1)
    package_filename=$(echo "$line" | cut -f8)
    if [ ! -e "md5/${package_filename}.md5sums" ]
    then
      echo "$package_filename"
    fi
  fi
done < timmy-virgintest/db/versions/6.0/versions.tsv
