import os
import shelve

import testutil
from twill.commands import *

from pony_build import coordinator
import pony_build_client as pbc

rpc_url = None
DB_TEST_FILE='tests/tests.db'

###

def make_db(filename=DB_TEST_FILE):
    try:
        os.unlink(filename)
    except OSError:
        pass

    db = shelve.open(filename, 'c')
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
    assert testutil._server_url
    
    global rpc_url
    rpc_url = testutil._server_url + 'xmlrpc'

def teardown():
    testutil.kill_server()

def test_check_fn():
    tags = ['a_tag']
    package = 'test-underway'
    hostname = 'testhost'
    arch = 'fooarch'

    assert not pbc.check(package, rpc_url,
                         tags=tags, hostname=hostname, arch=arch)

def test_send_fn():
    client_info = dict(package='test-underway2', arch='fooarch2',
                       success=True)
    results = (client_info, [])

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 0
    
    pbc.send(rpc_url, results, hostname='testhost2', tags=('b_tag',))

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 1
