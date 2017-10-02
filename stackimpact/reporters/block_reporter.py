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

if runtime_info.GEVENT:
    import gevent


class BlockReporter:
    SAMPLING_RATE = 0.05
    MAX_TRACEBACK_SIZE = 25 # number of frames


    def __init__(self, agent):
        self.agent = agent
        self.setup_done = False
        self.started = False
        self.profiler_scheduler = None
        self.profile_lock = threading.Lock()
        self.profile = None
        self.profile_duration = 0
        self.prev_signal_handler = None
        self.handler_active = False


    def setup(self):
        if self.agent.get_option('block_profiler_disabled'):
            return

        if runtime_info.OS_WIN:
            self.agent.log('Block profiler is not available on Windows.')
            return

        sample_time = self.SAMPLING_RATE * 1000

        main_thread_id = None
        if runtime_info.GEVENT:
            main_thread_id = gevent._threading.get_ident()
        else:
            main_thread_id = threading.current_thread().ident

        def _sample(signum, signal_frame):
            if self.handler_active:
                return
            self.handler_active = True

            with self.profile_lock:
                try:
                    self.process_sample(signal_frame, sample_time, main_thread_id)
                    signal_frame = None
                except Exception:
                    self.agent.exception()

            self.handler_active = False

        self.prev_signal_handler = signal.signal(signal.SIGALRM, _sample)

        self.setup_done = True


    def start(self):
        if not self.setup_done:
            return

        if self.started:
            return
        self.started = True

        self.reset()

        self.profiler_scheduler = ProfilerScheduler(self.agent, 10, 2, 120, self.record, self.report)
        self.profiler_scheduler.start()


    def stop(self):
        if not self.started:
            return;
        self.started = False

        self.profiler_scheduler.stop()


    def destroy(self):
        if not self.setup_done:
            return

        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.prev_signal_handler)


    def reset(self):
        self.profile = Breakdown('root')
        self.profile_duration = 0


    def record(self, duration):
        self.agent.log('Activating block profiler.')

        signal.setitimer(signal.ITIMER_REAL, self.SAMPLING_RATE, self.SAMPLING_RATE)
        time.sleep(duration)
        signal.setitimer(signal.ITIMER_REAL, 0)

        self.agent.log('Deactivating block profiler.')

        self.profile_duration += duration

        self.agent.log('Block profiler CPU overhead per activity second: {0} seconds'.format(self.profile._overhead / self.profile_duration))


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
                    current_node.increment(sample_time, 1)

                thread_id, thread_frame, stack = None, None, None

            items = None
            current_frames = None

            self.profile._overhead += (time.clock() - start)


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


    def report(self):
        if self.agent.config.is_profiling_disabled():
            return

        if self.profile_duration == 0:
            return

        with self.profile_lock:
            self.profile.normalize(self.profile_duration)
            self.profile.propagate()
            self.profile.floor()
            self.profile.filter(2, 1, float("inf"))

            metric = Metric(self.agent, Metric.TYPE_PROFILE, Metric.CATEGORY_BLOCK_PROFILE, Metric.NAME_BLOCKING_CALL_TIMES, Metric.UNIT_MILLISECOND)
            measurement = metric.create_measurement(Metric.TRIGGER_TIMER, self.profile.measurement, 1, self.profile)
            self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()
