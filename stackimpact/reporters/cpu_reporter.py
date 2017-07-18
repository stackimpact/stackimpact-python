from __future__ import division

import os
import sys
import time
import threading
import re
import signal

from ..runtime import min_version, runtime_info
from ..profiler_scheduler import ProfilerScheduler
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame



class CPUReporter:
    SAMPLING_RATE = 0.01
    MAX_TRACEBACK_SIZE = 25 # number of frames


    def __init__(self, agent):
        self.agent = agent
        self.profiler_scheduler = None
        self.profile = None
        self.profile_lock = threading.Lock()
        self.profile_duration = 0
        self.prev_signal_handler = None
        self.handler_active = False


    def start(self):
        if self.agent.get_option('cpu_profiler_disabled'):
            return

        if not runtime_info.OS_LINUX and not runtime_info.OS_DARWIN:
            self.agent.log('CPU profiler is only supported on Linux and OS X.')
            return

        def _sample(signum, signal_frame):
            if self.handler_active:
                return
            self.handler_active = True

            with self.profile_lock:
                try:
                    self.process_sample(signal_frame)
                    signal_frame = None
                except Exception:
                    self.agent.exception()

            self.handler_active = False

        self.prev_signal_handler = signal.signal(signal.SIGPROF, _sample)

        self.reset()

        self.profiler_scheduler = ProfilerScheduler(self.agent, 10, 2, 120, self.record, self.report)
        self.profiler_scheduler.start()


    def destroy(self):
        if self.agent.get_option('cpu_profiler_disabled'):
            return

        if self.prev_signal_handler != None:
            signal.setitimer(signal.ITIMER_PROF, 0)
            signal.signal(signal.SIGPROF, self.prev_signal_handler)

        if self.profiler_scheduler:
            self.profiler_scheduler.destroy()


    def reset(self):
        with self.profile_lock:
            self.profile = Breakdown('root')
            self.profile_duration = 0


    def record(self, duration):
        if self.agent.config.is_profiling_disabled():
            return

        self.agent.log('Activating CPU profiler.')

        signal.setitimer(signal.ITIMER_PROF, self.SAMPLING_RATE, self.SAMPLING_RATE)
        time.sleep(duration)
        signal.setitimer(signal.ITIMER_PROF, 0)

        self.agent.log('Deactivating CPU profiler.')

        self.profile_duration += duration

        self.agent.log('CPU profiler CPU overhead per activity second: {0} seconds'.format(self.profile._overhead / self.profile_duration))


    def process_sample(self, signal_frame):
        if self.profile:
            start = time.clock()
            if signal_frame:
                stack = self.recover_stack(signal_frame)
                if stack:
                    self.update_profile(self.profile, stack)

                stack = None

            self.profile._overhead += (time.clock() - start)
            

    def recover_stack(self, signal_frame):
        stack = []

        depth = 0
        while signal_frame is not None and depth <= self.MAX_TRACEBACK_SIZE:
            if signal_frame.f_code and signal_frame.f_code.co_name and signal_frame.f_code.co_filename:
                func_name = signal_frame.f_code.co_name
                filename = signal_frame.f_code.co_filename
                lineno = signal_frame.f_lineno

                if self.agent.frame_selector.is_agent_frame(filename):
                    return None

                if not self.agent.frame_selector.is_system_frame(filename):
                    frame = Frame(func_name, filename, lineno)
                    stack.append(frame)

                signal_frame = signal_frame.f_back
            
            depth += 1

        if len(stack) == 0:
            return None
        else:
            return stack


    def update_profile(self, profile, stack):
        current_node = profile
        current_node.increment(0, 1)

        for frame in reversed(stack):
            current_node = current_node.find_or_add_child(str(frame))
            current_node.increment(0, 1)


    def report(self):
        if self.agent.config.is_profiling_disabled():
            return

        if self.profile_duration == 0:
            return

        with self.profile_lock:
            self.profile.evaluate_percent(self.profile_duration / self.SAMPLING_RATE)

            self.profile.filter(2, 1, 100)

            metric = Metric(self.agent, Metric.TYPE_PROFILE, Metric.CATEGORY_CPU_PROFILE, Metric.NAME_MAIN_THREAD_CPU_USAGE, Metric.UNIT_PERCENT)
            measurement = metric.create_measurement(Metric.TRIGGER_TIMER, self.profile.measurement, None, self.profile)
            self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()
