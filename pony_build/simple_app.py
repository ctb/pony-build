from urlparse import urlparse
import cgi
import traceback
import urllib

_DEBUG_SAVE_RESULTS=True
_debug_results_filename='results.pickle'

class SimpleApp(object):
    pages = { '' : 'index',
              'hello' : 'hello',
              'archs' : 'archs',
              'packages' : 'packages',
              'hosts' : 'hosts',
              'view_arch' : 'view_arch',
              'view_host' : 'view_host',
              'view_package' : 'view_package'
              }
    
    def __init__(self):
        self.results_list = []
        if _DEBUG_SAVE_RESULTS:
            from cPickle import load
            try:
                fp = open(_debug_results_filename)
                self.results_list = load(fp)
                fp.close()

                print '_DEBUG: LOADED'
                print self.results_list
                self._process_results()
            except IOError:
                pass

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

        print 'CALLING', fn, url.query
        qs = cgi.parse_qs(url.query)

        qs2 = {}
        for k in qs:
            v = qs[k]
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            qs2[k] = v
        qs = qs2
        
        print '**', qs

        try:
            return fn(headers, **qs)
        except TypeError:
            traceback.print_exc()
            return 404, ["Content-type: text/html"], "<font color='red'>bad args</font>"            

    def add_results(self, client_info, results):
        print client_info
        print results
        print '---'
        self.results_list.append((client_info, results))

        if _DEBUG_SAVE_RESULTS:
            from cPickle import dump
            fp = open(_debug_results_filename, 'w')
            dump(self.results_list, fp)
            fp.close()

        self._process_results()

    def _process_results(self):
        self._hosts = hosts = {}
        self._archs = archs = {}
        self._packages = packages = {}

        for n, (client_info, results_list) in enumerate(self.results_list):
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
        s = set()
        for client_info, results in self.results_list:
            host = client_info['host']
            arch = client_info['arch']
            pkg_name = client_info['package_name']

            s.add((host, arch, pkg_name))

        x.append("<title>pony-build main</title><b>Host / architecture / package list</b><p>")
        for (host, arch, pkg_name) in s:
            x.append("%s - %s - %s<p>" % (host, arch, pkg_name,))

        x.append("<hr>\n")

        x.append("<a href='packages'>List packages</a><p>")
        x.append("<a href='hosts'>List hosts</a><p>")
        x.append("<a href='archs'>List architectures</a><p>")
        
        return 200, ["Content-type: text/html"], "%s" % ("\n".join(x))

    def hello(self, headers, query):
        return 200, ["Content-type: text/html"], "hello"

    def packages(self, headers):
        x = []
        l = self._packages.keys()
        l.sort()

        for pkg in l:
            s = "%s - <a href='view_package?package='%s'>view latest result</a>" % (pkg, urllib.quote_plus(pkg))
            x.append(s)

        x = "Packages: <ul>" + "<li>".join(x) + "</ul>"
        return 200, ["Content-type: text/html"], x

    def hosts(self, headers):
        x = []
        l = self._hosts.keys()
        l.sort()

        for host in l:
            s = "%s - <a href='view_host?host=%s'>view latest result</a>" \
                % (host, urllib.quote_plus(host),)
            x.append(s)

        x = "<title>Hosts</title>Hosts: <ul>" + "<li>".join(x) + "</ul>"
        return 200, ["Content-type: text/html"], x

    def archs(self, headers):
        x = []
        l = self._archs.keys()
        l.sort()

        for arch in l:
            s = "%s - <a href='view_arch?arch=%s'>view latest result</a>" \
                % (arch, urllib.quote_plus(arch))
            x.append(s)

        x = "Architectures: <ul>" + "<li>".join(x) + "</ul>"
        return 200, ["Content-type: text/html"], x

    def view_arch(self, headers, arch=''):
        if not len(self._archs.get(arch, [])):
            return 200, ["Content-type: text/html"], "no such arch"
        
        latest = self._archs[arch][-1]
        client_info, results = self.results_list[latest]

        host = client_info['host']
        arch = client_info['arch']
        pkg = client_info['package_name']
        
        x = """<title>Result view</title>Package: %s<br>Host: %s<br>Architecture: %s<br><hr>""" % (pkg, host, arch,)

        l = []
        for r in results:
            typ = r['type']
            status = r['status']
            if status == 0:
                status = 'success'
            else:
                status = 'failure (%d)' % (status,)
            output = r['output']
            errout = r['errout']

            l.append("<li> %s - %s" % (typ, status,))

        x += "<ul>" + "\n".join(l) + "</ul>"

        return 200, ["content-type: text/html"], x
