##-----------------------------------------------------------------------
##
## DTest - A Distributed test framework
##
## Copyright (c) 2006-2008 Eric NOULARD, Lionel DUROYON and Frederik DEWEERDT 
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
DTest utility classes or functions.
"""
import sys
import os
import time
import logging

class Utils (object):
    
    def getUserHostPath(cls,argument):
        """ Retrieve user, host, path
        element from a string like
        [[<user>@]<host>]:/path
        and return them is a dictionnary.
        """

        retval = dict()
        if argument.find("@") != -1:
            (retval['user'],argument) = argument.split("@",1)
        else:
            retval['user'] = os.environ["USER"]
            
        if argument.find(":") != -1:
            (retval['host'],retval['path']) = argument.split(":",1)
        else:
            retval['host'] = "localhost"
            retval['path'] = argument
                
        return retval

    getUserHostPath = classmethod(getUserHostPath)

