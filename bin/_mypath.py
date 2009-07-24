import os.path, sys
thisdir = os.path.dirname(__file__)
libdir = os.path.join(thisdir, '..')
libdir = os.path.abspath(libdir)

if libdir not in sys.path:
    sys.path.insert(0, libdir)
