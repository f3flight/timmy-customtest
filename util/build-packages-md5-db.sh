#!/bin/bash

release='6.0'

mkdir -p ../db/md5/${release}

rm -rf tmp-deb
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
      find $dir -type f -exec md5sum {} + >> ../../db/md5/${release}/${package_filename}.md5sums 2> /dev/null
    done
    cd ..
    rm -rf tmp-deb
  fi
done

rm -rf tmp-rpm
files="$(find /var/www/nailgun/centos/ -name '*.rpm')"
for file in $files
do
  mkdir tmp-rpm
  cd tmp-rpm
  rpm2cpio $file | cpio -id --quiet
  if [ "$?" -eq 0 ]
  then
    package_filename=$(echo $file | rev | cut -d/ -f1 | rev)
    for dir in $(ls -d */ | grep -v 'etc\|root\|home\|mnt\|proc\|sys\|tmp\|dev\|run')
    do
      sudo find $dir -type f -exec md5sum {} + >> ../../db/md5/${release}/${package_filename}.md5sums 2> /dev/null
    done
  fi
  cd ..
  sudo rm -rf tmp-rpm
done

# # check for packages for which md5 was not generated - these should be inspected (virtual package, nothing in usr, var, ... or error)
# while read line
# do
#   job_id=$(echo "$line" | cut -f2)
#   if [ "$job_id" -eq 0 ]
#   then
#     id=$(echo "$line" | cut -f1)
#     package_filename=$(echo "$line" | cut -f8)
#     if [ ! -e "md5/${package_filename}.md5sums" ]
#     then
#       echo "$package_filename"
#     fi
#   fi
# done < ../db/versions/6.0/versions.tsv

find ../db/md5/${release} -size 0c -delete
