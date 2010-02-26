"""
svn VCS client tests.
"""
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import SvnCheckout, TempDirectoryContext, _run_command

_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()

def teardown():
    os.chdir(_cwd)

class Test_SvnNonCachingCheckout(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

    def teardown(self):
        self.context.finish()

    def test_basic(self):
        "Run the SvnCheckout command w/o caching and verify it."
        command = SvnCheckout('pony-build-svn-test', self.repository_url,
                              use_cache=False)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))


def create_cache_location(repository_url):
    # use os.environ to specify a new place for VCS cache stuff
    temp_cache_parent = tempfile.mkdtemp()
    temp_cache_location = os.path.join(temp_cache_parent, "the_cache")
    os.environ['PONY_BUILD_CACHE'] = temp_cache_location

    # figure out what the end checkout result should be
    repository_path = urlparse.urlparse(repository_url)[2]
    repository_dirname = repository_path.rstrip('/').split('/')[-1]

    print 'calculated repository dirname as:', repository_dirname

    (_, repository_cache) = pony_client.guess_cache_dir(repository_dirname)
    assert repository_cache.startswith(temp_cache_location)

    # this will create 'the_cache' directory that contains individual
    # pkg caches.
    pony_client.create_cache_dir(repository_cache, repository_dirname)
    assert os.path.isdir(temp_cache_location)

    return (temp_cache_parent, temp_cache_location)


class Test_SvnCachingCheckout(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the SvnCheckout command and verify that it works."
        command = SvnCheckout('pony-build-svn-test', self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))
        finally:
            os.chdir(cwd)


class Test_SvnCachingUpdate(object):
    repository_url = 'http://pony-build.googlecode.com/svn/pony-build-svn-test'

    def setup(self):
        # create a context within which to run the SvnCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

        cwd = os.getcwd()                       # save current directory

        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(cache_dir)

        # now, check out the test svn repository.
        (ret, out, err) = _run_command(['svn', 'checkout',
                                        self.repository_url,
                                        'pony-build-svn-test'])
        assert ret == 0, (out, err)

        # forcibly check out the first revision, instead of the second.
        (ret, out, err) = _run_command(['svn', 'update', '-r2'],
                                       cwd='pony-build-svn-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
        assert not os.path.exists(os.path.join('pony-build-svn-test', 'test2'))

        os.chdir(cwd)                           # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the SvnCheckout command and verify that it updates right."
        command = SvnCheckout('pony-build-svn-test', self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-svn-test', 'test2'))
        finally:
            os.chdir(cwd)
        

        
                   
