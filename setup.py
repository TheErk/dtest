#!/usr/bin/env python

##-----------------------------------------------------------------------
##
## DTest - A Distributed test framework
##
## Copyright (c) 2006,2007 Eric NOULARD and Frederik DEWEERDT 
##
## This library is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public
## License as published by the Free Software Foundation; either
## version 2.1 of the License, or (at your option) any later version.
##
## This library is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public
## License along with this library; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##
##-----------------------------------------------------------------------


longdesc = '''
This is a library implementing a distributed test framework.
DTest may be used to realize distributed test scenario
including but not limiting to client/serveur application
testing.

Required packages:
    paramiko
'''

import sys
import time
##try:
##    from setuptools import setup
##    kw = {
##        'install_requires': 'paramiko',
##    }
##except ImportError:
##    from distutils.core import setup
kw = {}

from distutils.core import setup

version_string='0.4'
#version_string=version_string+"-"+time.strftime("%d%h%Y-%Hh%M")

setup(name='dtest',
      version=version_string,      
      description='A Distributed Test Framework',
      author='Eric Noulard',
      author_email='eric.noulard@gmail.com',
      packages=['dtest'],
      scripts=['tests/dtest-autotest','tests/dtest-sshtest'],
      license = 'LGPL',
      url     = 'no URL yet :))',
      classifiers = [ 'Development Status :: 1 - Alpha',
                      'Intended Audience :: Developers',
                      'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
                      'Operating System :: OS Independent'],
      long_description = longdesc,
      **kw
      )
