import unittest
import sys
import json

import stackimpact
from stackimpact.utils import timestamp

from test_server import TestServer



class MessageQueueTest(unittest.TestCase):


    def test_flush(self):
        server = TestServer(5005)
        server.start()

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5005',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        m = {
            'm1': 1
        }
        agent.message_queue.add('t1', m)

        m = {
            'm2': 2
        }        
        agent.message_queue.add('t1', m)

        agent.message_queue.queue[0]['added_at'] = timestamp() - 20 * 60

        agent.message_queue.flush()

        data = json.loads(server.get_request_data())
        self.assertEqual(data['payload']['messages'][0]['content']['m2'], 2)

        agent.destroy()
        server.join()


    def test_flush_fail(self):
        server = TestServer(5006)
        server.set_response_data("unparsablejson")
        server.start()

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5006',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        m = {
            'm1': 1
        }
        agent.message_queue.add('t1', m)

        m = {
            'm2': 2
        }        
        agent.message_queue.add('t1', m)

        agent.message_queue.flush()
        self.assertEqual(len(agent.message_queue.queue), 2)

        agent.destroy()
        server.join()

if __name__ == '__main__':
    unittest.main()
