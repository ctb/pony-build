"""
A Quixote-based Web UI for pony-build.

"""
import os, os.path

import warnings

import pkg_resources
with warnings.catch_warnings():
    warnings.simplefilter("ignore")

    pkg_resources.require('Quixote>=2.6') # Quixote has some deprecated code
    import quixote
    from quixote.directory import Directory
    from quixote.publish import Publisher
    from quixote.util import StaticDirectory, StaticFile
    
from urllib import quote_plus
import pprint
import email.utils

###

from .util import env, templatesdir, format_timestamp
from . import urls

from .. import rss
from ..coordinator import build_tagset

class QuixoteWebApp(Directory):
    """
    URL: /
    """
    _q_exports = [ '', 'css', 'exit', 'recv_file', 'rss2', 'p', 'test',
                   'img']

    def __init__(self, coord, push_list=[]):
        self.coord = coord            # PonyBuildCoordinator w/results etc.

        # get notified of new results by the coordinator...
        self.coord.add_listener(self)

        if push_list:
            print '** PuSH servers:', push_list
        else:
            print '** PuSH disabled'
        self.push_list = list(push_list)
        self.rss2 = RSS2FeedDirectory(coord)
        self.p = PackageDirectory(coord)
        self.img = StaticDirectory(os.path.join(templatesdir, 'img'))
        self.css = StaticFile(os.path.join(templatesdir, 'style.css'))

    def exit(self):
        os._exit(0)

    def notify_result_added(self, result_key):
        """
        Notify pubsubhubbub servers of any changes to the RSS feeds.
        """
        # first, find any registered snoopers that care about this new build
        snooper_keys = rss.check_new_builds(self.coord, result_key)
        print '***', snooper_keys

        feed_urls = set()
        for key in snooper_keys:
            feed_url = urls.base_url + urls.named_rss_feed_url % \
                       dict(feedname=key)
            feed_urls.add(feed_url)

        # next, construct the generic feed URLs that will have changed
        receipt, client_info, results = self.coord.db_get_result_info(result_key)
        package = client_info['package']

        generic_url = urls.base_url + urls.generic_rss_feed_root % \
                      dict(package=package)

        all_url = generic_url + 'all'
        feed_urls.add(all_url)
        
        if not client_info['success']:
            # also notify 'failed'
            failed_url = generic_url + 'failed'
            feed_urls.add(failed_url)

        # finally, NOTIFY pubsubhubbub servers of the changed URLs.
        feed_urls = list(feed_urls)
        for push_server in self.push_list:
            rss.notify_pubsubhubbub_server(push_server, *feed_urls)

    def _q_index(self):
        packages = self.coord.get_all_packages()

        qp = quote_plus
        template = env.get_template('top_index.html')
        return template.render(locals())

def create_publisher(coordinator, pubsubhubbub_server=None):
    push_list = []
    if pubsubhubbub_server:
        push_list.append(pubsubhubbub_server)
        
    qx_app = QuixoteWebApp(coordinator, push_list)
    
    # sets global Quixote publisher
    Publisher(qx_app, display_exceptions='plain')

    # return a WSGI wrapper for the Quixote Web app.
    return quixote.get_wsgi_app()

###

class PackageDirectory(Directory):
    """
    URL: /p/
    """
    _q_exports = [ '' ]

    def __init__(self, coord):
        self.coord = coord

    def _q_index(self):
        request = quixote.get_request()
        response = quixote.get_response()
        response.redirect(request.get_url(2))

    def _q_lookup(self, component):
        return PackageInfo(self.coord, component)

###

class RSS2FeedDirectory(Directory):
    """
    URL: /rss2/
    """
    _q_exports = [ '', '_generic' ]

    def __init__(self, coord):
        self.coord = coord
        self._generic = RSS2_GenericFeeds(self.coord)

    def _q_index(self):
        feeds = []
        for k in rss.build_snoopers:
            snooper = rss.build_snoopers[k]
            feeds.append((k, str(snooper)))
            
        template = env.get_template('feed_index.html')
        return template.render(locals()).encode('latin-1', 'replace')
    
    def _q_lookup(self, component):
        try:
            snooper = rss.build_snoopers[component]
        except KeyError:
            response = quixote.get_response()
            response.set_status(404)
            return "404: no such component"

        package_url = urls.base_url + '/' + urls.package_url_template
        per_result_url = urls.base_url + '/' + urls.per_result_url_template
        source_url = urls.base_url + '/rss2/' + component

        xml = snooper.generate_rss(self.coord, package_url, per_result_url,
                                   source_url=source_url)
        
        response = quixote.get_response()
        response.set_content_type('text/xml')
        
        return xml

