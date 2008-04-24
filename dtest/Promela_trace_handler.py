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

class PromelaTraceHandler (TraceHandler):
    """Represents a DTest TAP trace handler.

    A DTest Test Anything Protocol (TAP) trace handler 
    """

    logger = logging.getLogger("PromelaTraceHandler")
    
    def __init__(self,outputFile=sys.__stdout__):
        super(PromelaTraceHandler,self).__init__("PromelaTraceHandler")
        self.output = TraceHandler.getFileOrOpenPath(output,ext=".pml")  
           
    def newSequence(self, dtestmaster):
        self.logger.info("Registering Test Sequence <" + dtestmaster.name + ">...")
        self.dtestmaster  = dtestmaster
        #a queue for globally ordering execution steps from DTester threads
        self.__global_execution_steps_queue = Queue(0)
        #the list of steps building from global_execution_steps_queue
        self.__execution_steps_list = []

    def initializeSequence(self):
        """ Initialize sequence for every trace trace handler
        This gives a chance for the handler to build a header
        """
        self.logger.info("Current sequence has <%d> DTesters." % self.dtesters.__len__())
        self.builder.set_plan(self.dtestmaster.nbSteps, None)

    def finalizeSequence(self):
        while not self.global_execution_steps_queue.empty():
            line=self.global_execution_steps_queue.get()
            self.__execution_steps_list.append(line) 
        
    def traceStep(self,srcDTester,dstDTester,step):
        self.global_execution_steps_queue.put((srcDTester,dstDTester,step))            
    
    def traceStepResult(self,ok_nok,desc,skip,todo):
        pass
    
    def traceStepComment(self,comment):
        pass

    def finalize(self):        
        TraceHandler.closeIfNotStdout(self.output)
        
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
            __nbSteps=0
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
                        lines.append("\t"+methodName+"_"+str(__nbSteps)+":printf(\""+methodName+"_"+str(__nbSteps)+"\");\n\n")
                else:
                #other steps
                    lines.append("\t"+methodName+"_"+str(__nbSteps)+":printf(\""+methodName+"_"+str(__nbSteps)+"\");\n\n")
                __nbSteps+=1
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
