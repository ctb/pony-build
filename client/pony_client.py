"""
Client library + simple command-line script for pony-build.

See http://github.com/ctb/pony-build/.
"""

import sys
import subprocess
import xmlrpclib
import tempfile
import shutil
import os, os.path
import time
import urlparse
import traceback
from optparse import OptionParser
import pprint

pb_servers = {
    'pb-dev' : 'http://lyorn.idyll.org/ctb/pb-dev/xmlrpc',
    'local' : 'http://localhost:8000/xmlrpc'
    }
pb_servers['default'] = pb_servers['pb-dev']

###

DEFAULT_CACHE_DIR='~/.pony-build'
def guess_cache_dir(dirname):
    parent = os.environ.get('PONY_BUILD_CACHE', DEFAULT_CACHE_DIR)
    parent = os.path.expanduser(parent)
    result = os.path.join(parent, dirname)

    return result

###

def _replace_variables(cmd, variables_d):
    if cmd.startswith('PB:'):
        cmd = variables_d[cmd[3:]]
    return cmd

def _run_command(command_list, cwd=None, variables=None):
    if variables:
        x = []
        for cmd in command_list:
            cmd = _replace_variables(cmd, variables)
            x.append(cmd)
        command_list = x
        
    try:
        p = subprocess.Popen(command_list, shell=False, cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out, err = p.communicate()
        ret = p.returncode
    except:
        out = ''
        err = traceback.format_exc()
        ret = -1

    return (ret, out, err)

class Context(object):
    def __init__(self):
        self.history = []
        self.start_time = self.end_time = None
        self.build_dir = None
        
    def initialize(self):
        self.start_time = time.time()

    def finish(self):
        self.end_time = time.time()
        
    def start_command(self, command):
        if self.build_dir:
            os.chdir(self.build_dir)

    def end_command(self, command):
        self.history.append(command)

    def update_client_info(self, info):
        info['duration'] = self.end_time - self.start_time

class TempDirectoryContext(Context):
    def __init__(self, cleanup=True):
        Context.__init__(self)
        self.cleanup = cleanup

    def initialize(self):
        Context.initialize(self)
        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        
        print 'changing to temp directory:', self.tempdir
        os.chdir(self.tempdir)

    def finish(self):
		os.chdir(self.cwd)
		try:
			Context.finish(self)
		finally:
			if self.cleanup:
				print 'removing', self.tempdir
				shutil.rmtree(self.tempdir, ignore_errors=True)

    def update_client_info(self, info):
        Context.update_client_info(self, info)
        info['tempdir'] = self.tempdir

class VirtualenvContext(Context):
    """
    @CTB unfinished
    """
    
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
        info['virtualenv'] = True

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None):
        self.command_list = command_list
        if name:
            self.command_name = name
        self.run_cwd = run_cwd
        
        self.status = None
        self.output = None
        self.errout = None
        self.duration = None

        self.variables = None

    def set_variables(self, v):
        self.variables = dict(v)
        
    def run(self, context):
        start = time.time()
        (ret, out, err) = _run_command(self.command_list, cwd=self.run_cwd,
                                       variables=self.variables)
        
        self.status = ret
        self.output = out
        self.errout = err
        end = time.time()

        self.duration = end - start

    def success(self):
        return self.status == 0

    def get_results(self):
        results = dict(status=self.status,
                       output=self.output,
                       errout=self.errout,
                       command=str(self.command_list),
                       type=self.command_type,
                       name=self.command_name,
                       duration=self.duration)
        return results

class SetupCommand(BaseCommand):
    command_type = 'setup'
    command_name = 'setup'

class BuildCommand(BaseCommand):
    command_type = 'build'
    command_name = 'build'
        
class TestCommand(BaseCommand):
    command_type = 'test'
    command_name = 'test'

