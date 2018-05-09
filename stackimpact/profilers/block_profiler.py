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

if runtime_info.GEVENT:
    import gevent


class BlockProfiler(object):
    SAMPLING_RATE = 0.05
    MAX_TRACEBACK_SIZE = 25 # number of frames


    def __init__(self, agent):
        self.agent = agent
        self.ready = False
        self.profile = None
        self.profile_lock = threading.Lock()
        self.prev_signal_handler = None
        self.sampler_active = False


    def setup(self):
        if self.agent.get_option('block_profiler_disabled'):
            return

        if not runtime_info.OS_LINUX and not runtime_info.OS_DARWIN:
            self.agent.log('CPU profiler is only supported on Linux and OS X.')
            return

        sample_time = self.SAMPLING_RATE * 1000

        main_thread_id = None
        if runtime_info.GEVENT:
            main_thread_id = gevent._threading.get_ident()
        else:
            main_thread_id = threading.current_thread().ident

        def _sample(signum, signal_frame):
            if self.sampler_active:
                return
            self.sampler_active = True

            with self.profile_lock:
                try:
                    self.process_sample(signal_frame, sample_time, main_thread_id)
                    signal_frame = None
                except Exception:
                    self.agent.exception()

            self.sampler_active = False

        self.prev_signal_handler = signal.signal(signal.SIGALRM, _sample)

        self.ready = True


    def destroy(self):
        if not self.ready:
            return

        signal.signal(signal.SIGALRM, self.prev_signal_handler)


    def reset(self):
        self.profile = Breakdown('Execution call graph', Breakdown.TYPE_CALLGRAPH)


    def start_profiler(self):
        self.agent.log('Activating block profiler.')

        signal.setitimer(signal.ITIMER_REAL, self.SAMPLING_RATE, self.SAMPLING_RATE)


    def stop_profiler(self):
        signal.setitimer(signal.ITIMER_REAL, 0)

        self.agent.log('Deactivating block profiler.')


    def build_profile(self, duration):
        with self.profile_lock:
            self.profile.normalize(duration)
            self.profile.propagate()
            self.profile.floor()
            self.profile.filter(2, 1, float("inf"))

            return [{
                'category': Metric.CATEGORY_BLOCK_PROFILE,
                'name': Metric.NAME_BLOCKING_CALL_TIMES,
                'unit': Metric.UNIT_MILLISECOND,
                'unit_interval': 1,
                'profile': self.profile
            }]


    def process_sample(self, signal_frame, sample_time, main_thread_id):
        if self.profile:
            start = time.clock()

            current_frames = sys._current_frames()
            items = current_frames.items()
            for thread_id, thread_frame in items:
                if thread_id == main_thread_id:
                    thread_frame = signal_frame

                stack = self.recover_stack(thread_frame)
                if stack:
                    current_node = self.profile
                    for frame in reversed(stack):
                        current_node = current_node.find_or_add_child(str(frame))
                        current_node.set_type(Breakdown.TYPE_CALLSITE)
                    current_node.increment(sample_time, 1)

                thread_id, thread_frame, stack = None, None, None

            items = None
            current_frames = None


    def recover_stack(self, thread_frame):
        stack = []

        system_only = True
        depth = 0
        while thread_frame is not None and depth <= self.MAX_TRACEBACK_SIZE:
            if thread_frame.f_code and thread_frame.f_code.co_name and thread_frame.f_code.co_filename:
                func_name = thread_frame.f_code.co_name
                filename = thread_frame.f_code.co_filename
                lineno = thread_frame.f_lineno

                if self.agent.frame_cache.is_agent_frame(filename):
                    return None

                if not self.agent.frame_cache.is_system_frame(filename):
                    system_only = False

                frame = Frame(func_name, filename, lineno)
                stack.append(frame)

                thread_frame = thread_frame.f_back
            
            depth += 1

        if system_only:
            return None

        if len(stack) == 0:
            return None
        else:
            return stack
