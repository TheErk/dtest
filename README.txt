
DTest for busy people:
---------------------

If you want to tests dtest (not kidding :)))

tar zxvf dtest-0.x.tar.gz
cd dtest-0.x
export PYTHONPATH=`pwd`
tests/dtest-autotest


This the DTest source release
-----------------------------

0) If you want to install dtest you'll have to do
   python setup.py install

   Note that dtest requires some third-party python modules:
        pytap    [required]
        paramiko [required]
	pycrypto [required by paramiko]
 
   see dtest/external/where_dtest_external.txt
   for having the URLs of the previous packages

0bis) You may want to "only" try dtest without installing it 
      then go to "DTest for busy people" above in this file

1) If you want to build the source package you may run:

   python setup.py sdist

2) If you want to install dtest

   python setup.py install

3) If you want to generate the documentation using epydoc

   1.a) Do a simple check 
        epydoc --check dtest
  
   1.b) Generate HTML output
        epydoc --html -o docs/html dtest

4) If you need to run the autotests for dtest you may run:
   
   dtest-autotest
   dtest-sshtest
   dtest-tracetest
   dtest_md5.py
