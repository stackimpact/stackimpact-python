
import unittest
import sys
import random

import stackimpact
from stackimpact.metric import Metric,Breakdown


class MetricTestCase(unittest.TestCase):

    def test_counter_metric(self):
        stackimpact._agent = None
        agent = stackimpact.start(
            dashboard_address = 'http://localhost:5001',
            agent_key = 'key1',
            app_name = 'TestPythonApp',
            debug = True
        )

        m = Metric(agent, Metric.TYPE_COUNTER, Metric.CATEGORY_CPU, Metric.NAME_CPU_USAGE, Metric.UNIT_NONE)

        m.create_measurement(Metric.TRIGGER_TIMER, 100)
        self.assertFalse(m.has_measurement())

        m.create_measurement(Metric.TRIGGER_TIMER, 110)
        self.assertEqual(m.measurement.value, 10)

        m.create_measurement(Metric.TRIGGER_TIMER, 115)
        self.assertEqual(m.measurement.value, 5)

        agent.destroy()



    def test_profile_filter(self):
        root = Breakdown('root')
        root.measurement = 10

        child1 = Breakdown('child1')
        child1.measurement = 9
        root.add_child(child1)

        child2 = Breakdown('child2')
        child2.measurement = 1
        root.add_child(child2)

        child2child1 = Breakdown('child2child1')
        child2child1.measurement = 1
        child2.add_child(child2child1)

        root.filter(2, 3, 100)

        self.assertTrue(root.find_child('child1'))
        self.assertTrue(root.find_child('child2'))
        self.assertFalse(child2.find_child('child2child1'))


    def test_profile_depth(self):
        root = Breakdown("root")

        child1 = Breakdown("child1")
        root.add_child(child1)

        child2 = Breakdown("child2")
        root.add_child(child2)

        child2child1 = Breakdown("child2child1")
        child2.add_child(child2child1)

        self.assertEqual(root.depth(), 3)
        self.assertEqual(child1.depth(), 1)
        self.assertEqual(child2.depth(), 2)


    def test_profile_p95(self):
        root = Breakdown("root")

        child1 = Breakdown("child1")
        root.add_child(child1)

        child2 = Breakdown("child2")
        root.add_child(child2)

        child2child1 = Breakdown("child2child1")
        child2.add_child(child2child1)

        child2child1.update_p95(6.5)
        child2child1.update_p95(4.2)
        child2child1.update_p95(5.0)
        child2child1.evaluate_p95()
        root.propagate()

        self.assertEqual(root.measurement, 6.5)


    def test_profile_p95_big(self):
        root = Breakdown("root")

        for i in range(0, 10000):
            root.update_p95(200.0 + random.randint(0, 50))

        root.evaluate_p95()

        self.assertTrue(root.measurement >= 200 and root.measurement <= 250)



if __name__ == '__main__':
    unittest.main()


