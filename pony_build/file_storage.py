"""
A KISS file storage system for tracking and expiring uploaded files.

Stores files under '.files' in the directory above the pony-build main,
OR wherever is specified by the 'PONY_BUILD_FILES' environment variable.

@CTB both 'open' and 'sweep' need to lock in multithreading situations.

"""
import os
from os.path import join, getsize, getmtime
import shutil
import urllib

###

FILE_LIMIT = 50*1000*1000

### files location

if 'PONY_BUILD_FILES' in os.environ:
    files_dir = os.path.abspath(os.environ['PONY_BUILD_FILES'])
else:
    files_dir = os.path.dirname(__file__)
    files_dir = os.path.join(files_dir, '..', '.files')
    files_dir = os.path.abspath(files_dir)

if not os.path.exists(files_dir):
    os.mkdir(files_dir)

print 'putting uploaded files into %s' % files_dir

def sweep():
    """
    Expire files based on oldest-dir-first, once the total is over the limit.

    For small caches, files from infrequently-updated packages may be
    entirely eliminated in favor keeping uploads from regularly
    updated packages. A smarter way to do this would be to group files
    by package and do an initial sweep within all the packages.

    Or you could just increase the disk space you've allocated to the cache ;)
    
    """
    print '** sweeping uploaded_files cache'
    sizes = {}
    times = {}
    for root, dirs, files in os.walk(files_dir):
        if root == files_dir:
            continue

        sizes[root] = sum(getsize(join(root, name)) for name in files)
        times[root] = os.path.getmtime(root)

    times = times.items()
    times = sorted(times, key = lambda x: x[1], reverse=True)

    sumsize = 0
    rm_list = []
    for path, _ in times:
        sumsize += sizes[path]

        if sumsize > FILE_LIMIT:
            rm_list.append(path)

    if rm_list:
        for path in rm_list:
            print 'REMOVING', path
            shutil.rmtree(path)
    else:
        print '** nothing to remove'

###

class UploadedFile(object):
    """
    Provide storage, file path munging and safety checks for uploaded files.
    """
    def __init__(self, subdir, filename, description, visible):
        self.subdir = subdir
        self.filename = filename
        self.description = description
        self.visible = visible

    def make_subdir(self):
        """
        Make sure the specified subdirectory exists, and make it if not.
        """
        subdir = os.path.join(files_dir, self.subdir)
        subdir = os.path.abspath(subdir)
        if not os.path.isdir(subdir):
            os.mkdir(subdir)

    def _make_abspath(self):
        """
        Munge the file path us urllib.quote_plus, and make sure it's under
        the right directory.
        """
        safe_path = urllib.quote_plus(self.filename)
        fullpath = os.path.join(files_dir, self.subdir, safe_path)
        fullpath = os.path.abspath(fullpath)
        if not fullpath.startswith(files_dir):
            raise Exception("security warning: %s not under %s" % \
                            (self.filename, files_dir))
        return fullpath

    def exists(self):
        "Check to see if the file still exists."
        return os.path.isfile(self._make_abspath())

    def size(self):
        "Return the size, in bytes, of the file."
        return os.path.getsize(self._make_abspath())

    def open(self, mode='rb'):
        "Provide a handle to the file contents.  Make sure to use binary..."
        return open(self._make_abspath(), mode)
