import unittest
import sys
import random
import time

import stackimpact
from stackimpact.profiler_scheduler import ProfilerScheduler


class ProfilerSchedulerTestCase(unittest.TestCase):


    def test_start_profiler(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        stats = {
            "records": 0,
            "reports": 0,
        }

        def record_func(duration):
            stats["records"] += 1

        def report_func():
            stats["reports"] += 1

        ps = ProfilerScheduler(agent, 0.010, 0.002, 0.050, record_func, report_func)
        ps.start()

        time.sleep(0.150)

        self.assertFalse(stats["records"] < 10)
        self.assertFalse(stats["reports"] < 2)

        ps.stop()
        agent.destroy()



if __name__ == '__main__':
    unittest.main()
