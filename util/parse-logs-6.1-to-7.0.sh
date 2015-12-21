#!/bin/bash

for file in `ls 6.1-*.log`
do
  id=$(grep 'jenkins-6.1.proposed-to-updates-' $file | head -n 1 | egrep -o '#[[:digit:]]+' | cut -c 2-)
  release='6.1'
  mu='mu'
  packages=$(egrep -o "/[^/*]+\.(deb|rpm)" $file | cut -c 2- | sort -u)
  for package in `echo "$packages"`
  do
    if [ "$(echo $package | grep -c '.deb$')" -eq 1 ]
    then
      os='ubuntu'
      p_name=$(echo $package | cut -d_ -f1)
      p_version=$(echo $package | rev | cut -c5- | rev | cut -d_ -f2)
    elif [ "$(echo $package | grep -c '.rpm$')" -eq 1 ]
    then
      os='centos'
      p_name=$(echo $package | perl -pe 's/(.+?)-\d.*/\1/')
      p_version=$(echo $package | perl -pe 's/.+?-(\d.+)\..+\.rpm$/\1/')
    fi
    echo -e $id'\t'$release'\t'$mu'\t'$os'\t'$p_name'\t'$p_version'\t'$package
  done
done



for file in `ls 7.0-*.log`
do
  id=$(grep 'jenkins-7.0.proposed-to-updates-' $file | head -n 1 | egrep -o '#[[:digit:]]+' | cut -c 2-)
  release='7.0'
  mu='mu'
  packages=$(egrep -o "/[^/*]+\.(deb|rpm)" $file | cut -c 2- | sort -u)
  for package in `echo "$packages"`
  do
    if [ "$(echo $package | grep -c '.deb$')" -eq 1 ]
    then
      os='ubuntu'
      p_name=$(echo $package | cut -d_ -f1)
      p_version=$(echo $package | rev | cut -c5- | rev | cut -d_ -f2)
    elif [ "$(echo $package | grep -c '.rpm$')" -eq 1 ]
    then
      os='centos'
      p_name=$(echo $package | perl -pe 's/(.+?)-\d.*/\1/')
      p_version=$(echo $package | perl -pe 's/.+?-(\d.+)\..+\.rpm$/\1/')
    fi
    echo -e $id'\t'$release'\t'$mu'\t'$os'\t'$p_name'\t'$p_version'\t'$package
  done
done

