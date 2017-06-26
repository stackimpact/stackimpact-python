from __future__ import division

import random
import math

from .utils import timestamp, base64_encode
from .metric import Metric

class ProfilerScheduler:

    def __init__(self, agent, record_interval, record_duration, report_interval, record_func, report_func):
        self.agent = agent
        self.record_interval = record_interval
        self.record_duration = record_duration
        self.report_interval = report_interval
        self.record_func = record_func
        self.report_func = report_func
        self.random_timer = None
        self.record_timer = None
        self.report_timer = None


    def start(self):
        if self.record_func:
            def random_delay():
                timeout = random.randint(0, round(self.record_interval - self.record_duration))
                self.random_timer = self.agent.delay(timeout, self.execute_record)

            self.record_timer = self.agent.schedule(self.record_interval, self.record_interval, random_delay)

        self.report_timer = self.agent.schedule(self.report_interval, self.report_interval, self.execute_report)


    def destroy(self):
        if self.random_timer:
            self.random_timer.cancel()
            self.random_timer = None

        if self.record_timer:
            self.record_timer.cancel()
            self.record_timer = None

        if self.report_timer:
            self.report_timer.cancel()
            self.report_timer = None


    def execute_record(self):
        with self.agent.profiler_lock:
            try:
                self.record_func(self.record_duration)
            except Exception:
                self.agent.exception()


    def execute_report(self):
        with self.agent.profiler_lock:
            try:
                self.report_func()
            except Exception:
                self.agent.exception()

