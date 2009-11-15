# @CTB have a generated ascii key, or a name, for each snooper?  how to refer
# to it in an RSS feed?

import datetime
from cStringIO import StringIO
from .PyRSS2Gen import RSS2, RSSItem, _element, Guid

SERVER='XXX'

build_snoopers = {}

def add_snooper(snooper, key):
    assert key not in build_snoopers
    build_snoopers[key] = snooper

def register_snooper_for_package(package, snooper):
    pass

def check_new_builds(*build_keylist):
    pass

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
            if status:
                title = 'Package %s build succeeded (tags %s)' % \
                        (self.package_name, tagset)
                description = "status: success"
            else:
                title = 'Package %s build FAILED (tags %s)' % \
                        (self.package_name, tagset)
                description = "status: failure"

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
