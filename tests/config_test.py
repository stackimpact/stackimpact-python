import unittest
import sys

import stackimpact


class ConfigTestCase(unittest.TestCase):

    def test_set_get_props(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        self.assertFalse(agent.config.is_profiling_disabled())
        agent.config.set_profiling_disabled(True)
        self.assertTrue(agent.config.is_profiling_disabled())

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
