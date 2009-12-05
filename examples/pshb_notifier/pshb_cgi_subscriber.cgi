#! /u/t/dev/venv/bin/python
"""
A simple example pubsubhubbub subscriber script.

Developed for use in dumb pony-build notifiers.
"""
import sys

MAIL_SERVER = 'localhost'
MAIL_FROM = 'pony-noreply'
MAIL_TO = 'titus@idyll.org'

import quixote
from quixote.directory import Directory
from quixote.server.cgi_server import run
from quixote.publish import Publisher

from parse_pony_build_rss import PonyBuildRSSParser

def do_notify(content):
    # do as you will with new_feed_content
    # ... < HERE > ...

    p = PonyBuildRSSParser()
    time_info, entry, values = p.consume_feed(content)

    values = dict(values)
    values['mail_to'] = MAIL_TO

    message = """\
From: pony-build notifier <pony-noreply>
To: %(mail_to)s
Subject: %(package)s build on %(build arch)s: %(status)s

status: %(status)s
arch: %(build arch)s
tags: %(tags)s
package: %(package)s
build host: %(build host)s
result id: %(result_key)s
""" % values

    # for example,
    import smtplib
    server = smtplib.SMTP(MAIL_SERVER)
    server.sendmail(MAIL_FROM, [MAIL_TO], message)
    server.quit()

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
