from __future__ import division, print_function, absolute_import

import time
import datetime
import sys
import traceback
import socket
import threading
import os
import signal
import atexit
import platform
import random
import math

from .runtime import min_version, runtime_info, register_signal
from .utils import timestamp, generate_uuid
from .config import Config
from .config_loader import ConfigLoader
from .message_queue import MessageQueue
from .frame_cache import FrameCache
from .reporters.process_reporter import ProcessReporter
from .reporters.profile_reporter import ProfileReporter, ProfilerConfig
from .reporters.error_reporter import ErrorReporter
from .reporters.span_reporter import SpanReporter
from .profilers.cpu_profiler import CPUProfiler
from .profilers.allocation_profiler import AllocationProfiler
from .profilers.block_profiler import BlockProfiler
from .profilers.tf_profiler import TFProfiler


class Span(object):

    def __init__(self, stop_func = None):
        if stop_func:
            self.stop_func = stop_func


    def stop(self):
        if self.stop_func:
            self.stop_func()


    def __enter__(self):
        pass


    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class Agent(object):

    AGENT_VERSION = "1.2.4"
    SAAS_DASHBOARD_ADDRESS = "https://agent-api.stackimpact.com"

    def __init__(self, **kwargs):
        self.agent_started = False
        self.agent_destroyed = False

        self.profiler_active = False
        self.span_active = False

        self.main_thread_func = None

        self.run_ts = None
        self.run_id = None
        self.config = Config(self)
        self.config_loader = ConfigLoader(self)
        self.message_queue = MessageQueue(self)
        self.frame_cache = FrameCache(self)
        self.process_reporter = ProcessReporter(self)
        self.error_reporter = ErrorReporter(self)
        self.span_reporter = SpanReporter(self)

        config = ProfilerConfig()
        config.log_prefix = 'CPU profiler'
        config.max_profile_duration = 20
        config.max_span_duration = 5
        config.max_span_count = 30
        config.span_interval = 20
        config.report_interval = 120
        self.cpu_reporter = ProfileReporter(self, CPUProfiler(self), config)

        config = ProfilerConfig()
        config.log_prefix = 'Allocation profiler'
        config.max_profile_duration = 20
        config.max_span_duration = 5
        config.max_span_count = 30
        config.span_interval = 20
        config.report_interval = 120
        self.allocation_reporter = ProfileReporter(self, AllocationProfiler(self), config)

        config = ProfilerConfig()
        config.log_prefix = 'Block profiler'
        config.max_profile_duration = 20
        config.max_span_duration = 5
        config.max_span_count = 30
        config.span_interval = 20
        config.report_interval = 120
        self.block_reporter = ProfileReporter(self, BlockProfiler(self), config)

        config = ProfilerConfig()
        config.log_prefix = 'TensorFlow profiler'
        config.max_profile_duration = 20
        config.max_span_duration = 5
        config.max_span_count = 30
        config.span_interval = 20
        config.report_interval = 120
        self.tf_reporter = ProfileReporter(self, TFProfiler(self), config)

        self.options = None


    def get_option(self, name, default_val=None):
        if name not in self.options:
            return default_val
        else:
            return self.options[name]


    def start(self, **kwargs):
        if not min_version(2, 7) and not min_version(3, 4):
            raise Exception('Supported Python versions 2.6 or higher and 3.4 or higher')

        if platform.python_implementation() != 'CPython':
            raise Exception('Supported Python interpreter is CPython')

        if self.agent_destroyed:
            self.log('Destroyed agent cannot be started')
            return

        if self.agent_started:
            return

        self.options = kwargs

        if 'auto_profiling' not in self.options:
            self.options['auto_profiling'] = True

        if 'dashboard_address' not in self.options:
            self.options['dashboard_address'] = self.SAAS_DASHBOARD_ADDRESS

        if 'agent_key' not in self.options:
            raise Exception('missing option: agent_key')

        if 'app_name' not in self.options:
            raise Exception('missing option: app_name')

        if 'host_name' not in self.options:
            self.options['host_name'] = socket.gethostname()

        self.run_id = generate_uuid()
        self.run_ts = timestamp()

        self.config_loader.start()
        self.message_queue.start()
        self.frame_cache.start()

        self.cpu_reporter.setup()
        self.allocation_reporter.setup()
        self.block_reporter.setup()
        self.tf_reporter.setup()
        self.span_reporter.setup()
        self.error_reporter.setup()
        self.process_reporter.setup()

        # execute main_thread_func in main thread on signal
        def _signal_handler(signum, frame):
            if(self.main_thread_func):
                func = self.main_thread_func
                self.main_thread_func = None
                try:
                    func()
                except Exception:
                    self.exception()

                return True

        if not runtime_info.OS_WIN:
            register_signal(signal.SIGUSR2, _signal_handler)

        if self.get_option('auto_destroy') is None or self.get_option('auto_destroy') is True:
            # destroy agent on exit
            def _exit_handler(*arg):
                if not self.agent_started or self.agent_destroyed:
                    return

                try:
                    self.message_queue.flush()
                    self.destroy()
                except Exception:
                    self.exception()


            atexit.register(_exit_handler)

            if not runtime_info.OS_WIN:
                register_signal(signal.SIGQUIT, _exit_handler, once = True)
                register_signal(signal.SIGINT, _exit_handler, once = True)
                register_signal(signal.SIGTERM, _exit_handler, once = True)
                register_signal(signal.SIGHUP, _exit_handler, once = True)


        self.agent_started = True
        self.log('Agent started')


    def enable(self):
        if not self.config.is_agent_enabled():
            self.cpu_reporter.start()
            self.allocation_reporter.start()
            self.block_reporter.start()
            self.tf_reporter.start()
            self.span_reporter.start()
            self.error_reporter.start()
            self.process_reporter.start()
            self.config.set_agent_enabled(True)


    def disable(self):
        if self.config.is_agent_enabled():
            self.cpu_reporter.stop()
            self.allocation_reporter.stop()
            self.block_reporter.stop()
            self.tf_reporter.stop()
            self.span_reporter.stop()
            self.error_reporter.stop()
            self.process_reporter.stop()
            self.config.set_agent_enabled(False)


    def profile(self, name='Default'):
        if not self.agent_started or self.span_active:
          return Span(None)

        self.span_active = True

        selected_reporter = None
        active_reporters = []
        if self.cpu_reporter.started:
            active_reporters.append(self.cpu_reporter)
        if self.allocation_reporter.started:
            active_reporters.append(self.allocation_reporter)
        if self.block_reporter.started:
            active_reporters.append(self.block_reporter)
        if self.tf_reporter.started:
            active_reporters.append(self.tf_reporter)

        if len(active_reporters) > 0:
            selected_reporter = active_reporters[int(math.floor(random.random() * len(active_reporters)))]
            if not selected_reporter.start_profiling(True, True):
                selected_reporter = None

        start_timestamp = time.time()

        def stop_func():
            if selected_reporter:
                selected_reporter.stop_profiling()

            duration = time.time() - start_timestamp
            self.span_reporter.record_span(name, duration)

            if not self.get_option('auto_profiling'):
                self.config_loader.load(True)
                if selected_reporter:
                    selected_reporter.report(True);
                self.message_queue.flush(True)

            self.span_active = False

        return Span(stop_func)


    def _start_profiler(self, reporter):
        if not self.agent_started or self.get_option('auto_profiling'):
          return

        self.span_active = True

        reporter.start()
        reporter.start_profiling(True, False)


    def _stop_profiler(self, reporter):
        if not self.agent_started or self.get_option('auto_profiling'):
          return

        reporter.stop_profiling()
        reporter.report(False)
        reporter.stop()
        self.message_queue.flush(False)

        self.span_active = False


    def start_cpu_profiler(self):
        self._start_profiler(self.cpu_reporter)


    def stop_cpu_profiler(self):
        self._stop_profiler(self.cpu_reporter)


    def start_allocation_profiler(self):
        self._start_profiler(self.allocation_reporter)


    def stop_allocation_profiler(self):
        self._stop_profiler(self.allocation_reporter)


    def start_block_profiler(self):
        self._start_profiler(self.block_reporter)


    def stop_block_profiler(self):
        self._stop_profiler(self.block_reporter)


    def start_tf_profiler(self):
        self._start_profiler(self.tf_reporter)


    def stop_tf_profiler(self):
        self._stop_profiler(self.tf_reporter)


    def destroy(self):
        if not self.agent_started:
            self.log('Agent has not been started')
            return

        if self.agent_destroyed:
            return

        self.config_loader.stop()
        self.message_queue.stop()
        self.frame_cache.stop()
        self.cpu_reporter.stop()
        self.allocation_reporter.stop()
        self.block_reporter.stop()
        self.tf_reporter.stop()
        self.error_reporter.stop()
        self.span_reporter.stop()
        self.process_reporter.stop()

        self.cpu_reporter.destroy()
        self.allocation_reporter.destroy()
        self.block_reporter.destroy()
        self.tf_reporter.destroy()
        self.error_reporter.destroy()
        self.span_reporter.destroy()
        self.process_reporter.destroy()

        self.agent_destroyed = True
        self.log('Agent destroyed')


    def log_prefix(self):
        return '[' + datetime.datetime.now().strftime('%H:%M:%S.%f') + '] StackImpact ' + self.AGENT_VERSION + ':'


    def log(self, message):
        if self.get_option('debug'):
            print(self.log_prefix(), message)


    def print_err(self, *args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)


    def error(self, message):
        if self.get_option('debug'):
            self.print_err(self.log_prefix(), message)


    def exception(self):
        if self.get_option('debug'):
            traceback.print_exc()


    def delay(self, timeout, func, *args):
        def func_wrapper():
            try:
                func(*args)
            except Exception:
                self.exception()

        t = threading.Timer(timeout, func_wrapper, ())
        t.start()

        return t


    def schedule(self, timeout, interval, func, *args):
        tw = TimerWraper()

        def func_wrapper():
            start = time.time()

            try:
                func(*args)
            except Exception:
                self.exception()

            with tw.cancel_lock:
                if not tw.canceled:
                    tw.timer = threading.Timer(abs(interval - (time.time() - start)), func_wrapper, ())
                    tw.timer.start()

        tw.timer = threading.Timer(timeout, func_wrapper, ())
        tw.timer.start()

        return tw


    def run_in_thread(self, func):
        def func_wrapper():
            try:
                func()
            except Exception:
                self.exception()

        t = threading.Thread(target=func_wrapper)
        t.start()
        return t


    def run_in_main_thread(self, func):
        if self.main_thread_func:
            return False

        self.main_thread_func = func
        os.kill(os.getpid(), signal.SIGUSR2)

        return True



class TimerWraper(object):
    def __init__(self):
        self.timer = None
        self.cancel_lock = threading.Lock()
        self.canceled = False

    def cancel(self):
        with self.cancel_lock:
            self.canceled = True
            self.timer.cancel()

