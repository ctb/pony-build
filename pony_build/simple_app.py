from urlparse import urlparse
import cgi
import traceback
import urllib
import time
import datetime
from jinja2 import Template

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    return dt.strftime("%A, %d %B %Y, %I:%M%p")

class SimpleApp(object):
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
    
    def __init__(self, db=None):
        self.results_list = []
        self.db = db

        if db is not None:
            keys = [ (int(k), k) for k in db.keys() ]
            keys.sort()
            self.results_list = [ db[k] for (_, k) in keys ]
            self._process_results()

    def handle(self, command, path, headers):
        url = urlparse(path)
        words = url.path.split('/')[1:]
        words = filter(None, words)

        if not len(words): words = ['']

        fn_name = self.pages.get(words[0], None)
        if fn_name:
            fn = getattr(self, fn_name, None)

        if fn_name is None or fn is None:
            return 404, ["Content-type: text/html"], "<font color='red'>not found</font>"

        qs = cgi.parse_qs(url.query)

        qs2 = {}
        for k in qs:
            v = qs[k]
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            qs2[k] = v
        qs = qs2
        
        try:
            return fn(headers, **qs)
        except TypeError:
            traceback.print_exc()
            return 404, ["Content-type: text/html"], "<font color='red'>bad args</font>"            

    def add_results(self, client_ip, client_info, results):
        print client_ip
        print client_info
        print results
        print '---'
        receipt = dict(time=time.time(), client_ip=client_ip)
        
        next_key = str(len(self.results_list))
        if self.db is not None:
            self.db[next_key] = (receipt, client_info, results)
            self.db.sync()

        self.results_list.append((receipt, client_info, results))

        self._process_results()

    def _process_results(self):
        self._hosts = hosts = {}
        self._archs = archs = {}
        self._packages = packages = {}

        for n, (receipt, client_info, results_list) in enumerate(self.results_list):
            host = client_info['host']
            arch = client_info['arch']
            pkg = client_info['package_name']

            l = hosts.get(host, [])
            l.append(n)
            hosts[host] = l

            l = archs.get(arch, [])
            l.append(n)
            archs[arch] = l

            l = packages.get(pkg, [])
            l.append(n)
            packages[pkg] = l

    def index(self, headers):
        x = []

        page = """\
<title>pony-build main</title>
<h2>pony-build main</h2>

{% if not results_list %}
   No results yet.
{% else %}
   {% if last_status %}
      <b><font color='green'>SUCCESS</font></b>
   {% else %}
      <b><font color='red'>FAILURE</font></b>
   {% endif %}

   - {{ last_package }} / {{ last_arch }} on {{ last_timestamp }}
{% endif %}

<hr>
<a href='packages'>List packages</a>
<p>
<a href='hosts'>List hosts</a>
<p>
<a href='archs'>List architectures</a>
<p>
"""
        results_list = self.results_list
        if results_list:
            receipt, client_info, results = results_list[-1]
            last_status = client_info['success']
            last_timestamp = format_timestamp(receipt['time'])
            last_host = client_info['host']
            last_arch = client_info['arch']
            last_package = client_info['package_name']

        t = Template(page)
        html = t.render(locals())
        
        return 200, ["Content-type: text/html"], html

    def packages(self, headers):
        packages = self._packages.keys()
        packages.sort()

        page = """\
<title>Package list</title>
<h2>Package list</h2>

<ul>
{% for package in packages %}
<li> {{ package }} - <a href='view_package?package={{ package }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def hosts(self, headers):
        hosts = self._hosts.keys()
        hosts.sort()

        page = """\
<title>Host list</title>
<h2>Host list</h2>

