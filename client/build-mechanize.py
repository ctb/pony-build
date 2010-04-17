#! /usr/bin/env python
import sys
import pprint
from pony_client import BuildCommand, TestCommand, do, send, \
     TempDirectoryContext, SetupCommand, SvnCheckout, check, parse_cmdline

options, args = parse_cmdline()
if args:
    print 'ignoring command line args: ', args

repo_url = 'http://wwwsearch.sourceforge.net/mechanize/src/mechanize-0.1.11.tar.gz'

python_exe = 'python'
if args:
    python_exe = args[0]

name = 'mechanize'
tags = ['mechanize']
server_url = options.server_url

if not options.force_build:
    if not check(name, server_url, tags=tags):
        print 'check build says no need to build; bye'
        sys.exit(0)

commands = [ SvnCheckout('mechanize', repo_url, name='checkout'),
             BuildCommand([python_exe, 'setup.py', 'test'])
             ]

context = TempDirectoryContext()
results = do(name, commands, context=context)
client_info, reslist, files = results

if options.report:
    print 'result: %s; sending' % (client_info['success'],)
    send(server_url, results, tags=tags)
else:
    print 'build result:'
    pprint.pprint(client_info)
    pprint.pprint(reslist)
    
    print '(NOT SENDING BUILD RESULT TO SERVER)'

if not client_info['success']:
    sys.exit(-1)
