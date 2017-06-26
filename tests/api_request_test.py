import unittest
import sys
import json
import os
import socket

import stackimpact
from stackimpact.api_request import APIRequest

from test_server import TestServer


class ApiRequestTestCase(unittest.TestCase):

    def test_post(self):
        server = TestServer(5001)
        server.set_response_data(json.dumps({'c': 3, 'd': 4}))
        server.start()

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            app_environment = 'test',
            app_version = '1.1.1',
            debug = True
        )

        api_request = APIRequest(agent)

        api_request.post('test', {'a': 1, 'b': 2})
        data = json.loads(server.get_request_data())
        self.assertEqual(data['run_id'], agent.run_id)
        self.assertEqual(data['run_ts'], agent.run_ts)
        self.assertEqual(data['process_id'], os.getpid())
        self.assertEqual(data['host_name'], socket.gethostname())
        self.assertEqual(data['runtime_type'], 'python')
        self.assertEqual(data['runtime_version'], '{0.major}.{0.minor}.{0.micro}'.format(sys.version_info))
        self.assertEqual(data['agent_version'], agent.AGENT_VERSION)
        self.assertEqual(data['app_name'], 'TestPythonApp')
        self.assertEqual(data['app_environment'], 'test')
        self.assertEqual(data['app_version'], '1.1.1')
        self.assertEqual(data['payload'], {'a': 1, 'b': 2})

        agent.destroy()
        server.join()


if __name__ == '__main__':
    unittest.main()
