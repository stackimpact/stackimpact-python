from __future__ import division

import sys
import time
import re

from ..runtime import min_version, runtime_info, read_vm_size
from ..profiler_scheduler import ProfilerScheduler
from ..metric import Metric
from ..metric import Breakdown

if min_version(3, 4):
    import tracemalloc


class AllocationReporter:
    MAX_TRACEBACK_SIZE = 25 # number of frames
    MAX_MEMORY_OVERHEAD = 10 * 1e6 # 10MB
    MAX_PROFILED_ALLOCATIONS = 25


    def __init__(self, agent):
        self.agent = agent
        self.profiler_scheduler = None
        self.profile = None
        self.profile_duration = 0


    def start(self):
        if self.agent.get_option('allocation_profiler_disabled'):
            return

        if not min_version(3, 4):
            self.agent.log('Memory allocation profiling is available for Python 3.4 or higher')
            return

        self.reset()

        self.profiler_scheduler = ProfilerScheduler(self.agent, 20, 5, 120, self.record, self.report)
        self.profiler_scheduler.start()


    def destroy(self):
        if self.agent.get_option('allocation_profiler_disabled'):
            return

        if self.profiler_scheduler:
            self.profiler_scheduler.destroy()


    def metrics(self):
        if runtime_info.OS_LINUX:
            return {
                'vm-size': read_vm_size()
            }

        return None


    def reset(self):
        self.profile = Breakdown('root')
        self.profile_duration = 0


    def record(self, max_duration):
        if self.agent.config.is_profiling_disabled():
            return

        self.agent.log('Activating memory allocation profiler.')

        def start():
            tracemalloc.start(self.MAX_TRACEBACK_SIZE)
        self.agent.run_in_main_thread(start)

        duration = 0
        step = 1
        while duration < max_duration:
            time.sleep(step)
            duration += step

            if tracemalloc.get_tracemalloc_memory() > self.MAX_MEMORY_OVERHEAD:
                break

        self.agent.log('Deactivating memory allocation profiler.')

        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            self.agent.log('Allocation profiler memory overhead {0} bytes'.format(tracemalloc.get_tracemalloc_memory()))
            tracemalloc.stop()
            self.process_snapshot(snapshot, duration)

        self.profile_duration += duration



    def process_snapshot(self, snapshot, duration):
        stats = snapshot.statistics('traceback')

        for stat in stats[:self.MAX_PROFILED_ALLOCATIONS]:
            if stat.traceback:
                skip_stack = False
                for frame in stat.traceback:
                    if self.agent.frame_selector.is_agent_frame(frame.filename):
                        skip_stack = True
                        break
                if skip_stack:
                    continue

                current_node = self.profile
                current_node.increment(stat.size, stat.count)

                for frame in reversed(stat.traceback):
                    if frame.filename == '<unknown>':
                        continue

                    if self.agent.frame_selector.is_system_frame(frame.filename):
                        continue

                    frame_name = '{0}:{1}'.format(frame.filename, frame.lineno)

                    current_node = current_node.find_or_add_child(frame_name)
                    current_node.increment(stat.size, stat.count)


    def report(self):
        if self.agent.config.is_profiling_disabled():
            return

        if self.profile_duration == 0:
            return

        self.profile.normalize(self.profile_duration)
        self.profile.filter(2, 1000, float("inf"))

        metric = Metric(self.agent, Metric.TYPE_PROFILE, Metric.CATEGORY_MEMORY_PROFILE, Metric.NAME_UNCOLLECTED_ALLOCATIONS, Metric.UNIT_BYTE)
        measurement = metric.create_measurement(Metric.TRIGGER_TIMER, self.profile.measurement, 1, self.profile)
        self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()

