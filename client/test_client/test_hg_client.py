import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import HgClone, TempDirectoryContext, _run_command

def create_cache_location(repository_url):
    # use os.environ to specify a new place for VCS cache stuff
    temp_cache_parent = tempfile.mkdtemp()
    temp_cache_location = os.path.join(temp_cache_parent, "the_cache")
    os.environ['PONY_BUILD_CACHE'] = temp_cache_location

    # figure out what the end checkout result should be
    repository_path = urlparse.urlparse(repository_url)[2]
    repository_dirname = repository_path.rstrip('/').split('/')[-1]

    print 'calculated repository dirname as:', repository_dirname

    repository_cache = pony_client.guess_cache_dir(repository_dirname)
    assert repository_cache.startswith(temp_cache_location)

    # this will create 'the_cache' directory that contains individual
    # pkg caches.
    pony_client.create_cache_dir(repository_cache, repository_dirname)
    assert os.path.isdir(temp_cache_location)

    return (temp_cache_parent, temp_cache_location)

class Test_MercurialCachingCheckout(object):
    repository_url = 'http://bitbucket.org/ctb/pony-build-hg-test/'

    def setup(self):
        # create a context within which to run the HgCheckout command
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

        shutil.rmtree(self.cache_parent)

    def test_basic(self):
        "Run the HgClone command and verify that it Does the Right Thing."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)

        pprint.pprint(command.get_results()) # debugging output

        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))

        

        
                   
