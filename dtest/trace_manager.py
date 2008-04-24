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

class TraceManager (object):
    """Represents DTest sequence trace manager.

    A DTest trace manager is linked with one
    or several DTestMaster which represent a complete
    and standalone test sequence.
    The DTestMaster and its registered DTester(s)
    may call the TraceManager services in order to ask
    for tracing.
    
    The Trace manager forward the trace call to all
    registered TraceHandler.
    A TraceHandler may produce output to stdout or
    build a file containing a specific trace
    format (HTML, TAP, Promela, MSC...) 
    """

    class SequenceNotFinishedException(Exception):
        "Used when setting the next sequence before the preceding did finish"

    class SequenceAlreadyRunningException(Exception):
        "Used when setting an already running sequence"
        
    logger = logging.getLogger("TraceManager")
    def __init__(self):
        self.__dtestSequence = None
        self.__handlers      = set()
    
    def registerTraceHandler(self, traceHandler):
        self.logger.info("Registering Trace Handler <" + traceHandler.name + ">...")
        # Add traceHandler to the set of handlers
        self.__handlers.add(traceHandler)

    def newSequence(self, dtestmaster):
        self.logger.info("Registering Test Sequence <" + dtestmaster.name + ">...")
        # we cannot change sequence if the preceding sequence is not finished
        if (self.__dtestSequence != None):
            if ((self.__dtestSequence.runner != None) and (self.__dtestSequence.runner.isAlive())):
                raise SequenceNotFinishedException, "currently running sequence ="+self.__dtestSequence.name
        if ((dtestmaster.runner != None) and (dtestmaster.runner.isAlive())):
            raise SequenceAlreadyRunningException, "currently running sequence ="+self.__dtestSequence.name
        self.__dtestSequence=dtestmaster
        # tell every trace handlers there is a new sequence coming
        # (this will reset previously registered DTesters)
        for handler in self.__handlers:
            handler.newSequence(dtestmaster)

    def initializeSequence(self):
        """ Initialize sequence for every trace trace handler
        This gives a chance for the handler to build a header
        """
        for handler in self.__handlers:
            # we register all dtester from the tester into handler
            for dtester in self.__dtestSequence.dtesters:
                handler.registerDTester(dtester)
            # then we initialize the Sequence
            handler.initializeSequence()

    def finalizeSequence(self):
        """ Finalize the sequence for every trace trace handler.
        This gives a chance for the handler to build a trailer.
        """
        for handler in self.__handlers:
            handler.finalizeSequence()
            
    def traceStep(self,srcDTester,dstDTester,step):
        for handler in self.__handlers:
            handler.traceStep(srcDTester,dstDTester,step)
    
    def traceStepResult(self,ok_nok,desc=None,skip=None,todo=None):
        for handler in self.__handlers:
            handler.traceStepResult(ok_nok,desc,skip,todo)
    
    def traceStepComment(self,comment):
        for handler in self.__handlers:
            handler.traceStepComment(comment)
            
    def finalize(self):
        """Add an execution trace step to the execution steps queue to order them all
        One may not call newSequence after that call
        """
        for handler in self.__handlers:
            handler.finalize()
        
