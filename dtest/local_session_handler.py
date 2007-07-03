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

import logging
import dtest
    
class LocalSessionHandler(dtest.SessionHandler):
    """
    A Local DTest session handler which may run command through a local pty connection
    """
    def __init__(self):
        super(LocalSessionHandler,self).__init__(runCommandCapable=True, fileTransferCapable=False)
        

    def open(self,*args,**kwargs):
        self.sessionOpened = True

    def close(self):
        self.sessionOpened = False 
        
    def updateEnviron(self,environ):
        raise UnableToUpdateEnviron()

    def send(self, string):
        raise UnableToRunCommand("Cannot send")

    def sendall(self, string):
        raise UnableToRunCommand("Cannot sendall")

    def recv_ready(self):
        raise UnableToRunCommand("Cannot recv_ready")

    def recv(self, size, buffer=None):
        raise UnableToRunCommand("Cannot recv")

    def putFile(self, sourcePath, destinationPath):
        raise UnableToFileTransfer("Cannot putFile")

    def getFile(self, sourcePath, destinationPath):
        raise UnableToFileTransfer("Canoot getFile")
