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
import urllib
import traceback
from optparse import OptionParser
import pprint
import glob
import datetime
import signal

pb_servers = {
    'pb-dev' : 'http://lyorn.idyll.org/ctb/pb-dev/xmlrpc',
    'local' : 'http://localhost:8000/xmlrpc'
    }
pb_servers['default'] = pb_servers['pb-dev']

error_state = False
###

DEBUG_LEVEL = 5
INFO_LEVEL = 3
WARNING_LEVEL = 2
CRITICAL_LEVEL = 1
_log_level = WARNING_LEVEL

def log_debug(*args):
    log(DEBUG_LEVEL, *args)
    
def log_info(*args):
    log(INFO_LEVEL, *args)

def log_warning(*args):
    log(WARNING_LEVEL, *args)
    
def log_critical(*args):
    log(CRITICAL_LEVEL, *args)

def log(level, *what):
    if level <= _log_level:
        sys.stdout.write(" ".join([ str(x) for x in what]) + "\n")

def set_log_level(level):
    global _log_level
    _log_level = level

###

DEFAULT_CACHE_DIR='~/.pony-build'
def guess_cache_dir(dirname):
    """Return the full path of the VCS cache directory for the given pkg."""
    parent = os.environ.get('PONY_BUILD_CACHE', DEFAULT_CACHE_DIR)
    parent = os.path.expanduser(parent)
    result = os.path.join(parent, dirname)

    return (parent, result)

def create_cache_dir(cache_dir, dirname):
    # trim the pkg name so we can create the main cache_dir and not the 
    # repo dir. I believe it has to be done this way to handle different
    # user PATH setup (OS's, custom stuff etc)

    # @CTB can't we use os.path.split here, instead?
    # @CTB refactor create_cache_dir to check to see if it exists, maybe?
    
    pkglen = len(dirname) 
    cache_dir = cache_dir[:-pkglen]
    
    if os.path.isdir(cache_dir):
        log_info('VCS cache_dir %s exists already!' % cache_dir)
    else:
        try:
            log_info('created new VCS cache dir: %s' % cache_dir)
            os.mkdir(cache_dir)
        except OSError:
            log_critical('Unable to create VCS cache_dir: %s' % cache_dir)
            raise

###

def _replace_variables(cmd, variables_d):
    if cmd.startswith('PB:'):
        cmd = variables_d[cmd[3:]]
    return cmd


