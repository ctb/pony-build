#! /usr/bin/env python
import sys
import httplib
from urlparse import urlparse

url = urlparse(sys.argv[1])

print url.hostname, url.port, url.path

data = open('rss-test-example.rss').read()
h = httplib.HTTPConnection(url.hostname, url.port)
h.request('POST', url.path, data)
print h.getresponse().read()
