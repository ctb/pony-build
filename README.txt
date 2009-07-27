==========
pony-build
==========

pony-build server
=================

The command: ::

   python bin/run-server <shelve filename> <port>

will run the pony-build server on the given port, reading & writing from the
shelve database in 'filename'.

For example,

   python bin/run-server test.db 8080

will run a server that can be accessed on http://localhost:8080/.

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
