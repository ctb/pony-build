from pony_build import coordinator
import time

class Test_Coordinator_API(object):
    def setup(self):
        db = coordinator.IntDictWrapper({})
        self.coord = coordinator.PonyBuildCoordinator(db)
        
        self.some_client_info = dict(success=True,
                                     tags=['tag1'],
                                     package='package1',
                                     duration=0.1,
                                     host='test-machine',
                                     arch='foo')
        self.tagset = coordinator.build_tagset(self.some_client_info)

    def load_results(self):
        k = self.coord.add_results('127.0.0.1', self.some_client_info, [])
        return k

    def test_get_no_arch(self):
        keys = self.coord.get_all_archs()
        assert len(keys) == 0

    def test_get_arch(self):
        self.load_results()
        keys = self.coord.get_all_archs()
        assert len(keys) == 1
        assert keys[0] == 'foo'

    def test_get_no_packages(self):
        keys = self.coord.get_all_packages()
        assert len(keys) == 0

    def test_get_all_packages(self):
        self.load_results()
        keys = self.coord.get_all_packages()
        assert len(keys) == 1
        assert keys[0] == 'package1'

    def test_get_no_host(self):
        keys = self.coord.get_all_hosts()
        assert len(keys) == 0

    def test_get_host(self):
        self.load_results()
        keys = self.coord.get_all_hosts()
        assert len(keys) == 1
        assert keys[0] == 'test-machine'

    def test_get_unique_tagsets(self):
        """
        We should only have a single tagset for our results.
        """
        
        self.load_results()

        x = self.coord.get_unique_tagsets_for_package('package1')
        x = x.keys()
        
        assert [ self.tagset ] == x

    def test_get_unique_tagsets_is_single(self):
        """
        We should only have a single tagset for our results, even if we
        load twice.
        """
        
        self.load_results()
        self.load_results()

        x = self.coord.get_unique_tagsets_for_package('package1')
        x = x.keys()
        
        assert [ self.tagset ] == x

    def test_check_should_build_no_results(self):
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_too_recent(self):
        self.load_results()
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_too_old(self):
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0             # force "old" result
        self.coord.db[k] = receipt, client_info, results

        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]
        
    def test_check_should_build_unsuccessful(self):
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        client_info['success'] = False             # force fail
        self.coord.db[k] = receipt, client_info, results

        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_force_do_build(self):
        self.load_results()
        self.coord.set_request_build(self.some_client_info, True)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_force_dont_build(self):
        self.load_results()
        self.coord.set_request_build(self.some_client_info, False)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building(self):
        self.coord.notify_build('package1', self.some_client_info)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_2(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building...
        self.coord.notify_build('package1', self.some_client_info)

        # ...and check immediately.
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_but_is_slow(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building...
        self.coord.notify_build('package1', self.some_client_info)

        # ...but wait for longer than it took to build the last time.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]

    def test_check_should_build_is_building_but_requested(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building, and request 0.5 seconds...
        self.coord.notify_build('package1', self.some_client_info, 0.5)

        # ...and wait for longer than it took to build the last time,
        # but less than requested.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert not do_build[0]

    def test_check_should_build_is_building_but_longer_than_requested(self):
        # first, set up a forced 'old' result
        k = self.load_results()
        receipt, client_info, results = self.coord.db[k]
        receipt['time'] = 0
        self.coord.db[k] = receipt, client_info, results

        # notify of building, and request 0.1 seconds...
        self.coord.notify_build('package1', self.some_client_info, 0.1)

        # ...but wait for longer than requested.
        time.sleep(0.2)
        do_build = self.coord.check_should_build(self.some_client_info)
        assert do_build[0]
