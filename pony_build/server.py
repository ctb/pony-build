from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

def add_results(client_info, results):
    # client_info is a dictionary of client information
    # results is a list of dictionaries, each dict containing build/test info

    # basically assert that they have the right methods ;)
    client_info.keys()
    for d in results:
        d.keys()

    print client_info
    print results

    return 1
    
# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc',)


def create(interface, port):
    # Create server
    server = SimpleXMLRPCServer((interface, port),
                                requestHandler=RequestHandler)

    server.register_function(add_results)

    return server
