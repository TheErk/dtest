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
from trace_manager import TraceManager
from trace_handler import TraceHandler
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
        # Initialize all registered dtesters
        for dtester in self.dtestmaster.dtesters:
            self.logger.info("Initializing <"+ dtester.getName()+ ">...")
            try:
                dtester.initialize()
            except (UnknownBarrier,InvalidBarrierUsage), err:
                self.logger.error("%s : %s" % (err.__class__,err))
                t.cancel()
                return
            self.dtestmaster.nb_steps += dtester.nb_steps
        self.logger.debug("Defined %d barriers" % len(self.dtestmaster.barriers))
        self.dtestmaster.nb_steps += len(self.dtestmaster.barriers)
        # plan test 
        # We add a final step for consolidated timeout
        self.dtestmaster.builder.set_plan(self.dtestmaster.nb_steps+1, None)
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
                self.dtestmaster.builder.ok(False,"Tester <%s> did timeout" % dtester.getName())
                break;
        if noTimeOut:
            self.dtestmaster.builder.ok(True,"No Tester did timeout.")
    
class DTestMaster():
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
    def __init__(self, name=None, description=None):
        if name==None:
            self.__name="DTestMaster"
        else:
            self.__name=name
        if description==None:
            self.__description=""
        else:
            self.__description=description
               
        self.builder      = TAP.Builder.create()
        self.barriers     = {}
        self.dtesters     = set()
        self.startTime    = 0
        self.endTime      = 0
        self.runningDTesters = 0
        self.nb_steps        = 0
        self.timeout         = None
        self.runner          = None

        #for execution trace
        #activate pseudoexecution mode
        self.__pseudoexec=0
        #activate tracing mode
        self.__trace=0
        #a queue for globally ordering execution steps from DTester threads
        self.global_execution_steps_queue = Queue(0)
        #the list of steps building from global_execution_steps_queue
        self.__execution_steps_list = []

        # create and register a default TAP trace 
        self.traceManager = TraceManager()
        self.traceManager.registerTraceHandler(TraceHandler())
        self.traceManager.newSequence(self)

    def __getName(self):
        return self.__name
    name=property(fget=__getName,doc='sequence name')

    def __getDescription(self):
        return self.__description
    description=property(fget=__getDescription,doc='sequence description')
        
    def __getTrace(self):
        return self.__trace
    def __setTrace(self,v):
        self.__trace=v
    trace=property(fget=__getTrace,fset=__setTrace,doc='execution trace')
    
    def __getPseudoExec(self):
        return self.__pseudoexec    
    def __setPseudoExec(self,v):
        self.__pseudoexec=v
    pseudoexec=property(fget=__getPseudoExec,fset=__setPseudoExec,doc='pseudo-execution trace')
    
