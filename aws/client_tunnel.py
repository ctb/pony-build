#! /usr/bin/env python2.6
import sys
import paramiko
import xmlrpclib

import socket
import select
import SocketServer
import time
import threading

###

#hostname = 'lyorn.idyll.org'
#key_filename='/Users/t/.ssh/id_dsa'
#username = 't'

hostname = 'ec2-75-101-168-104.compute-1.amazonaws.com'
key_filename = '/Users/t/.aws/default.pem'
username = 'root'

addr = '127.0.0.1'
src_port = 8899
dest_port = 8811

###

def verbose(x):
    #print x
    pass

class ForwardServer(SocketServer.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception, e:
            verbose('Incoming request to %s:%d failed: %s' % (self.chain_host,
                                                              self.chain_port,
                                                              repr(e)))
            return
        if chan is None:
            verbose('Incoming request to %s:%d was rejected by the SSH server.' %
                    (self.chain_host, self.chain_port))
            return

        verbose('Connected!  Tunnel open %r -> %r -> %r' % (self.request.getpeername(),
                                                            chan.getpeername(), (self.chain_host, self.chain_port)))
        while True:
            r, w, x = select.select([self.request, chan], [], [], 0.5)
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()


_server = None
def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHandler (Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport
        timeout = 0.5

    global _server
    
    _server = ForwardServer(('127.0.0.1', local_port), SubHandler)
    _server.die_horribly = False
    while not _server.die_horribly:
        _server.handle_request()
        time.sleep(0.5)

###

def install_stuff(hostname, key_filename, username='root'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, key_filename=key_filename)

    _, stdout, stderr = ssh.exec_command('apt-get update')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('apt-get -y install git-core')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('git clone git://github.com/ctb/pony-build.git')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('cd pony-build && git pull origin rpc')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('cd pony-build/aws && python rpc_server.py >& rpc_server.out &')
    print stdout.readlines()
    print stderr.readlines()

def establish_pony_client_rpc(hostname, key_filename, username='root'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, key_filename=key_filename)

    transport = ssh.get_transport()

    args = (src_port, addr, dest_port, transport)
    threading.Thread(target=forward_tunnel, args=args).start()

def conn():
    s = xmlrpclib.ServerProxy('http://localhost:8899')
    print s.hello("world")
    print s.runscript("upload-example")


if __name__ == '__main__':
    assert len(sys.argv[1])
    
    hostname = sys.argv[1]
    install_stuff(hostname, key_filename)
    establish_pony_client_rpc(hostname, key_filename)
    try:
        conn()
    finally:
        #print 'signaling DEATH'
        _server.die_horribly = True
