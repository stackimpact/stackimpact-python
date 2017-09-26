
import time
import unittest
import random
import threading
import sys
import traceback

import stackimpact
from stackimpact.runtime import min_version


class ErrorReporterTestCase(unittest.TestCase):

    def test_add_exception(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )
        agent.error_reporter.start()

        try:
            raise ValueError('test_exc_1')
        except:
            traceback.print_exc()

        time.sleep(1.1)

        profile_handled_exc = agent.error_reporter.profile
        #print(profile_handled_exc)

        self.assertTrue('ValueError: test_exc_1' in str(profile_handled_exc))
        self.assertTrue('test_add_exception' in str(profile_handled_exc))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
