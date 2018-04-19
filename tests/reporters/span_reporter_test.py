
import time
import unittest
import random
import threading
import sys
import traceback

import stackimpact
from stackimpact.runtime import min_version


class SpanReporterTestCase(unittest.TestCase):

    def test_record_span(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )
        agent.span_reporter.start()

        for i in range(10):
            agent.span_reporter.record_span("span1", 10);

        span_counters = agent.span_reporter.span_counters;
        agent.span_reporter.report();

        counter = span_counters['span1']
        #print(counter)

        self.assertEqual(counter.name, 'span1')
        self.assertEqual(counter.measurement, 10000)

        agent.destroy()


if __name__ == '__main__':
    unittest.main()
