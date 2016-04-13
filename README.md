# timmy-customtest
Python-based tool for Mirantis OpenStack which uses Timmy as a backend. Provides the following info about environemnts and Fuel server:
- custom package versions
- post-install file changes (built-in md5 verification)
- checks if these customizations interfere with MU installation
- provides a list of packages for which there are updated versions available

# Supported MOS versions:
6.0, 6.1, 7.0, 8.0

# Prerequisites
- install timmy - `pip install git+https://github.com/adobdin/timmy.git`

# Usage
- always update timmy before updating timmy-customtest
- make sure you are ok to load your nodes (root partition), since the tool will do md5 verification of each installed package on each node (timmy uses `nice` and `ionice` to minimize the impact)
- optionally edit `config.yaml` to your liking / requirements
- start the tool by running `./customtest.py` (executing from a different folder not yet supprted), optionally redirect output to a file: `./customtest.py > results.yaml
- be happy

# Reading the output
Output is self-explanatory, you might want to view it with Vim and set up folding like so:
```
:set shiftwidth=2
:set foldmethod=indent
zM
```
Now you can unfold the sections you are interested in with `za` and fold them back with `zc`. More info on [Vim wikia](http://vim.wikia.com/wiki/Folding).