def _run_command(command_list, cwd=None, variables=None, extra_kwargs={},
                 verbose=False):

    if variables:
        x = []
        for cmd in command_list:
            cmd = _replace_variables(cmd, variables)
            x.append(cmd)
        command_list = x

    default_kwargs = dict(shell=False, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if extra_kwargs:
        default_kwargs.update(extra_kwargs)

    log_debug('_run_command cwd', os.getcwd())
    log_debug('_run_command running in ->', cwd)
    log_debug('_run_command command list:', command_list)
    log_debug('_run_command default kwargs:', default_kwargs)

    try:
        p = subprocess.Popen(command_list, cwd=cwd, **default_kwargs)

        out, err = p.communicate()
        ret = p.returncode
    except:
        out = ''
        err = traceback.format_exc()
        ret = -1

    log_debug('_run_command status', str(ret))
    log_debug('_run_command stdout', out)
    log_debug('_run_command stderr', err)

    return (ret, out, err)

class FileToUpload(object):
    def __init__(self, filename, location, description, visible):
        """
        filename - name to publish as
        location - full location on build system (not sent to server)
        description - brief description of file/arch for server
        """
        
        self.data = open(location, 'rb').read()
        self.filename = filename
        self.description = description
        self.visible = visible

    def __repr__(self):
        return "<FileToUpload('%s', '%s')>" % (self.filename,
                                               self.description)

class Context(object):
    def __init__(self):
        self.history = []
        self.start_time = self.end_time = None
        self.build_dir = None
        self.files = []

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

    def add_file_to_upload(self, name, location, description, visible):
        o = FileToUpload(name, location, description, visible)
        self.files.append(o)

class TempDirectoryContext(Context):
    def __init__(self, cleanup=True):
        Context.__init__(self)
        self.cleanup = cleanup

    def initialize(self):
        Context.initialize(self)
        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()

        log_info('changing to temp directory:', self.tempdir)
        os.chdir(self.tempdir)

def finish(self):
    os.chdir(self.cwd)
    try:
        Context.finish(self)
    finally:
        if self.cleanup:
            log_info('removing', self.tempdir)
            shutil.rmtree(self.tempdir, ignore_errors=True)

def update_client_info(self, info):
    Context.update_client_info(self, info)
    info['tempdir'] = self.tempdir

class VirtualenvContext(Context):
    """
    A context that works within a new virtualenv.

    VirtualenvContext works by modifying the path to the Python executable.
    """
    def __init__(self, always_cleanup=True, dependencies=[], optional=[],
                 python='python'):
        Context.__init__(self)
        self.cleanup = always_cleanup
        self.dependencies = dependencies
        self.optional = optional        # optional dependencies
        self.python = python

        # Create the virtualenv. Have to do this here so that commands can use
        # VirtualenvContext.python (etc) to get at the right python.
        import virtualenv

        self.tempdir = tempfile.mkdtemp()

        log_info('creating virtualenv')
        cmdlist = [python, '-m', 'virtualenv', '--no-site-packages',
                   self.tempdir]
        (ret, out, err) = _run_command(cmdlist)

        if ret != 0:
            raise Exception("error in running virtualenv: %s, %s" % (out, err))

        # calculate where a few things live so we can easily shell out to 'em
        bindir = os.path.join(self.tempdir, 'bin')

        self.python = os.path.join(bindir, 'python')
        self.easy_install = os.path.join(bindir, 'easy_install')
        self.pip = os.path.join(bindir, 'pip')

        os.environ['PATH'] = bindir + os.pathsep + os.environ['PATH']

    def initialize(self):
        Context.initialize(self)
        global error_state
        log_info('changing to temp directory:', self.tempdir)
        
        self.cwd = os.getcwd()
        os.chdir(self.tempdir)

        # install pip, then use it to install any packages desired
        log_info('installing pip')

        (ret, out, err) = _run_command([self.easy_install, '-U', 'pip'])
        if ret != 0:
            raise Exception("error in installing pip: %s, %s" % (out, err))
        
        for dep in self.dependencies:
            log_info('installing dependency:', dep)
            (ret, out, err) = _run_command([self.pip, 'install', '-U', '-I',
                                            dep])

            if ret != 0:
                error_state = True
                print 'about to break'
                log_critical('pip could not install req dependency: %s' % dep)
                break
            
        for dep in self.optional:
            log_info("installing optional dependency:", dep)
            (ret, out, err) = _run_command([self.pip, 'install', '-U', '-I',
                                            dep])

            # @CTB should record failed installs of optional packages
            # to client?
            if ret != 0:
                log_warning("pip cannot install optional dependency: %s" % dep)

    def finish(self):
        os.chdir(self.cwd)
        try:
            Context.finish(self)
        finally:
            if self.cleanup:
                log_info("VirtualenvContext: removing", self.tempdir)
                shutil.rmtree(self.tempdir, ignore_errors=True)

    def update_client_info(self, info):
        Context.update_client_info(self, info)
        info['tempdir'] = self.tempdir
        info['virtualenv'] = True
        info['dependencies'] = self.dependencies
        info['optional'] = self.optional


class UploadAFile(object):
    """
    A build command that arranges to upload a specific file to the server.
    
    @CTB add glob support!
    """
    def __init__(self, filepath, public_name, description, visible=True):
        self.filepath = os.path.realpath(filepath)
        self.public_name = public_name
        self.description = description
        self.visible = visible

    def success(self):
        return os.path.exists(self.filepath)

    def run(self, context):
        context.add_file_to_upload(self.public_name, self.filepath,
                                   self.description, self.visible)

    def get_results(self):
        try:
            filesize = os.path.getsize(self.filepath)
        except OSError:
            filesize = -1

        results = dict(type='file_upload',
                       description=self.description,
                       filesize=filesize,
                       errout="", # @CTB should be unnecessary!
                       status=0) # @CTB should be unnecessary!
        return results

class BaseCommand(object):
    def __init__(self, command_list, name='', run_cwd=None,
                 subprocess_kwargs=None, ignore_failure=False):
        self.command_list = command_list
        if name:
            self.command_name = name
        self.run_cwd = run_cwd

        self.status = None
        self.output = None
        self.errout = None
        self.duration = None

        self.variables = None

        self.subprocess_kwargs = {}
        if subprocess_kwargs:
            self.subprocess_kwargs = dict(subprocess_kwargs)

        self.ignore_failure = ignore_failure

    def __repr__(self):
        return "%s (%s)" % (self.command_name, self.command_type)

    def set_variables(self, v):
        self.variables = dict(v)

    def run(self, context):
        start = time.time()
        (ret, out, err) = _run_command(self.command_list, cwd=self.run_cwd,
                                       variables=self.variables,
                                       extra_kwargs=self.subprocess_kwargs)

        self.status = ret
        self.output = out
        self.errout = err
        end = time.time()

        self.duration = end - start

    def success(self):
        return self.ignore_failure or (self.status == 0)

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

class PythonPackageEgg(BaseCommand):
    command_type = 'package'
    command_name = 'package_egg'

    def __init__(self, python_exe='python'):
        BaseCommand.__init__(self, [python_exe, 'setup.py', 'bdist_egg'],
                             name='build an egg')

    def run(self, context):
        BaseCommand.run(self, context)
        if self.status == 0: # success?
            eggfiles = os.path.join('dist', '*.egg')
            eggfiles = glob.glob(eggfiles)

            for filename in eggfiles:
                context.add_file_to_upload(os.path.basename(filename),
                                           filename,
                                           'an egg installation file',
                                           visible=True)

class _VersionControlClientBase(SetupCommand):
    """
    Base class for version control clients.

    Subclasses should define:

      - get_dirname()
      - update_repository()
      - create_repository(url, dirname, step='stepname')
      - record_repository_info(dirname)

    and optionally override 'get_results()'.
    
    """
    
    def __init__(self, use_cache=True, **kwargs):
        SetupCommand.__init__(self, [], **kwargs)
        self.use_cache = use_cache

        self.duration = -1
        self.version_info = ''
        self.results_dict = {}

    def run(self, context):
        # dirname is the directory created by a succesful checkout.
        dirname = self.get_dirname()

        # cwd is the directory we're going to ultimately put dirname under.
        cwd = os.getcwd()

        # NOTE: we flat out don't like the situation where the
        # directory already exists.  Force a clean checkout.
        assert not os.path.exists(dirname)
        
        if self.use_cache:
            # 'repo_dir' is the full cache directory containing the repo.
            # this will be something like '~/.pony-build/<dirname>'.
            #
            # 'cache_dir' is the parent dir.
            
            cache_dir, repo_dir = guess_cache_dir(dirname)
            
            # does the repo already exist?
            if os.path.exists(repo_dir):              # YES
                os.chdir(repo_dir)
                log_info('changed to: ', repo_dir, 'to do fetch.')
                self.update_repository()
            else:                                     # NO
                # do a clone to create the repo dir
                log_info('changing to: ' + cache_dir + ' to make new repo dir')
                os.chdir(cache_dir)

                self.create_repository(self.repository, dirname,
                                       step='create cache')
                assert os.path.isdir(repo_dir)
                
            os.chdir(cwd)

            log_info('Using the local cache at %s for cloning' % repo_dir)
            location = repo_dir
        else:
            location = self.repository

        self.create_repository(location, dirname, step='clone')

        if not os.path.exists(dirname) and os.path.isdir(dirname):
            log_critical('wrong guess; %s does not exist. whoops' % (dirname,))
            raise Exception

        # get some info on what our repository version is
        self.record_repository_info(dirname)
        # record the build directory, too.
        context.build_dir = os.path.join(os.getcwd(), dirname)
        # signal success!
        self.status = 0

    def get_results(self):
        self.results_dict['out'] = self.results_dict['errout'] = ''
        self.results_dict['status'] = self.status
        self.results_dict['type'] = self.command_type
        self.results_dict['name'] = self.command_name

        return self.results_dict

class GitClone(_VersionControlClientBase):
    """Check out and/or update a git repository."""
    
    command_name = 'checkout'

    def __init__(self, repository, branch='master', use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache, **kwargs)
        
        self.repository = repository
        self.branch = branch

    def get_dirname(self):
        "Calculate the directory name resulting from a successful checkout."
        p = urlparse.urlparse(self.repository)
        path = p[2]                     # urlparse -> path

        dirname = path.rstrip('/').split('/')[-1]
        if dirname.endswith('.git'):
            dirname = dirname[:-4]
            
        log_info('git checkout dirname guessed as: %s' % (dirname,))
        return dirname

    def update_repository(self):
        branchspec = '%s:%s' % (self.branch, self.branch)
        cmdlist = ['git', 'fetch', '-ufv', self.repository, branchspec]
        print '***', cmdlist
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_update'] = dict(status=ret, output=out,
                                                 errout=err,
                                                 command=str(cmdlist))

        if ret != 0:
            raise Exception("cannot update cache: %s" % repo_dir)

        cmdlist = ['git', 'checkout', '-f', self.branch]
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_checkout_head'] = dict(status=ret, output=out,
                                                        errout=err,
                                                        command=str(cmdlist))

        if ret != 0:
            raise Exception("cannot reset cache: %s" % repo_dir)

    def create_repository(self, url, dirname, step='clone'):
        cmdlist = ['git', 'clone', url]
        (ret, out, err) = _run_command(cmdlist)

       	self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                          command=str(cmdlist))

        if ret != 0:
            cwd = os.getcwd()
            raise Exception("cannot clone repository %s in %s" % (url, cwd))

        if self.branch != 'master':
            # fetch the right branch
            branchspec = '%s:%s' % (self.branch, self.branch)
            cmdlist = ['git', 'fetch', '-ufv', self.repository, branchspec]
            (ret, out, err) = _run_command(cmdlist, dirname)
            assert ret == 0, (out, err)

            # check out the right branch
            cmdlist = ['git', 'checkout', '-f', self.branch]
            (ret, out, err) = _run_command(cmdlist, dirname)
            assert ret == 0, (out, err)

    def record_repository_info(self, repo_dir):
        cmdlist = ['git', 'log', '-1', '--pretty=oneline']
        (ret, out, err) = _run_command(cmdlist, repo_dir)

        assert ret == 0, (cmdlist, ret, out, err)

        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['version_type'] = 'git'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        self.results_dict['command'] = 'GitClone(%s, %s)' % (self.repository,
                                                             self.branch)

        return self.results_dict

