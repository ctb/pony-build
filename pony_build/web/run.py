from optparse import OptionParser
from .. import web as qx_web

if __name__ == '__main__':
#    import figleaf
#    figleaf.start()
    import sys
    parser = OptionParser()

    parser.add_option('-i', '--interface', dest='interface',
                      help='interface to bind', default='localhost')
    parser.add_option('-p', '--port', dest='port', help='port to bind',
                      type='int', default='8000')
    parser.add_option('-f', '--dbfile', dest='dbfile',
                     help='database filename', type='string',
                      default=':memory:')
    parser.add_option('-u', '--url', dest='url', help='public URL',
                      default=None)
    parser.add_option('-P', '--use-pubsubhubbub', dest='use_pubsubhubbub',
                      help='notify a pubsubhubbub server of changed RSS feeds',
                      action='store_true', default=False)
    parser.add_option('-S', '--set-pubsubhubbub-server', dest='push_server',
                      help='set the pubsubhubbub server to use',
                      type='str', default='http://pubsubhubbub.appspot.com/')
    

    (options, args) = parser.parse_args()

    if args:
        print "pony-build Web server doesn't take any arguments??"
        sys.exit(-1)

    push_server = None
    if options.use_pubsubhubbub:
        push_server = options.push_server

    qx_web.run(options.interface, options.port, options.dbfile, public_url=options.url,
               pubsubhubbub_server=push_server)
