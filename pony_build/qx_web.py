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
    _q_exports = [ '', 'show_latest', 'show_all' ]
    
    def __init__(self, coord, package):
        self.coord = coord
        self.package = package
        
    def show_latest(self):
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
<title>Build summary for '{{ packge }}'</title>
<h2>Package '{{ package }}'</h2>
Build summary:<p>
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
   <p>
   <a href='./'>show default report</a>
   <p>
   <a href='./show_all'>show all results</a>
{% else %}
 No results for this package!
{% endif %}
"""

        return Template(html).render(locals())

    def _q_index(self):
        package = self.package
        d = self.coord.get_unique_tagset_for_package(package)

        def calc_status(tagset):
            _, client_info, _ = d[tagset]
            status = client_info['success']
            if status:
                return "<font color='green'>SUCCESS</font>"
            else:
                return "<font color='red'>FAILURE</font>"

        def calc_time(tagset):
            receipt, _, _ = d[tagset]
            t = receipt['time']
            return format_timestamp(t)

        def get_host(tagset):
            return d[tagset][1]['host']

        def get_arch(tagset):
            return d[tagset][1]['arch']

        def nicetagset(tagset):
            tagset = sorted([ x for x in list(tagset) if not x.startswith('__')])
            return ", ".join(tagset)

        def sort_by_timestamp(a, b):
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        it = d.items()
        it.sort(sort_by_timestamp)
        tagset_list = [ k for (k, v) in it ]

        html = """
<title>Build summary for `{{ package }}`</title>
<h2>Package '{{ package }}'</h2>
Build summary:<p>
{% if d %}
   <table border='1'>
      <tr><th>Tags</th><th>Host</th><th>Arch</th><th>Status</th><th>last report</th></tr>
   {% for tagset in tagset_list %}
      <tr>
        <td>{{ nicetagset(tagset) }}</td>
        <td>{{ get_host(tagset)}}</td>
        <td>{{ get_arch(tagset)}}</td>
        <td>{{ calc_status(tagset) }}</td>
        <td>{{ calc_time(tagset) }}</td>
      </tr>
   {% endfor %}
   </table>

   <p>
   <a href='./show_latest'>show latest results, by architecture</a>
   <p>
   <a href='./show_all'>show all results</a>
{% else %}
 No results for this package!
{% endif %}
"""

        return Template(html).render(locals())

    def show_all(self):
        package = self.package
        all_results = self.coord.get_all_results_for_package(package)
        
        def calc_status(status):
            print 'STATUS:', status
            if status:
                return "<font color='green'>SUCCESS</font>"
            else:
                return "<font color='red'>FAILURE</font>"

        def calc_time(t):
            return format_timestamp(t)

        def nicetagset(tagset):
            tagset = sorted([ x for x in tagset if not x.startswith('__')])
            return ", ".join(tagset)

        html = """
<title>All build results for `{{ package }}`</title>
<h2>Package '{{ package }}'</h2>
All build information:<p>
{% if all_results %}
   <table border='1'>
      <tr><th>Host</th><th>Arch</th><th>Status</th><th>Tags</th><th>Time</th></tr>
   {% for (receipt, client_info, results_list) in all_results %}
      <tr>
        <td>{{ client_info['host'] }}</td>
        <td>{{ client_info['arch'] }}</td>
        <td>{{ calc_status(client_info['success']) }}</td>
        <td>{{ nicetagset(client_info['tags']) }}</td>
        <td>{{ calc_time(receipt['time']) }}</td>
      </tr>
   {% endfor %}
   </table>

   <p>
   <a href='./'>show default report</a>
   <p>
   <a href='./show_latest'>show latest results, by architecture</a>
{% else %}
 No results for this package!
{% endif %}
"""

        return Template(html).render(locals())
