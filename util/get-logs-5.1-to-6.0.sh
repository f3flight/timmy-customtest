#!/bin/bash

set -e

wget http://osci-jenkins.srt.mirantis.net:8080/job/release-update/lastBuild/consoleText -O 5.1-to-6.0-last.log
last_id=$(grep 'jenkins-release-update-' 5.1-to-6.0-last.log | egrep -o '#[[:digit:]]+' | cut -c 2-)
rm 5.1-to-6.0-last.log
for i in $(seq 1 $last_id)
do
  echo $i
  wget -O 5.1-to-6.0-$i.log http://osci-jenkins.srt.mirantis.net:8080/job/release-update/$i/consoleText
done
