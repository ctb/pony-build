#! /usr/bin/env python
import sys
import httplib
from urlparse import urlparse
import urllib

url = sys.argv[1]

package = open('github-notify.json').read()
d = dict(payload=package)

print urllib.urlencode(d)

print urllib.urlopen(url, urllib.urlencode(d)).read()