<ul>
{% for host in hosts %}
<li> {{ host }} - <a href='view_host?host={{ host }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def archs(self, headers):

        archs = self._archs.keys()
        archs.sort()

        page = """\
<title>Architecture list</title>
<h2>Architecture list</h2>

<ul>
{% for arch in archs %}
<li> {{ arch }} - <a href='view_arch?arch={{ arch }}'>view latest result</a>
{% endfor %}
</ul>
"""
        t = Template(page)
        return 200, ["Content-type: text/html"], t.render(locals())

    def view_arch(self, headers, arch=''):
        if not len(self._archs.get(arch, [])):
            return 200, ["Content-type: text/html"], "no such arch"
        
        latest = self._archs[arch][-1]
        return self.display_result_detail(headers, n=latest)

    def view_host(self, headers, host=''):
        if not len(self._hosts.get(host, [])):
            return 200, ["Content-type: text/html"], "no such host"
        
        latest = self._hosts[host][-1]
        return self.display_result_detail(headers, n=latest)

    def view_package(self, headers, package=''):
        if not len(self._packages.get(package, [])):
            return 200, ["Content-type: text/html"], "no such package"
        
        latest = self._packages[package][-1]
        return self.display_result_detail(headers, n=latest)

    def display_result_detail(self, headers, n=''):
        n = int(n)
        receipt, client_info, results = self.results_list[n]

        host = client_info['host']
        arch = client_info['arch']
        pkg = client_info['package_name']
        
        x = """<title>Result view</title><h2>Result detail</h2>Package: %s<br>Host: %s (%s)<br>Architecture: %s<br>""" % (pkg, host, receipt['client_ip'], arch,)

        success = client_info['success']
        if success:
            x += "<p><b><font color='green'>SUCCESS</font></b>"
        else:
            x += "<p><b><font color='red'>FAILURE</font></b>"

        x += "<p>Timestamp: %s<p>" % (format_timestamp(receipt['time']),)

        l = []
        for n, r in enumerate(results):
            name = r['name']
            typ = r['type']
            status = r['status']
            if status == 0:
                status = '<font color="green">success</font>'
            else:
                status = '<font color="red">failure (%d)</font>' % (status,)
            l.append("<a href='#%d'>%s; %s; %s</a>" % (n, typ, name, status))

        x += "Build steps: <ol><li>" + "<li>".join(l) + "</ol>"

        x += "<h2>Details</h2>"

        l = []
        for n, r in enumerate(results):
            name = r['name']
            typ = r['type']
            command = r['command']
            status = r['status']
            if status == 0:
                status = '<font color="green">success</font>'
            else:
                status = '<font color="red">failure (%d)</font>' % (status,)
            output = r['output']
            errout = r['errout']

            l.append("<a name='%d'>\n" % (n,))
            l.append("<hr><b>%s:</b></b> %s - %s<p>" % (name, typ, status,))
            l.append("<b>command line:</b> %s<p>" % (command,))
            l.append("<b>stdout:</b><pre>%s</pre><p>" % (output,))
            if errout.strip():
                l.append("<b>stderr:</b><pre>%s</pre><p>" % (errout,))
            else:
                l.append("<i>(no stderr)</i><p>")

        x += "<ul>" + "\n".join(l) + "</ul>"

        x += "<hr><a href='inspect?n=%d'>inspect raw record</a>" % (n,)

        return 200, ["content-type: text/html"], x
        
    def inspect(self, headers, n=''):
        n = int(n)
        receipt, client_info, results = self.results_list[n]

        l = ["Receipt info:<pre>"]
        for k in receipt:
            v = receipt[k]
            l.append("%s: %s\n" % (k, repr(v)))
            
        l.append("</pre><hr>Client info:<pre>")
        for k in client_info:
            v = client_info[k]
            l.append("%s: %s\n" % (k, repr(v)))
            
        l.append("</pre><hr>Results:<ol>")
        for n, result_d in enumerate(results):
            l.append('<li>Result %d:<br><pre>' % (n,))
            for k in result_d:
                v = result_d[k]
                l.append("%s: %s\n" % (k, repr(v)))
            l.append('</pre>')
            

        return 200, ["Content-type: text/html"], "".join(l)
