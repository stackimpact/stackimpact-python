
import time
import unittest
import sys

import stackimpact
from stackimpact.runtime import runtime_info, min_version
from stackimpact.metric import Metric


class ProcessReporterTestCase(unittest.TestCase):

    def test_report(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )
        agent.process_reporter.start()

        agent.process_reporter.report()
        time.sleep(0.1)
        agent.process_reporter.report()

        metrics = agent.process_reporter.metrics

        if not runtime_info.OS_WIN:
            self.is_valid(metrics, Metric.TYPE_COUNTER, Metric.CATEGORY_CPU, Metric.NAME_CPU_TIME, 0, float("inf"))
            self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_CPU, Metric.NAME_CPU_USAGE, 0, float("inf"))

        if not runtime_info.OS_WIN:
            self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_MAX_RSS, 0, float("inf"))

        if runtime_info.OS_LINUX:
            self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_CURRENT_RSS, 0, float("inf"))
            self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_VM_SIZE, 0, float("inf"))

        self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_GC, Metric.NAME_GC_COUNT, 0, float("inf"))
        if min_version(3, 4):
            self.is_valid(metrics, Metric.TYPE_COUNTER, Metric.CATEGORY_GC, Metric.NAME_GC_COLLECTIONS, 0, float("inf"))
            self.is_valid(metrics, Metric.TYPE_COUNTER, Metric.CATEGORY_GC, Metric.NAME_GC_COLLECTED, 0, float("inf"))
            self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_GC, Metric.NAME_GC_UNCOLLECTABLE, 0, float("inf"))

        self.is_valid(metrics, Metric.TYPE_STATE, Metric.CATEGORY_RUNTIME, Metric.NAME_THREAD_COUNT, 0, float("inf"))

        agent.destroy()


    def is_valid(self, metrics, typ, category, name, min_value, max_value):
        key = typ + category + name

        self.assertTrue(key in metrics, key)

        m = metrics[key]
        if m.has_measurement():
            #print(typ, category, name, m.measurement.value)
            self.assertTrue(m.measurement.value >= min_value and m.measurement.value <= max_value, key)


if __name__ == '__main__':
    unittest.main()
