from urlparse import urlparse

class SimpleApp(object):
    pages = { '' : 'index',
              'hello' : 'hello' }
    
    def __init__(self):
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

    def index(self, headers, query):
        return 200, ["Content-type: text/html"], "index"

    def hello(self, headers, query):
        return 200, ["Content-type: text/html"], "hello"
