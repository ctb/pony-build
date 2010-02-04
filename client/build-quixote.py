#! /usr/bin/env python
import sys
import pprint
from pony_client import BuildCommand, TestCommand, do, send, \
     TempDirectoryContext, SetupCommand, GitClone, check, parse_cmdline, \
     PythonPackageEgg

options, args = parse_cmdline()

python_exe = 'python2.5'
if args:
    python_exe = args[0]

repo_url = 'git://quixote.ca/quixote'

tags = [python_exe]
name = 'quixote'

server_url = options.server_url

if not options.force_build:
    if not check(name, server_url, tags=tags):
        print 'check build says no need to build; bye'
        sys.exit(0)

context = TempDirectoryContext()
commands = [ GitClone(repo_url, name='checkout'),
             BuildCommand([python_exe, 'setup.py', 'install'],
                          name='compile')]#,
             #PythonPackageEgg(python_exe)]

results = do(name, commands, context=context)
client_info, reslist, files = results

if options.report:
    print 'result: %s; sending' % (client_info['success'],)
    #send(server_url, results, tags=tags)
    send("http://localhost:8080/xmlrpc", results, tags=tags)
else:
    print 'build result:'
    pprint.pprint(client_info)
    pprint.pprint(reslist)
    
    print '(NOT SENDING BUILD RESULT TO SERVER)'

if not client_info['success']:
    sys.exit(-1)
