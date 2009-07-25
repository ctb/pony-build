## use wsgiref.BaseHandler and pass in a WSGI app!!

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from BaseHTTPServer import BaseHTTPRequestHandler

def add_results(client_info, results):
    # client_info is a dictionary of client information
    # results is a list of dictionaries, each dict containing build/test info

    # basically assert that they have the right methods ;)
    client_info.keys()
    for d in results:
        d.keys()

    _app.add_results(client_info, results)

    return 1
    
# Restrict to a particular path.

_app = None
class RequestHandler(BaseHTTPRequestHandler, SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)

    def do_POST(self):
        if not SimpleXMLRPCRequestHandler.is_rpc_path_valid(self):
            return self.do_nonrpc_POST()

        return SimpleXMLRPCRequestHandler.do_POST(self)

    def do_nonrpc_POST(self):
        response_code, headers, content = _app.handle(self.command,
                                                      self.path,
                                                      self.headers)
        
        self.send_response(response_code)
        for h in headers:
            k, v = h.split(':', 1)
            self.send_header(k, v)
        self.end_headers()
        
        self.wfile.write(content)

        # shut down the connection
        self.wfile.flush()
        self.connection.shutdown(1)

    def do_GET(self):
        return self.do_nonrpc_POST()

def create(interface, port, app):
    global _app
    
    # Create server
    server = SimpleXMLRPCServer((interface, port),
                                requestHandler=RequestHandler)
    _app = app

    server.register_function(add_results)

    return server
