
import time
import unittest
import random
import threading
import sys
import traceback

import stackimpact
from stackimpact.runtime import runtime_info


class CPUProfilerTestCase(unittest.TestCase):

    def test_record_profile(self):
        if runtime_info.OS_WIN:
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )

        agent.cpu_reporter.profiler.reset()

        def record():
            agent.cpu_reporter.profiler.start_profiler()
            time.sleep(2)
            agent.cpu_reporter.profiler.stop_profiler()


        record_t = threading.Thread(target=record)
        record_t.start()

        def cpu_work_main_thread():
            for i in range(0, 1000000):
                text = "text1" + str(i)
                text = text + "text2"
        cpu_work_main_thread()

        record_t.join()

        profile = agent.cpu_reporter.profiler.build_profile(2)[0]['profile'].to_dict()
        #print(profile)
    
        self.assertTrue('cpu_work_main_thread' in str(profile))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