class HgClone(_VersionControlClientBase):
    """Check out or update an Hg (Mercurial) repository."""
    command_name = 'checkout'

    def __init__(self, repository, branch='default', use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache, **kwargs)
        self.repository = repository
        self.branch = branch
        assert branch == 'default'

    def get_dirname(self):
        "Calculate the directory name resulting from a successful checkout."
        p = urlparse.urlparse(self.repository)
        path = p[2]                     # urlparse -> path

        dirname = path.rstrip('/').split('/')[-1]
        log_info('git checkout dirname guessed as: %s' % (dirname,))
        return dirname

    def update_repository(self):
        cmdlist = ['hg', 'pull', self.repository]
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_pull'] = dict(status=ret, output=out,
                                               errout=err,
                                               command=str(cmdlist))

        if ret != 0:
            raise Exception, "cannot pull from %s" % self.repository

        cmdlist = ['hg', 'update', '-C']
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['cache_update'] = \
             dict(status=ret, output=out, errout=err,
                  command=str(cmdlist))

        assert ret == 0, (out, err)

    def create_repository(self, url, dirname, step='clone'):
        cmdlist = ['hg', 'clone', url]
        (ret, out, err) = _run_command(cmdlist)

       	self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                       command=str(cmdlist))

        if ret != 0:
            cwd = os.getcwd()
            raise Exception("cannot clone repository %s in %s" % (url, cwd))

        # @CTB branch stuff unimplemented
            
    def record_repository_info(self, repo_dir):
        # get some info on what our HEAD is
        cmdlist = ['hg', 'id', '-nib']
        (ret, out, err) = _run_command(cmdlist, repo_dir)
        assert ret == 0, (cmdlist, ret, out, err)
        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['command'] = 'HgCheckout(%s, %s)' % (self.repository,
                                                               self.branch)
        self.results_dict['version_type'] = 'hg'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        return self.results_dict

