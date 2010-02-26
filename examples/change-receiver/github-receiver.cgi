#! /u/t/dev/venv/bin/python
"""
A simple webhook receiver for github notification events.
"""
import sys

import pprint

import quixote
from quixote.directory import Directory
from quixote.server.cgi_server import run
from quixote.publish import Publisher

import json
from cgi import parse_qs

def process_notify_data(payload):
    pprint.pprint(payload)

    print 'branch info is:', payload['ref']
    print 'repository name:', payload['repository']['name']
    print 'repository url:', payload['repository']['url']

    return

class GithubSubscriber(Directory):
        _q_exports = [ '' ]

        def _q_index(self):
            request = quixote.get_request()
            form = request.form

            if 'payload' in form:
                payload = form['payload']
                payload = json.loads(payload)
                
                process_notify_data(payload)

                response = request.response
                response.set_status(204)
            else:
                return "ok, but got nothing?"
        
def create_publisher():
    # sets global Quixote publisher
    return Publisher(GithubSubscriber(), display_exceptions='plain')

if __name__ == '__main__':
    run(create_publisher)
