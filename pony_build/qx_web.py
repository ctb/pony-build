"""
A Quixote-based Web UI for pony-build.
"""

import pkg_resources
pkg_resources.require('Quixote>=2.6')

import quixote
from quixote.directory import Directory
from quixote.publish import Publisher
from jinja2 import Template
from urllib import quote_plus

class QuixoteWebApp(Directory):
    _q_exports = [ '' ]
    
    def __init__(self, coord):
        self.coord = coord            # PonyBuildCoordinator w/results etc.

    def _q_index(self):
        packages = self.coord.get_all_packages()

        qp = quote_plus
        page = """
{% if packages %}
   We have build information for:
   <ul>
   {% for p in packages %}
      <li> <a href='./{{ qp(p) }}/'>{{ p }}</a
   {% endfor %}
   </ul>
{% else %}
   No package information received yet.
{% endif %}
"""
        return Template(page).render(locals())

    def _q_lookup(self, component):
        return PackageInfo(component)

def create_publisher(coordinator):
    # sets global Quixote publisher
    Publisher(QuixoteWebApp(coordinator), display_exceptions='plain')

    # return a WSGI wrapper for the Quixote Web app.
    return quixote.get_wsgi_app()

###

class PackageInfo(Directory):
    _q_exports = [ '' ]
    
    def __init__(self, package):
        self.package = package
        
    def _q_index(self):
        return "hello, world!"
