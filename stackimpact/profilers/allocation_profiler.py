from __future__ import division

import sys
import time
import re
import threading

from ..runtime import min_version, runtime_info, read_vm_size
from ..utils import timestamp
from ..metric import Metric
from ..metric import Breakdown

if min_version(3, 4):
    import tracemalloc


class AllocationProfiler(object):
    MAX_TRACEBACK_SIZE = 25 # number of frames
    MAX_MEMORY_OVERHEAD = 10 * 1e6 # 10MB
    MAX_PROFILED_ALLOCATIONS = 25


    def __init__(self, agent):
        self.agent = agent
        self.ready = False
        self.profile = None
        self.profile_lock = threading.Lock()
        self.overhead_monitor = None
        self.start_ts = None


    def setup(self):
        if self.agent.get_option('allocation_profiler_disabled'):
            return

        if not runtime_info.OS_LINUX and not runtime_info.OS_DARWIN:
            self.agent.log('CPU profiler is only supported on Linux and OS X.')
            return

        if not min_version(3, 4):
            self.agent.log('Memory allocation profiling is available for Python 3.4 or higher')
            return

        self.ready = True


    def reset(self):
        self.profile = Breakdown('Allocation call graph', Breakdown.TYPE_CALLGRAPH)


    def start_profiler(self):
        self.agent.log('Activating memory allocation profiler.')

        def start():
            tracemalloc.start(self.MAX_TRACEBACK_SIZE)
        self.agent.run_in_main_thread(start)

        self.start_ts = time.time()

        def monitor_overhead():
            if tracemalloc.is_tracing() and tracemalloc.get_tracemalloc_memory() > self.MAX_MEMORY_OVERHEAD:
                self.agent.log('Allocation profiler memory overhead limit exceeded: {0} bytes'.format(tracemalloc.get_tracemalloc_memory()))
                self.stop_profiler()

        self.overhead_monitor = self.agent.schedule(0.5, 0.5, monitor_overhead)


    def stop_profiler(self):
        self.agent.log('Deactivating memory allocation profiler.')

        with self.profile_lock:
            if self.overhead_monitor:
                self.overhead_monitor.cancel()
                self.overhead_monitor = None

            if tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                self.agent.log('Allocation profiler memory overhead {0} bytes'.format(tracemalloc.get_tracemalloc_memory()))
                tracemalloc.stop()
                self.process_snapshot(snapshot, time.time() - self.start_ts)


    def build_profile(self, duration):
        with self.profile_lock:
            self.profile.normalize(duration)
            self.profile.propagate()
            self.profile.floor()
            self.profile.filter(2, 1000, float("inf"))

            return [{
                'category': Metric.CATEGORY_MEMORY_PROFILE,
                'name': Metric.NAME_UNCOLLECTED_ALLOCATIONS,
                'unit': Metric.UNIT_BYTE,
                'unit_interval': 1,
                'profile': self.profile
            }]


    def destroy(self):
        pass
        

    def process_snapshot(self, snapshot, duration):
        stats = snapshot.statistics('traceback')

        for stat in stats[:self.MAX_PROFILED_ALLOCATIONS]:
            if stat.traceback:
                skip_stack = False
                for frame in stat.traceback:
                    if self.agent.frame_cache.is_agent_frame(frame.filename):
                        skip_stack = True
                        break
                if skip_stack:
                    continue

                current_node = self.profile
                for frame in reversed(stat.traceback):
                    if frame.filename == '<unknown>':
                        continue

                    frame_name = '{0}:{1}'.format(frame.filename, frame.lineno)
                    current_node = current_node.find_or_add_child(frame_name)
                    current_node.set_type(Breakdown.TYPE_CALLSITE)
                current_node.increment(stat.size, stat.count)
