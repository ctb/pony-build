import os
import sys
import subprocess
import urllib
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import twill
    import quixote

_server_url = None
_server_host = None
_server_port = None

DEFAULT_PORT=8912

def run_server_wsgi_intercept(dbfilename):
    host = 'localhost'
    port = 80
    
    from pony_build import server, coordinator, dbsqlite
    from pony_build.qx_web import create_publisher, urls
    
    dbfile = dbsqlite.open_shelf(dbfilename)
    dbfile = coordinator.IntDictWrapper(dbfile)

    ###

    pbs_app = coordinator.PonyBuildCoordinator(db=dbfile)
    wsgi_app = create_publisher(pbs_app)

    #the_server = server.create(host, port, pbs_app, wsgi_app)
    url = urls.calculate_base_url(host, port)
    urls.set_base_url(url)

    twill.add_wsgi_intercept('localhost', port, lambda: wsgi_app)

    global _server_url, _server_host, _server_port
    _server_host = host
    _server_port = port
    _server_url = 'http://%s:%d/' % (host, port)

def kill_server_wsgi_intercept():
    quixote.publish._publisher = None
    twill.remove_wsgi_intercept(_server_host, _server_port)

def run_server(DB_FILE, PORT=None):
    """
    Run a Quixote simple_server on localhost:PORT with subprocess.
    All output is captured & thrown away.

    The parent process returns the URL on which the server is running.
    """
    import time, tempfile
    global _server_url

    if PORT is None:
        PORT = int(os.environ.get('TWILL_TEST_PORT', DEFAULT_PORT))

    outfd = tempfile.mkstemp('twilltst')[0]

    print 'STARTING:', sys.executable, 'pony_build.qx_web.run', os.getcwd()
    process = subprocess.Popen([sys.executable, '-u',
                                '-m', 'pony_build.qx_web.run', DB_FILE,
                                '-p', str(PORT)],
                               stderr=subprocess.STDOUT,
                               stdout=outfd)
   
    time.sleep(1)

    _server_url = 'http://localhost:%d/' % (PORT,)
	
def kill_server():
    """
    Kill the previously started Quixote server.
    """
    global _server_url
    if _server_url != None:
       try:
          fp = urllib.urlopen('%sexit' % (_server_url,))
       except:
          pass

    _server_url = None
