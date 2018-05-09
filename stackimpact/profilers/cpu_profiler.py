from __future__ import division

import os
import sys
import time
import threading
import re
import signal

from ..runtime import min_version, runtime_info
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame



class CPUProfiler(object):
    SAMPLING_RATE = 0.01
    MAX_TRACEBACK_SIZE = 25 # number of frames


    def __init__(self, agent):
        self.agent = agent
        self.ready = False
        self.profile = None
        self.profile_lock = threading.Lock()
        self.prev_signal_handler = None
        self.sampler_active = False


    def setup(self):
        if self.agent.get_option('cpu_profiler_disabled'):
            return

        if not runtime_info.OS_LINUX and not runtime_info.OS_DARWIN:
            self.agent.log('CPU profiler is only supported on Linux and OS X.')
            return

        def _sample(signum, signal_frame):
            if self.sampler_active:
                return
            self.sampler_active = True

            with self.profile_lock:
                try:
                    self.process_sample(signal_frame)
                    signal_frame = None
                except Exception:
                    self.agent.exception()

            self.sampler_active = False

        self.prev_signal_handler = signal.signal(signal.SIGPROF, _sample)

        self.ready = True


    def reset(self):
        self.profile = Breakdown('Execution call graph', Breakdown.TYPE_CALLGRAPH)


    def start_profiler(self):
        self.agent.log('Activating CPU profiler.')

        signal.setitimer(signal.ITIMER_PROF, self.SAMPLING_RATE, self.SAMPLING_RATE)


    def stop_profiler(self):
        signal.setitimer(signal.ITIMER_PROF, 0)


    def destroy(self):
        if not self.ready:
            return

        signal.signal(signal.SIGPROF, self.prev_signal_handler)


    def build_profile(self, duration):
        with self.profile_lock:
            self.profile.propagate()
            self.profile.evaluate_percent(duration / self.SAMPLING_RATE)
            self.profile.filter(2, 1, 100)

            return [{
                'category': Metric.CATEGORY_CPU_PROFILE,
                'name': Metric.NAME_MAIN_THREAD_CPU_USAGE,
                'unit': Metric.UNIT_PERCENT,
                'unit_interval': None,
                'profile': self.profile
            }]


    def process_sample(self, signal_frame):
        if self.profile:
            start = time.clock()
            if signal_frame:
                stack = self.recover_stack(signal_frame)
                if stack:
                    self.update_profile(self.profile, stack)

                stack = None
            

    def recover_stack(self, signal_frame):
        stack = []

        depth = 0
        while signal_frame is not None and depth <= self.MAX_TRACEBACK_SIZE:
            if signal_frame.f_code and signal_frame.f_code.co_name and signal_frame.f_code.co_filename:
                func_name = signal_frame.f_code.co_name
                filename = signal_frame.f_code.co_filename
                lineno = signal_frame.f_lineno

                if self.agent.frame_cache.is_agent_frame(filename):
                    return None

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

        for frame in reversed(stack):
            current_node = current_node.find_or_add_child(str(frame))
            current_node.set_type(Breakdown.TYPE_CALLSITE)
        
        current_node.increment(0, 1)
