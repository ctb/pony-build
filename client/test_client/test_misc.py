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