class SvnCheckout(_VersionControlClientBase):
    """Check out or update a subversion repository."""
    command_name = 'checkout'

    def __init__(self, dirname, repository, use_cache=True, **kwargs):
        _VersionControlClientBase.__init__(self, use_cache=use_cache)
        
        self.dirname = dirname
        self.repository = repository

    def get_dirname(self):
        return self.dirname

    def update_repository(self):
        cmdlist = ['svn', 'update', '--accept', 'theirs-full']
        (ret, out, err) = _run_command(cmdlist)

        self.results_dict['svn update'] = dict(status=ret, output=out,
                                               errout=err,
                                               command=str(cmdlist))

        if ret != 0:
            log_critical("cannot svn update")
            raise Exception, (cmdlist, ret, out, err)

    def create_repository(self, url, dirname, step='clone'):
        if os.path.isdir(url):          # local dir? COPY.
            shutil.copytree(url, dirname)
        else:                           # remote repo? CO.
            cmdlist = ['svn', 'co', url, dirname]
            (ret, out, err) = _run_command(cmdlist)

            self.results_dict[step] = dict(status=ret, output=out, errout=err,
                                           command=str(cmdlist))

            if ret != 0:
                log_critical("cannot svn checkout %s into %s" % (url, dirname))
                raise Exception, "cannot svn checkout %s into %s" % (url, dirname)

    def record_repository_info(self, repo_dir):
        cmdlist = ['svnversion']
        (ret, out, err) = _run_command(cmdlist, repo_dir)
        assert ret == 0, (cmdlist, ret, out, err)
        self.version_info = out.strip()

    def get_results(self):
        # first, update basic
        _VersionControlClientBase.get_results(self)
        
        self.results_dict['command'] = 'SvnCheckout(%s, %s)' %(self.repository,
                                                               self.dirname)
        self.results_dict['version_type'] = 'hg'
        if self.version_info:
            self.results_dict['version_info'] = self.version_info

        return self.results_dict

