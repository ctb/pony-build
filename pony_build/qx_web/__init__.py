"""
A Quixote-based Web UI for pony-build.
"""
import os, os.path

import pkg_resources
pkg_resources.require('Quixote>=2.6')

import quixote
from quixote.directory import Directory
from quixote.publish import Publisher
from jinja2 import Template
from urllib import quote_plus
import datetime

from .util import env, templatesdir
from ..coordinator import build_tagset

day_diff = datetime.timedelta(1)
hour_diff = datetime.timedelta(0, 3600)
min_diff = datetime.timedelta(0, 60)

def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()

    diff = now - dt
    if diff < min_diff:
        return dt.strftime("less than a minute ago (%I:%M %p)")
    elif diff < hour_diff:
        return dt.strftime("less than an hour ago (%I:%M %p)")
    elif diff < day_diff:
        return dt.strftime("less than a day ago (%I:%M %p)")
    
    return dt.strftime("%A, %d %B %Y, %I:%M %p")

class QuixoteWebApp(Directory):
    _q_exports = [ '', 'css', 'exit' ]
    
    def __init__(self, coord):
        self.coord = coord            # PonyBuildCoordinator w/results etc.

    def exit(self):
        os._exit(0)

    def _q_index(self):
        packages = self.coord.get_all_packages()

        qp = quote_plus
        template = env.get_template('top_index.html')
        return template.render(locals())

    def css(self):
        cssfile = os.path.join(templatesdir, 'thin_green_line.css')
        
        response = quixote.get_response()
        response.set_content_type('text/css')
        return open(cssfile).read()

    def _q_lookup(self, component):
        return PackageInfo(self.coord, component)

def create_publisher(coordinator):
    # sets global Quixote publisher
    Publisher(QuixoteWebApp(coordinator), display_exceptions='plain')

    # return a WSGI wrapper for the Quixote Web app.
    return quixote.get_wsgi_app()

###

class PackageInfo(Directory):
    _q_exports = [ '', 'show_latest', 'show_all', 'inspect', 'detail',
                   'request_build']
    
    def __init__(self, coord, package):
        self.coord = coord
        self.package = package
        
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

        template = env.get_template('package_summary.html')
        return template.render(locals()).encode('latin-1', 'replace')

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

        template = env.get_template('package_all.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def detail(self):
        request = quixote.get_request()
        key = request.form['result_key']
        receipt, client_info, results = self.coord.db_get_result_info(key)

        if self.package != client_info['package']:
            raise Exception

        qp = quote_plus
        timestamp = format_timestamp(receipt['time'])
        package = self.package
        tags = ", ".join(client_info['tags'])

        template = env.get_template('package_detail.html')
        return template.render(locals()).encode('latin-1', 'replace')
        
    def inspect(self):
        request = quixote.get_request()
        key = request.form['result_key']
        receipt, client_info, results = self.coord.db_get_result_info(key)

        if self.package != client_info['package']:
            raise Exception

        def repr_dict(d):
            return dict([ (k, repr(d[k])) for k in d ])

        package = self.package
        receipt = repr_dict(receipt)
        tagset = list(build_tagset(client_info))
        client_info = repr_dict(client_info)
        results = [ repr_dict(d) for d in results ]
        
        qp = quote_plus

        template = env.get_template('package_inspect.html')
        return template.render(locals()).encode('latin-1', 'replace')

    def request_build(self):
        request = quixote.get_request()
        key = request.form['result_key']
        receipt, client_info, results = self.coord.db_get_result_info(key)

        self.coord.set_request_build(client_info, True)

        return quixote.redirect('./')
