import sys
import pony_client

def setup():
    pony_client.set_log_level(pony_client.DEBUG_LEVEL)

def test_python_version():
    my_version = "%d.%d" % (sys.version_info[:2])
    
    reported_version = pony_client.get_python_version(sys.executable)
    reported_version = reported_version

    assert my_version == reported_version, (my_version, reported_version)
