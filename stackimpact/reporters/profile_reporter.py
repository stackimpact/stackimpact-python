from __future__ import division

import os
import sys
import time
import threading
import re
import random

from ..runtime import min_version, runtime_info
from ..utils import timestamp
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame


class ProfilerConfig(object):

    def __init__(self):
      self.log_prefix = None
      self.max_profile_duration = None
      self.max_span_duration = None
      self.max_span_count = None
      self.span_interval = None
      self.report_interval = None
      self.report_only = False


class ProfileReporter:
  
    def __init__(self, agent, profiler, config):
        self.agent = agent
        self.profiler = profiler
        self.config = config
        self.started = False
        self.span_timer = None
        self.span_timeout = None
        self.random_timer = None
        self.report_timer = None
        self.profile_start_ts = None
        self.profile_duration = None
        self.span_count = None
        self.span_active = False
        self.span_start_ts = None
        self.span_trigger = None


    def setup(self):
        self.profiler.setup()


    def start(self):
        if not self.profiler.ready:
            return

        if self.started:
            return
        self.started = True

        self.reset()

        if self.agent.get_option('auto_profiling'):
            if not self.config.report_only:
                def random_delay():
                    timeout = random.randint(0, round(self.config.span_interval - self.config.max_span_duration))
                    self.random_timer = self.agent.delay(timeout, self.start_profiling, False, True)

                self.span_timer = self.agent.schedule(0, self.config.span_interval, random_delay)

            self.report_timer = self.agent.schedule(self.config.report_interval, self.config.report_interval, self.report)


    def stop(self):
        if not self.started:
            return

        self.started = False

        if self.span_timer:
            self.span_timer.cancel()
            self.span_timer = None

        if self.random_timer:
            self.random_timer.cancel()
            self.random_timer = None

        if self.report_timer:
            self.report_timer.cancel()
            self.report_timer = None

        self.stop_profiling()


    def destroy(self):
        self.profiler.destroy()


    def reset(self):
        self.profiler.reset()
        self.profile_start_ts = timestamp()
        self.profile_duration = 0
        self.span_count = 0
        self.span_trigger = Metric.TRIGGER_TIMER


    def start_profiling(self, api_call, with_timeout):
        if not self.started:
            return False

        if self.profile_duration > self.config.max_profile_duration:
            self.agent.log(self.config.log_prefix + ': max profiling duration reached.')
            return False

        if api_call and self.span_count > self.config.max_span_count:
            self.agent.log(self.config.log_prefix + ': max recording count reached.')
            return False

        if self.agent.profiler_active:
            self.agent.log(self.config.log_prefix + ': profiler lock exists.')
            return False

        self.agent.profiler_active = True
        self.agent.log(self.config.log_prefix + ': started.')

        try:
            self.profiler.start_profiler()
        except Exception:
            self.agent.profiler_active = False
            self.exception()
            return False

        if with_timeout:
            self.span_timeout = self.agent.delay(self.config.max_span_duration, self.stop_profiling)

        self.span_count = self.span_count + 1
        self.span_active = True
        self.span_start_ts = time.time()

        if api_call:
            self.span_trigger = Metric.TRIGGER_API

        return True


    def stop_profiling(self):
        if not self.span_active:
            return
        self.span_active = False

        try:
            self.profile_duration = self.profile_duration + time.time() - self.span_start_ts
            self.profiler.stop_profiler()
        except Exception:
            self.exception()

        self.agent.profiler_active = False

        if self.span_timeout:
            self.span_timeout.cancel()

        self.agent.log(self.config.log_prefix + ': stopped.')


    def report(self, with_interval=False):
        if not self.started:
          return

        if with_interval:
          if self.profile_start_ts > timestamp() - self.config.report_interval:
            return
          elif self.profile_start_ts < timestamp() - 2 * self.config.report_interval:
            self.reset()
            return

        if not self.config.report_only and self.profile_duration == 0:
          return

        self.agent.log(self.config.log_prefix + ': reporting profile.')

        profile_data = self.profiler.build_profile(self.profile_duration)

        for data in profile_data:
          metric = Metric(self.agent, Metric.TYPE_PROFILE, data['category'], data['name'], data['unit'])
          metric.create_measurement(self.span_trigger, data['profile'].measurement, data['unit_interval'], data['profile'])
          self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()