class GitClone(SetupCommand):
    command_name = 'checkout'
    
    def __init__(self, repository, branch='master', cache_dir=None,
                 use_cache=True, **kwargs):
        SetupCommand.__init__(self, [], **kwargs)
        self.repository = repository
        self.branch = branch

        self.use_cache = use_cache
        self.cache_dir = cache_dir

        self.duration = -1
        self.version_info = ''

        self.results_dict = {}
        
    def run(self, context):
        # first, guess the co dir name
        p = urlparse.urlparse(self.repository) # what about Windows path names?
        path = p.path

        dirname = path.rstrip('/').split('/')[-1]
        if dirname.endswith('.git'):
            dirname = dirname[:-4]

        print 'git checkout dirname guessed as: %s' % (dirname,)

        if self.use_cache:
            cache_dir = self.cache_dir
            if not cache_dir:
                cache_dir = guess_cache_dir(dirname)
                
        ##

        if self.use_cache and cache_dir:
            cwd = os.getcwd()
            os.chdir(cache_dir)
            branchspec = '%s:%s' % (self.branch, self.branch)
            cmdlist = ['git', 'fetch', '-ufv', self.repository, branchspec]
            (ret, out, err) = _run_command(cmdlist)

            self.results_dict['cache_update'] = \
                     dict(status=ret, output=out, errout=err,
                          command=str(cmdlist))
            
            if ret != 0:
                return

            os.chdir(cwd)

        ##

        print cmdlist, out

        # now, do a clone, from either the parent OR the local cache
        location = self.repository
        if cache_dir:
            location = cache_dir
            
        cmdlist = ['git', 'clone', self.repository]
        (ret, out, err) = _run_command(cmdlist)
        
        self.results_dict['clone'] = \
                 dict(status=ret, output=out, errout=err,
                      command=str(cmdlist))
        if ret != 0:
            return

        print cmdlist, out

        if not os.path.exists(dirname) and os.path.isdir(dirname):
            print 'wrong guess; %s does not exist.  whoops' % (dirname,)
            self.status = -1
            return

        ##

        # check out the right branch
        if self.branch != 'master':
            cmdlist = ['git', 'checkout', 'origin/'+self.branch]
            (ret, out, err) = _run_command(cmdlist, dirname)

            print cmdlist, out

            self.results_dict['checkout+origin'] = \
                    dict(status=ret, output=out, errout=err,
                         command=str(cmdlist), branch=self.branch)
            if ret != 0:
                return

            cmdlist = ['git', 'checkout', '-b', self.branch]

            print cmdlist, out

            (ret, out, err) = _run_command(cmdlist, dirname)
            self.results_dict['checkout+-b'] = \
                    dict(status=ret, output=out, errout=err,
                         command=str(cmdlist), branch=self.branch)
            if ret != 0:
                return

        # get some info on what our HEAD is
        cmdlist = ['git', 'log', '-1', '--pretty=oneline']
        (ret, out, err) = _run_command(cmdlist, dirname)

        assert ret == 0, (cmdlist, ret, out, err)

        self.version_info = out.strip()

        self.status = 0

        # set the build directory, too.
        context.build_dir = os.path.join(os.getcwd(),
                                         dirname)

    def get_results(self):
        self.results_dict['out'] = self.results_dict['errout'] = ''
        self.results_dict['command'] = 'GitClone(%s, %s)' % (self.repository,
                                                             self.branch)
        self.results_dict['status'] = self.status
        self.results_dict['type'] = self.command_type
        self.results_dict['name'] = self.command_name

        self.results_dict['version_type'] = 'git'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info
        
        return self.results_dict
            
class SvnUpdate(SetupCommand):
    command_name = 'checkout'

    def __init__(self, dirname, repository, cache_dir=None, **kwargs):
        SetupCommand.__init__(self, [], **kwargs)
        self.repository = repository

        self.cache_dir = None
        if cache_dir:
            self.cache_dir = os.path.expanduser(cache_dir)
        self.duration = -1
        self.dirname = dirname
        
    def run(self, context):
        dirname = self.dirname

        ##

        if self.cache_dir:
            print 'updating cache dir:', self.cache_dir
            cwd = os.getcwd()
            os.chdir(self.cache_dir)
            cmdlist = ['svn', 'update']
            (ret, out, err) = _run_command(cmdlist)
            if ret != 0:
                self.command_list = cmdlist
                self.status = ret
                self.output = out
                self.errout = err
                return

            subdir = os.path.join(cwd, dirname)
            shutil.copytree(self.cache_dir, subdir)

            os.chdir(subdir)
        else:
            cmdlist = ['svn', 'co', self.repository, dirname]

            (ret, out, err) = _run_command(cmdlist)
            if ret != 0:
                self.command_list = cmdlist
                self.status = ret
                self.output = out
                self.errout = err

                return

            print cmdlist, out

            if not os.path.exists(dirname) and os.path.isdir(dirname):
                self.command_list = cmdlist
                self.status = -1
                self.output = ''
                self.errout = 'pony-build-client cannot find expected svn dir: %s' % (dirname,)
            
                print 'wrong guess; %s does not exist.  whoops' % (dirname,)
                return

            os.chdir(dirname)

        ##

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
    s = xmlrpclib.ServerProxy(server, allow_none=True)
    s.add_results(info, results)

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

        reslist.append(c.get_results())

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

    return (client_info, reslist)

