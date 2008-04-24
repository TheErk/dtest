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
import sys
from trace_handler import TraceHandler
import TAP

class TAPTraceHandler (TraceHandler):
    """Represents a DTest TAP trace handler.

    A DTest Test Anything Protocol (TAP) trace handler 
    """

    logger = logging.getLogger("TAPTraceHandler")
    
    def __init__(self,output=sys.stdout):
        super(TAPTraceHandler,self).__init__("TAPTraceHandler")
        self.output = TraceHandler.getFileOrOpenPath(output,ext=".tap")
            
    def newSequence(self, dtestmaster):
        self.logger.info("Registering Test Sequence <" + dtestmaster.name + ">...")
        self.builder      = TAP.Builder.create(out=self.output)
        self.dtestmaster    = dtestmaster
        self.sequence_passed = True 

    def initializeSequence(self):    
        self.logger.info("Current sequence has <%d> DTesters." % self.dtesters.__len__())
        self.output.write("## Test Sequence <"+self.dtestmaster.name+"> ...\n")
        self.output.write("## Number of DTesters = %d\n" % self.dtesters.__len__())
        self.output.write("##   Description:\n")
        self.output.write("##   " +self.dtestmaster.description+"\n")
        self.builder.set_plan(self.dtestmaster.nbSteps, None)
    
    def finalizeSequence(self):
        self.output.write("## Test Sequence <"+self.dtestmaster.name+">")
        if (self.sequence_passed):
            self.output.write(": PASSED.\n")
        else:
            self.output.write(": FAILED.\n")                    
    
    def traceStepResult(self,ok_nok,desc,skip=None,todo=None):
        self.builder.ok(ok_nok,desc=desc,skip=skip,todo=todo)
        if (not ok_nok):
            self.sequence_passed = False
    
    def traceStepComment(self,comment):
        self.output.write("##" + comment)

    def finalize(self):        
        TraceHandler.closeIfNotStdout(self.output)
