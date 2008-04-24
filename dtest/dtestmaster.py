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

import threading
from threading import Thread
from dtester import DTester
from trace_manager import TraceManager
from TAP_trace_handler import TAPTraceHandler
#from tap_trace_handler import TAPTraceHandler
import sys
import os
import time
import signal
import logging
#for execution trace
from Queue import Queue

try:
    set
except NameError:
    from sets import Set as set, Immutable as frozenset

class DTestMasterRunner(Thread):
    """The Thread sub-class which effectively run the sequence
    represented by the DTestMaster
    """

    logger = logging.getLogger("DTestMasterRunner")
    
    def __init__(self, dtestmaster):
        super(DTestMasterRunner,self).__init__(name="DTestMasterRunner-"+dtestmaster.name)
        self.dtestmaster = dtestmaster
        
    def run(self):
        """Run Thread method"""
        self.dtestmaster.startTime = time.clock()
        # set up global time out
        if self.dtestmaster.timeout != None:
            t = threading.Timer(self.dtestmaster.timeout,self.dtestmaster.globalTimeOutTriggered)
            t.start()
        # Start all registered dtesters
        for dtester in self.dtestmaster.dtesters:
            self.logger.info("Starting <"+ dtester.getName()+ ">...")
            dtester.start()
            self.dtestmaster.runningDTesters += 1
        self.logger.info("Now <%d> registered DTesters launched.",self.dtestmaster.runningDTesters)
        # Wait for DTesters to terminate
        self.dtestmaster.joinedDTesters = set()
        while self.dtestmaster.runningDTesters > 0:
            for dtester in self.dtestmaster.dtesters:
                if dtester.isAlive():
                    time.sleep(1)
                else:                    
                    dtester.join()
                    self.logger.info("joined <"+ dtester.getName()+ ">.")
                    self.dtestmaster.joinedDTesters.add(dtester)                    
                    self.dtestmaster.runningDTesters -= 1;
                    dtester.session.close()
            # use the powerful difference_update on set
            # to continue looping on remaining (not already joined dtesters)
            self.dtestmaster.dtesters.difference_update(self.dtestmaster.joinedDTesters)
        if self.dtestmaster.timeout!=None:
            t.cancel()
        endTime = time.clock()
        noTimeOut = True
        for dtester in self.dtestmaster.joinedDTesters:
            if dtester.hasTimedOut:
                noTimeOut = False
                self.dtestmaster.traceManager.traceStepResult(False,"Tester <%s> did timeout" % dtester.getName())
                break;
        if noTimeOut:
            self.dtestmaster.traceManager.traceStepResult(True,"No Tester did timeout.")
    
