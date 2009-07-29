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
import datetime

day_diff = datetime.timedelta(1)
hour_diff = datetime.timedelta(0, 3600)

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()

    diff = now - dt
    if diff < hour_diff:
        return dt.strftime("less than an hour ago (%I:%M%p)")
    elif diff < day_diff:
        return dt.strftime("less than a day ago (%I:%M%p)")
    
    return dt.strftime("%A, %d %B %Y, %I:%M%p")

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
        return PackageInfo(self.coord, component)

def create_publisher(coordinator):
    # sets global Quixote publisher
    Publisher(QuixoteWebApp(coordinator), display_exceptions='plain')

    # return a WSGI wrapper for the Quixote Web app.
    return quixote.get_wsgi_app()

###

class PackageInfo(Directory):
    _q_exports = [ '' ]
    
    def __init__(self, coord, package):
        self.coord = coord
        self.package = package
        
    def _q_index(self):
        package = self.package
        d = self.coord.get_latest_arch_result_for_package(package)

        def calc_status(arch):
            _, client_info, _ = d[arch]
            status = client_info['success']
            if status:
                return "<font color='green'>SUCCESS</font>"
            else:
                return "<font color='red'>FAILURE</font>"

        def calc_time(arch):
            receipt, _, _ = d[arch]
            t = receipt['time']
            return format_timestamp(t)

        def sort_by_timestamp(a, b):
            print a
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        it = d.items()
        it.sort(sort_by_timestamp)
        arch_list = [ k for (k, v) in it ]

        html = """
<h2>Package '{{ package }}'</h2>
Build information:<p>
{% if d %}
   <table border='1'>
      <tr><th>Architecture</th><th>Status</th><th>last report</th></tr>
   {% for arch in arch_list %}
      <tr>
        <td>{{ arch }}</td>
        <td>{{ calc_status(arch) }}</td>
        <td>{{ calc_time(arch) }}</td>
      </tr>
   {% endfor %}
   </table>
{% else %}
 No results for this package!
{% endif %}
"""

        return Template(html).render(locals())
