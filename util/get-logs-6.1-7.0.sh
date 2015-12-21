#!/bin/bash

set -e

wget -O 6.1-last.log https://patching-ci.infra.mirantis.net/view/All/job/6.1.proposed-to-updates/lastBuild/consoleText
last_id=$(grep 'jenkins-6.1.proposed-to-updates-' 6.1-last.log | head -n 1 | egrep -o '#[[:digit:]]+' | cut -c 2-)
rm 6.1-last.log
set +e
for i in $(seq 1 $last_id)
do
  echo $i
  wget -O 6.1-$i.log https://patching-ci.infra.mirantis.net/view/All/job/6.1.proposed-to-updates/$i/consoleText
done



set -e

wget -O 7.0-last.log https://patching-ci.infra.mirantis.net/view/All/job/7.0.proposed-to-updates/lastBuild/consoleText
last_id=$(grep 'jenkins-7.0.proposed-to-updates-' 7.0-last.log | head -n 1 | egrep -o '#[[:digit:]]+' | cut -c 2-)
rm 7.0-last.log
set +e
for i in $(seq 1 $last_id)
do
  echo $i
  wget -O 7.0-$i.log https://patching-ci.infra.mirantis.net/view/All/job/7.0.proposed-to-updates/$i/consoleText
done
