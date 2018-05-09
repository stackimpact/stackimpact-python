
import sys
import threading
import traceback
import collections

from ..runtime import runtime_info, patch, unpatch
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame


class SpanReporter(object):

    MAX_QUEUED_EXC = 100


    def __init__(self, agent):
        self.agent = agent
        self.started = False
        self.report_timer = None
        self.span_counters = None
        self.span_lock = threading.Lock()


    def setup(self):
        pass


    def destroy(self):
        pass


    def reset(self):
        self.span_counters = dict()


    def start(self):
        if not self.agent.get_option('auto_profiling'):
            return

        if self.started:
            return
        self.started = True

        self.reset()

        self.report_timer = self.agent.schedule(60, 60, self.report)


    def stop(self):
        if not self.started:
            return
        self.started = False

        self.report_timer.cancel()
        self.report_timer = None
    

    def record_span(self, name, duration):
        if not self.started:
            return

        counter = None
        if name in self.span_counters:
            counter = self.span_counters[name]
        else:
            with self.span_lock:
                counter = Breakdown(name)
                self.span_counters[name] = counter
    
        counter.update_p95(duration * 1000)


    def report(self):
        for name, counter in self.span_counters.items():
            counter.evaluate_p95();

            metric = Metric(self.agent, Metric.TYPE_STATE, Metric.CATEGORY_SPAN, counter.name, Metric.UNIT_MILLISECOND)
            measurement = metric.create_measurement(Metric.TRIGGER_TIMER, counter.measurement, 60)
            self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()
