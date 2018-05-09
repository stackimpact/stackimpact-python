from __future__ import division

import os
import sys
import time
import threading
import re
import signal
from functools import wraps

from ..runtime import min_version, runtime_info, patch, unpatch
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame

if runtime_info.GEVENT:
    import gevent


class Sampler(object):

    SAMPLING_INTERVAL = 1
    MAX_SAMPLED_RUNS = 10
    MAX_SAMPLED_DURATION = 0.1

    def __init__(self, agent):
        self.last_update_ts = time.time()
        self.count = 0
        self.duration = 0


    def sample(self):
        if self.last_update_ts < time.time() - self.SAMPLING_INTERVAL:
            self.last_update_ts = time.time()
            self.count = 0
            self.duration = 0
            return True
        elif self.count < self.MAX_SAMPLED_RUNS and self.duration < self.MAX_SAMPLED_DURATION:
            return True

        return False


    def update(self, run_duration):
        self.count = self.count + 1
        self.duration = self.duration + run_duration



class TFProfiler(object):

    def __init__(self, agent):
        self.agent = agent
        self.ready = False
        self.cpu_profile = None
        self.allocation_profile = None
        self.profile_lock = threading.Lock()
        self.profiler_active = False
        self.sampler = Sampler(agent)
        self.sampling_active = False
        self.run_metadata = None
        self.total_run_duration = None
        self.sampled_run_duration = None


    def setup(self):
        if self.agent.get_option('tf_profiler_disabled'):
            return

        try:
            import tensorflow as tf
        except Exception:
            self.agent.log('TensorFlow not found.')
            return

        try:
            def before_run(args, kwargs):
                session = args[0]
                data = None

                if self.profiler_active:
                    data = dict()
                    data['start_ts'] = time.time()
                
                    if not self.sampling_active and self.sampler.sample():
                        self.sampling_active = True
                        self.agent.log('Tracing TensorFlow session.')

                        if 'options' in kwargs:
                            kwargs['options'].trace_level = tf.RunOptions.FULL_TRACE
                        else:
                            kwargs['options'] = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)

                        if 'run_metadata' not in kwargs:
                            kwargs['run_metadata'] = tf.RunMetadata()
                        self.run_metadata = kwargs['run_metadata']

                return args, kwargs, data

            def after_run(args, kwargs, ret, data):
                session = args[0]

                if data and 'start_ts' in data:
                    run_duration = time.time() - data['start_ts']
                    self.total_run_duration = self.total_run_duration + run_duration
                    if self.sampling_active:
                        self.sampled_run_duration = self.sampled_run_duration + run_duration
                        self.sampler.update(run_duration)
                        self.update_cpu_profile(session.graph, self.run_metadata.step_stats.dev_stats)
                        self.update_allocation_profile(session.graph, self.run_metadata.step_stats.dev_stats)
                        self.sampling_active = False

            if not patch(tf.Session, 'run', before_run, after_run):
                self.agent.log('Error wrapping TensorFlow session.')

        except Exception:
            self.agent.log('Error setting up TensorFlow session wrappers.')
            self.agent.exception()
            return

        self.ready = True


    def destroy(self):
        if not self.ready:
            return


    def reset(self):
        self.cpu_profile = Breakdown('Operation definition call graph', Breakdown.TYPE_CALLGRAPH)
        self.allocation_profile = Breakdown('Operation definition call graph', Breakdown.TYPE_CALLGRAPH)
        self.total_run_duration = 0
        self.sampled_run_duration = 0


    def start_profiler(self):
        self.agent.log('Activating TensorFlow profiler.')

        self.profiler_active = True


    def stop_profiler(self):
        self.profiler_active = False

        self.agent.log('Deactivating TensorFlow profiler.')


    def build_profile(self, duration):
        with self.profile_lock:
            if self.sampled_run_duration > 0:
                scale = self.total_run_duration / self.sampled_run_duration

                self.cpu_profile.scale(scale)
                self.cpu_profile.normalize(duration)
                self.cpu_profile.propagate()

                self.allocation_profile.scale(scale)
                self.allocation_profile.normalize(duration)
                self.allocation_profile.propagate()
                self.allocation_profile.floor()
                self.allocation_profile.filter(2, 1000, float("inf"))

            return [{
                'category': Metric.CATEGORY_CPU_PROFILE,
                'name': Metric.NAME_TF_OPERATION_TIMES,
                'unit': Metric.UNIT_MILLISECOND,
                'unit_interval': 1,
                'profile': self.cpu_profile
            },
            {
                'category': Metric.CATEGORY_MEMORY_PROFILE,
                'name': Metric.NAME_TF_OPERATION_ALLOCATION_RATE,
                'unit': Metric.UNIT_BYTE,
                'unit_interval': 1,
                'profile': self.allocation_profile
            }]


    def update_cpu_profile(self, graph, dev_stats):
        with self.profile_lock:
            op_index = dict()
            for op in graph.get_operations():
                op_index[op.name] = op

            for device_index, device_stats in enumerate(dev_stats):
                device_node = self.cpu_profile.find_or_add_child(device_stats.device)

                for node_stats in device_stats.node_stats:
                    if node_stats.node_name == '_SOURCE' or node_stats.node_name == '_SINK':
                        continue

                    duration = (node_stats.op_end_rel_micros - node_stats.op_start_rel_micros) / 1000
                    if duration == 0:
                        continue

                    if node_stats.node_name in op_index:
                        op = op_index[node_stats.node_name]
                        tb = op.traceback
                        if tb:
                            current_node = device_node
                            for tb_frame in tb:
                                frame = Frame(tb_frame[2], tb_frame[0], tb_frame[1])
                                current_node = current_node.find_or_add_child(str(frame))
                                current_node.set_type(Breakdown.TYPE_CALLSITE)

                            current_node = current_node.find_or_add_child(node_stats.node_name)
                            current_node.add_metadata('Type', op.type)
                            current_node.set_type(Breakdown.TYPE_OPERATION)
                            current_node.increment(duration, 1)



    def update_allocation_profile(self, graph, dev_stats):
        with self.profile_lock:
            op_index = dict()
            for op in graph.get_operations():
                op_index[op.name] = op

            for device_index, device_stats in enumerate(dev_stats):
                device_node = self.allocation_profile.find_or_add_child(device_stats.device)

                for node_stats in device_stats.node_stats:
                    if node_stats.node_name == '_SOURCE' or node_stats.node_name == '_SINK':
                        continue

                    num_bytes = 0
                    for index, output in enumerate(node_stats.output):
                        allocation = output.tensor_description.allocation_description
                        num_bytes = num_bytes + allocation.requested_bytes
                    if num_bytes == 0:
                        continue

                    if node_stats.node_name in op_index:
                        op = op_index[node_stats.node_name]
                        tb = op.traceback
                        if tb:
                            current_node = device_node
                            for tb_frame in tb:
                                frame = Frame(tb_frame[2], tb_frame[0], tb_frame[1])
                                current_node = current_node.find_or_add_child(str(frame))
                                current_node.set_type(Breakdown.TYPE_CALLSITE)

                            current_node = current_node.find_or_add_child(node_stats.node_name)
                            current_node.add_metadata('Type', op.type)
                            current_node.set_type(Breakdown.TYPE_OPERATION)
                            current_node.increment(num_bytes, 1)
