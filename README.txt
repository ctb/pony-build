==========
pony-build
==========

pony-build is a simple continuous integration package that lets you
run a server to display client build results.  It consists of two
components, a server (which is run in some central & accessible
location), and one or more clients (which must be able to contact the
server via HTTP).

Philosophy statement: good development tools for Python should be easy
to install, easy to hack, and not overly constraining.  Two out of
three ain't bad ;).

The pony-build architectural model is this: use decoupled components
that communicate via webhooks whenever possible.

Also see `buildbot <http://buildbot.sf.net/>`__.

Links
=====

pony-build is hosted on github.

pony-build central repository: http://github.com/ctb/pony-build

pony-build issue tracking: http://github.com/ctb/pony-build/issues

pony-build wiki: http://wiki.github.com/ctb/pony-build

pony-build mailing list: http://lists.idyll.org/listinfo/pony-build

Requirements
============

Server side:
  Requires Python 2.6 or above.

  Jinja2 (easy_installable).

  For the Quixote Web UI, Quixote 2.6 (also easy_installable).

Client side:
  Python.  Should work down to Python 2.4.  Developed with 2.5.

pony-build server
=================

The command: ::

   python -m pony_build.web.run <shelve filename> -p <port>

will run the Quixote-based pony-build Web app on the given port,
reading & writing from the sqlite database in 'filename'.

For example, ::

   python -m pony_build.web.run test.db -p 8080

will run a server that can be accessed on http://localhost:8080/.  This
server will report on whatever results are sent to it by the client (see
below), based on the package name ('name', below).

See 'architecture, and extending pony-build', below.

pony-build client scripts
=========================

Build scripts
--------------

Client build scripts are just scripts that set up & run a list of commands: ::

  from pony_client import BuildCommand, TestCommand, do, send

  name = 'example'
  server_url = 'http://localhost:8080/xmlrpc'

  commands = [ BuildCommand(['/bin/echo', 'hello, world'], name='step 1'),
               TestCommand(['/bin/echo', 'this is a test'], name='step 2')
               ]

  results = do('package', commands)
  send('http://localhost:8080/xmlrpc', results)

Client results are communicated to the server by XML-RPC, so the client
must be able to reach the server via the HTTP protocol.

See ``client/build-cpython`` for an example of building a Subversion-based
C project (checkout, configure, make, run tests).

See ``client/build-pony-build`` for an example of building a Git-based
Python project (clone, build, run tests).

Note that 'pony_client' doesn't depend on the rest of pony-build, so you
can distribute it with other packages if you want.

Client query scripts
--------------------

Client query scripts request information from the server.  For example,
see 'bin/notify-failure-email', which checks the status of the last build
of a particular package and sends an e-mail.

Architecture, and extending pony-build
======================================