###

def get_hostname():
    import socket
    return socket.gethostname()

def get_arch():
    import distutils.util
    return distutils.util.get_platform()

###

def _send(server, info, results):
    log_info('connecting to', server)
    s = xmlrpclib.ServerProxy(server, allow_none=True)
    (result_key, auth_key) = s.add_results(info, results)
    return str(auth_key)

def _upload_file(server_url, fileobj, auth_key):
    # @CTB make sure files can't be uploaded from elsewhere on system?

    # @CTB hack hack
    assert server_url.endswith('xmlrpc')
    upload_url = server_url[:-6] + 'upload'

    if fileobj.visible:
        visible='yes'
    else:
        visible = 'no'

    qs = urllib.urlencode(dict(description=fileobj.description,
                               filename=fileobj.filename,
                               auth_key=str(auth_key),
                               visible=visible))
    upload_url += '?' + qs

    try:
        http_result = urllib.urlopen(upload_url, fileobj.data)
    except:
        log_warning('file upload failed:', str(fileobj))
        log_warning(traceback.format_exc())

def do(name, commands, context=None, arch=None, stop_if_failure=True):
    reslist = []
    
    if context:
        context.initialize()
    print 'error_state:',error_state
    if error_state:
        context.finish()
        success = False
        arch = get_arch()
        client_info = dict(package=name, arch=arch, success=success)
        print 'client_info:',client_info
        context.update_client_info(client_info)
        files_to_upload = None
        return (client_info, reslist, files_to_upload)
        

    for c in commands:
        log_debug('running:', str(c))
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

    success = True
    for c in commands:
        if not c.success():
            success = False
            break

    client_info = dict(package=name, arch=arch, success=success)
    files_to_upload = None

    if context:
        context.update_client_info(client_info)

        if context.files:
            files_to_upload = context.files

    return (client_info, reslist, files_to_upload)