#    def __getExecutionStepsQueue(self):
#            return self.global_execution_steps_queue
#    global_execution_steps_queue=property(fget=__getglobal_execution_steps_queue,doc='execution steps queue')
    
    def buildStepSequenceList(self):
        while not self.global_execution_steps_queue.empty():
            line=self.global_execution_steps_queue.get()
            self.__execution_steps_list.append(line) 
    
    def traceStep(self,source,destination,step):
        """Add an execution trace step to the execution steps queue to order them all"""
        self.global_execution_steps_queue.put((source,destination,step))

    def mscGenerator(self):
        """We generate message sequence chart diagram from the execution steps enqueued"""
        f=open("execution_trace.msc","w")
        f.write("entity "+self.getName()+'\n')
        #we represent each step for msc diagram generation, we represent fully only "ok" and "barrier" steps
        for line in self.__execution_steps_list:
            src=line[0]
            dest=line[1]
            step=line[2]
            methodName=step[0].__name__
            firstArg=str(step[1])
            firstArg = str.replace(firstArg,",","")
            secondArg=""
            #for the online msc generator http://websequencediagrams.com/ 
            mscline=src+"->"+dest+":"+methodName+firstArg+secondArg
            f.write(mscline+'\n')
        f.close()
        print "MSC execution trace generated in execution_trace.msc"

    def promelaGenerator(self):
        """We generate promela code from the execution steps list"""
        testers_steps={}
        lines=[]
        barriername_list=[]
        lines.append("/*type of message*/\n") 
        lines.append("mtype = {a};\n\n")      
        
        #finding testers name
        for tester in self.joinedDTesters:
            testers_steps[tester.name]=[]
        testers_steps[self.getName()]=[]
        
        #we group execution steps by tester
        for line in self.__execution_steps_list:
            src=line[0]
            testers_steps[src].append(line)
    
        #building promela instructions        
        for k in testers_steps.keys():
            lines.append("proctype "+k+"()\n{\n\n")
            nb_steps=0
            if (len(testers_steps[k])==0):
               lines.append("\tskip;\n")
            for l in testers_steps[k]:
                src=l[0]
                dest=l[1]
                step=l[2]
                methodName=step[0].__name__
                firstArg=str(step[1])
                firstArg = str.replace(firstArg,"('","")
                firstArg = str.replace(firstArg,"')","")
                barrierKey = str.replace(firstArg,"',)","")
                barrierName = str.replace(barrierKey,"(","")
                barrierName = str.replace(barrierName,")","")
                barrierName = str.replace(barrierName," ","_")          
                if(methodName=="barrier"):
                #handling barrier step
                    if barrierName not in barriername_list:
                        barriername_list.append(barrierName)
                    if src!=dest:
                        #lines.append("\t"+methodName+"_"+barriername+"_"+src+"!a;\n\n")
                        lines.append("\t"+barrierName+" = "+barrierName+" + 1 ;\n\n")
                        lines.append("\t("+barrierName+"=="+str(len(self.barriers[barrierKey]["init"]))+");\n\n")  
                    #self barrier step:                     
                    else:
                        lines.append("\t"+methodName+"_"+str(nb_steps)+":printf(\""+methodName+"_"+str(nb_steps)+"\");\n\n")
                else:
                #other steps
                    lines.append("\t"+methodName+"_"+str(nb_steps)+":printf(\""+methodName+"_"+str(nb_steps)+"\");\n\n")
                nb_steps+=1
            lines.append("}\n\n")
        
        promela_file=open("execution_trace.pml","w")
        #adding channel declaration for barrier
        #promela_file.write("/*chan declaration for barrier*/\n")
        #for b in barriername_list:
            #promela_file.write("chan barrier"+b+" = [1] of { byte } ;\n\n")
        #adding barrier counter declaration
        promela_file.write("/*barrier counter declaration*/\n")
        for b in barriername_list:
            promela_file.write("byte "+b+";\n\n")
        for line in lines:
           promela_file.write(line)
        #initializing barriers
        promela_file.write("init \n{\n")
        for b in barriername_list:
            promela_file.write("\t"+b+" = 0;\n")
        promela_file.write("atomic {\n")
        #atomicly launching processes
        for key in testers_steps.keys():
            promela_file.write("\trun "+key+"();\n")
        promela_file.write("\t}\n")
        promela_file.write("}\n")
        promela_file.close()
        print "Promela execution generated in execution_trace.pml"     

        #declaration du type de message - ok
        #declaration compteur de barrieres - ok
        #declaration canaux barriere - ok
        #gestion des barrieres - ok
        #declaration des canaux - ok
        #creation des proctypes - ok
        #grouper les pas d'execution par proctype - ok
        #transformation de chaque pas self en etiquette numerotee - ok
        #initialisation des compteurs - ok
        #lancement de chaque processus - ok
        
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
        self.builder.ok(*args,**kwargs)
        return 0

    def globalTimeOutTriggered(self):
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
            self.builder.ok(True,desc="Barrier <%s> crossed by all <%d> registered DTester(s)" % (barrierId, len(self.barriers[barrierId]['init']))) 
            self.barriers[barrierId]['barrier'].set()
        else:
            self.barriers[barrierId]['barrier'].wait(timeout)
            if (not self.barriers[barrierId]['barrier'].isSet()):
                self.builder.ok(False,desc="Barrier <%s> timed-out for DTester <%s> waiting no more than <%f seconds>" % (barrierId,dtester.getName(),timeout))
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
        self.runner = DTestMasterRunner(self)
        self.runner.start()

    def waitTestSequenceEnd(self):
        """Wait for the test sequence ending"""
        self.runner.join()
        #execution trace 
        if (self.trace):
            self.buildStepSequenceList()
            #print self.__execution_steps_list
            self.mscGenerator()
            self.promelaGenerator()
