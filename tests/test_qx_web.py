import os
import shelve

import testutil
from twill.commands import *

from pony_build import coordinator

DB_TEST_FILE='tests/tests.db'
def make_db(filename=DB_TEST_FILE):
    try:
        os.unlink(filename)
    except OSError:
        pass

    db = shelve.open(filename, 'c')
    db = coordinator.IntDictWrapper(db)
    coord = coordinator.PonyBuildCoordinator(db)

    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-underway',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    coord.add_results('120.0.0.127', client_info, results)
    del coord
    db.close()

def setup():
    make_db()
    testutil.run_server(DB_TEST_FILE)

def teardown():
    testutil.kill_server()

def test_index():
    go(testutil._server_url)

    title('pony-build main')
    code(200)

def test_package_index():
    go(testutil._server_url)
    code(200)
    
    go('./test-underway/')
    title('Build summary for')
    code(200)
    show()
    
    follow('view details')
    code(200)
    show()

    follow('inspect raw record')
    code(200)
    show()
