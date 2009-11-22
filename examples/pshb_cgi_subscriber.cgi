#! /u/t/dev/venv/bin/python
"""
A simple example pubsubhubbub subscriber script.

Developed for use in dumb pony-build notifiers.
"""
import sys

import quixote
from quixote.directory import Directory
from quixote.server.cgi_server import run
from quixote.publish import Publisher

def do_notify(content):
    # do as you will with new_feed_content
    # ... < HERE > ...

    # for example,
    import smtplib
    server = smtplib.SMTP('localhost')
    server.sendmail('t@lyorn.idyll.org', ['t@idyll.org'], content)
    server.quit()

    sys.stderr.write('sent: %s\n' % (content,))

class PSHB_Subscriber(Directory):
        _q_exports = [ '' ]

        def _q_index(self):
            request = quixote.get_request()
            form = request.form

            if 'hub.challenge' in form:
                return form['hub.challenge']

            length = request.get_header('content-length')
            if length:
                length = int(length)
                new_feed_content = request.stdin.read(length)

                do_notify(new_feed_content)

                response = request.response
                response.set_status(204)
            else:
                return "ok, but got nothing?"
        
def create_publisher():
    # sets global Quixote publisher
    return Publisher(PSHB_Subscriber(), display_exceptions='plain')

if __name__ == '__main__':
    run(create_publisher)
