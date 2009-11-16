from optparse import OptionParser

from .. import qx_web

if __name__ == '__main__':
    import sys
    parser = OptionParser()

    parser.add_option('-i', '--interface', dest='interface',
                      help='interface to bind', default='localhost')
    parser.add_option('-p', '--port', dest='port', help='port to bind',
                      type='int', default='5000')
    parser.add_option('-u', '--url', dest='url', help='public URL',
                      default=None)

    (options, args) = parser.parse_args()
    dbfile=args[0]

    qx_web.run(options.interface, options.port, dbfile, public_url=options.url)
