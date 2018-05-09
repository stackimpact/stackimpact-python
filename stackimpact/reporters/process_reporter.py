from __future__ import division

import re
import os
import gc
import threading
import multiprocessing


from ..runtime import runtime_info, min_version, read_cpu_time, read_max_rss, read_current_rss, read_vm_size
from ..metric import Metric

class ProcessReporter(object):

    def __init__(self, agent):
        self.agent = agent
        self.started = False
        self.metrics = None
        self.report_timer = None


    def setup(self):
        pass


    def destroy(self):
        pass


    def reset(self):
        pass


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


    def reset(self):
        self.metrics = {}


    def report(self):
        # CPU
        if not runtime_info.OS_WIN:
            cpu_time = read_cpu_time()
            if cpu_time != None:
                cpu_time_metric = self.report_metric(Metric.TYPE_COUNTER, Metric.CATEGORY_CPU, Metric.NAME_CPU_TIME, Metric.UNIT_NANOSECOND, cpu_time)
                if cpu_time_metric.has_measurement():
                    cpu_usage = (cpu_time_metric.measurement.value / (60 * 1e9)) * 100
                    try:
                        cpu_usage = cpu_usage / multiprocessing.cpu_count()
                    except Exception:
                        pass

                    self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_CPU, Metric.NAME_CPU_USAGE, Metric.UNIT_PERCENT, cpu_usage)


        # Memory
        if not runtime_info.OS_WIN:
            max_rss = read_max_rss()
            if max_rss != None:
                self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_MAX_RSS, Metric.UNIT_KILOBYTE, max_rss)

        if runtime_info.OS_LINUX:
            current_rss = read_current_rss()
            if current_rss != None:
                self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_CURRENT_RSS, Metric.UNIT_KILOBYTE, current_rss)

            vm_size = read_vm_size()
            if vm_size != None:
                self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_MEMORY, Metric.NAME_VM_SIZE, Metric.UNIT_KILOBYTE, vm_size)


        # GC stats
        gc_count0, gc_count1, gc_count2 = gc.get_count()
        total_gc_count = gc_count0 + gc_count1 + gc_count2
        self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_GC, Metric.NAME_GC_COUNT, Metric.UNIT_NONE, total_gc_count)

        if min_version(3, 4):
            gc_stats = gc.get_stats()
            if gc_stats and gc_stats[0] and gc_stats[1] and gc_stats[2]:
                total_collections = gc_stats[0]['collections'] + gc_stats[1]['collections'] + gc_stats[2]['collections']
                self.report_metric(Metric.TYPE_COUNTER, Metric.CATEGORY_GC, Metric.NAME_GC_COLLECTIONS, Metric.UNIT_NONE, total_collections)

                total_collected = gc_stats[0]['collected'] + gc_stats[1]['collected'] + gc_stats[2]['collected']
                self.report_metric(Metric.TYPE_COUNTER, Metric.CATEGORY_GC, Metric.NAME_GC_COLLECTED, Metric.UNIT_NONE, total_collected)

                total_uncollectable = gc_stats[0]['uncollectable'] + gc_stats[1]['uncollectable'] + gc_stats[2]['uncollectable']
                self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_GC, Metric.NAME_GC_UNCOLLECTABLE, Metric.UNIT_NONE, total_uncollectable)

        # Runtime
        thread_count = threading.active_count()
        self.report_metric(Metric.TYPE_STATE, Metric.CATEGORY_RUNTIME, Metric.NAME_THREAD_COUNT, Metric.UNIT_NONE, thread_count)


    def report_metric(self, typ, category, name, unit, value):
        key = typ + category + name
        metric = None
        if key not in self.metrics:
            metric = Metric(self.agent, typ, category, name, unit)
            self.metrics[key] = metric
        else:
            metric = self.metrics[key]

        metric.create_measurement(Metric.TRIGGER_TIMER, value)

        if metric.has_measurement():
            self.agent.message_queue.add('metric', metric.to_dict())

        return metric

