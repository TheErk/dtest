
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

"""
DTest is a distributed tests framework which enables the
seamless definitio and run of distributed test which may
be useful for application whose purpose is essentially
networked, like client-server or multi-tiers applications.
DTest offers a framework for the definition of coordinated
testers program which may be run on a remote machine through
a supported DTestSessionHandler (at least SSH is supported)
"""

from dtester import DTester, SessionHandler
from dtestmaster import DTestMaster
from ssh_session_handler import SSHSessionHandler
from local_session_handler import LocalSessionHandler

# fix module names for epydoc
# borrowed from paramiko __init__.py
for c in locals().values():
    if issubclass(type(c), type) or type(c).__name__ == 'classobj':
        # classobj for exceptions :/
        c.__module__ = __name__

__all__ = [ 'DTester',
            'DTestMaster',            
            'SessionHandler',
            'SSHSessionHandler',
            'LocalSessionHandler'
            ]    
