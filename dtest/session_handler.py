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
DTest session support.
"""
import logging

class SessionHandler (object):
    """Represents low-level DTest session handler.

    A dtest session handler is responsible for giving
    a DTester the low level mean to have a pty-like
    access to the session and an eventual file manipulation
    capability
    Thus DTestSessionHandler may have several capabilities:
         - command run capability
         - file transfer capability

    The command run capability includes:
        - a way to update environment
        - a way to send a string to pty input
        - a way to recv data from pty output
    """

    class UnableToUpdateEnvironException(Exception):
        """This DTest Session Handler is not capable to update environ"""
        pass

    class UnableToRunCommandException(Exception):
        """This DTest Session Handler is not capable to run command"""
        pass

    class UnableToFileTransferException(Exception):
        """This DTest Session Handler is not capable to transfer file"""
        pass

    class SessionFailureException(Exception):
        """The DTest Session Handler encounter a failure"""
        pass

    logger = logging.getLogger("DTesterSessionHandler")
    sh  = logging.StreamHandler()
    fmt = logging.Formatter(fmt="## [%(threadName)s]|%(name)s::%(levelname)s:: %(message)s")
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    def __init__(self,runCommandCapable=False, fileTransferCapable=False):
        """
        Create a Default Session Handler with no capability.        
        """
        self.isRunCommandCapable     = runCommandCapable
        self.isFileTransferCapable   = fileTransferCapable
        self.sessionOpened           = False
        self.environ                 = None
        self.__lastReceive           = None
        self.__lastSent              = None
        self.CTRL_C  = chr(03)
        self.ETX     = chr(03)
        self.EOT     = chr(04)
        self.CR      = chr(13)
        self.LF      = chr(10)
        self.CRLF    = self.CR + self.LF
        self.NEWLINE = self.LF
        self.ESC     = chr(27)
        self.stdin   = None
        self.stderr  = None
        self.stdout  = None
        self.__hasTimedOut = False

    def __getHasTimedOut(self):
	return self.__hasTimedOut

    def __setHasTimedOut(self,value):
	 self.__hasTimedOut = value
    hasTimedOut = property(fget=__getHasTimedOut,fset=__setHasTimedOut)

    def __getLastReceive(self):
        return self.__LastReceive
    
    def __setLastReceive(self,string):
        self.__lastReceive = string
        # FIXME should add logger
        #print "LastReceive = %s" % string

    lastReceive = property(fget=__getLastReceive,fset=__setLastReceive)

    def __getLastSent(self):
        return self.__lastSent
    
    def __setLastSent(self,string):
        self.__lastSent = string
        # FIXME should add logger
        #print "LastSent = %s" % string
    lastSent = property(fget=__getLastSent,fset=__setLastSent)

    def __isnotoverloaded(self,method):
        methname = method.__name__
        return (getattr(self.__class__,methname)==getattr(SessionHandler,methname))
        
    def openIfNotOpened(self):
        """ Open the session if it is not already opened."""
        if not self.sessionOpened:
            self.open()

    def open(self,*args,**kwargs):
        """ Open the session """
        self.sessionOpened = True

    def close(self):
        """ Close the session. """
        if (not self.stdin==None):
            self.stdin.close()
        if (not self.stderr==None):
            self.stderr.close()
        if (not self.stdout==None):
            self.stdout.close()    
        self.sessionOpened = False 
        
    def updateEnviron(self,environ):
        """ Update the environment """
        self.environ = environ
        for envvar in self.environ.iteritems():
           envcmd = "%s=%s" % envvar
           self.sendall(envcmd+self.NEWLINE) 

    def send(self, string):
        """ Send a string to the session """
        self.lastSent = string
        if (not self.stdin==None):
            self.stdin.write(string)
        if (self.__isnotoverloaded(SessionHandler.send)):
            raise self.UnableToRunCommandException("Cannot send")        

    def sendall(self, string):
        self.lastSent = string
        if (not self.stdin==None):
            self.stdin.write(string)
        if (self.__isnotoverloaded(SessionHandler.sendall)):
            raise self.UnableToRunCommandException("Cannot sendall")

    def recv_ready(self):
        if (self.__isnotoverloaded(SessionHandler.recv_ready)):
            raise self.UnableToRunCommandException("Cannot recv_ready")

    def recv(self, size, buffer=None):
        """Receive a string from the session"""
        if (not self.stdout==None):
            self.stdout.write(self.__lastReceive)
        if (self.__isnotoverloaded(SessionHandler.recv)):
            raise self.UnableToRunCommandException("Cannot recv")

    def putFile(self, sourcePath, destinationPath):
        """ Put a file from sourcePath to destinationPath """
        if (self.__isnotoverloaded(SessionHandler.putFile)):
            raise self.UnableToFileTransferException("Cannot putFile")

    def getFile(self, sourcePath, destinationPath):
        """ Get a file from sourcePath to destinationPath """
        if (self.__isnotoverloaded(SessionHandler.getFile)):
            raise self.UnableToFileTransferException("Cannot getFile")
