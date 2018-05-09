from __future__ import division

import threading
import random
import math

from .utils import timestamp, generate_uuid, generate_sha1

class Metric(object):

    TYPE_STATE = 'state'
    TYPE_COUNTER = 'counter'
    TYPE_PROFILE = 'profile'
    TYPE_TRACE = 'trace'

    CATEGORY_CPU = 'cpu'
    CATEGORY_MEMORY = 'memory'
    CATEGORY_GC = 'gc'
    CATEGORY_RUNTIME = 'runtime'
    CATEGORY_SPAN = 'span'
    CATEGORY_CPU_PROFILE = 'cpu-profile'
    CATEGORY_MEMORY_PROFILE = 'memory-profile'
    CATEGORY_BLOCK_PROFILE = 'block-profile'
    CATEGORY_ERROR_PROFILE = 'error-profile'

    NAME_CPU_TIME = 'CPU time'
    NAME_CPU_USAGE = 'CPU usage'
    NAME_MAIN_THREAD_CPU_USAGE = 'Main thread CPU usage'
    NAME_MAX_RSS = 'Max RSS'
    NAME_CURRENT_RSS = 'Current RSS'
    NAME_VM_SIZE = 'VM Size'
    NAME_GC_COUNT = 'Uncollected objects'
    NAME_GC_COLLECTIONS = 'Collections'
    NAME_GC_COLLECTED = 'Collected objects'
    NAME_GC_UNCOLLECTABLE = 'Uncollectable objects'
    NAME_THREAD_COUNT = 'Active threads'
    NAME_UNCOLLECTED_ALLOCATIONS = 'Uncollected allocations'
    NAME_BLOCKING_CALL_TIMES = 'Blocking call times'
    NAME_HANDLED_EXCEPTIONS = 'Handled exceptions'
    NAME_TF_OPERATION_TIMES = 'TensorFlow operation times'
    NAME_TF_OPERATION_ALLOCATION_RATE = 'TensorFlow operation allocation rate'
    
    UNIT_NONE = ''
    UNIT_MILLISECOND = 'millisecond'
    UNIT_MICROSECOND = 'microsecond'
    UNIT_NANOSECOND = 'nanosecond'
    UNIT_BYTE = 'byte'
    UNIT_KILOBYTE = 'kilobyte'
    UNIT_PERCENT = 'percent'

    TRIGGER_TIMER = 'timer'
    TRIGGER_API = 'api'


    def __init__(self, agent, typ, category, name, unit):
        metric_id = generate_sha1("{0}{1}{2}{3}{4}{5}{6}".format(
            agent.get_option('app_name'), 
            agent.get_option('app_environment'), 
            agent.get_option('host_name'),
            typ, category, name, unit))

        self.agent = agent
        self.id = metric_id
        self.typ = typ
        self.category = category
        self.name = name
        self.unit = unit
        self.measurement = None
        self.has_last_value = False
        self.last_value = None


    def has_measurement(self):
        return self.measurement != None


    def create_measurement(self, trigger, value, duration = None, breakdown = None):
        ready = True

        if self.typ == Metric.TYPE_COUNTER:
            if not self.has_last_value:
                ready = False
                self.has_last_value = True
                self.last_value = value
            else:
                tmp_value = value
                value = value - self.last_value
                self.last_value = tmp_value

        if ready:
            self.measurement = Measurement(
                generate_uuid(),
                trigger,
                value,
                duration,
                breakdown,
                timestamp())


    def to_dict(self):
        measurement_map = None
        if self.measurement:
            measurement_map = self.measurement.to_dict()

        metric_map = {
            'id': self.id,
            'type': self.typ,
            'category': self.category,
            'name': self.name,
            'unit': self.unit,
            'measurement': measurement_map,
        }

        return metric_map



class Measurement:
    def __init__(self, id, trigger, value, duration, breakdown, timestamp):
        self.id = id
        self.trigger = trigger
        self.value = value
        self.duration = duration
        self.breakdown = breakdown
        self.timestamp = timestamp

    def to_dict(self):
        breakdown_map = None
        if self.breakdown:
           breakdown_map = self.breakdown.to_dict()

        measurement_map = {
            'id': self.id,
            'trigger': self.trigger,
            'value': self.value,
            'duration': self.duration,
            'breakdown': breakdown_map,
            'timestamp': self.timestamp,
        }

        return measurement_map