def send(server_url, x, hostname=None, tags=()):
    client_info, reslist = x
    if hostname is None:
        import socket
        hostname = socket.gethostname()

    client_info['host'] = hostname
    client_info['tags'] = tags

    server_url = get_server_url(server_url)
    print 'using server URL:', server_url
    _send(server_url, client_info, reslist)

def check(name, server_url, tags=(), hostname=None, arch=None, reserve_time=0):
    if hostname is None:
        hostname = get_hostname()
        
    if arch is None:
        arch = get_arch()
        
    client_info = dict(package=name, host=hostname, arch=arch, tags=tags)
    server_url = get_server_url(server_url)
    s = xmlrpclib.ServerProxy(server_url, allow_none=True)
    (flag, reason) = s.check_should_build(client_info, True, reserve_time)
    return flag

def get_server_url(server_name):
    try_url = urlparse.urlparse(server_name)
    if try_url.scheme:
        server_url = server_name
    else:                               # not a URL?
        server_url = pb_servers[server_name]

    return server_url

def get_tagsets_for_package(server, package):
    server = get_server_url(server)
    s = xmlrpclib.ServerProxy(server, allow_none=True)
    return s.get_tagsets_for_package(package)

###

def parse_cmdline(argv=[]):
    cmdline = OptionParser()
    cmdline.add_option('-f', '--force-build', dest='force_build',
                       action='store_true', default=False,
                       help="run a build whether or not it's stale")
    
    cmdline.add_option('-n', '--no-report', dest='report',
                       action='store_false', default=True,
                       help="do not report build results to server")
    
    cmdline.add_option('-N', '--no-clean-temp', dest='cleanup_temp',
                       action='store_false', default=True,
                       help='do not clean up the temp directory')

    cmdline.add_option('-s', '--server-url', dest='server_url',
                       action='store', default='default',
                       help='set pony-build server URL for reporting results')

    cmdline.add_option('-v', '--verbose', dest='verbose',
                       action='store_true', default=False,
                       help='set verbose reporting')

    if not argv:
        (options, args) = cmdline.parse_args()
    else:
        (options, args) = cmdline.parse_args(argv)

    return options, args


###

def get_python_config(options, args):
    if not len(args):
        python_ver = 'python2.5'
    else:
        python_ver = args[0]
        print 'setting python version:', python_ver
        
    tags = [python_ver]

    if len(args) > 1:
        tags.extend(args[1:])

    return dict(python_exe=python_ver, tags=tags)

# PYTHON: generic recipe elements
PYTHON_EXE = 'PB:python_exe'

PythonBuild = BuildCommand([PYTHON_EXE, 'setup.py', 'build'])
PythonBuildInPlace = BuildCommand([PYTHON_EXE, 'setup.py', 'build_ext', '-i'])
PythonTest = TestCommand([PYTHON_EXE, 'setup.py', 'test'])

recipes = {
    'pony-build' : (get_python_config,
                    [ GitClone('git://github.com/ctb/pony-build.git'),
                      PythonBuild,
                      PythonTest
             ]),
    'twill' : (get_python_config,
               [ SvnUpdate('twill', 'https://twill.googlecode.com/svn/branches/0.9.2-dev/twill', cache_dir='~/.pony-build/twill'),
                 PythonBuild,
                 PythonTest
             ]),
    }

###

if __name__ == '__main__':
    options, args = parse_cmdline()
    
    package = args[0]
    (config_fn, recipe) = recipes[package]
    variables = config_fn(options, args[1:])

    tags = variables['tags']

    for r in recipe:
        r.set_variables(variables)

    ###

    server_url = options.server_url
    
    if not options.force_build:
        if not check(package, server_url, tags=tags):
            print 'check build says no need to build; bye'
            sys.exit(0)

    context = TempDirectoryContext()
    results = do(package, recipe, context=context, stop_if_failure=False)
    client_info, reslist = results
    
    if options.report:
        print 'result: %s; sending' % (client_info['success'],)
        send(server_url, results, tags=tags)
    else:
        print 'build result:'
        pprint.pprint(client_info)
        pprint.pprint(reslist)

        print '(NOT SENDING BUILD RESULT TO SERVER)'

    if not client_info['success']:
        print 'build failed.'
        sys.exit(-1)
        
    print 'build succeeded.'
    sys.exit(0)
