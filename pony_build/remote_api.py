### public XML-RPC API.

class XmlRpcFunctions(object):
    def __init__(self, coordinator, client_ip):
        self.coordinator = coordinator
        self.client_ip = client_ip

    def add_results(self, client_info, results):
        """
        Add build results to the server.

        'client_info' is a dictionary of client information; 'results' is
        a list of dictionaries, with each dict containing build/test info
        for a single step.
        """
        # assert that they have the right methods ;)
        client_info.keys()
        for d in results:
            d.keys()

        client_ip = self.client_ip
        coordinator = self.coordinator

        try:
            key = coordinator.add_results(client_ip, client_info, results)
        except:
            traceback.print_exc()
            raise

        return key

    def get_results(self, results_key):
        x = self.coordinator.db_get_result_info(results_key)
        (receipt, client_info, results) = x

        return x

    def check_should_build(self, client_info, reserve_build=True,
                           build_allowance=0):
        """
        Should a client build, according to the server?

        Returns a tuple (flag, reason).  'flag' is bool; 'reason' is a
        human-readable string.

        A 'yes' (True) could be for several reasons, including no build
        result for this tagset, a stale build result (server
        configurable), or a request to force-build.
        """
        flag, reason = self.coordinator.check_should_build(client_info)
        print (flag, reason)
        if flag:
            if reserve_build:
                print 'RESERVING BUILD'
                self.coordinator.notify_build(client_info['package'],
                                              client_info, build_allowance)
            return True, reason
        return False, reason

    def get_tagsets_for_package(self, package):
        """
        Get the list of tagsets containing build results for the given package.
        """

        # here 'tagsets' will be ImmutableSet objects
        tagsets = self.coordinator.get_tagsets_for_package(package)

        # convert them into lists, then return
        return [ list(x) for x in tagsets ]

    def get_last_result_for_tagset(self, package, tagset):
        """
        Get the most recent result for the given package/tagset combination.
        """
        return self.coordinator.get_last_result_for_tagset(package, tagset)
