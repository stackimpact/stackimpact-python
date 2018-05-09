
import time
import unittest
import random
import threading
import sys
import traceback

import stackimpact
from stackimpact.runtime import runtime_info


# virtualenv -p python3 venv_tf
# source venv_tf/bin/activate
# pip install tensorflow
# pip install keras

class TFProfilerTestCase(unittest.TestCase):

    def test_record_tf_profile(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            auto_profiling = False,
            debug = True
        )

        agent.tf_reporter.profiler.reset()

        if not agent.tf_reporter.profiler.ready:
            return

        def record():
            agent.tf_reporter.profiler.start_profiler()
            time.sleep(1)
            agent.tf_reporter.profiler.stop_profiler()


        record_t = threading.Thread(target=record)
        record_t.start()

        import tensorflow as tf

        x = tf.random_normal([1000, 1000])
        y = tf.random_normal([1000, 1000])
        res = tf.matmul(x, y)

        with tf.Session() as sess:
            sess.run(res)

        record_t.join()

        profile = agent.tf_reporter.profiler.build_profile(1)[0]['profile'].to_dict()
        #print(profile)
        self.assertTrue('test_record_tf_profile' in str(profile))

        profile = agent.tf_reporter.profiler.build_profile(1)[1]['profile'].to_dict()
        #print(profile)
        self.assertTrue('test_record_tf_profile' in str(profile))

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
