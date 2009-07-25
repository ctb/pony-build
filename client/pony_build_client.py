import subprocess
import xmlrpclib
import tempfile
import shutil
import os

def _run_command(command_list, cwd):
    p = subprocess.Popen(command_list, shell=False, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = p.communicate()
    ret = p.returncode

    return (ret, out, err)

class Context(object):
    def __init__(self):
        self.history = []
        
    def initialize(self):
        pass

    def finish(self):
        pass
        
    def start_command(self, command):
        pass

    def end_command(self, command):
        self.history.append(command)

    def update_client_info(self, info):
        pass

class TempDirectoryContext(Context):
    def __init__(self, always_cleanup=True):
        Context.__init__(self)
        self.always_cleanup = always_cleanup

    def initialize(self):
        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        
        print 'changing to temp directory:', self.tempdir
        os.chdir(self.tempdir)

    def finish(self):
        if self.always_cleanup:
            do_cleanup = self.always_cleanup
        else:
            success = [ c.success() for c in self.history ]
            if all(success):
                print 'all commands succeeded; setting cleanup=True'
                do_cleanup = True

        if do_cleanup:
            print 'removing', self.tempdir
            shutil.rmtree(self.tempdir)

        os.chdir(self.cwd)

    def update_client_info(self, info):
        info['tempdir'] = self.tempdir

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None):
        self.command_list = command_list
        self.command_name = name
        self.run_cwd = run_cwd
        
        self.status = None
        self.output = None
        self.errout = None
        
    def run(self, context):
        (ret, out, err) = _run_command(self.command_list, self.run_cwd)
        self.status = ret
        self.output = out
        self.errout = err

    def success(self):
        return self.status == 0

class SetupCommand(BaseCommand):
    command_type = 'setup'

class BuildCommand(BaseCommand):
    command_type = 'build'
        
class TestCommand(BaseCommand):
    command_type = 'test'

def _send(server, info, results):
    print 'connecting to', server
    s = xmlrpclib.ServerProxy(server)
    print s.add_results(info, results)

def do(name, commands, context=None, arch=None, stop_if_failure=True):
    reslist = []

    if context:
        context.initialize()

    for c in commands:
        print 'running: %s (%s)' % (c.command_name, c.command_type)
        if context:
            context.start_command(c)
        c.run(context)
        if context:
            context.end_command(c)
        results = dict(status=c.status,
                       output=c.output,
                       errout=c.errout,
                       command=str(c.command_list),
                       type=c.command_type,
                       name=c.command_name)
        reslist.append(results)

        if stop_if_failure and not c.success():
            break

    if context:
        context.finish()

    if arch is None:
        import sys
        arch = sys.platform

    success = all([ c.success() for c in commands ])

    client_info = dict(package_name=name, arch=arch, success=success)
    if context:
        context.update_client_info(client_info)
        
    return (client_info, reslist)

def send(server, x, hostname=None):
    client_info, reslist = x
    if hostname is None:
        import socket
        hostname = socket.gethostname()

    client_info['host'] = hostname
    _send(server, client_info, reslist)

if __name__ == '__main__':
    import sys
    
    c = BuildCommand(['/bin/echo', 'build output'])
    t = TestCommand(['/bin/echo', 'test output'])

    name = sys.argv[1]
    server = sys.argv[2]
    results = do(name, [c, t])
    send(server, results)
