from urlparse import urlparse

_DEBUG_SAVE_RESULTS=True
_debug_results_filename='results.pickle'

class SimpleApp(object):
    pages = { '' : 'index',
              'hello' : 'hello',
              'archs' : 'archs',
              'packages' : 'packages',
              'hosts' : 'hosts'
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

        print 'CALLING', fn
        return fn(headers, url.query)

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

    def index(self, headers, query):
        x = []
        for client_info, results in self.results_list:
            host = client_info['host']
            arch = client_info['arch']
            pkg_name = client_info['package_name']

            x.append("%s - %s - %s<p>" % (host, arch, pkg_name,))
        
        return 200, ["Content-type: text/html"], "%s" % ("\n".join(x))

    def hello(self, headers, query):
        return 200, ["Content-type: text/html"], "hello"

    def packages(self, headers, query):
        x = []
        l = self._packages.keys()
        l.sort()

        print l

        x = "Packages: <ul>" + "<li>".join(l) + "</ul>"
        return 200, ["Content-type: text/html"], x

    def hosts(self, headers, query):
        x = []
        l = self._hosts.keys()
        l.sort()

        x = "Hosts: <ul>" + "<li>".join(l) + "</ul>"
        return 200, ["Content-type: text/html"], x

    def archs(self, headers, query):
        x = []
        l = self._archs.keys()
        l.sort()

        x = "Architectures: <ul>" + "<li>".join(l) + "</ul>"
        return 200, ["Content-type: text/html"], x
