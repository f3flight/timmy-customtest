# timmy-virgintest
Python-based tool which uses Timmy to find customizations in Mirantis OpenStack and check if MU installation would overwrite them.

# Prerequisites
- Timmy (https://github.com/adobdin/timmy)
- symlink Timmy folder into a python path (for example /usr/lib/python2.6/site-packages)

# Usage 
- start the tool by running `./virgintest.py`, optionally redirect output to a file: `./virgintest.py > results.yaml`
- be happy

# Reading the output
Output is self-explanatory, you might want to view it with Vim and set up folding like so:
```
:set shiftwidth=2
:set foldmethod=indent
zM
```
Now you can unfold the sections you are interested in with `za` and fold them back with `zc`. More info on [Vim wikia](http://vim.wikia.com/wiki/Folding).