def send(server_url, x, hostname=None, tags=()):
    client_info, reslist, files_to_upload = x
    if hostname is None:
        import socket
        hostname = socket.gethostname()

    client_info['host'] = hostname
    client_info['tags'] = tags

    server_url = get_server_url(server_url)
    log_info('using server URL:', server_url)
    auth_key = _send(server_url, client_info, reslist)

    if files_to_upload:
        for fileobj in files_to_upload:
            log_debug('uploading', str(fileobj))
            _upload_file(server_url, fileobj, auth_key)

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
    if try_url[0]:                      # urlparse -> scheme
        server_url = server_name
    else: # not a URL?
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
                       
    cmdline.add_option('-e', '--python-executable', dest='python_executable',
                       action='store', default='python',
                       help='override the version of python used to build with')
                       
    cmdline.add_option('-t', '--tagset', dest='tagset',
                       action='store', default=[],
                       help='comma-delimited list of tags to be applied')
    cmdline.add_option('-l', '--log-level', dest='log_level',
                       action='store', default='WARNING_LEVEL',
                       help='Change the amount of output you get during build process.')

    if not argv:
        (options, args) = cmdline.parse_args()
    else:
        (options, args) = cmdline.parse_args(argv)
        
    # parse the tagset
    if options.tagset:
        options.tagset = options.tagset.split(',')
        
    # there should be nothing in args.
    # if there is, print a warning, then crash and burn.
    if args:
        print "Error--unknown arguments detected.  Failing..."
        sys.exit(0)

    return options, args


###


def test_python_version(python_exe):
    result = subprocess.Popen(python_exe + " -c \"print 'hello, world'\"", shell=True, \
                    stdout=subprocess.PIPE).communicate()
    if result[0] != "hello, world\n":
        return False
    return True

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
Python_package_egg = PythonPackageEgg(PYTHON_EXE)

recipes = {
    'pony-build' : (get_python_config,
                    [ GitClone('git://github.com/ctb/pony-build.git'),
                      PythonBuild,
                      PythonTest,
                      Python_package_egg
             ]),
    'scikits.image' : (get_python_config,
                       [ GitClone('git://github.com/stefanv/scikits.image.git'),
                         PythonBuild,
                         PythonTest,
                         Python_package_egg
             ]),
    'twill' : (get_python_config,
               [ SvnCheckout('twill', 'http://twill.googlecode.com/svn/branches/0.9.2-dev/twill', cache_dir='~/.pony-build/twill'),
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
    client_info, reslist, files_list = results

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
