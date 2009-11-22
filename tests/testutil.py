import os
import sys
import subprocess
import urllib

_server_url = None

DEFAULT_PORT=8912

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
