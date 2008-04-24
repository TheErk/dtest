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

class MSCTraceHandler (TraceHandler):
    """Represents a DTest MSC trace handler.

    A DTest Message Sequence Chart (MSC) trace handler 
    """

    logger = logging.getLogger("MSCTraceHandler")
    
    def __init__(self,output=sys.stdout):
        super(MSCTraceHandler,self).__init__("MSCTraceHandler")    
        self.output = TraceHandler.getFileOrOpenPath(output,ext=".msc")                 
            
    def newSequence(self, dtestmaster):
        self.logger.info("Registering Test Sequence <" + dtestmaster.name + ">...")        
        self.dtestmaster  = dtestmaster        
         
    def initializeSequence(self):
        """ Initialize sequence for every trace trace handler
        This gives a chance for the handler to build a header
        """
        self.logger.info("Current sequence has <%d> DTesters." % self.dtesters.__len__())        
        self.output.write("entity "+self.dtestmaster.name+'\n')                
        
    def traceStep(self,srcDTester,dstDTester,step):
        methodName=step[0].__name__
        firstArg=str(step[1])
        firstArg = str.replace(firstArg,",","")
        secondArg=""
        #for the online msc generator http://websequencediagrams.com/ 
        mscline=srcDTester.name+"->"+dstDTester.name+":"+methodName+firstArg+secondArg
        self.output.write(mscline+'\n')
    
    def traceStepResult(self,ok_nok,desc,skip,todo):        
        pass
    
    def traceStepComment(self,comment):
        # FIXME implement comments in the MSC?
        pass

    def finalize(self):        
        TraceHandler.closeIfNotStdout(self.output)
