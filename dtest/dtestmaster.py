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

import TAP
import threading
from threading import Thread
from dtester import DTester
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
    
class DTestMaster(Thread):
    """The master object which run and synchronize the differents L{DTester}

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
    def __init__(self, name=None):
        if name==None:
            super(DTestMaster,self).__init__(name="DTestMaster")
        else:
            super(DTestMaster,self).__init__(name="DTestMaster-"+name+"-")
        self.__builder   = TAP.Builder.create()
        self.barriers  = {}
        self.dtesters  = set()
        self.startTime = 0
        self.endTime   = 0
        self.runningDTesters = 0
        self.nb_steps  = 0
        self.timeout   = None
        #for execution trace
        #activate pseudoexecution mode
        self.pseudoexec=0
        #activate tracing mode
        self.trace=0
        #a queue for globally ordering execution steps
        self.global_execution_steps_queue = Queue(0)

    def setTrace(self,val):
        self.trace=val
            
    def setPseudoExec(self,val):
        self.pseudoexec=val
            
    def getTrace(self):
        return self.trace
           
    def getPseudoExec(self):
        return self.pseudoexec
        
    def traceStep(self,source,destination,step):
        """Add an execution trace step to the execution steps queue to order them all"""
        self.global_execution_steps_queue.put((source,destination,step))

    def mscGenerator(self):
        """We generate message sequence chart diagram from the execution steps enqueued"""
        #for the online msc generator http://websequencediagrams.com/ , it places DTestmaster always on the left of the diagram
        print "entity "+self.getName()
        #we represent each step for msc diagram generation, we represent fully only "ok" and "barrier" steps
        while not self.global_execution_steps_queue.empty():
            line=self.global_execution_steps_queue.get()
            src=line[0]
            dest=line[1]
            step=line[2]
            methodName=step[0].__name__
            firstArg=str(step[1])
            firstArg = str.replace(firstArg,",","")
            secondArg=""
            #secondArg=str(step[2])
            #secondArg=str.replace(secondArg,"{","")
            #secondArg=str.replace(secondArg,"}","")
            #for the online msc generator http://websequencediagrams.com/ 
            mscline=src+"->"+dest+":"+methodName+firstArg+secondArg
            #mscline=src+"=>"+dest+ "[label=\""+methodName+firstArg+secondArg+"\"]"
            print mscline
        
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
        """ok TAP method"""
        self.__builder.ok(*args,**kwargs)
        return 0

    def __globalTimeOutTriggered(self):
        self.logger.fatal("Global Time out triggered, exiting")
        for dtester in self.dtesters:
            dtester.abort()
        os._exit(1)
        #sys.exit(1)
        
    def barrier(self, dtester, barrierId, timeout):
        """barrier DTest method"""
        # check whether the barrier has been registered
        #for execution trace 
        if ( self.trace ):
            self.traceStep(dtester.getName(),self.getName(),(self.barrier,"('"+barrierId+"')",""))
        if not self.barriers.has_key(barrierId):
            raise UnknownBarrierException, "barrier ID ="+barrierId
        try:
            self.barriers[barrierId]['reached'].remove(dtester)
        except KeyError:
            self.logger.warning("DTester <"+ dtester.getName()+ " does not belong to barrier.")
            return
        
        self.logger.info("DTester < "+ dtester.getName()+ "> entered barrier <" + barrierId + ">.")
        if len(self.barriers[barrierId]['reached']) == 0:
            self.__builder.ok(True,desc="Barrier <%s> crossed by all <%d> registered DTester(s)" % (barrierId, len(self.barriers[barrierId]['init']))) 
            self.barriers[barrierId]['barrier'].set()
        else:
            self.barriers[barrierId]['barrier'].wait(timeout)
            if (not self.barriers[barrierId]['barrier'].isSet()):
                self.__builder.ok(False,desc="Barrier <%s> timed-out for DTester <%s> waiting no more than <%f seconds>" % (barrierId,dtester.getName(),timeout))
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

    def run(self):
        """Run thread method"""
        self.startTime = time.clock()
        # set up global time out
        if self.timeout != None:
            t = threading.Timer(self.timeout,self.__globalTimeOutTriggered)
            t.start()
        # Initialize all registered dtesters
        for dtester in self.dtesters:
            self.logger.info("Initializing <"+ dtester.getName()+ ">...")
            try:
                dtester.initialize()
            except (UnknownBarrier,InvalidBarrierUsage), err:
                self.logger.error("%s : %s" % (err.__class__,err))
                t.cancel()
                return
            self.nb_steps += dtester.nb_steps
        self.logger.debug("Defined %d barriers" % len(self.barriers))
        self.nb_steps += len(self.barriers)
        # plan test 
        self.__builder.set_plan(self.nb_steps, None)
        # Start all registered dtesters
        for dtester in self.dtesters:
            self.logger.info("Starting <"+ dtester.getName()+ ">...")
            dtester.start()
            self.runningDTesters += 1
        self.logger.info("Now <%d> registered DTesters launched.",self.runningDTesters)
        # Wait for DTesters to terminate
        self.joinedDTesters = set()
        while self.runningDTesters > 0:
            for dtester in self.dtesters:
                if dtester.isAlive():
                    time.sleep(1)
                else:                    
                    dtester.join()
                    self.logger.info("joined <"+ dtester.getName()+ ">.")
                    self.joinedDTesters.add(dtester)                    
                    self.runningDTesters -= 1;
            # use the powerful difference_update on set
            # to continue looping on remaining (not already joined dtesters)
            self.dtesters.difference_update(self.joinedDTesters)
        if self.timeout !=None:
            t.cancel()
        endTime = time.clock()   

    def startTestSequence(self):
        """Start the test sequence"""
        self.start()

    def waitTestSequenceEnd(self):
        """Wait for the test sequence ending"""
        self.join()
        #execution trace 
        if (self.trace):
            self.mscGenerator()
