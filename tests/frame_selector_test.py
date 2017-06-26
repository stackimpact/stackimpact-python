import unittest
import sys
import threading
import os

import stackimpact


class FrameSelectorTestCase(unittest.TestCase):

    def test_skip_stack(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        test_agent_file = os.path.realpath(stackimpact.__file__)
        self.assertTrue(agent.frame_selector.is_agent_frame(test_agent_file))

        test_system_file = os.path.realpath(threading.__file__)
        self.assertTrue(agent.frame_selector.is_system_frame(test_system_file))

        agent.frame_selector.add_http_frame_regexp(os.path.join('a', 'b', 'c'))
        self.assertTrue(agent.frame_selector.is_http_frame(os.path.join('a', 'b', 'c', 'd')))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
