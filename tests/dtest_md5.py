#!/usr/bin/env python

##-----------------------------------------------------------------------
##
## DTest - A Distributed test framework
##
## Copyright (c) 2006-2008 Lionel DUROYON
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
import dtest
import time
import logging
import os
import filecmp
import getopt,sys

def getDir(s):
    spl=s .split('/')
    di=""
    for elem in spl[0:len(spl)-1]:
        if (elem.isalnum()):
            di+="/"+elem
    di+="/"
    return di
    
def usage():
    print "Usage:\n %s  --source=user@host:sourceFile --destination=user@host:destinationFile" % sys.argv[0]

def getUserHostPath(argument):
    if argument.find("@") != -1:
        (user,argument) = argument.split("@",1)
    else:
        user = os.environ["USER"]
    if argument.find(":") != -1:
        (host,fich) = argument.split(":",1)
    else:
        host = "localhost"
        fich = argument
    retval = dict()
    retval['user'] = user
    retval['host'] = host
    retval['fich'] = fich
    return retval

try:
    opts, args = getopt.getopt(sys.argv[1:], "s:d", ["source=","destination="])
    print opts,args
except getopt.GetoptError, err:
    print >> sys.stderr, "opt = %s, msg = %s" % (err.opt,err.msg)
    usage()
    sys.exit(2)

if len(opts)<2:
    usage()
    sys.exit(2)

for o, a in opts:
    if o in ("-s", "--source"):
        source_param   = getUserHostPath(a)
    if o in ("-d", "--destination"):
        dest_param = getUserHostPath(a)

#setting host and users for ssh connections 
file1=source_param['user']+"@"+source_param['host']+":"+source_param['fich']  
resultfile1=source_param['fich']+"_result"

file2=dest_param['user']+"@"+dest_param['host']+":"+dest_param['fich']
resultfile2=dest_param['fich']+"_result"

md5scriptname="md5sum.py"
md5command1=getDir(source_param['fich'])+md5scriptname+" "+source_param['fich']+" "+resultfile1
md5command2=getDir(dest_param['fich'])+md5scriptname+" "+dest_param['fich']+" "+resultfile2
   
# Create as many DTester as you need
tester1     = dtest.DTester("tester1",session=dtest.SSHSessionHandler(source_param['user'],source_param['host']))
tester2     = dtest.DTester("tester2",session=dtest.SSHSessionHandler(dest_param['user'],dest_param['host']))

# Setting up output files
tester1.stdout = file(tester1.name+".out",'w+')
tester1.stderr = file(tester1.name+".err",'w+')
tester1.stdin = file(tester1.name+".in",'w+')

tester2.stdout = file(tester2.name+".out",'w+')
tester2.stderr = file(tester2.name+".err",'w+')
tester2.stdin = file(tester2.name+".in",'w+')

#The goal of this script is to easily illustrate the functionnalities of dtest with a simple example
#so here we want to assure that a file has been correctly copied from a computer source_param['host'] to a computer dest_param['host']
#to do that, we want to compare the md5sum of the original file on server A to the md5sum of the copied file on server B
#we suppose that python is installed on server A and B

#tester1 steps
tester1.addRunStep("ok",True,skip="%s starting, source file : %s"%(tester1.name,file1))
#1/put md5script on server A
tester1.addRunStep("putFile",md5scriptname,getDir(source_param['fich'])+md5scriptname)
tester1.addRunStep("runCommand",command="chmod +x "+getDir(source_param['fich'])+md5scriptname)
#2/generate md5sum of source file
tester1.addRunStep("runCommand",command="%s"%(md5command1))
tester1.addRunStep("expectFromCommand",pattern="md5done")
#3/get source file from server A
tester1.addRunStep("getFile",source_param['fich'],"source_file")
#4/get md5sum from server A
tester1.addRunStep("getFile",resultfile1,"res1")
tester1.addRunStep("barrier","source getted")
tester1.addRunStep("terminateCommand")
tester1.addRunStep("waitCommandTermination")
#we check that diff result on standard output is like "same files"
tester1.addRunStep("ok",True,skip="%s has finished"%tester1.name)

#tester2 steps
tester2.addRunStep("ok",True,skip="%s starting, destination file : %s"%(tester2.name,file2))
#5/put md5script on server B
tester2.addRunStep("putFile",md5scriptname,getDir(dest_param['fich'])+md5scriptname)
tester2.addRunStep("runCommand",command="chmod +x "+getDir(dest_param['fich'])+md5scriptname)
tester2.addRunStep("barrier","source getted")
#6/put source file on server B (becoming dest file)
tester2.addRunStep("putFile","source_file",dest_param['fich'])
#7/generate md5sum on server B
tester2.addRunStep("runCommand",command="%s"%(md5command2))
tester2.addRunStep("expectFromCommand",pattern="md5done")
#8/get md5sum from server B
tester2.addRunStep("getFile",resultfile2,"res2")
tester2.addRunStep("terminateCommand")
tester2.addRunStep("waitCommandTermination")
#9/compare res1 and res2
def compareFiles(dtester):
    dtester.ok(filecmp.cmp("res1","res2"),"Compare res1 with res2")
tester2.addRunStep(compareFiles)
tester2.nb_steps += 1

# Here begins the test
dtest.DTestMaster.logger.setLevel(level=logging.WARNING)
dtest.DTester.logger.setLevel(level=logging.WARNING)
dtest.SSHSessionHandler.logger.setLevel(level=logging.WARNING)

myDTestMaster = dtest.DTestMaster()
myDTestMaster.setTrace(1)
#register dtesters in DTestMaster
myDTestMaster.register(tester1)
myDTestMaster.register(tester2)
myDTestMaster.startTestSequence()
myDTestMaster.waitTestSequenceEnd()

#####################################################################################################################################################
#WARNING : you may have to adapt the script to your remote host, for example if the remote host asks you which terminal you want at session starting
#####################################################################################################################################################

#example of script launching
#./dtest_md5.py --source=lduroyon@lanoux:/udd/deri/lduroyon/MD5/fichtest --destination=lduroyon@lanoux:/udd/deri/lduroyon/Desktop/OLD/fichtestcopie

