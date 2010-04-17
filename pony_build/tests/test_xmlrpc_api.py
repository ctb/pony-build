import os
import shelve
import time

import testutil
from twill.commands import *

from pony_build import coordinator, dbsqlite

###
import sys
clientlib = os.path.join(os.path.dirname(__file__), '..', '..', 'client')
clientlib = os.path.abspath(clientlib)
sys.path.insert(0, clientlib)

import pony_client as pbc
###

rpc_url = None
DB_TEST_FILE=os.path.join(os.path.dirname(__file__), 'tests.db')

###

def make_db(filename=DB_TEST_FILE):
    print 'FILENAME', filename
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
    del coord
    db.close()

def setup():
    make_db()
    testutil.run_server(DB_TEST_FILE)
    assert testutil._server_url
    
    global rpc_url
    rpc_url = testutil._server_url + 'xmlrpc'
    print 'RPC URL:', rpc_url

def teardown():
    testutil.kill_server()

def test_check_fn():
    tags = ['a_tag']
    package = 'test-underway'
    hostname = 'testhost'
    arch = 'fooarch'

    x = pbc.check(package, rpc_url, tags=tags, hostname=hostname, arch=arch)
    assert not x, x

def test_send_fn():
    client_info = dict(package='test-underway2', arch='fooarch2',
                       success=True)
    results = (client_info, [], None)

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 0
    
    pbc.send(rpc_url, results, hostname='testhost2', tags=('b_tag',))

    x = pbc.get_tagsets_for_package(rpc_url, 'test-underway2')
    assert len(x) == 1
