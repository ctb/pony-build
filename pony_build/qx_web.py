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
        return dt.strftime("less than an hour ago (%I:%M %p)")
    elif diff < day_diff:
        return dt.strftime("less than a day ago (%I:%M %p)")
    
    return dt.strftime("%A, %d %B %Y, %I:%M %p")

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
    _q_exports = [ '', 'show_latest', 'show_all', 'inspect', 'detail' ]
    
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

        def get_result_key(arch):
            receipt, _, _ = d[arch]
            return receipt['result_key']

        def sort_by_timestamp(a, b):
            print a
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        it = d.items()
        it.sort(sort_by_timestamp)
        arch_list = [ k for (k, v) in it ]

        html = """
<title>Build summary for '{{ package }}'</title>
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
        <td><a href='detail?result_key={{ get_result_key(arch) }}'>view details</a></td>      </tr>
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

        def get_result_key(tagset):
            return quote_plus(d[tagset][0]['result_key'])

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
        <td><a href='detail?result_key={{ get_result_key(tagset) }}'>view details</a></td>
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

        qp = quote_plus
        
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
        <td><a href='detail?result_key={{ qp(receipt['result_key']) }}'>view details</a></td>      </tr>
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

    def detail(self):
        request = quixote.get_request()
        key = request.form['result_key']
        receipt, client_info, results = self.coord.db_get_result_info(key)

        if self.package != client_info['package']:
            raise Exception

        qp = quote_plus

        timestamp = format_timestamp(receipt['time'])
        
        page = """
<title>Result view</title>
<h2>Result detail</h2>

Package: {{ client_info['package'] }}<br>
Host: {{ client_info['host'] }} ({{ receipt['client_ip'] }})<br>
Architecture: {{client_info['arch'] }}<br>

<p>

<b>
 {% if client_info['success'] -%}
   <font color='green'>SUCCESS</font>
 {% else %}
   <font color='red'>FAILURE</font>
 {% endif %}
</b>

<p>
Timestamp: {{ timestamp }}
<p>

Build steps:
<ol>
{% for r in results %}
   <li> <a href='#{{ loop.index0 }}'>{{ r['type'] }}; {{ r['name'] }};
   {% if r['status'] == 0 %}
      <font color="green">success</font>
   {% else %}
      <font color="red">failure ({{ r['status'] }})</font>
   {% endif %}
   </a>
{% endfor %}
</ol>

<h2>Details</h2>
<ul>
{% for r in results %}
   <hr>
   <li> <a name='{{ loop.index0 }}'>
   <b>{{ r['name'] }}</b> {{ r['type'] }} -
   {% if r['status'] == 0 %}
      <font color="green">success</font>
   {% else %}
      <font color="red">failure ({{ r['status'] }})</font>
   {% endif %}

   <p>
   
   <b>command line:</b>{{ r['command'] }}
   <p>
   <b>stdout:</b><pre>{{ r['output'] }}</pre>
   
   {% if r['errout'].strip() %}
   <b>stderr:</b><pre>{{ r['errout'] }}</pre>
   {% else %}
   <i>no stderr</i>
   {% endif %}
   <p>
{% endfor %}
</ul>
<hr><a href='inspect?result_key={{ qp(key) }}'>inspect raw record</a>
"""
        return Template(page).render(locals())
        
    def inspect(self):
        request = quixote.get_request()
        key = request.form['result_key']
        receipt, client_info, results = self.coord.db_get_result_info(key)

        if self.package != client_info['package']:
            raise Exception

        def repr_dict(d):
            return dict([ (k, repr(d[k])) for k in d ])

        receipt = repr_dict(receipt)
        client_info = repr_dict(client_info)
        results = [ repr_dict(d) for d in results ]

        page = """\
<title>Inspector for record {{ n }}</title>
<h2>Inspector for record {{ n }}</h2>

Receipt info:
<pre>
{% for k, v in receipt.items() -%}
   {{ k }}: {{ v }}
{% endfor -%}
</pre>

Client info:
<pre>
{% for k, v in client_info.items() -%}
   {{ k }}: {{ v }}
{% endfor -%}
</pre>

<b>Results:</b>
<ul>
{% for result_d in results -%}
   <li>Result {{ loop.index }}:<br>
   <pre>
   {% for k, v in result_d.items() -%}
      {{ k }}: {{ v }}
   {% endfor -%}
   </pre>
{% endfor %}
</ul>
"""
        return Template(page).render(locals())
