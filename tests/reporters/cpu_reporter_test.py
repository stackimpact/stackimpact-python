
import time
import unittest
import random
import threading
import sys
import traceback

import stackimpact
from stackimpact.runtime import runtime_info


class CPUReporterTestCase(unittest.TestCase):

    def test_record_profile(self):
        if runtime_info.OS_WIN:
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )
        agent.cpu_reporter.start()

        def record():
            agent.cpu_reporter.record(2)

        record_t = threading.Thread(target=record)
        record_t.start()

        def cpu_work_main_thread():
            for i in range(0, 1000000):
                text = "text1" + str(i)
                text = text + "text2"
        cpu_work_main_thread()

        record_t.join()

        #print(agent.cpu_reporter.profile)
    
        self.assertTrue('cpu_work_main_thread' in str(agent.cpu_reporter.profile))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
