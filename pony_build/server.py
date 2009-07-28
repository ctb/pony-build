"""
A combined XML-RPC + WSGI server for pony-build, based on wsgiref.

This is a hacked implementation that combines SimpleXMLRPCServer with
a wsgiref WSGIServer, redirecting all requests to '/xmlrpc' into
SimpleXMLRPCServer and letting wsgiref pass the rest on to a WSGI
application.

One nice feature of this is that you can swap out the Web UI
completely without affecting the RPC functionality; and, since all of
the RPC functionality and data handling is in the PonyBuildCoordinator
class (see 'coordinator.py') you can just write a new Web UI around
that internal interface.
"""
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, \
     SimpleXMLRPCDispatcher
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, \
     ServerHandler

client_ip = None
_coordinator = None
def add_results(client_info, results):
    # client_info is a dictionary of client information
    # results is a list of dictionaries, each dict containing build/test info

    # basically assert that they have the right methods ;)
    client_info.keys()
    for d in results:
        d.keys()

    _coordinator.add_results(client_ip, client_info, results)

    return 1
    
# Restrict to a particular path.

_coordinator = None

class PonyBuildServer(WSGIServer, SimpleXMLRPCDispatcher):
    def __init__(self, *args, **kwargs):
        WSGIServer.__init__(self, *args, **kwargs)
        SimpleXMLRPCDispatcher.__init__(self, False, None)


class RequestHandler(WSGIRequestHandler, SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)

    def handle(self):
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        if SimpleXMLRPCRequestHandler.is_rpc_path_valid(self):
            # @CTB hack hack hack, I should be ashamed of myself.
            global client_ip
            client_ip = self.client_address[0]
            return SimpleXMLRPCRequestHandler.do_POST(self)

        handler = ServerHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ()
        )
        handler.request_handler = self      # backpointer for logging
        handler.run(self.server.get_app())

def get_coordinator():
    global _coordinator
    return _coordinator

def create(interface, port, pbs_coordinator, wsgi_app):
    global _coordinator
    
    # Create server
    server = PonyBuildServer((interface, port), RequestHandler)
    
    server.set_app(wsgi_app)
    _coordinator = pbs_coordinator
    
    server.register_function(add_results)
    
    return server
