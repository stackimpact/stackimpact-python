
import time
import unittest
import random
import threading

import stackimpact
from stackimpact.runtime import min_version, runtime_info


class AllocationProfilerTestCase(unittest.TestCase):

    def test_record_allocation_profile(self):
        if runtime_info.OS_WIN or not min_version(3, 4):
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )

        agent.allocation_reporter.profiler.reset()

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
            agent.allocation_reporter.profiler.start_profiler()
            time.sleep(2)
            agent.allocation_reporter.profiler.stop_profiler()

        t = threading.Thread(target=record)
        t.start()

        # simulate leak
        mem_leak5()

        t.join()

        profile = agent.allocation_reporter.profiler.build_profile(2)[0]['profile'].to_dict()
        #print(str(profile))

        self.assertTrue('allocation_profiler_test.py' in str(profile))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
