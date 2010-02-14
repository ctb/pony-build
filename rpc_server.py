#! /usr/bin/env python2.6
import os, subprocess, sys

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

def hello(name):
    return "hello, " + name

def runscript(name):
    if '/' in name:
        raise Exception("must specify script name with no path components")
    
    fullname = os.path.join('client', name)

    if not os.path.exists(fullname):
        raise Exception("%s does not exist" % fullname)

    args = [sys.executable, fullname, '-f']
    p = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    returncode = p.returncode

    return returncode, out, err

def create_server():
    server = SimpleXMLRPCServer(("localhost", 8811),
                                requestHandler=RequestHandler)
    server.register_function(hello)
    server.register_function(runscript)
    
    return server

if __name__ == '__main__':
    assert os.path.isdir('./client'), "must run in pony-build top dir"
    assert os.path.exists('./client/pony_client.py')
    
    server = create_server()
    server.serve_forever()


