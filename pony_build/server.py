"""
A combined XML-RPC + WSGI server for pony-build, based on wsgiref.

This is a hacked implementation that combines SimpleXMLRPCServer with
a wsgiref WSGIServer, redirecting all requests to '/xmlrpc' into
SimpleXMLRPCServer, handling uploads of raw files into '/upload', and
letting wsgiref pass the rest on to a WSGI application.

One nice feature of this is that you can swap out the Web UI
completely without affecting the RPC functionality; and, since all of
the RPC functionality and data handling is in the PonyBuildCoordinator
class (see 'coordinator.py') you can just write a new Web UI around
that internal interface.
"""
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, \
     SimpleXMLRPCDispatcher
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, \
     ServerHandler
#import figleaf

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

### public XML-RPC API.

client_ip = None
_coordinator = None
def add_results(client_info, results):
    """
    Add build results to the server.

    'client_info' is a dictionary of client information; 'results' is
    a list of dictionaries, with each dict containing build/test info
    for a single step.
    """
    # assert that they have the right methods ;)
    client_info.keys()
    for d in results:
        d.keys()

    try:
        key = _coordinator.add_results(client_ip, client_info, results)
    except:
        traceback.print_exc()
        raise

    return key

def get_results(results_key):
    x = _coordinator.db_get_result_info(results_key)
    (receipt, client_info, results) = x

    return x

def check_should_build(client_info, reserve_build=True, build_allowance=0):
    """
    Should a client build, according to the server?

    Returns a tuple (flag, reason).  'flag' is bool; 'reason' is a
    human-readable string.

    A 'yes' (True) could be for several reasons, including no build
    result for this tagset, a stale build result (server
    configurable), or a request to force-build.
    """
    flag, reason = _coordinator.check_should_build(client_info)
    print (flag, reason)
    if flag:
        if reserve_build:
            print 'RESERVING BUILD'
            _coordinator.notify_build(client_info['package'],
                                      client_info, build_allowance)
        return True, reason
    return False, reason

def get_tagsets_for_package(package):
    """
    Get the list of tagsets containing build results for the given package.
    """
    return [ list(x) for x in _coordinator.get_tagsets_for_package(package) ]

def get_last_result_for_tagset(package, tagset):
    """
    Get the most recent result for the given package/tagset combination.
    """
    return _coordinator.get_last_result_for_tagset(package, tagset)

###

_coordinator = None

class PonyBuildServer(WSGIServer, SimpleXMLRPCDispatcher):
    def __init__(self, *args, **kwargs):
        WSGIServer.__init__(self, *args, **kwargs)
        SimpleXMLRPCDispatcher.__init__(self, False, None)


class RequestHandler(WSGIRequestHandler, SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)
    
    MAX_CONTENT_LENGTH = 5*1000*1000    # allow only 5 mb at a time.

    def _send_html_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', str(len(message)))
        self.end_headers()

        self.wfile.write(message)
        self.wfile.close()

    def _handle_upload(self):
        url, qs = self.path.split('?', 1)
        qs = parse_qs(qs)

        try:
            description = qs.get('description')[0]
            filename = qs.get('filename')[0]
            auth_key = qs.get('auth_key')[0]
            visible = qs.get('visible', ['no'])[0] == 'yes'
        except (TypeError, ValueError, KeyError):
            message = 'upload attempt, but missing filename, description, or auth_key!?'
            self._send_html_response(400, message)
            return

        content_length = self.headers.getheader('content-length')
        if content_length:
            content_length = int(content_length)
            data = self.rfile.read(content_length)
            
            code = 401
            message = "you are not auth to upload files!"

            if _coordinator.db_add_uploaded_file(auth_key,
                                                 filename,
                                                 data,
                                                 description,
                                                 visible):
                code = 200
                message = ''
        else:
            code = 400
            message = 'upload attempt, but no upload content?!'

        self._send_html_response(code, message)

    def handle(self):
        try:
            self._handle()
        finally:
            #figleaf.write_coverage('.figleaf')
            pass

    def _handle(self):
        """
        Handle:
          /xmlrpc => SimpleXMLRPCServer
          /upload => self._handle_upload
          all else => WSGI app for Web UI
        """
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        print "SERVER HANDLE: path is '%s'" % self.path
        
        content_length = self.headers.getheader('content-length')
        if not content_length:
            content_length = 0
        content_length = int(content_length)

        print 'content length is:', content_length

        if content_length > self.MAX_CONTENT_LENGTH:
            message = "403 FORBIDDEN: You're trying to upload %d bytes; we only allow %d per request." % (content_length, self.MAX_CONTENT_LENGTH)
            self._send_html_response(403, message)
            return

        if SimpleXMLRPCRequestHandler.is_rpc_path_valid(self):
            # @CTB hack hack hack, I should be ashamed of myself.
            global client_ip
            client_ip = self.client_address[0]
            return SimpleXMLRPCRequestHandler.do_POST(self)
        
        elif self.path.startswith('/upload?'):
            return self._handle_upload()

        ## else:

        handler = ServerHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ(),
            multithread=False, multiprocess=False
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
    server.register_function(get_results)
    server.register_function(check_should_build)
    server.register_function(get_tagsets_for_package)
    server.register_function(get_last_result_for_tagset)
    
    return server
