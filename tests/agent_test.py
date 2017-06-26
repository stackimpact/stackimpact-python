import unittest
import sys
import threading

import stackimpact


# python -m unittest discover -s tests -p *_test.py

class AgentTestCase(unittest.TestCase):

    def test_run_in_main_thread(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        result = {}

        def _run():
            result['thread_id'] = threading.current_thread().ident

        def _thread():
            agent.run_in_main_thread(_run)

        t = threading.Thread(target=_thread)
        t.start()
        t.join()

        self.assertEqual(result['thread_id'], threading.current_thread().ident)

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
