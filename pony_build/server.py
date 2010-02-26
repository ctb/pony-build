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
import json                             # requires python2.6

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

##

from .remote_api import XmlRpcFunctions

###

# various error message:

too_big_message = "403 FORBIDDEN: You're trying to upload %d bytes; we only allow %d per request."
missing_package = "missing 'package' parameter on notification"
no_auth_upload = "you are not authorized to upload files!"
missing_upload_data = 'upload attempt, but missing filename, description, or auth_key!?'

#
# The PonyBuildServer class just pulls together the WSGIServer and the
# SimpleXMLRPCDispatcher so that a single Web server can handle both
# XML-RPC and WSGI duties.
#

class PonyBuildServer(WSGIServer, SimpleXMLRPCDispatcher):
    def __init__(self, *args, **kwargs):
        WSGIServer.__init__(self, *args, **kwargs)
        SimpleXMLRPCDispatcher.__init__(self, False, None)

#
# The RequestHandler class handles all of the file upload, UI and
# XML-RPC Web calls.  It does so by first checking to see if a Web
# call is to the XML-RPC URL, file upload fn, or notify, and, if not,
# then passes it on to the WSGI handler.
#
# The object is to make it really easy to write a new UI without messing
# with the basic server functionality, which includes things like security
# measures to block DoS by uploading large files.
#
# See the handle function for more information.
#

class RequestHandler(WSGIRequestHandler, SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)
    
    MAX_CONTENT_LENGTH = 5*1000*1000    # allow only 5 mb at a time.

    def _send_html_response(self, code, message):
        """Send an HTTP response."""
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', str(len(message)))
        self.end_headers()

        self.wfile.write(message)
        self.wfile.close()

    def _handle_upload(self):
        """Handle file upload via POST."""
        
        qs = {}
        if '?' in self.path:
            url, qs = self.path.split('?', 1)
            qs = parse_qs(qs)

        try:
            description = qs.get('description')[0]
            filename = qs.get('filename')[0]
            auth_key = qs.get('auth_key')[0]
            visible = qs.get('visible', ['no'])[0] == 'yes'
        except (TypeError, ValueError, KeyError):
            self._send_http_response(400, missing_upload_data)
            return

        content_length = self.headers.getheader('content-length')
        if content_length:
            content_length = int(content_length)
            data = self.rfile.read(content_length)
            
            code = 401
            message = no_auth_upload

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
        """
        Handle:
          /xmlrpc => SimpleXMLRPCServer
          /upload => self._handle_upload
          all else => WSGI app for Web UI
        """
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        content_length = self.headers.getheader('content-length')
        if not content_length:
            content_length = 0
        content_length = int(content_length)

        print 'content length is:', content_length

        if content_length > self.MAX_CONTENT_LENGTH:
            message = too_big_message % (content_length,
                                         self.MAX_CONTENT_LENGTH)
            self._send_html_response(403, message)
            return

        if SimpleXMLRPCRequestHandler.is_rpc_path_valid(self):
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

    def _dispatch(self, method, params):
        """
        Handle all XML-RPC dispatch (see do_POST call, above).
        """
        client_ip = self.client_address[0]
        
        fn_obj = XmlRpcFunctions(_coordinator, client_ip)
        fn = getattr(fn_obj, method)
        return fn(*params)

###

_coordinator = None

def get_coordinator():
    global _coordinator
    return _coordinator

def create(interface, port, pbs_coordinator, wsgi_app):
    global _coordinator
    
    # Create server
    server = PonyBuildServer((interface, port), RequestHandler)
    
    server.set_app(wsgi_app)
    _coordinator = pbs_coordinator
    
    return server