class Breakdown:

    TYPE_CALLGRAPH = 'callgraph'
    TYPE_DEVICE = 'device'
    TYPE_CALLSITE = 'callsite'
    TYPE_OPERATION = 'operation'
    TYPE_ERROR = 'error'

    RESERVOIR_SIZE = 1000

    def __init__(self, name, typ = None):
        self.name = name
        self.type = typ
        self.metadata = dict()
        self.children = dict()
        self.measurement = 0
        self.num_samples = 0
        self.reservoir = []


    def set_type(self, typ):
        self.type = typ


    def add_metadata(self, key, value):
        self.metadata[key] = value


    def get_metadata(self, key):
        if key in self.metadata:
            return self.metadata[key]
        else:
            return None


    def find_child(self, name):
        if name in self.children:
            return self.children[name]

        return None


    def max_child(self):
        max_ch = None
        for name, child in self.children.items():
            if max_ch is None or child.measurement > max_ch.measurement:
                max_ch = child

        return max_ch


    def min_child(self):
        min_ch = None
        for name, child in self.children.items():
            if min_ch == None or child.measurement < min_ch.measurement:
                min_ch = child
        
        return min_ch


    def add_child(self, child):
        self.children[child.name] = child
        

    def remove_child(self, child):
        del self.children[child.name]


    def find_or_add_child(self, name):
        child = self.find_child(name)
        if child == None:
            child = Breakdown(name)
            self.add_child(child)

        return child


    def filter(self, from_level, min_measurement, max_measurement):
        self.filter_level(1, from_level, min_measurement,  max_measurement)


    def filter_level(self, current_level, from_level, min_measurement, max_measurement):
        for name in list(self.children.keys()):
            child = self.children[name]
            if current_level >= from_level and (child.measurement < min_measurement or child.measurement > max_measurement):
                del self.children[name]
            else:
                child.filter_level(current_level + 1, from_level, min_measurement, max_measurement)


    def depth(self):
        max_depth = 0
        
        for name, child in self.children.items():
            child_depth = child.depth()
            if child_depth > max_depth:
                max_depth = child_depth

        return max_depth + 1


    def propagate(self):
        for name, child in self.children.items():
            child.propagate()
            self.measurement += child.measurement
            self.num_samples += child.num_samples


    def increment(self, value, count):
        self.measurement += value
        self.num_samples += count


    def update_p95(self, value):
        r_len = 0
        r_exists = True

        if self.reservoir == None:
            r_exists = False
        else:
            r_len = len(self.reservoir)

        if not r_exists:
            self.reservoir = []

        if r_len < self.RESERVOIR_SIZE:
            self.reservoir.append(value)
        else:
            self.reservoir[random.randint(0, self.RESERVOIR_SIZE - 1)] = value

        self.num_samples += 1


    def evaluate_p95(self):
        if self.reservoir != None and len(self.reservoir) > 0:
            self.reservoir.sort()
            index = int(len(self.reservoir) / 100 * 95)
            self.measurement = self.reservoir[index]

            self.reservoir = self.reservoir[:0]

        for name, child in self.children.items():
            child.evaluate_p95()


    def evaluate_percent(self, total_samples):
        self.measurement = (self.num_samples / total_samples) * 100

        for name, child in self.children.items():
            child.evaluate_percent(total_samples)


    def convert_to_percent(self, total):
        self.measurement = (self.measurement / total) * 100

        for name, child in self.children.items():
            child.convert_to_percent(total)


    def normalize(self, factor):
        self.measurement = self.measurement / factor
        self.num_samples = int(math.ceil(self.num_samples / factor))

        for name, child in self.children.items():
            child.normalize(factor)


    def scale(self, factor):
        self.measurement = self.measurement * factor
        self.num_samples = int(math.ceil(self.num_samples * factor))

        for name, child in self.children.items():
            child.scale(factor)


    def round(self):
        self.measurement = round(self.measurement)

        for name, child in self.children.items():
            child.round()


    def floor(self):
        self.measurement = int(self.measurement)

        for name, child in self.children.items():
            child.floor()


    def to_dict(self):
        children_map = []
        for name, child in self.children.items():
            children_map.append(child.to_dict())

        node_map = {
            "name": self.name,
            "metadata": self.metadata,
            "measurement": self.measurement,
            "num_samples": self.num_samples,
            "children": children_map,
        }

        return node_map


    def __str__(self):
        return self.dump_level(0)


    def dump_level(self, level):
        dump_str = ''

        for i in range(0, level):
            dump_str += ' '

        dump_str += '{0} - {1} ({2})\n'.format(self.name, self.measurement, self.num_samples)
        for name, child in self.children.items():
            dump_str += child.dump_level(level + 1)
        
        return dump_str
