import unittest
import sys
import json

import stackimpact
from test_server import TestServer



class ConfigLoaderTest(unittest.TestCase):

    def test_load(self):
        server = TestServer(5008)
        server.set_response_data('{"profiling_disabled":"yes"}')
        server.start()

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5008',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        agent.config_loader.load()
        
        self.assertTrue(agent.config.is_profiling_disabled())

        agent.destroy()
        server.join()

if __name__ == '__main__':
    unittest.main()
