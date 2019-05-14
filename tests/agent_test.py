import unittest
import sys
import threading
import random
import time

import stackimpact
from stackimpact.runtime import runtime_info, min_version


# python3 -m unittest discover -v -s tests -p *_test.py

class AgentTestCase(unittest.TestCase):

    def test_run_in_main_thread(self):
        if runtime_info.OS_WIN:
            return

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


    def test_profile(self):
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

        span = agent.profile()
        for i in range(0, 2000000):
            random.randint(1, 1000000)
        span.stop()

        agent.cpu_reporter.report()
    
        self.assertTrue('test_profile' in str(agent.message_queue.queue))

        agent.destroy()


    def test_with_profile(self):
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

        with agent.profile():
            for i in range(0, 2000000):
                random.randint(1, 1000000)

        agent.cpu_reporter.report()
    
        self.assertTrue('test_with_profile' in str(agent.message_queue.queue))

        agent.destroy()


    def test_cpu_profile(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )

        messages = []
        def add_mock(topic, message):
            messages.append(message)
        agent.message_queue.add = add_mock

        agent.start_cpu_profiler()

        for j in range(0, 2000000):
            random.randint(1, 1000000)

        agent.stop_cpu_profiler()

        self.assertTrue('test_cpu_profile' in str(messages))

        agent.destroy()


    def test_allocation_profile(self):
        if runtime_info.OS_WIN or not min_version(3, 4):
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )
        
        messages = []
        def add_mock(topic, message):
            messages.append(message)
        agent.message_queue.add = add_mock

        agent.start_allocation_profiler()

        mem1 = []
        for i in range(0, 1000):
            obj1 = {'v': random.randint(0, 1000000)}
            mem1.append(obj1)

        agent.stop_allocation_profiler()

        self.assertTrue('agent_test.py' in str(messages))

        agent.destroy()


    def test_block_profile(self):
        if runtime_info.OS_WIN or not min_version(3, 4):
            return

        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )

        messages = []
        def add_mock(topic, message):
            messages.append(message)
        agent.message_queue.add = add_mock

        agent.start_block_profiler()

        def blocking_call():
            time.sleep(0.1)

        for i in range(5):
            blocking_call()

        agent.stop_block_profiler()

        self.assertTrue('blocking_call' in str(messages))

        agent.destroy()
        

if __name__ == '__main__':
    unittest.main()
