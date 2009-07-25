import subprocess
import xmlrpclib

def _run_command(command_list, cwd):
    p = subprocess.Popen(command_list, shell=False, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = p.communicate()
    ret = p.returncode

    return (ret, out, err)

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None):
        self.command_list = command_list
        self.command_name = name
        self.run_cwd = run_cwd
        
        self.status = None
        self.output = None
        self.errout = None
        
    def run(self):
        (ret, out, err) = _run_command(self.command_list, self.run_cwd)
        self.status = ret
        self.output = out
        self.errout = err

class BuildCommand(BaseCommand):
    command_type = 'build'
    def __init__(self, *args, **kwargs):
        BaseCommand.__init__(self, *args, **kwargs)
        
class TestCommand(BaseCommand):
    command_type = 'test'
    def __init__(self, *args, **kwargs):
        BaseCommand.__init__(self, *args, **kwargs)

def _send(server, info, results):
    print 'connecting to', server
    s = xmlrpclib.ServerProxy(server)
    print s.add_results(info, results)

def do(name, commands, server, hostname=None, arch=None):
    reslist = []

    for c in commands:
        print 'running: %s (%s)' % (c.command_name, c.command_type)
        c.run()
        results = dict(status=c.status,
                       output=c.output,
                       errout=c.errout,
                       command=str(c.command_list),
                       type=c.command_type,
                       name=c.command_name)
        reslist.append(results)

    if hostname is None:
        import socket
        hostname = socket.gethostname()

    if arch is None:
        import sys
        arch = sys.platform

    client_info = dict(package_name=name, host=hostname, arch=arch)

    print client_info
    print reslist

    _send(server, client_info, reslist)

if __name__ == '__main__':
    import sys
    
    c = BuildCommand(['/bin/echo', 'build output'])
    t = TestCommand(['/bin/echo', 'test output'])

    name = sys.argv[1]
    server = sys.argv[2]
    do(name, [c, t], server)

#    c.run()
#    print (c.status, c.output, c.errout,)

#    t.run()
#    print (t.status, t.output, t.errout,)
