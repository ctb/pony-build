"""
Installation and test-running details for pony-build.
"""

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

#
# gather together the template files
#

root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
templates_dir = os.path.join('pony_build', 'qx_web', 'templates')

data_files = []
for dirpath, dirnames, filenames in os.walk(templates_dir):
    if filenames:
        fullpaths = [os.path.join(dirpath, f) for f in filenames ]
        data_files.append([dirpath, fullpaths])

setup(name='pony-build',
      version='0.5+20100116',
      description='pony-build, a simple Continuous Integration framework',
      author = 'C. Titus Brown',
      author_email = 't@idyll.org',
      url = 'http://github.com/ctb/pony-build',
      license = 'BSD',
      packages = ['pony_build', 'pony_build.qx_web'],
      data_files = data_files,
      test_suite = 'nose.collector',
#      py_modules = ['client/pony_build_client'],
      )
