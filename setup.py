try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='pony-build',
      version='0.5+20090802',
      description='pony-build, a simple Continuous Integration framework',
      author = 'C. Titus Brown',
      author_email = 't@idyll.org',
      url = 'http://github.com/ctb/pony-build',
      license = 'BSD',
      packages = ['pony_build'],
#      py_modules = ['client/pony_build_client'],
      )
