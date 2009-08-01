import subprocess
import xmlrpclib
import tempfile
import shutil
import os, os.path
import time
import urlparse

def _run_command(command_list, cwd=None):
    p = subprocess.Popen(command_list, shell=False, cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = p.communicate()
    ret = p.returncode

    return (ret, out, err)

class Context(object):
    def __init__(self):
        self.history = []
        self.start = self.end = None
        
    def initialize(self):
        self.start = time.time()

    def finish(self):
        self.end = time.time()
        
    def start_command(self, command):
        pass

    def end_command(self, command):
        self.history.append(command)

    def update_client_info(self, info):
        info['duration'] = self.end - self.start

class TempDirectoryContext(Context):
    def __init__(self, always_cleanup=True):
        Context.__init__(self)
        self.always_cleanup = always_cleanup

    def initialize(self):
        Context.initialize(self)
        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        
        print 'changing to temp directory:', self.tempdir
        os.chdir(self.tempdir)

    def finish(self):
        Context.finish(self)
        
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
        Context.update_client_info(self, info)
        info['tempdir'] = self.tempdir

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None):
        self.command_list = command_list
        self.command_name = name
        self.run_cwd = run_cwd
        
        self.status = None
        self.output = None
        self.errout = None
        self.duration = None
        
    def run(self, context):
        start = time.time()
        (ret, out, err) = _run_command(self.command_list, self.run_cwd)
        
        self.status = ret
        self.output = out
        self.errout = err
        end = time.time()

        self.duration = end - start

    def success(self):
        return self.status == 0

class SetupCommand(BaseCommand):
    command_type = 'setup'

class BuildCommand(BaseCommand):
    command_type = 'build'
        
class TestCommand(BaseCommand):
    command_type = 'test'

class GitClone(SetupCommand):
    def __init__(self, repository, branch='master', cache_dir=None, **kwargs):
        SetupCommand.__init__(self, [], **kwargs)
        self.repository = repository
        self.branch = branch
        self.cache_dir = cache_dir
        self.duration = -1
        
    def run(self, context):
        # first, guess the co dir name
        p = urlparse.urlparse(self.repository) # what about Windows path names?
        path = p.path

        dirname = path.split('/')[-1]
        if dirname.endswith('.git'):
            dirname = dirname[:-4]

        print 'git checkout dirname guessed as: %s' % (dirname,)

        ##

        # now, do a clone.
        cmdlist = ['git', 'clone', self.repository]
        (ret, out, err) = _run_command(cmdlist)
        if ret != 0:
            self.status = ret
            self.output = out
            self.errout = err

            return

        if not os.path.exists(dirname) and os.path.isdir(dirname):
            self.status = -1
            self.output = ''
            self.errout = 'pony-build-client cannot find expected git dir: %s' % (dirname,)
            
            print 'wrong guess; %s does not exist.  whoops' % (dirname,)
            return

        self.status = 0                 # success
        self.output = ''
        self.errout = ''

###

def get_hostname():
    import socket
    return socket.gethostname()

def get_arch():
    import distutils.util
    return distutils.util.get_platform()

###

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
                       name=c.command_name,
                       duration=c.duration)
        reslist.append(results)

        if stop_if_failure and not c.success():
            break

    if context:
        context.finish()

    if arch is None:
        arch = get_arch()

    success = all([ c.success() for c in commands ])

    client_info = dict(package=name, arch=arch, success=success)
    if context:
        context.update_client_info(client_info)

    print client_info
        
    return (client_info, reslist)

def send(server, x, hostname=None, tags=()):
    client_info, reslist = x
    if hostname is None:
        import socket
        hostname = socket.gethostname()

    client_info['host'] = hostname
    client_info['tags'] = tags

    print client_info
    print reslist
    
    _send(server, client_info, reslist)

def check(name, server, tags=(), hostname=None, arch=None):
    if hostname is None:
        hostname = get_hostname()
        
    if arch is None:
        arch = get_arch()
        
    client_info = dict(package=name, host=hostname, arch=arch, tags=tags)
    s = xmlrpclib.ServerProxy(server)
    return s.check_should_build(client_info)

if __name__ == '__main__':
    import sys
    
    c = BuildCommand(['/bin/echo', 'build output'])
    t = TestCommand(['/bin/echo', 'test output'])

    name = sys.argv[1]
    server = sys.argv[2]
    results = do(name, [c, t])
    send(server, results)
