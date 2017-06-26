
import time
import unittest
import random
import threading

import stackimpact
from stackimpact.runtime import min_version


class AllocationReporterTestCase(unittest.TestCase):

    def test_record_allocation_profile(self):
        if not min_version(3, 4):
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        mem1 = []
        def mem_leak(n = 100000):
            mem2 = []
            for i in range(0, n):
                mem1.append(random.randint(0, 1000))
                mem2.append(random.randint(0, 1000))

        def mem_leak2():
            mem_leak()

        def mem_leak3():
            mem_leak2()

        def mem_leak4():
            mem_leak3()

        def mem_leak5():
            mem_leak4()

        result = {}
        def record():
            agent.allocation_reporter.record(2)

        t = threading.Thread(target=record)
        t.start()

        # simulate leak
        mem_leak5()

        t.join()

        #print(agent.allocation_reporter.profile)

        self.assertTrue('allocation_reporter_test.py' in str(agent.allocation_reporter.profile))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
