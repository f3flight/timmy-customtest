# timmy-customtest
Python-based tool for Mirantis OpenStack which uses [Timmy](https://github.com/adobdin/timmy) as a backend. Provides the following info about environments and Fuel server:
- custom package versions
- post-install file changes (built-in md5 verification)
- checks if these customizations interfere with MU installation
- provides a list of packages for which there are updated versions available

# Supported MOS versions:
6.0, 6.1, 7.0, 8.0

# Prerequisites
- designed to run on Fuel node, if running from any other node, these requirements should be met:
  1. python 2.6 or 2.7
  2. root access via public key to any node via Fuel admin network
  3. edit `config.yaml` to specify Fuel's IP address instead of `127.0.0.1`
  4. PyYAML python module should be installed (requirement for Timmy)
- install git `yum install git`
- for easy install, install pip `yum install python-pip`
- install [Timmy](https://github.com/adobdin/timmy) - `pip install git+https://github.com/adobdin/timmy`
- verify the installation - `python -c 'import timmy'` should not print tracebacks
- if the installation for some reason was not successful, install Timmy manually (for ex. into /root folder):
  1. `cd /root; git clone https://github.com/adobdin/timmy.git`
  2. `ln -s /root/timmy/timmy /usr/lib/python2.X/site-packages/timmy` # change X to the version of Python 2 available on the system
  3. verify the installation - `python -c 'import timmy'` should not print tracebacks

# Installation and updates
- always update [Timmy](https://github.com/adobdin/timmy) before updating timmy-customtest. To update Timmy if it is installed by pip, uninstall and reinstall: `pip uninstall timmy; pip install timmy`. If using git directly, do `git pull` in the folder where you cloned Timmy.
- install timmy-customtest: `pip install git+https://github.com/f3flight/timmy-customtest`
- alternatively, clone without installing: `git clone https://github.com/f3flight/timmy-customtest`
- To update already installed timmy-customtest, use the same methods as for Timmy (mentined above)

# Usage
- make sure you are ok to IO load your nodes (root partition), since the tool will do md5 verification of each installed package on each node (timmy uses `nice` and `ionice` to minimize the impact)
- optionally copy and edit `/usr/share/timmy-customtest/timmy-config-default.yaml` - for example you can filter nodes by various parameters, then use `-c` option to specify your edited configuration file (if you have not installed via pip then simply edit `timmy-config.yaml`)
- run the tool - `timmy-customtest`
- if you cloned only, then cd into `timmy-customtest` folder and start the tool by running `./timmy-customtest`
- optionally redirect output to a file: `timmy-customtest | tee results.yaml`
- you can regenerate the report any time without actually collecting data from nodes again (connection to Fuel still needed to initialize the array of nodes) - to do this specify `-f` (`--fake`) option - this will use data previously collected in `/tmp/timmy/info` folder (unless you or Timmy have erased it)
- be happy
- data (except stdout which you have to capture manually) is collected into `/tmp/timmy/info` if you decide to use/share it

# Reading the output
Output is self-explanatory, you might want to view it with Vim and set up folding like so:
```
:set shiftwidth=2
:set foldmethod=indent
zM
```
Now you can unfold the sections you are interested in with `za` and fold them back with `zc`. More info on [Vim wikia](http://vim.wikia.com/wiki/Folding).
