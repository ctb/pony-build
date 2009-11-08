from .. import qx_web

if __name__ == '__main__':
    import sys
    HOST=''
    PORT=int(sys.argv[2])
    DBFILE=sys.argv[1]
    
    qx_web.run(HOST, PORT, DBFILE)
