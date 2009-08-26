"""
The XML-RPC & internal API for pony-build.

You can get the current coordinator object by calling
pony_build.server.get_coordinator().
"""

import time
import sets
from datetime import datetime, timedelta

def build_tagset(client_info, no_arch=False, no_host=False):
    arch = client_info['arch']
    host = client_info['host']
    package = client_info['package']

    tags = list(client_info['tags'])

    tags.append('__package=' + package)
    if not no_arch:
        tags.append('__arch=' + arch)
    if not no_host:
        tags.append('__host=' + host)

    tagset = sets.ImmutableSet(tags)
    return tagset

class PonyBuildCoordinator(object):
    def __init__(self, db=None):
        self.results_list = []
        self.db = db

        if db is not None:
            keys = [ (int(k), k) for k in db.keys() ]
            keys.sort()
            self.results_list = [ db[k] for (_, k) in keys ]
            
        self._process_results()
        self.request_build = {}

    def add_results(self, client_ip, client_info, results):
        print client_ip
        print client_info
        print results
        print '---'
        receipt = dict(time=time.time(), client_ip=client_ip)

        key = self.db_add_result(receipt, client_ip, client_info, results)
        self._process_results()

    def set_request_build(self, client_info, value):
        tagset = build_tagset(client_info)
        self.request_build[tagset] = value

    def check_should_build(self, client_info):
        package = client_info['package']
        tagset = build_tagset(client_info)
        print 'CHECK TAGSET', tagset
        
        last_build = self.get_unique_tagset_for_package(package)
        print 'LAST BUILD', last_build.keys()

        build = False
        if tagset in self.request_build:
            del self.request_build[tagset]
            build = True
        elif tagset in last_build:
            last_t = last_build[tagset][0]['time']
            last_t = datetime.fromtimestamp(last_t)
            
            now = datetime.now()
            diff = now - last_t
            if diff >= timedelta(1): # 1 day, default
                build = True
            else:
                print 'last build was %s ago; too recent to build' % (diff,)

            # was it successful?
            success = last_build[tagset][1]['success']
            if not success:
                print 'last build was unsuccessful; go!'
                build = True
        else:
            # tagset not in last_build
            print 'NO BUILD recorded for %s; build!' % (tagset,)
            build = True

        return build

    def _process_results(self):
        self._hosts = hosts = {}
        self._archs = archs = {}
        self._packages = packages = {}

        for n, (receipt, client_info, results_list) in enumerate(self.results_list):
            host = client_info['host']
            arch = client_info['arch']
            pkg = client_info['package']

            l = hosts.get(host, [])
            l.append(n)
            hosts[host] = l

            l = archs.get(arch, [])
            l.append(n)
            archs[arch] = l

            l = packages.get(pkg, [])
            l.append(n)
            packages[pkg] = l

    def db_get_result_info(self, result_id):
        return self.results_list[int(result_id)]

    def db_add_result(self, receipt, client_ip, client_info, results):
        next_key = str(len(self.results_list))
        receipt['result_key'] = next_key
        
        if self.db is not None:
            self.db[next_key] = (receipt, client_info, results)
            self.db.sync()
            
        self.results_list.append((receipt, client_info, results))
        return next_key

    def get_all_packages(self):
        k = self._packages.keys()
        k.sort()
        return k

    def get_last_result_for_package(self, package):
        x = self._packages.get(package)
        if x:
            return x[-1]
        return None

    def get_all_results_for_package(self, package):
        l = self._packages.get(package, [])
        if l:
            return [ self.results_list[n] for n in l ]
        return []

    def get_all_archs(self):
        k = self._archs.keys()
        k.sort()
        return k

    def get_last_result_for_arch(self, arch):
        x = self._archs.get(arch)
        if x:
            return x[-1]
        return None
    

    def get_all_hosts(self):
        k = self._hosts.keys()
        k.sort()
        return k

    def get_last_result_for_host(self, host):
        x = self._hosts.get(host)
        if x:
            return x[-1]
        return None

    def get_latest_arch_result_for_package(self, package):
        d = {}
        for arch, l in self._archs.iteritems():
            for n in l:
                print n
                receipt, client_info, results = self.results_list[n]
                if client_info['package'] == package:
                    d[arch] = (receipt, client_info, results)

        return d

    def get_unique_tagsets_for_package(self, package,
                                      no_host=False, no_arch=False):
        """
        Get the 'unique' set of latest results for the given package,
        based on tags, host, and architecture.  'no_host' says to
        collapse multiple hosts, 'no_arch' says to ignore multiple
        archs.

        Returns a dictionary of (receipt, client_info, results_list)
        tuples indexed by the set of keys used for 'uniqueness',
        i.e. an ImmutableSet of the tags + host + arch.  For display
        purposes, anything beginning with a '__' should be filtered
        out of the keys.
        
        """
        result_indices = self._packages.get(package)
        if not result_indices:
            return {}

        d = {}
        for n in result_indices:
            receipt, client_info, results_list = self.results_list[n]
            key = build_tagset(client_info, no_host=no_host, no_arch=no_arch)
            
            # check if already stored
            if key in d:
                receipt2, _, _ = d[key]
                # store the more recent one...
                if receipt['time'] > receipt2['time']:
                    d[key] = receipt, client_info, results_list
            else:
                d[key] = receipt, client_info, results_list

        return d

    def get_tagsets_for_package(self, package, no_host=False, no_arch=False):
        result_indices = self._packages.get(package)
        if not result_indices:
            return []

        x = set()
        for n in result_indices:
            receipt, client_info, results_list = self.results_list[n]
            key = build_tagset(client_info, no_host=no_host, no_arch=no_arch)

            x.add(key)

        return list(x)

    def get_last_result_for_tagset(self, package, tagset):
        result_indices = self._packages.get(package)
        if not result_indices:
            return 0

        result_indices.reverse()
        for n in result_indices:
            receipt, client_info, results_list = self.results_list[n]
            key = build_tagset(client_info)

            if set(tagset) == set(key):
                return (receipt, client_info, results_list)

        return 0