class DTestMaster(object):
    """The master object which run and synchronize the different L{DTester}

    Each L{DTester} which wants to participate to the test should
    register itself in an instance of DTestMaster
    """
    
    class UnknownBarrierException(Exception):
        "Used when requesting an unknown barrier"
        
    class InvalidBarrierUsageException(Exception):
        "Your are misusing the barrier mechanism"
            
    # configure DTestMaster specific logger
    logger = logging.getLogger("DTestMaster")
    sh  = logging.StreamHandler()
    fmt = logging.Formatter(fmt="## [%(threadName)s]|%(name)s::%(levelname)s:: %(message)s")
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    def __init__(self, name=None, description=None):
        if name==None:
            self.__name="DTestMaster"
        else:
            self.__name=name
        if description==None:
            self.__description="None"
        else:
            self.__description=description
                       
        self.barriers     = {}
        self.dtesters     = set()
        self.startTime    = 0
        self.endTime      = 0
        self.runningDTesters = 0
        self.__nbSteps        = 0
        self.timeout         = None
        self.runner          = None

        #for execution trace
        #activate pseudo-execution mode
        self.__pseudoexec=0        

        # create and register a default TAP trace 
        self.traceManager = TraceManager()
        self.traceManager.registerTraceHandler(TAPTraceHandler())
        self.traceManager.newSequence(self)

    def __getNbSteps(self):
        return self.__nbSteps
    def __setNbSteps(self,nbSteps):
        self.__nbSteps = nbSteps
        
    nbSteps=property(fget=__getNbSteps,fset=__setNbSteps,doc='Number of steps in the DTest sequence')    

    def __getName(self):
        return self.__name
    name=property(fget=__getName,doc='DTest Sequence name')

    def __getDescription(self):
        return self.__description
    description=property(fget=__getDescription,doc='DTest Sequence description')
    
    def __getPseudoExec(self):
        return self.__pseudoexec    
    def __setPseudoExec(self,v):
        self.__pseudoexec=v
    pseudoexec=property(fget=__getPseudoExec,fset=__setPseudoExec,doc='pseudo-execution trace')
            
    def register(self, dtester):
        """Register the DTester dtester to this DTesMaster"""
        self.logger.info("Registering <" + dtester.getName() + ">...")
        # Add DTester to the set of DTester
        self.dtesters.add(dtester)
        # Link myself to the DTester
        # since DTester will call me back for ok, barrier etc...
        dtester.dtestmaster = self
        #self.registerForBarrier(dtester,"StartTest")
        #self.registerForBarrier(dtester,"EndTest")
        self.logger.info("<" + dtester.getName() + "> has registered.")

    def registerForBarrier(self, dtester, barrierId):
        """Add the DTester dtester for participating to the barrier barrierID"""
        self.logger.info("Barrier <"+ barrierId+ "> registered for DTester <"+ dtester.getName()+ ">")
        # automagically create barrier 'barrierId'
        if not self.barriers.has_key(barrierId):
            self.barriers[barrierId]= dict()
            self.barriers[barrierId]['init']    = set()
            self.barriers[barrierId]['reached'] = set()
            self.barriers[barrierId]['barrier'] = threading.Event()
        # verify the same DTester does not try to "re-use" the same barrier twice
        if dtester in self.barriers[barrierId]['init']:
            raise InvalidBarrierUsageException("Trying to reuse barrier <%s> for dtester <%s> twice (at least)" % (barrierId,dtester.getName()))
        else:
            self.barriers[barrierId]['init'].add(dtester)
            self.barriers[barrierId]['reached'].add(dtester)
               
    def ok(self, dtester, *args, **kwargs):
        """ok TAP-like method"""
        self.traceManager.traceStepResult(*args,**kwargs)
        return 0

    def globalTimeOutTriggered(self):
        self.logger.fatal("Global Time out triggered, exiting")
        for dtester in self.dtesters:
            dtester.abort()
        self.traceManager.finalizeSequence()
        # FIXME we should avoid exit for "multi sequence scenarii"
        os._exit(1)
        #sys.exit(1)
        
    def barrier(self, dtester, barrierId, timeout):
        """barrier DTest method"""
        # check whether the barrier has been registered
        # for execution trace
        self.traceManager.traceStep(dtester,self,(self.barrier,"('"+barrierId+"')",""))             
        if not self.barriers.has_key(barrierId):
            raise UnknownBarrierException, "barrier ID ="+barrierId
        try:
            self.barriers[barrierId]['reached'].remove(dtester)
        except KeyError:
            self.logger.warning("DTester <"+ dtester.getName()+ " does not belong to barrier.")
            return
        
        self.logger.info("DTester < "+ dtester.getName()+ "> entered barrier <" + barrierId + ">.")
        if len(self.barriers[barrierId]['reached']) == 0:
            self.traceManager.traceStepResult(True,desc="Barrier <%s> crossed by all <%d> registered DTester(s)" % (barrierId, len(self.barriers[barrierId]['init']))) 
            self.barriers[barrierId]['barrier'].set()
        else:
            self.barriers[barrierId]['barrier'].wait(timeout)
            if (not self.barriers[barrierId]['barrier'].isSet()):
                self.traceManager.traceStepResult(False,desc="Barrier <%s> timed-out for DTester <%s> waiting no more than <%f seconds>" % (barrierId,dtester.getName(),timeout))
                # re-add myself since I did timed-out
                self.barriers[barrierId]['reached'].add(dtester)
                # relieve other to cross the barrier.
                # FIXME is there a race condition on others which make them
                # FIXME believe they timed-out too??
                # NOT a real issue since barrier are one-shot
                # and a barrier failed if only 1 stakeholder missed it
                self.barriers[barrierId]['barrier'].set()
            else:
                self.logger.info("DTester < "+ dtester.getName()+ "> crossed barrier <" + barrierId + ">.")     
        

    def startTestSequence(self):
        """Start the test sequence"""
        # Initialize all registered dtesters
        for dtester in self.dtesters:
            self.logger.info("Initializing <"+ dtester.getName()+ ">...")
            try:
                dtester.initialize()
            except (UnknownBarrier,InvalidBarrierUsage), err:
                self.logger.error("%s : %s" % (err.__class__,err))                
                return
            self.nbSteps += dtester.nbSteps
        self.logger.debug("Defined %d barriers" % len(self.barriers))
        # each barrier step will generate an ok step
        self.nbSteps += len(self.barriers)        
        # We add a final step for consolidated timeout
        self.nbSteps += 1;
        self.traceManager.initializeSequence() 
        self.runner = DTestMasterRunner(self)
        self.runner.start()

    def waitTestSequenceEnd(self):
        """Wait for the test sequence ending"""
        # join the sequence runner
        self.runner.join()
        # finalize trace 
        self.traceManager.finalizeSequence()        
