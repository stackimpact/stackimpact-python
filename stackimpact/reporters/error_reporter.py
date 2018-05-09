
import sys
import threading
import traceback
import collections

from ..runtime import runtime_info, patch, unpatch
from ..metric import Metric
from ..metric import Breakdown
from ..frame import Frame


class ErrorReporter(object):
    MAX_QUEUED_EXC = 100


    def __init__(self, agent):
        self.agent = agent
        self.ready = False
        self.started = False
        self.process_timer = None
        self.report_timer = None
        self.exc_queue = collections.deque()
        self.profile = None
        self.profile_lock = threading.Lock()
        self.added_exceptions = None


    def setup(self):
        if self.agent.get_option('error_profiler_disabled'):
            return

        def _exc_info(args, kwargs, ret, data):
            try:
                if not self.agent.agent_started or self.agent.agent_destroyed:
                    return

                if len(self.exc_queue) <= self.MAX_QUEUED_EXC:
                    self.exc_queue.append(ret)

            except Exception:
                self.agent.log('exc_info wrapper exception')

        patch(sys, 'exc_info', None, _exc_info)

        self.ready = True


    def destroy(self):
        if not self.ready:
            return

        unpatch(sys, 'exc_info')


    def reset(self):
        with self.profile_lock:
            self.profile = Breakdown('Error call graph', Breakdown.TYPE_ERROR)
            self.added_exceptions = {}


    def start(self):
        if self.agent.get_option('error_profiler_disabled'):
            return

        if not self.agent.get_option('auto_profiling'):
            return

        if self.started:
            return
        self.started = True

        self.reset()


        self.process_timer = self.agent.schedule(1, 1, self.process)
        self.report_timer = self.agent.schedule(60, 60, self.report)


    def stop(self):
        if not self.started:
            return
        self.started = False

        self.process_timer.cancel()
        self.process_timer = None

        self.report_timer.cancel()
        self.report_timer = None
    

    def report(self):
        with self.profile_lock:
            self.profile.propagate()

            metric = Metric(self.agent, Metric.TYPE_PROFILE, Metric.CATEGORY_ERROR_PROFILE, Metric.NAME_HANDLED_EXCEPTIONS, Metric.UNIT_NONE)
            measurement = metric.create_measurement(Metric.TRIGGER_TIMER, self.profile.measurement, 60, self.profile)
            self.agent.message_queue.add('metric', metric.to_dict())

        self.reset()


    def process(self):
        while True:
            try:
                exc = self.exc_queue.pop()
                self.update_profile(exc)
            except IndexError:
                return


    def recover_stack(self, exc):
        stack = []

        _, _, tb = exc

        tb_stack = traceback.extract_tb(tb, 25)
        for tb_frame in tb_stack:
            func_name = tb_frame[2]
            filename = tb_frame[0]
            lineno = tb_frame[1]

            if self.agent.frame_cache.is_agent_frame(filename):
                return None

            if not self.agent.frame_cache.is_system_frame(filename):
                frame = Frame(func_name, filename, lineno)
                stack.append(frame)

        return stack


    def update_profile(self, exc):
        with self.profile_lock:
            exc_type, exc_obj, _ = exc
            if not exc_type or not exc_obj:
                return

            exc_id = str(id(exc_obj))
            if exc_id in self.added_exceptions:
                return
            else:
                self.added_exceptions[exc_id] = True


            stack = self.recover_stack(exc)
            if not stack:
                return

            current_node = self.profile

            for frame in reversed(stack):
                current_node = current_node.find_or_add_child(str(frame))
                current_node.set_type(Breakdown.TYPE_CALLSITE)

            message = ''
            if exc_type:
                message += exc_type.__name__

            exc_msg = str(exc_obj)
            if exc_msg:
                message += ': ' + exc_msg

            if message == '':
                message = 'Undefined'

            message_node = current_node.find_child(message)
            if message_node == None:
                if len(current_node.children) < 5:
                    message_node = current_node.find_or_add_child(message)
                else:
                    message_node = current_node.find_or_add_child('Other')

            message_node.set_type(Breakdown.TYPE_ERROR)
            message_node.increment(1, 0)
