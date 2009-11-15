"""
Functions to help generate RSS2 feeds for pony_build results.

RSS2 and pubsubhubbub (http://code.google.com/p/pubsubhubbub/) are the
core of the notification system built into pony_build; the "officially
correct" way to actively notify interested people of build results is
to publish them via RSS2, push them to a pubsubhubbub server, and let
someone else deal with translating those into e-mail alerts, etc.

This module contains infrastructure for creating and publishing RSS
feeds using Andrew Dalke's PyRSS2Gen, and pushing change notifications
to pubsubhubbub servers via Brett Slatkin's Python module.

The main class to pay attention to is BuildSnooper, ... @CTB ...

Apart from standard UI stuff (creating and managing) RSS feeds, the
remaining bit of trickiness is that any RSS feeds must be served via a
URL and also contain ref URLs, which is the responsibility of the Web
interface.  So the 'generate_rss' function on each BuildSnooper object
must be called from the Web app and requires some input in the form of
canonical URLs

"""

import datetime
from cStringIO import StringIO
from .PyRSS2Gen import RSS2, RSSItem, _element, Guid
from .pubsubhubbub_publish import publish as pshb_publish, PublishError

build_snoopers = {}

def add_snooper(snooper, key):
    assert key not in build_snoopers
    build_snoopers[key] = snooper

def register_snooper_for_package(package, snooper):
    pass

def check_new_builds(*build_keylist):
    pass

def notify_pubsubhubbub_server(server, *rss_urls):
    try:
        pshb_publish(server, *rss_urls)
        return True
    except PublishError, e:
        print 'error notify pshb server %s' % (pshb_server,)
        traceback.print_exc()
        
    return False

class BuildSnooper(object):
    def generate_rss(self, pb_coord, base_url):
        pass
    
    def is_match(self, receipt, client_info, results):
        pass

class PackageSnooper(BuildSnooper):
    def __init__(self, package_name, only_failures=False):
        self.package_name = package_name
        self.report_successes = not only_failures

    def __str__(self):
        modifier = 'failed'
        if self.report_successes:
            modifier = 'all'
        return "Report on %s builds for package '%s'" % (modifier,
                                                         self.package_name,)

    def generate_rss(self, pb_coord, base_url):
        packages = pb_coord.get_unique_tagsets_for_package(self.package_name)

        def sort_by_timestamp(a, b):
            ta = a[1][0]['time']
            tb = b[1][0]['time']
            return -cmp(ta, tb)

        it = packages.items()

        if not self.report_successes:
            it = [ (k, v) for (k, v) in it if not v[1]['success'] ]
        
        it.sort(sort_by_timestamp)

        rss_items = []
        for k, v in it:
            tagset = sorted([ x for x in list(k) if not x.startswith('__')])
            tagset = ", ".join(tagset)

            receipt, client_info, _ = v
            result_key = receipt['result_key']
            status = client_info['success']

            x = []
            if status:
                title = 'Package %s build succeeded (tags %s)' % \
                        (self.package_name, tagset)
                x.append("status: success")
            else:
                title = 'Package %s build FAILED (tags %s)' % \
                        (self.package_name, tagset)
                x.append("status: failure")

            x.append("result_key: %s" % (receipt['result_key'],))
            x.append("package: %s" % (self.package_name,))
            x.append("build host: %s" % (client_info['host'],)) # @CTB XSS
            x.append("build arch: %s" % (client_info['arch'],))

            tags = list(client_info['tags'])
            x.append("tags: %s" % (", ".join(tags)))
            description = "<br>".join(x)

            pubDate = datetime.datetime.fromtimestamp(v[0]['time'])

            link = '%s/%s/detail?result_key=%s' % (base_url, self.package_name,
                                                   result_key)
            item = RSSItem(title=title,
                           link=link,
                           description=description,
                           guid=Guid(link),
                           pubDate=pubDate)
            rss_items.append(item)

        rss = PSHB_RSS2(
            title = "pony-build feed for %s" % (self.package_name,),
            link = '%s/%s/' % (base_url, self.package_name),
            description = 'package build & test information for "%s"' \
                % self.package_name,

            lastBuildDate = datetime.datetime.now(),
            items=rss_items
          )

        fp = StringIO()
        rss.write_xml(fp)
        return fp.getvalue()
        
    def is_match(self, *args):
        (receipt, client_info, results) = args
        assert self.package_name == client_info['package']
        return True

###

class PSHB_RSS2(RSS2):
    def publish_extensions(self, handler):
        pass
        # is this necessary? it breaks Firefoxes RSS reader...
        #_element(handler, "atom:link", "", dict(rel='hub', href='http://pubsubhubbub.appspot.com'))
