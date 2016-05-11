# timmy-customtest
Python-based tool for Mirantis OpenStack which uses [Timmy](https://github.com/adobdin/timmy) as a backend. Provides the following info about environemnts and Fuel server:
- custom package versions
- post-install file changes (built-in md5 verification)
- checks if these customizations interfere with MU installation
- provides a list of packages for which there are updated versions available

# Supported MOS versions:
6.0, 6.1, 7.0, 8.0

# Prerequisites
- designed to run on Fuel node, if running from any other node, these requirements should be met:
  1. root access via public key to any node via Fuel admin network
  2. edit `config.yaml` to specify Fuel's IP address instead of `127.0.0.1`
- install `git`
- install [Timmy](https://github.com/adobdin/timmy) - `pip install git+https://github.com/adobdin/timmy.git`
- verify the installation - `python -c 'import timmy'` should not print tracebacks
- if the installation for some reason was not successful, install Timmy manually (for ex. into /root folder):
  1. `cd /root; git clone https://github.com/adobdin/timmy.git`
  2. `ln -s /root/timmy/timmy /usr/lib/python2.X/site-packages/timmy` # change X to the version of Python 2 available on server
  3. verify the installation - `python -c 'import timmy'` should not print tracebacks

# Usage
- always update [Timmy](https://github.com/adobdin/timmy) before updating timmy-customtest
- clone timmy-customtest: `git clone https://github.com/f3flight/timmy-customtest.git`
- make sure you are ok to IO load your nodes (root partition), since the tool will do md5 verification of each installed package on each node (timmy uses `nice` and `ionice` to minimize the impact)
- optionally edit `config.yaml` to your liking / requirements - for example you can filter nodes by various parameters
- cd into `timmy-customtest` folder and start the tool by running `./customtest.py` (executing from a different folder not yet supprted), optionally redirect output to a file: `./customtest.py > results.yaml`
- be happy

# Reading the output
Output is self-explanatory, you might want to view it with Vim and set up folding like so:
```
:set shiftwidth=2
:set foldmethod=indent
zM
```
Now you can unfold the sections you are interested in with `za` and fold them back with `zc`. More info on [Vim wikia](http://vim.wikia.com/wiki/Folding).
