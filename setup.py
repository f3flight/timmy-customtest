#!/usr/bin/env python

from setuptools import setup
import os

d = os.path.join(os.path.abspath(os.sep), 'usr', 'share', 'timmy-customtest')
d_files = [(os.path.join(d, root), [os.path.join(root, f) for f in files])
           for root, dirs, files in os.walk('rq')]
d_files.append((os.path.join(d), ['timmy-config-default.yaml', 'rq.yaml']))
d_files += [(os.path.join(d, root), [os.path.join(root, f) for f in files])
            for root, dirs, files in os.walk('db')]

setup(name='timmy-customtest',
      version='1.2.1',
      author='Dmitry Sutyagin',
      author_email='f3flight@gmail.com',
      license='Apache2',
      url='https://github.com/f3flight/timmy-customtest',
      long_description=open('README.md').read(),
      packages=["timmy_customtest"],
      data_files=d_files,
      include_package_data=True,
      entry_points={'console_scripts':
                    ['timmy-customtest=timmy_customtest.customtest:main']})
