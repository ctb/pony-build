import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse
 
import pony_client
from pony_client import HgClone, TempDirectoryContext, _run_command
 
_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()
 
def teardown():
    os.chdir(_cwd)
 
class Test_MercurialNonCachingCheckout(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
    def teardown(self):
        self.context.finish()
 
    def test_basic(self):
        "Run the HgClone command w/o caching and verify it."
        command = HgClone(self.repository_url, use_cache=False)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
 
 
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
 
 
class Test_MercurialCachingCheckout(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent
 
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']
 
        shutil.rmtree(self.cache_parent)
 
    def test_basic(self):
        "Run the HgClone command and verify that it produces the right repo."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
        
    def test_other_branch(self):
        "Run the HgClone command for another branch."
         
        command = HgClone('http://bitbucket.org/cherkf/pony-build-hg-test/')
        command.run(self.context)
        #commands.getoutput('hg', 'update', 'extrabranch')
        
        #pprint.pprint(cmdlist.get_results()) #debugging output

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == '949a4d660f2e 2 default'
        assert results_info['version_type'] == 'hg'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
            assert  os.path.exists(os.path.join('pony-build-hg-test',
                                                   'test2'))
          #  assert os.path.exists(os.path.join('pony-build-hg-test', 'test4'))
        finally:
            os.chdir(cwd)
 
 
class Test_MercurialCachingUpdate(object):
    repository_url = 'http://bitbucket.org/cherkf/pony-build-hg-test/'
 
    def setup(self):
        # create a context within which to run the HgClone command
        self.context = TempDirectoryContext()
        self.context.initialize()
 
        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent
 
        cwd = os.getcwd() # save current directory
 
        #
        # next, we want to set up the cached repository so that it contains an
        # old checkout.
        #
        
        os.chdir(cache_dir)
 
        # now, check out the test hg repository.
        (ret, out, err) = _run_command(['hg', 'clone', self.repository_url])
        assert ret == 0, (out, err)
 
        # forcibly check out revision 7 instead of revision 1.
        (ret, out, err) = _run_command(['hg', 'checkout', '7'],
                                       cwd='pony-build-hg-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert  os.path.exists(os.path.join('pony-build-hg-test', 'test4.py'))
 
        os.chdir(cwd) # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']
 
        shutil.rmtree(self.cache_parent)
 
    def test_basic(self):
        "Run the HgClone command and verify that it produces an updated repo."
        command = HgClone(self.repository_url)
        command.verbose = True
        command.run(self.context)
 
        pprint.pprint(command.get_results()) # debugging output
 
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-hg-test', 'test2'))
    def test_other_branch(self):
        "Run the HgClone command for another branch."
        
        command = HgClone(self.repository_url)
        command.run(self.context)
         # forcibly check out revision 7 instead of revision 1.
        (ret, out, err) = _run_command(['hg', 'checkout', '7'],
                                       cwd='pony-build-hg-test')
        (ret, out, err) = _run_command(['hg', 'identify'],
                                       cwd='pony-build-hg-test')
 
        #os.chdir(cwd) # return to working dir.
        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == '949a4d660f2e 2 default'
        assert results_info['version_type'] == 'hg'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
             assert ret == 0, (out, err)
             assert os.path.exists(os.path.join('pony-build-hg-test', 'test1'))
             assert os.path.exists(os.path.join('pony-build-hg-test',
                                                   'test2'))
             assert os.path.exists(os.path.join('pony-build-hg-test', 'test4.py'))
        finally:
            os.chdir(cwd)
 
        
 
