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

from .runtime import min_version, runtime_info, register_signal
from .utils import timestamp, generate_uuid
from .config import Config
from .config_loader import ConfigLoader
from .message_queue import MessageQueue
from .frame_selector import FrameSelector
from .reporters.process_reporter import ProcessReporter
from .reporters.cpu_reporter import CPUReporter
from .reporters.allocation_reporter import AllocationReporter
from .reporters.block_reporter import BlockReporter
from .reporters.error_reporter import ErrorReporter


class Agent:

    AGENT_VERSION = "1.0.4"
    SAAS_DASHBOARD_ADDRESS = "https://agent-api.stackimpact.com"

    def __init__(self, **kwargs):
        self.agent_started = False
        self.agent_destroyed = False

        self.profiler_lock = threading.Lock()

        self.main_thread_func = None

        self.run_ts = None
        self.run_id = None
        self.config = Config(self)
        self.config_loader = ConfigLoader(self)
        self.message_queue = MessageQueue(self)
        self.frame_selector = FrameSelector(self)
        self.process_reporter = ProcessReporter(self)
        self.cpu_reporter = CPUReporter(self)
        self.allocation_reporter = AllocationReporter(self)
        self.block_reporter = BlockReporter(self)
        self.error_reporter = ErrorReporter(self)

        self.options = None


    def get_option(self, name, default_val = None):
        if name not in self.options:
            return default_val
        else:
            return self.options[name]


    def start(self, **kwargs):
        if not min_version(2, 7) and not min_version(3, 4):
            raise Exception('Supported Python versions 2.6 or highter and 3.4 or higher')

        if platform.python_implementation() != 'CPython':
            raise Exception('Supported Python interpreter is CPython')

        if self.agent_destroyed:
            self.log('Destroyed agent cannot be started')
            return

        if self.agent_started:
            return

        self.options = kwargs

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
        self.frame_selector.start()
        self.process_reporter.start()
        self.cpu_reporter.start()
        self.allocation_reporter.start()
        self.block_reporter.start()
        self.error_reporter.start()

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

        register_signal(signal.SIGUSR2, _signal_handler)

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

        register_signal(signal.SIGQUIT, _exit_handler, ignore_default = False)
        register_signal(signal.SIGINT, _exit_handler, ignore_default = False)
        register_signal(signal.SIGTERM, _exit_handler, ignore_default = False)
        register_signal(signal.SIGHUP, _exit_handler, ignore_default = False)

        self.agent_started = True
        self.log('Agent started')


    def destroy(self):
        if not self.agent_started:
            self.log('Agent has not been started')
            return

        if self.agent_destroyed:
            return

        self.config_loader.destroy()
        self.message_queue.destroy()
        self.frame_selector.destroy()
        self.process_reporter.destroy()
        self.cpu_reporter.destroy()
        self.allocation_reporter.destroy()
        self.block_reporter.destroy()
        self.error_reporter.destroy()

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
            self.print_err(sys.exc_info()[0])
            traceback.print_exc()


    def delay(self, timeout, func):
        def func_wrapper():
            try:
                func()
            except Exception:
                self.exception()

        t = threading.Timer(timeout, func_wrapper, ())
        t.start()

        return t


    def schedule(self, timeout, interval, func):
        tw = TimerWraper()

        def func_wrapper():
            start = time.time()

            try:
                func()
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



class TimerWraper():
    def __init__(self):
        self.timer = None
        self.cancel_lock = threading.Lock()
        self.canceled = False

    def cancel(self):
        with self.cancel_lock:
            self.canceled = True
            self.timer.cancel()