class RSS2_GenericFeeds(Directory):
    """
    URL: /rss2/_generic/
    """
    _q_exports = [ '', 'redirect' ]
    
    def __init__(self, coord):
        self.coord = coord

    def _q_index(self):
        template = env.get_template('feed_generic_index.html')
        return template.render().encode('latin-1', 'replace')

    def redirect(self):
        request = quixote.get_request()
        response = quixote.get_response()
        url = request.get_url(1)
        
        form = request.form
        if 'package' in form:
            package = form['package'].strip()
            if package:
                return response.redirect('%s/%s/' % (url, package))

        return response.redirect('%s' % (url,))

    def _q_lookup(self, package):
        return RSS2_GenericPackageFeeds(self.coord, package)

class RSS2_GenericPackageFeeds(Directory):
    """
    URL: /rss2/_generic/<package>/
    """
    _q_exports = [ '' ]

    def __init__(self, coord, package):
        self.coord = coord
        self.package = package
    
    def _q_index(self):
        request = quixote.get_request()
        package = self.package
        package_exists = (self.package in self.coord.get_all_packages())
        
        template = env.get_template('feed_generic_package_index.html')
        return template.render(locals()).encode('latin-1', 'replace')
    
    def _q_lookup(self, component):
        if component == 'all':
            snooper = rss.PackageSnooper(self.package, register=False)
        elif component == 'failed':
            snooper = rss.PackageSnooper(self.package, only_failures=True,
                                         register=False)
#        elif component == 'no_recent_build':
#            pass
        else:
            response = quixote.get_response()
            response.set_status(404)
            return "No such feed"

        package_url = urls.base_url + '/' + urls.package_url_template
        per_result_url = urls.base_url + '/' + urls.per_result_url_template
        source_url = urls.base_url + '/rss2/_generic/%s/%s' % \
                     (self.package, component)

        xml = snooper.generate_rss(self.coord, package_url, per_result_url,
                                   source_url=source_url)

        response = quixote.get_response()
        response.set_content_type('text/xml')
        
        return xml

###

