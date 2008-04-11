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
DTest base classes support.
"""
import threading
from threading import Thread
import sys
import os
import time
import signal
from StringIO import StringIO
import logging
import inspect
import re
import session_handler
from session_handler import SessionHandler

class DTester (Thread):
    """Represent an elementary DTest stakeholder.
    
    DTest falls into (eventually) communicating and concurrent
    processes, the DTesters, which will be runned concurrently
    by a DTestMaster. A DTester contains
    sequential steps (either initialize or run steps) specified
    through addInitializeStep and/or addRunStep
    DTester method.
    FIXME: describe DTESTMASTER
    """
 
    class InvalidStepFunctionException(Exception):
        """The function step provided is invalid"""

    class StepNotCallableException(InvalidStepFunctionException):
        """The function step provided is not callable"""
            
    class StepFirstArgNotDTesterNorSelfException(InvalidStepFunctionException):
        """The function step should be either dtester or self"""

    class StepFailedException(Exception):
        """The previously executed step failed"""

    class NoRunningCommandException(Exception):
        """Trying to use command related action while no command currenlty running"""

    class SessionUnableToRunCommandException(Exception):
        """The DTest Session Handler cannot run command"""


    def __isbound(cls,function):
        return inspect.ismethod(function) and function.im_self != None
    __isbound = classmethod(__isbound)
    
    def __isfunction_or_unboundmethod(cls,function):        
        if (inspect.ismethod(function)):
            return function.im_self == None
        elif (inspect.isfunction(function)):
            return True
        else:
           return True
    __isfunction_or_unboundmethod = classmethod(__isfunction_or_unboundmethod)
        
    logger = logging.getLogger("DTester")
    sh  = logging.StreamHandler()
    fmt = logging.Formatter(fmt="## [%(threadName)s]|%(name)s::%(levelname)s:: %(message)s")
    sh.setFormatter(fmt)
    logger.addHandler(sh)
       
    def __init__(self,name,session=SessionHandler(),timeout=10):
        """Creates a DTester using the specified Sessionhandler.

        @param name: the name of the DTester
        @type name: C{string}
        @param session: the session handler associated with this
                        instance of DTester.
        @type session: L{SessionHandler}
        @param timeout: the timeout (in seconds) used for each potentially
                        timed call.
        @type timeout: C{int}
        """
        super(DTester,self).__init__(name=name)
        self.session            = session
        self.timeout            = timeout
        self.environ            = None
        self.dtestmaster        = None
        self.nb_steps           = 0
        
        self.__expectDidTimeOut   = False
        self.__runSteps           = []
        self.__initializeSteps    = []

    def __getHasTimedOut(self):
        return self.__expectDidTimeOut
        
    hasTimedOut = property(fget=__getHasTimedOut)
        
    def __getName(self):
        return self.getName()

    name = property(fget=__getName)

    def __getStderr(self):
        return self.session.stderr
    
    def __setStderr(self,file):
        self.session.stderr = file

    stderr = property(fget=__getStderr,fset=__setStderr)

    def __getStdin(self):
        return self.session.stdin
    
    def __setStdin(self,file):
        self.session.stdin = file

    stdin = property(fget=__getStdin,fset=__setStdin)

    def __getStdout(self):
        return self.session.stdout
    
    def __setStdout(self,file):
        self.session.stdout = file
        
    def getRunSteps(self):
        return self.__runSteps

    stdout = property(fget=__getStdout,fset=__setStdout)

    def registerForBarrier(self, barrierId):
        """Register for DTest barrier barrierId in the DTestMaster.

        This method does not need to be called explicitly.
        The DTester will generate the call as soon as a 'barrier'
        run step is added through L{addRunStep} method.
        @param barrierId: the barrier identifier
        @type barrierId: C{string}
        """
        self.dtestmaster.registerForBarrier(self,barrierId)
        
    def barrier(self, barrierId, timeout=None):
        """Wait until every stakeholder have reached the specified barrier.

        If timeout is not specified the DTester instance-wide timeout
        is used. If specified then the specified timeout is used.
        @param barrierId: the barrier identifier
        @type barrierId: C{string}
        @param timeout: the timeout (in seconds) to be used for waiting
                        for others to reach (if any) to reach the barrier.
                        0 means never timeout.
        @type timeout: C{int}
        """
        if (timeout==None):
            timeout = self.timeout
        self.dtestmaster.barrier(self,barrierId,timeout)

    def ok(self, *args, **kwargs):
        """Ok TAP (Test Anything Protocol) method"""
        self.dtestmaster.ok(self, *args, **kwargs)

    ## The following are command related API
    ## which are implemented using lower-level
    ## session handler API
    
    def runCommand(self, command=None, environ=None):
        """Run a command on the session handler DTest.session"""
        self.session.openIfNotOpened()
        if (environ != None):
            self.session.updateEnviron(environ)
        if (command != None):
            self.session.send(command+self.session.NEWLINE)    
           
    def abort(self):
        if self.stdin != None:
            self.stdin.flush()
        if self.stdout != None:
            self.stdout.flush()
        if self.stderr != None:
            self.stderr.flush()

    def __expectTimedOut(self,msg=None):
        self.logger.warning("Expect timeout: %s" % msg)
        self.abort()
        self.__expectDidTimeOut = True        
        # notify session 
        self.session.hasTimedOut = True

    def __createExpectTimer(self,timeout=10,msg=""):
        self.__expectDidTimeOut = False
        t = threading.Timer(timeout,self.__expectTimedOut,kwargs={'msg': msg})
        t.setName("Timer-"+self.getName())
        return t
    
    def expectFromCommand(self, pattern, timeout=None):    
        """Wait until the expected pattern is received on the session handler DTester.session"""
        pat       = re.compile(pattern)
        monitored = StringIO("")

        # if no timeout is specified then use
        # the one of the DTester instance
        if timeout==None:
            timeout=self.timeout
            
        # if timeout is not 0 then create and start timer
        if timeout!=None and timeout!=0:
            t = self.__createExpectTimer(timeout,"waiting for pattern <%s>" % pattern)
            t.start()

        # Monitor expected pattern from session
        # FIXME this way of monitoring is too simple
        # and probably innefficient when the session output
        # is huge since monitored an ever growing string.
        while (not pat.search(monitored.getvalue())) and (not self.__expectDidTimeOut):
            self.session.recv(1,monitored)

        # We will get there because time out handler did tell
        # the session handler the test has timedout
        if self.__expectDidTimeOut:
            #self.logger.warn("Monitored = %s" % monitored.getvalue())
            return False
        else:
            if timeout != None:
                t.cancel()
            return True
    
    def sendToCommand(self, string):
        """Send directly a string on the session handler DTester.session"""
        self.session.sendall(string)
        return True
    
    def waitCommandTermination(self, timeout=None):
        """Wait until the session handler DTester.session ends"""
        if self.session.sessionOpened:
            while self.session.recv_ready():
                self.session.recv(1)
        return True

    def waitDuring(self,duration):
        time.sleep(duration)
    
    def terminateCommand(self):
        """Send to the session handler DTester.session the command for terminating"""
        self.session.sendall(self.session.CTRL_C)
        self.session.sendall(self.session.NEWLINE)
        return True

    def putFile(self,srcPath,dstPath):
        self.session.openIfNotOpened()
        self.session.putFile(srcPath,dstPath)

    def getFile(self,srcPath,dstPath):
        self.session.openIfNotOpened()
        self.session.getFile(srcPath,dstPath)

    def addInitializeStep(self, stepmethod, *args, **kwargs):
        if not callable(stepmethod):
            raise DTester.StepNotCallableException, "Invalid initialize step:"+str(stepmethod)+"is not a callable object"
        self.__initializeSteps.append((stepmethod,args,kwargs))

    def addRunStep(self, stepmethod, *args, **kwargs):
        """Add stepmethod run step to a DTester
        
        @param stepmethod: the stepmethod name
        @type stepmethod: C{string}     
        
        Stepmethod parameter can be :
            
        ok : Test Anything Protocol display method.
        runCommand : runs a command on the associed session handler.
        expectFromCommand : waits for the reception of a string pattern on the associated session handler. 
        terminateCommand : terminates a command on the associated session handler.
        barrier : indicates that a DTester has reached a barrier.
        sendToCommand : sends a command on the associated session handler.
        waitCommandTermination : waits the command termination on the associated session handler.
        custom : allows to run any python "callable".
        
        Each stepmethod matches an implemented method of DTester, except custom which allows you
        to define and call your own python "callable"
        to see which args parameters must follow each stepmethod, you can look the matching method
        """
        
        # Handle string stepmethod case
        if isinstance(stepmethod,type("")):
            if hasattr(self,stepmethod):
                stepmethod_str = stepmethod
                stepmethod = getattr(self.__class__,stepmethod)
                self.logger.debug("stepmethod string <%s> resolved to %r" % (stepmethod_str,stepmethod))
            else:
                raise DTester.InvalidStepFunctionException, "Stepmethod is a unknown attribute string <%s> of class <%s>" % stepmethod, self.__class__.__name__

        # stepmethod should be callable, at least ...
        if not callable(stepmethod):
            raise DTester.StepNotCallableException, "Invalid run step:"+str(stepmethod)+"is not a callable object"

        if (inspect.ismethod(stepmethod)):
            # barrier and ok method
            # triggers special handling
            # we check for .im_func in order to capture both bounded
            # and unbounded method
            if stepmethod.im_func == DTester.barrier.im_func:
                self.addInitializeStep(DTester.registerForBarrier,args[0])
            elif stepmethod.im_func == DTester.ok.im_func:
                self.nb_steps += 1

        if DTester.__isfunction_or_unboundmethod(stepmethod):
            # We check first arg to be self or dtester 
            (iargs, ivarargs, ivarkw, idefaults) = inspect.getargspec(stepmethod)
            if iargs[0] != "dtester" and iargs[0] != "self":
                raise DTester.StepFirstArgNotDTesterNorSelfException, "args[0]="+iargs[0]
            
        self.logger.debug("addRunStep :: step %s args : %s", str(stepmethod), str(args))
        self.__runSteps.append((stepmethod,args,kwargs))        

    def initialize(self):
        self.logger.info("DTester <%s> begin initialize..." % self.getName())
        for step in self.__initializeSteps:
            self.logger.debug("initialize :: step[0]: %s", str(step[0]))
            self.logger.debug("initialize :: step[1:] %s", str(step[1:]))
            if (len(step[1]) > 0) or (len(step[2]) > 0):
                try:
                    step[0](self,*(step[1]),**(step[2]))
                except NotImplementedError, err:
                    self.logger.error("InitStep <%r> failed <%r>" % (step[0],err))
                    self.ok(False,desc="InitStep <%r> failed <%r>" % (step[0],err))
            else:
                try:
                    step[0](self)
                except NotImplementedError, err:
                    self.logger.error("Step <%r> failed <%r>" % (step[0],err))
                    self.ok(False,desc="Step <%r> failed <%r>" % (step[0],err))
        self.logger.info("DTester <%s> initialize complete." % self.getName())
        
    def run(self):
        """Run the DTester thread
        
        This method executes each run step defined previously by addRunStep
        """
        
        self.logger.info("DTester <%s> begin run..." % self.getName())
        for step in self.__runSteps:
            self.logger.debug("run :: step[0]: %s", str(step[0]))
            self.logger.debug("run :: step[1:] %s", str(step[1:]))
            isBarrierStep=(step[0].__name__==self.barrier.__name__)
            if (len(step[1]) > 0) or (len(step[2]) > 0):
                try:
                    if (DTester.__isbound(step[0])):
                        #for execution trace
                        if (self.dtestmaster.getTrace()):
                            self.dtestmaster.traceStep(self.getName(),self.getName(),step)
                        #for pseudo-execution
                        if ((not self.dtestmaster.getPseudoExec())or isBarrierStep):
                            step[0](*(step[1]),**(step[2]))
                    else:
                        #for execution trace
                        if (self.dtestmaster.getTrace()):
                            self.dtestmaster.traceStep(self.getName(),self.getName(),step)
                        #for pseudo-execution
                        if ((not self.dtestmaster.getPseudoExec()) or isBarrierStep):
                            step[0](self,*(step[1]),**(step[2]))
                except NotImplementedError, err:
                    self.logger.error("RunStep <%r> failed <%r>" % (step[0],err))
                    self.ok(False,desc="RunStep <%r> failed <%r>" % (step[0],err))
            else:
                try:
                    if (DTester.__isbound(step[0])):
                        #for execution trace
                        if (self.dtestmaster.getTrace()):
                            self.dtestmaster.traceStep(self.getName(),self.getName(),step)
                        #for pseudo-execution
                        if ((not self.dtestmaster.getPseudoExec()) or isBarrierStep):
                            step[0]()
                    else:
                        #for execution trace
                        if (self.dtestmaster.getTrace()):
                            self.dtestmaster.traceStep(self.getName(),self.getName(),step)
                        #for pseudo-execution
                        if ((not self.dtestmaster.getPseudoExec()) or isBarrierStep):
                            step[0](self)
                except NotImplementedError, err:
                    self.logger.error("Step <%r> failed <%r>" % (step[0],err))
                    self.ok(False,desc="Step <%r> failed <%r>" % (step[0],err))
        self.logger.info("DTester <%s> has terminated." % self.getName())
