"""
The default WSGI app for displaying pony-build results via the Web.

This default can be replaced by passing a different WSGI app into the
pony_build.server.create(...) function.
"""

from BaseHTTPServer import BaseHTTPRequestHandler

from urlparse import urlparse
import cgi
import traceback
import datetime
from jinja2 import Template
from urllib import quote_plus

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    return dt.strftime("%A, %d %B %Y, %I:%M%p")

class BasicWebApp(object):
    pages = { '' : 'index',
              'archs' : 'archs',
              'packages' : 'packages',
              'hosts' : 'hosts',
              'view_arch' : 'view_arch',
              'view_host' : 'view_host',
              'view_package' : 'view_package',
              'display_result_detail' : 'display_result_detail',
              'inspect' : 'inspect'
              }

    def __init__(self, coord):
        self.coord = coord            # PonyBuildCoordinator w/results etc.
    
    def handle(self, environ):
        path = environ['PATH_INFO']
        query_string = environ['QUERY_STRING']
    
        print 'HANDLE:', path, query_string
        
        url = urlparse(path)
        words = url.path.split('/')[1:]
        words = filter(None, words)

        if not len(words): words = ['']

        fn_name = self.pages.get(words[0], None)
        if fn_name:
            fn = getattr(self, fn_name, None)

        if fn_name is None or fn is None:
            return 404, ["Content-type: text/html"], "<font color='red'>not found</font>"

        ###

        qs = cgi.parse_qs(query_string)

        qs2 = {}
        for k in qs:
            v = qs[k]
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            qs2[k] = v
        qs = qs2
        
        try:
            return fn(None, **qs)
        except TypeError:
            traceback.print_exc()
            return 404, ["Content-type: text/html"], "<font color='red'>bad args</font>"

    def wsgi_interface(self, environ, start_response):
        """
        Provide a WSGI app.
        """
        status, response_headers, data = self.handle(environ)

        (message, _) = BaseHTTPRequestHandler.responses[status]

        response_headers = [ x.split(': ', 1) for x in response_headers ]
        response_headers = [ (a, b) for (a, b) in response_headers ]
        
        #print 'R', response_headers, type(data)
        data = str(data)
        
        status_str = "%d %s" % (status, message)
        start_response(status_str, response_headers)
        return [str(data)]

    def index(self, headers):
        x = []

        is_empty = True
        if self.coord.get_all_packages():
            is_empty = False

        page = """\
<title>pony-build main</title>
<h2>pony-build main</h2>

{% if is_empty %}
   No results yet.
{% else %}
   Last build:<br>
   {% if last_status %}
      <b><font color='green'>SUCCESS</font></b>
   {% else %}
      <b><font color='red'>FAILURE</font></b>
   {% endif %}

   - {{ last_package }} / {{ last_arch }} on {{ last_timestamp }}
   <br>
   
   <a href='display_result_detail?n=-1'>view</a>
{% endif %}

<hr>
<a href='packages'>List packages</a>
<p>
<a href='hosts'>List hosts</a>
<p>
<a href='archs'>List architectures</a>
<p>
"""
        try:
            receipt, client_info, results = self.coord.db_get_result_info(-1)
            
            last_status = client_info['success']
            last_timestamp = format_timestamp(receipt['time'])
            last_host = client_info['host']
            last_arch = client_info['arch']
            last_package = client_info['package_name']
        except IndexError:
            pass

        t = Template(page)
        html = t.render(locals())
        
        return 200, ["Content-type: text/html"], html

    def packages(self, headers):
        packages = self.coord.get_all_packages()

        qp = quote_plus
        page = """\
<title>Package list</title>
<h2>Package list</h2>

<ul>
{% for package in packages %}
<li> {{ package }} - <a href='view_package?package={{ qp(package) }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def hosts(self, headers):
        hosts = self.coord.get_all_hosts()

        qp = quote_plus
        page = """\
<title>Host list</title>
<h2>Host list</h2>

<ul>
{% for host in hosts %}
<li> {{ host }} - <a href='view_host?host={{ qp(host) }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def archs(self, headers):
        archs = self.coord.get_all_archs()

        qp = quote_plus
        page = """\
<title>Architecture list</title>
<h2>Architecture list</h2>

<ul>
{% for arch in archs %}
<li> {{ arch }} - <a href='view_arch?arch={{ qp(arch) }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def view_arch(self, headers, arch=''):
        latest = self.coord.get_last_result_for_arch(arch)
        if latest is None:
            return 200, ["Content-type: text/html"], "no such arch"
        
        return self.display_result_detail(headers, n=latest)

    def view_host(self, headers, host=''):
        latest = self.coord.get_last_result_for_host(host)
        if latest is None:
            return 200, ["Content-type: text/html"], "no such host"
        
        return self.display_result_detail(headers, n=latest)

    def view_package(self, headers, package=''):
        latest = self.coord.get_last_result_for_package(package)
        if latest is None:
            return 200, ["Content-type: text/html"], "no such package"
        
        return self.display_result_detail(headers, n=latest)

    def display_result_detail(self, headers, n=''):
        n = int(n)
        receipt, client_info, results = self.coord.db_get_result_info(n)

        timestamp = format_timestamp(receipt['time'])
        
        page = """
<title>Result view</title>
<h2>Result detail</h2>

Package: {{ client_info['package_name'] }}<br>
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
<hr><a href='inspect?n={{ n }}'>inspect raw record</a>
"""
        t = Template(page).render(locals())
        return 200, ["content-type: text/html"], t
        
    def inspect(self, headers, n=''):
        n = int(n)
        receipt, client_info, results = self.coord.db_get_result_info(n)

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

        html = Template(page).render(locals())
        return 200, ["Content-type: text/html"], html
