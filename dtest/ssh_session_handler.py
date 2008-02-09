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

import paramiko
import dtest
import sys
import os
import time
import signal
from StringIO import StringIO
import logging
import inspect
import re
import socket

class SSHSessionHandler(dtest.SessionHandler):
    """
    An SSH DTest session handler which may run command through an SSH connection
    """
    logging.getLogger("paramiko.transport").addHandler(dtest.DTester.sh)
    def __init__(self,user,host='localhost'):
        super(SSHSessionHandler,self).__init__(runCommandCapable=True, fileTransferCapable=False)
        self.host        = host
        self.user        = user
        self.SSHClient   = None
        self.SSHShell    = None
        self.SFTPClient  = None

    def open(self,*args,**kwargs):
        self.SSHClient   = paramiko.SSHClient()
        self.SSHClient.load_system_host_keys()
        try:
            self.SSHClient.connect(self.host,username=self.user)
            self.SSHShell   = self.SSHClient.invoke_shell('vt100',80,300)
            self.SFTPClient = self.SSHClient.open_sftp()
            self.sessionOpened = True
        except socket.error, err:
            self.sessionOpened = False

    def close(self):
        if self.sessionOpened:
            self.SSHShell.sendall(self.CTRL_C)
            self.SSHShell.sendall("exit")
            self.SSHClient.close()
            super(SSHSessionHandler,self).clsoe()

    def send(self, string):
        super(SSHSessionHandler,self).send(string)        
        return self.SSHShell.send(string)

    def sendall(self, string):
        super(SSHSessionHandler,self).sendall(string)
        return self.SSHShell.sendall(string)

    def recv_ready(self):
        return self.SSHShell.recv_ready()

    def recv(self,size,buffer=None):
        read=0
        retval  = None
        readval = None 
        if buffer==None:
            retval = True
            buffer = StringIO("")
        while (read!=size) and not self.hasTimedOut:
            if self.SSHShell.recv_ready():
                buffer.write(self.SSHShell.recv(1))
                read += 1
                self.logger.debug("buffer ="+buffer.getvalue())
            else:
                time.sleep(1)

        # remember the lastReceived values
        readval = buffer.getvalue()
        self.lastReceive = readval[len(readval)-size:]
        # call super before returning
        super(SSHSessionHandler,self).recv(size,buffer)
        if (retval==True):
            return buffer.getvalue()
        else:
            return retval

    def putFile(self, sourcePath, destinationPath):
        self.SFTPClient.put(sourcePath,destinationPath)

    def getFile(self, sourcePath, destinationPath):
        self.SFTPClient.get(sourcePath,destinationPath)