The pony-build server is basically a storage receptacle for "bags" of
key-value pairs.  It's easiest point of extension is in the Web
interface, where you can substitute any WSGI app object to serve Web
pages; see 'bin/run-server', and the function call to
'server.create(...)' (aka pony_build.server.create(...)'.

To write a new Web UI, you will need access to the stored pony-build
server data.  You should work through the 'PonyBuildCoordinator'
interface in 'pony_build.coordinator'; you can get a handle to the
current coordinator object with 'pony_build.server.get_coordinator()'.
**The coordinator API is will be stable and public**, after suitable
evolution.

Client-to-server communication
------------------------------

Each client sends two bags of information: the first, 'client_info',
contains information global to the build client, such as package name,
host name, architecture, and a list of tags.  The second,
'results_list', is an ordered list of dictionaries, each one
representing a build step.  (The default contents of these dictionaries
are pretty obvious: status, stderr, stdout, etc.)  Upon receipt of
this info, the pony-build server creates a third object, a dictionary,
containing information such as the server time at which the result
was received, 

These three bags of info -- 'receipt', 'client_info', and
'results_list' -- are it.  The coordinator functions give you ways to
slice and dice which results set you want (e.g. latest for a
particular package), and then usually return one or more triples of
(receipt, client_info, results_list).

Clients can send arbitrary key/value pairs in their "bags"; two
simple ways to extend things are to add new k/v pairs for specific
purposes, and/or to use the 'tags' key in the client_info dict.
The 'tags' associated value is a list of strings.

receipt['result_key'] is the internal key used to store the result.

Notifications
-------------

RSS2 and pubsubhubbub (http://code.google.com/p/pubsubhubbub/) are the
core of the notification system built into pony_build; the "officially
correct" way to actively notify interested people of build results is
to publish them via RSS2, push them to a pubsubhubbub server, and let
someone else deal with translating those into e-mail alerts, etc.

All of the RSS feeds that pony-build makes available can be posted to
pubsubhubbub with the proper configuration (see -P and -S options to
``pony_build.web.run``).  A simple example CGI callback script that
sends an e-mail is available in
``examples/push-cgi/notifier/push-subscriber.cgi`` in the pony-build
source distribution.

Note that there are also utility functions in ``pony_build.rss`` for
helping to create RSS2 feeds and notify pubsubhubbub servers of
new results

Some medium-term ideas
======================

One an initial release is out & any obvious bugs are cleaned up, here
are some ideas for the next release.

A flexible view builder-and-saver would be nice; maybe in Django?
Think, "separate results on this tag, etc; sort by time received;
expect these results to be shown or give an error."

It would be nice to be able to say "I *expect* a result from this
buildhost, where is it!?"

The build client 'subprocess' calls should be able to mimic 'tee',
that is, give real-time output of the build.

Some form of authentication from build clients.  Josh Williams
suggests an approved client list (server side info about what clients
can conenect); I'd been thinking about a buildbot-style password setup,
where build clients shared a secret with the server.  Both ideas are
good, I think.

In combination with authentication, we should put a default cap on the
total amount of data that can be dumped by an unauthenticated client.
Otherwise warez sites will be hosted inside of pony-build ;)

Development
===========

pony-build is hosted on github, at: http://github.com/ctb/pony-build

To run the server tests::

   python -m pony_build.tests.run

To run the client tests::

   cd client
   nosetests

Design and Ideas for the Future
===============================

Ideas that are easy to implement
--------------------------------

Build virtualenv in on the client side (as a Context?)

Dependency chains example on client side.

Integration with unittest, nose, py.test -> ship results back to
central server.

Cleanup
-------

Figure out a proper database abstraction, maybe?

Tests, duh.

Things I don't know how to do...
--------------------------------

...and don't want to spend time learning ;)

Josh Williams suggests supporting something other than a wsgiref
server.  I'm not sure this is really needed -- you can run whatever
WSGI app you want inside the server -- but I can see that it would
make things more flexible for people with existing Web server setups.
I think the way to do this is to make pony-build's (XML-RPC + WSGI
app) interace look like its own WSGI app, rather than hacking
SimpleXMLRPCServer and wsgiref together in an unholy union.  Ping me
for details if you dare.

Seriously, check out both pony_build.server.PonyBuildServer and
pony_build.server.RequestHandler (the latter is the most interesting).

Some general design principles
------------------------------

Titus says: A number of people are interested in pony-build, and I've
gotten many suggestions already.  This has basically forced me to
articulate a number of my design principles, including some that were
made un- or subconsciously, and/or just enshrined in my prototype
code.  I may change some of these decisions for v2, but I'd just as
soon let buildbot pick up the higher-end ideas if they're game, too.

 - All client/server interactions should be via RPC, and hence
   transactional.  No always-on connections, no real-time control by
   the central server.

   This is a major simplification and makes it possible to keep the
   code base small and simple.  Yay.

 - No partial results.  Doug Phillips ('dgou') suggested that we allow
   build clients to "push" individual results as they happen, rather
   than all at once at the end.  I can't think of a good, simple way
   to do that, and it's part of the 20% that I don't yet need myself.

   Here's a proposal that I think would work, from Doug: ::

     send "create new record, marked unfinished"
     receive "record marker, update token"
     send "first results, authenticate with update token"
     receive "ack"
     send "2nd results, authenticate with update token"
     receive "ack"
     ...
     send "final results, authenticate with update token"
     receive "ack"
   
Contributors
------------

Jacob Kaplan-Moss, Max Laite, Jack Carlson, Fatima Cherkaoui, and Khushboo
Shakya have all contributed code and ideas.

(If I'm missing anyone, please drop me a note!)

Acks
----

Titus says: Jesse Noller, Doug Philips, and Josh Williams discussed
things with me and are, collectively, entirely responsible for any bad
design decisions; the good ones are all mine.

Seriously, I appreciate the suggestions and comments from these fine
people, even though Doug has been a jerk to me since then.

Eric Henry built what I would consider 'pony-build prototype 1',
project-builder-pie.

You can also read this discussion starting here,

  http://lists.idyll.org/pipermail/testing-in-python/2009-March/001277.html

where Kumar suggests that I just use Hudson for chrissakes.  He's
probably right.

Eric Holscher and Jacob Kaplan-Moss took the pony-build idea and ran
with it, producing a parallel universe of Django-based reporting
servers and REST-ish clients that report via JSON.  Check out
devmason.com and 'pony_barn' to see their approach in action.

References
----------

webhooks: http://webhooks.pbworks.com/

--

CTB 2/24/10
