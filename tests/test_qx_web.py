import os
import shelve

import testutil
from twill.commands import *

from pony_build import coordinator, dbsqlite

DB_TEST_FILE='tests/tests.db'
def make_db(filename=DB_TEST_FILE):
    try:
        os.unlink(filename)
    except OSError:
        pass

    db = dbsqlite.open_shelf(filename, 'c')
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

    # mangle the receipt time in the database, in order to test stale flag.
    client_info = dict(success=True,
                       tags=['a_tag'],
                       package='test-stale',
                       duration=0.1,
                       host='testhost',
                       arch='fooarch')
    results = [ dict(status=0, name='abc', errout='', output='',
                    command=['foo', 'bar'],
                    type='test_the_test') ]
    k = coord.add_results('120.0.0.127', client_info, results)
    receipt, client_info, results_list = db[k]
    receipt['time'] = 0
    db[k] = receipt, client_info, results_list

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
    notfind("Stale build")
    
    follow('view details')
    code(200)
    show()

    follow('inspect raw record')
    code(200)
    show()

def test_package_stale():
    go(testutil._server_url)
    code(200)
    
    go('./test-stale/')
    title('Build summary for')
    code(200)
    show()

    find("Stale build")
