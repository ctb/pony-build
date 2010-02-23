"""
git VCS client tests.

TODO:
 - test different branches
"""
import sys
import os, os.path
import shutil
import tempfile
import pprint
import urlparse

import pony_client
from pony_client import GitClone, TempDirectoryContext, _run_command

_cwd = None
def setup():
    global _cwd
    _cwd = os.getcwd()

def teardown():
    os.chdir(_cwd)

class Test_GitNonCachingCheckout(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
        self.context = TempDirectoryContext()
        self.context.initialize()

    def teardown(self):
        self.context.finish()

    def test_basic(self):
        "Run the GitClone command w/o caching and verify it."
        command = GitClone(self.repository_url, use_cache=False)
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        # check files
        os.chdir(self.context.tempdir)
        assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
        assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        
    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other',
                           use_cache=False)
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)


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


class Test_GitCachingCheckout(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
        self.context = TempDirectoryContext()
        self.context.initialize()

        (cache_parent, cache_dir) = create_cache_location(self.repository_url)
        self.cache_parent = cache_parent

    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the GitClone command and verify that it produces the right repo."
        command = GitClone(self.repository_url)
        command.run(self.context)

        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        finally:
            os.chdir(cwd)

    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other')
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)


class Test_GitCachingUpdate(object):
    repository_url = 'http://github.com/ctb/pony-build-git-test.git'

    def setup(self):
        # create a context within which to run the GitClone command
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

        # now, check out the test git repository.
        (ret, out, err) = _run_command(['git', 'clone', self.repository_url])
        assert ret == 0, (out, err)

        # forcibly check out the first revision, instead of the second.
        (ret, out, err) = _run_command(['git', 'checkout', '0a59ded1fc'],
                                       cwd='pony-build-git-test')
        assert ret == 0, (out, err)
        assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
        assert not os.path.exists(os.path.join('pony-build-git-test', 'test2'))

        os.chdir(cwd)                           # return to working dir.
        
    def teardown(self):
        self.context.finish()
        del os.environ['PONY_BUILD_CACHE']

        shutil.rmtree(self.cache_parent, ignore_errors=True)

    def test_basic(self):
        "Run the GitClone command and verify that it produces an updated repo."
        command = GitClone(self.repository_url)
        command.run(self.context)

        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
c57591d8cc9ef3c293a2006416a0bb8b2ffed26d secondary commit"""
        assert results_info['version_type'] == 'git'

        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test2'))
        finally:
            os.chdir(cwd)
        
    def test_other_branch(self):
        "Run the GitClone command for another branch."
        
        command = GitClone(self.repository_url, branch='other')
        command.run(self.context)

        # check version info
        results_info = command.get_results()
        pprint.pprint(results_info) # debugging output

        assert results_info['version_info'] == """\
7f8a8e130a3cc631752e275ea57220a1b6e2dddb look ma, another branch\\!"""
        assert results_info['version_type'] == 'git'

        # check files
        cwd = os.getcwd()
        os.chdir(self.context.tempdir)
        try:
            assert os.path.exists(os.path.join('pony-build-git-test', 'test1'))
            assert not os.path.exists(os.path.join('pony-build-git-test',
                                                   'test2'))
            assert os.path.exists(os.path.join('pony-build-git-test', 'test3'))
        finally:
            os.chdir(cwd)
