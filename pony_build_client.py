import subprocess
import xmlrpclib

HOST='laptop'
MACHTYPE='linux/test'

def _run_command(command_list, cwd):
    p = subprocess.Popen(command_list, shell=False, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = p.communicate()
    ret = p.returncode

    return (ret, out, err)

class BaseCommand(object):
    def __init__(self):
        self.command_type = None
        self.status = None
        self.output = None
        self.errout = None
        self.run_cwd = None
        
    def run(self):
        (ret, out, err) = _run_command(self.command_list, self.run_cwd)
        self.status = ret
        self.output = out
        self.errout = err

class BuildCommand(BaseCommand):
    def __init__(self, command_list):
        BaseCommand.__init__(self)
        self.command_list = command_list
        self.command_type = 'build'
        
class TestCommand(BaseCommand):
    def __init__(self, command_list):
        BaseCommand.__init__(self)
        self.command_list = command_list
        self.command_type = 'test'

def _send(server, info, results):
    print 'connecting to', server
    s = xmlrpclib.ServerProxy(server)
    print s.add_results(info, results)

def do(name, commands, server):
    reslist = []

    for c in commands:
        c.run()
        results = dict(status=c.status,
                       output=c.output,
                       errout=c.errout,
                       type=c.command_type)
        reslist.append(results)

    client_info = dict(package_name=name, host=HOST, arch=MACHTYPE)

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
