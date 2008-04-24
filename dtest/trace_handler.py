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

import logging
import os
import sys

class TraceHandler (object):
    """Represents a DTest trace handler.

    A dtest trace handler 
    """
    
    class TraceHandlerAbstractMethod(Exception):
        "Used in order to enforce sort-of abstract method"
        
    logger = logging.getLogger("TraceHandler")
    
    def __getFileOrOpenPath(cls,out,ext=None):
        if (isinstance(out,file)):
            return out
        if (isinstance(out,type(""))):
            (name,builtin_ext) = os.path.splitext(out)
            if (builtin_ext=="" and ext):
                return file(out+ext,"w+")
            else:
                return file(out,"w+")
            
    getFileOrOpenPath = classmethod(__getFileOrOpenPath)
    
    def __closeIfNotStdout(self,out):
        if (out != sys.stdout):
            out.close()
            
    closeIfNotStdout = classmethod(__closeIfNotStdout)
    
    def __init__(self,name="TraceHandler"):
        self.__dtesters = set()
        self.__name     = name        
        

    def __getDTesters(self):
        return self.__dtesters
    dtesters = property(fget=__getDTesters,doc="dtesters getter")

    def __getName(self):
        return self.__name
    name=property(fget=__getName,doc='handler name')

    def registerDTester(self, dtester):
        self.logger.info("Registering DTester <" + dtester.name + ">...")
        # Add dtester to the set of dtesters
        self.__dtesters.add(dtester)

    def newSequence(self, dtestmaster):
        raise TraceHandlerAbstractMethod

    def initializeSequence(self):
        """ Initialize sequence for every trace trace handler
        This gives a chance for the handler to build a header
        """
        self.logger.info("Current sequence has <" + self.__dtesters.__len__() + "> DTesters.")
        pass

    def finalizeSequence(self):
        """ Finalize the sequence for every trace trace handler.
        This gives a chance for the handler to build a trailer.
        """
        pass
        
    def traceStep(self,srcDTester,dstDTester,step):
        pass
    
    def traceStepResult(self,ok_nok,desc,skip=None,todo=None):
        raise TraceHandlerAbstractMethod
    
    def traceStepComment(self,comment):
        pass

    def finalize(self):
        """Should finalize the handler"""
        raise TraceHandlerAbstractMethod
