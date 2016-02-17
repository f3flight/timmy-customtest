# timmy-virgintest
Python-based tool which uses Timmy as a backend. Provides the following info about the environemnts and Fuel server:
- custom package versions
- post-install file changes (built-in md5 verification)
- checks if these customizations interfere with MU installation
- provides a list of packages for which there are updated versions available

# Prerequisites
- clone Timmy (https://github.com/adobdin/timmy)
- symlink Timmy folder into a python path (for example `ln -s ~/timmy /usr/lib/python2.6/site-packages/timmy`)

# Usage
- make sure you are ok to load your nodes (root partition), since the tool will do md5 verification of each installed package on each node (Timmy uses `nice` and `ionice` to minimize the impact)
- start the tool by running `./virgintest.py` (executing from a different folder not yet supprted), optionally redirect output to a file: `./virgintest.py > results.yaml`
- be happy

# Reading the output
Output is self-explanatory, you might want to view it with Vim and set up folding like so:
```
:set shiftwidth=2
:set foldmethod=indent
zM
```
Now you can unfold the sections you are interested in with `za` and fold them back with `zc`. More info on [Vim wikia](http://vim.wikia.com/wiki/Folding).

