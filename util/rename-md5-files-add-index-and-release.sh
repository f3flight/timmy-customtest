#!/bin/bash

release='6.0'

pushd ../db/md5/${release} &> /dev/null

for i in $(ls)
do
  fn="$(echo $i | rev | cut -c9- | rev)"
  id=$(grep "	$fn" ../../versions/${release}/versions.tsv | awk '{print $1}')
  mv $i ${id}_${release}_${i}
done

popd &> /dev/null
