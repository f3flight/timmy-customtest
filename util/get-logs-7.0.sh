#!/bin/bash

for i in {1..35}; do wget -O patching-ci.infra.mirantis.net.7.0.$i.log https://patching-ci.infra.mirantis.net/view/All/job/7.0.proposed-to-updates/$i/consoleText; done
