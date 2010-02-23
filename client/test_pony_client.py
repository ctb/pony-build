import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import HgClone, TempDirectoryContext, _run_command

def test_create_cache_dir():
    """
    Test to make sure that create_cache_dir() does the right path calculation.
    """
    
    # build a fake cache_dir location
    tempdir = tempfile.mkdtemp()
    fake_dir = os.path.join(tempdir, 'CACHE_DIR')
    fake_pkg = os.path.join(fake_dir, 'SOME_PACKAGE')
    
    # use dependency injection to replace 'os.path.isdir' and 'os.mkdir'
    # in order to test create_cache_dir.
    def false(X):
        return False

    def noop(Y, expected_dirname=fake_dir):
        print 'NOOP GOT', Y
        Y = Y.rstrip(os.path.sep)
        expected_dirname = expected_dirname.rstrip(os.path.sep)
        
        assert Y == expected_dirname, \
               'fake mkdir got %s, expected %s' % (Y, expected_dirname)

    # replace stdlib functions
    _old_isdir, os.path.isdir = os.path.isdir, false
    _old_mkdir, os.mkdir = os.mkdir, noop

    try:
        pony_client.create_cache_dir(fake_pkg, 'SOME_PACKAGE')
        # here, the 'noop' function is actually doing the test.
    finally:
        # put stdlib functions back
        os.path.isdir, os.mkdir = _old_isdir, _old_mkdir
        shutil.rmtree(tempdir)

class Test_MercurialCachingCheckout(object):
    repository_url = 'http://bitbucket.org/ctb/pony-build-hg-test/'

    def setup(self):
        # create a context within which to run the HgCheckout command
        self.context = TempDirectoryContext()
        self.context.initialize()

        # use os.environ to specify a new place for VCS cache stuff
        self.temp_cache_parent = tempfile.mkdtemp()
        temp_cache_location = os.path.join(self.temp_cache_parent, "the_cache")
        os.environ['PONY_BUILD_CACHE'] = temp_cache_location

        # figure out what the end checkout result should be
        repository_path = urlparse.urlparse(self.repository_url)[2]
        repository_dirname = repository_path.rstrip('/').split('/')[-1]

        print 'calculated repository dirname as:', repository_dirname

        repository_cache = pony_client.guess_cache_dir(repository_dirname)
        assert repository_cache.startswith(temp_cache_location)

        # this will create 'the_cache' directory that contains individual
        # pkg caches.
        pony_client.create_cache_dir(repository_cache, repository_dirname)
        assert os.path.isdir(temp_cache_location)

        cwd = os.getcwd()                       # save current directory

        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(temp_cache_location)

        # now, check out the test hg repository.
        (ret, out, err) = _run_command(['hg', 'clone', self.repository_url])
        assert ret == 0, (out, err)

        # forcibly check out revision 0 instead of revision 1.
        (ret, out, err) = _run_command(['hg', 'checkout', '0'],
                                       cwd='pony-build-hg-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert not os.path.exists(os.path.join('pony-build-hg-test', 'test2'))

        os.chdir(cwd)                           # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.temp_cache_parent)

    def test_basic(self):
        "Run the HgClone command and verify that it Does the Right Thing."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))

        

        
                   
