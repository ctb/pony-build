"""
The XML-RPC & internal API for pony-build.

You can get the current coordinator object by calling
pony_build.server.get_coordinator().
"""

import time
import sets

class PonyBuildCoordinator(object):
    def __init__(self, db=None):
        self.results_list = []
        self.db = db

        if db is not None:
            keys = [ (int(k), k) for k in db.keys() ]
            keys.sort()
            self.results_list = [ db[k] for (_, k) in keys ]
            self._process_results()

    def add_results(self, client_ip, client_info, results):
        print client_ip
        print client_info
        print results
        print '---'
        receipt = dict(time=time.time(), client_ip=client_ip)

        key = self.db_add_result(receipt, client_ip, client_info, results)
        self._process_results()

    def _process_results(self):
        self._hosts = hosts = {}
        self._archs = archs = {}
        self._packages = packages = {}

        for n, (receipt, client_info, results_list) in enumerate(self.results_list):
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

    def db_get_result_info(self, result_id):
        return self.results_list[int(result_id)]

    def db_add_result(self, receipt, client_ip, client_info, results):
        next_key = str(len(self.results_list))
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
                if client_info['package_name'] == package:
                    d[arch] = (receipt, client_info, results)

        return d

    def get_unique_tagset_for_package(self, package,
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
            arch = client_info['arch']
            host = client_info['host']

            tags = list(client_info['tags'])
            if not no_arch:
                tags.append('__' + arch)
            if not no_host:
                tags.append('__' + host)
                
            key = sets.ImmutableSet(tags)

            # check if already stored
            if key in d:
                receipt2, _, _ = d[key]
                # store the more recent one...
                if receipt['time'] > receipt2['time']:
                    d[key] = receipt, client_info, results_list
            else:
                d[key] = receipt, client_info, results_list

        return d
