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

MAX=50

from datetime import datetime, timedelta
import traceback
from cStringIO import StringIO
from .PyRSS2Gen import RSS2, RSSItem, _element, Guid, Source
from .pubsubhubbub_publish import publish as push_publish, PublishError

build_snoopers = {}
build_snoopers_rev = {}

wildcard_snoopers = []
snoopers_per_package = {}

def add_snooper(snooper, key):
    """
    Add a snooper into the forward and reverse key mapping dictionaries.
    
    """
    assert key not in build_snoopers
    build_snoopers[key] = snooper
    build_snoopers_rev[snooper] = key

def register_wildcard_snooper(snooper):
    wildcard_snoopers.append(snooper)

def register_snooper_for_package(package, snooper):
    """
    Register a snooper to care about a particular package.
    
    """
    x = snoopers_per_package.get(package, [])
    x.append(snooper)
    snoopers_per_package[package] = x

def check_new_builds(coord, *build_keylist):
    """
    Return the list of snooper keys that care about new builds.

    Briefly, for each build in build_keylist, retrieve the package info and
    see if there are any snoopers interested in that package.  If there are,
    use 'snooper.is_match' to see if any of them care about this particular
    build result.
    
    """
    s = set()
    for result_key in build_keylist:
       receipt, client_info, results =  coord.db_get_result_info(result_key)

       # are there any snoopers interested in this package?
       package = client_info['package']
       x = snoopers_per_package.get(package, [])
       for snooper in x:
           # if is_match returns true, then yes: store key for later return.
           if snooper.is_match(receipt, client_info, results):
               snooper_key = build_snoopers_rev[snooper]
               s.add(snooper_key)

    return list(s)

def notify_pubsubhubbub_server(server, *rss_urls):
    """
    Notify the given pubsubhubbub server that the given RSS URLs have changed.

    Basically the same as pubsubhubbub_publish.publish, but ignore errors.
    
    """
    try:
        push_publish(server, *rss_urls)
        print '*** notifying PuSH server: %s' % server, rss_urls
        return True
    except PublishError, e:
        print 'error notifying PuSH server %s' % (server,)
        traceback.print_exc()
        
    return False

class BuildSnooper(object):
    def generate_rss(self, pb_coord, base_url):
        pass
    
    def is_match(self, receipt, client_info, results):
        pass

class BuildSnooper_All(object):
    def __init__(self, only_failures=False):
        self.report_successes = not only_failures

    def __str__(self):
        modifier = 'failed'
        if self.report_successes:
            modifier = 'all'
        return 'Report on %s builds' % modifier

    def is_match(self, *args):
        (receipt, client_info, results) = args
        success = client_info['success']
        
        if not self.report_successes and success:
            return False
            
        return True

    def generate_rss(self, pb_coord, package_url, per_result_url,
                     source_url=''):

        it = []
        keys = list(reversed(sorted(pb_coord.db.keys())))
        now = datetime.now()
        a_week = timedelta(days=1)
        
        for n, k in enumerate(keys):
            (receipt, client_info, results_list) = pb_coord.db[k]
            tagset = client_info['tags']

            t = receipt['time']
            t = datetime.fromtimestamp(t)

            if now - t > a_week:
                break
            
            it.append((t, (tagset, receipt, client_info, results_list)))

        if not self.report_successes:
            it = [ (t, v) for (t, v) in it if not v[2]['success'] ]
        
        rss_items = []
        for n, (_, v) in enumerate(it):
            if n > MAX:
                break
            
            tagset = sorted([ x for x in list(v[0]) if not x.startswith('__')])
            tagset = ", ".join(tagset)

            _, receipt, client_info, _ = v
            result_key = receipt['result_key']
            status = client_info['success']

            x = []
            if status:
                title = 'Package %s build succeeded (tags %s)' % \
                        (client_info['package'], tagset)
                x.append("status: success")
            else:
                title = 'Package %s build FAILED (tags %s)' % \
                        (client_info['package'], tagset)
                x.append("status: failure")

            x.append("result_key: %s" % (receipt['result_key'],))
            x.append("package: %s" % (client_info['package'],))
            x.append("build host: %s" % (client_info['host'],)) # @CTB XSS
            x.append("build arch: %s" % (client_info['arch'],))

            tags = list(client_info['tags'])
            x.append("tags: %s" % (", ".join(tags)))
            description = "<br>".join(x)

            pubDate = datetime.fromtimestamp(v[1]['time'])

            link = per_result_url % dict(result_key=result_key,
                                         package=client_info['package'])

            source_obj = Source('package build & test information for "%s"' % client_info['package'], source_url)
            
            item = RSSItem(title=title,
                           link=link,
                           description=description,
                           guid=Guid(link),
                           pubDate=pubDate,
                           source=source_obj)

            rss_items.append(item)

        rss = PuSH_RSS2(
            title = "pony-build feed",
            link = 'XXX',
            description = 'all package build & test information',

            lastBuildDate = datetime.now(),
            items=rss_items
          )

        fp = StringIO()
        rss.write_xml(fp)
        return fp.getvalue()
        
class PackageSnooper(BuildSnooper):
    def __init__(self, package_name, only_failures=False, register=True):
        self.package_name = package_name
        self.report_successes = not only_failures
        if register:
            register_snooper_for_package(package_name, self)

    def __str__(self):
        modifier = 'failed'
        if self.report_successes:
            modifier = 'all'
        return "Report on %s builds for package '%s'" % (modifier,
                                                         self.package_name,)

    def generate_rss(self, pb_coord, package_url, per_result_url,
                     source_url=''):
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

            pubDate = datetime.fromtimestamp(v[0]['time'])

            link = per_result_url % dict(result_key=result_key,
                                         package=self.package_name)

            source_obj = Source('package build & test information for "%s"' % self.package_name, source_url)
            
            item = RSSItem(title=title,
                           link=link,
                           description=description,
                           guid=Guid(link),
                           pubDate=pubDate,
                           source=source_obj)

            rss_items.append(item)

        rss = PuSH_RSS2(
            title = "pony-build feed for %s" % (self.package_name,),
            link = package_url % dict(package=self.package_name),
            description = 'package build & test information for "%s"' \
                % self.package_name,

            lastBuildDate = datetime.now(),
            items=rss_items
          )

        fp = StringIO()
        rss.write_xml(fp)
        return fp.getvalue()
        
    def is_match(self, *args):
        (receipt, client_info, results) = args
        assert self.package_name == client_info['package']
        success = client_info['success']
        
        if not self.report_successes and success:
            return False
            
        return True

###

class PuSH_RSS2(RSS2):
    def publish_extensions(self, handler):
        pass
        # is this necessary? it breaks Firefoxes RSS reader...
        #_element(handler, "atom:link", "", dict(rel='hub', href='http://pubsubhubbub.appspot.com'))
