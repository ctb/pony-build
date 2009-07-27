==========
pony-build
==========

pony-build is a simple continuous integration package that lets you
run a server to display client build results.  It consists of two
components, a server (which is run in some central & accessible
location), and one or more clients (which must be able to contact the
server via HTTP).

pony-build server
=================

The command: ::

   python bin/run-server <shelve filename> <port>

will run the pony-build server on the given port, reading & writing from the
shelve database in 'filename'.

For example, ::

   python bin/run-server test.db 8080

will run a server that can be accessed on http://localhost:8080/.  This
server will report on whatever results are sent to it by the client (see
below), based on the package name ('name', below).

pony-build client scripts
=========================

Clients are just scripts that set up & run a list of commands: ::

  from pony_build_client import BuildCommand, TestCommand, do, send

  name = 'example'
  server_url = 'http://localhost:8080/xmlrpc'

  commands = [ BuildCommand(['/bin/echo', 'hello, world'], name='step 1'),
               TestCommand(['/bin/echo', 'this is a test'], name='step 2')
               ]

  results = do('package_name', commands)
  send('http://localhost:8080/xmlrpc', results)

Client results are communicated to the server by XML-RPC, so the client
must be able to reach the server via the HTTP protocol.

--

CTB 7/27/09
