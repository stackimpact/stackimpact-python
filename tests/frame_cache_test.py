import unittest
import sys
import threading
import os

import stackimpact


class FrameCacheTestCase(unittest.TestCase):

    def test_skip_stack(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        test_agent_file = os.path.realpath(stackimpact.__file__)
        self.assertTrue(agent.frame_cache.is_agent_frame(test_agent_file))

        test_system_file = os.path.realpath(threading.__file__)
        self.assertTrue(agent.frame_cache.is_system_frame(test_system_file))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
