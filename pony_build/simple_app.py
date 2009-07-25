from urlparse import urlparse

_DEBUG_SAVE_RESULTS=True
_debug_results_filename='results.pickle'

class SimpleApp(object):
    pages = { '' : 'index',
              'hello' : 'hello' }
    
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