class PackageInfo(Directory):
    """
    /p/<package>/
    """
    _q_exports = [ '', 'show_latest', 'show_all', 'inspect', 'detail','files' ]
    
    def __init__(self, coord, package):
        self.coord = coord
        self.package = package
        
    def _q_index(self):
        package = self.package
        d = self.coord.get_unique_tagsets_for_package(package)
        stale_exists = {}

        def calc_status(tagset):
            _, client_info, _ = d[tagset]
            status = client_info['success']
            if status:
                s = "<font color='green'>SUCCESS</font>"
                flag, reason = self.coord.check_should_build(client_info,
                                                             True)
                if flag:
                    s += "<font color='red'>*</font>"
                    stale_exists['foo'] = True
            else:
                s = "<font color='red'>FAILURE</font>"

            return s

        def calc_time(tagset):
            receipt, _, _ = d[tagset]
            t = receipt['time']
            return format_timestamp(t)

        def get_host(tagset):
            return d[tagset][1]['host']

        def get_arch(tagset):
            return d[tagset][1]['arch']

        def get_result_key(tagset):
            return quote_plus(str(d[tagset][0]['result_key']))

        def nicetagset(tagset):
            tagset = sorted([ x for x in list(tagset) if not x.startswith('__')])
            return ", ".join(tagset)

        def sort_by_timestamp(a, b):
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        def files_exist(tagset):
            key = d[tagset][0]['result_key']
            x = self.coord.get_files_for_result(key)
            x = [ f for f in x if f.visible and f.exists() ]
            return len(x)

        it = d.items()
        it.sort(sort_by_timestamp)
        tagset_list = [ k for (k, v) in it ]

        template = env.get_template('package_summary.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def show_all(self):
        package = self.package
        all_results = self.coord.get_all_results_for_package(package)
        all_results.reverse()

        def qp(x):
            return quote_plus(str(x))
        
        def calc_status(status):
            if status:
                return "<font color='green'>SUCCESS</font>"
            else:
                return "<font color='red'>FAILURE</font>"

        def calc_time(t):
            return format_timestamp(t)

        def nicetagset(tagset):
            tagset = sorted([ x for x in tagset if not x.startswith('__')])
            return ", ".join(tagset)

        template = env.get_template('package_all.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def _q_lookup(self, component):
        if component == 'latest':
            d = self.coord.get_unique_tagsets_for_package(self.package)
            if not d:
                response = quixote.get_response()
                response.set_status(404)
                response.set_body("no results for this package")
                return 
            
            latest = d.itervalues().next()
            latest_time = latest[0]['time']
            for it in d.itervalues():
                if it[0]['time'] > latest_time:
                    latest = it
                    latest_time = latest[0]['time']

            component = latest[0]['result_key']
            
        return ResultInfo(self.coord, self.package, component)

class ResultInfo(Directory):
    """
    URL: /p/<package>/<result>/
    """
    _q_exports = ['', 'inspect', 'files', 'request_build' ]
    def __init__(self, coord, package, result_key):
        self.coord = coord
        self.result_key = result_key
        self.package = package
        
        self.receipt, self.client_info, self.results = \
                      self.coord.db_get_result_info(result_key)
        
        assert self.package == self.client_info['package']

        self.files = ResultFiles(coord, package, result_key)

    def _q_index(self):
        key = self.result_key
        receipt = self.receipt
        client_info = self.client_info
        results = self.results
        package = self.package

        qp = quote_plus
        timestamp = format_timestamp(receipt['time'])
        tags = ", ".join(client_info['tags'])

        def files_exist():
            x = self.coord.get_files_for_result(key)
            x = [ f for f in x if f.visible and f.exists() ]
            return len(x)

        template = env.get_template('results_index.html')
        return template.render(locals()).encode('latin-1', 'replace')
        
    def inspect(self):
        key = self.result_key
        receipt = self.receipt
        client_info = self.client_info
        results = self.results
        package = self.package

        def repr_dict(d):
            return dict([ (k, pprint.pformat(d[k])) for k in d ])

        receipt = repr_dict(receipt)
        tagset = list(build_tagset(client_info))
        client_info = repr_dict(client_info)
        results = [ repr_dict(d) for d in results ]
        
        qp = quote_plus

        template = env.get_template('results_inspect.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def request_build(self):
        key = self.result_key
        receipt = self.receipt
        client_info = self.client_info
        results = self.results
        package = self.package

        self.coord.set_request_build(client_info, True)

        return quixote.redirect('../')

class ResultFiles(Directory):
    """
    URL: /p/<package>/<result>/files/
    """
    _q_exports = ['']

    def __init__(self, coord, package, result_key):
        self.coord = coord
        self.package = package
        self.result_key = result_key

        file_list = self.coord.get_files_for_result(result_key)
        self.file_list = [ x for x in file_list if x.visible and x.exists() ]

    def _q_index(self):
        x = []

        result_key = self.result_key
        receipt, client_info, results = \
                 self.coord.db_get_result_info(result_key)
        file_list = self.file_list
        package = self.package
        tags = ", ".join(client_info['tags'])

        template = env.get_template('results_files_index.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def _q_traverse(self, paths):
        # can't use _q_lookup; quixote unescapes %2F in paths before '?'
        if len(paths) == 1 and paths[0] == '':
            return self._q_index()

        filename = "/".join(paths)

        print 'LOOKING FOR:', filename
        
        response = quixote.get_response()
        for fileobj in self.file_list:
            if fileobj.filename == filename:
                enc_filename = filename.replace('\\', '\\\\').replace('"', '\\"')
                response.set_content_type('application/binary')
                response.set_header('Content-Disposition',
                                    'filename=%s' % enc_filename)

                fp = fileobj.open()
                data = fp.read()
                fp.close()
                
                response.set_body(data)
                return

        response.set_status(404)
        response.set_body('not found')

###

def run(host, port, dbfilename, public_url=None, pubsubhubbub_server=None):
    from .. import server, coordinator, dbsqlite
    dbfile = dbsqlite.open_shelf(dbfilename)
    dbfile = coordinator.IntDictWrapper(dbfile)

    ###

    snooper = rss.PackageSnooper('pygr')
    rss.add_snooper(snooper, 'pygr-all')

    snooper = rss.PackageSnooper('pygr', only_failures=True)
    rss.add_snooper(snooper, 'pygr-failures')

    ###

    pbs_app = coordinator.PonyBuildCoordinator(db=dbfile)
    wsgi_app = create_publisher(pbs_app, pubsubhubbub_server)

    the_server = server.create(host, port, pbs_app, wsgi_app)
    if public_url is None:
        url = urls.calculate_base_url(host, port)
    else:
        url = public_url.rstrip('/')
    urls.set_base_url(url)

    try:
        print 'serving on host %s, port %d, path /xmlrpc' % (host, port)
        print 'public URL set to:', url
        the_server.serve_forever()
    except KeyboardInterrupt:
        print 'exiting'
