
import time
import sys
import re
import os
import signal
from functools import wraps
try:
    import resource
except ImportError:
    pass


class runtime_info(object):
    OS_LINUX = (sys.platform.startswith('linux'))
    OS_DARWIN = (sys.platform == 'darwin')
    OS_WIN = (sys.platform == 'win32')
    PYTHON_2 = (sys.version_info.major == 2)
    PYTHON_3 = (sys.version_info.major == 3)
    GEVENT = False

try:
    import gevent
    if hasattr(gevent, '_threading'):
        runtime_info.GEVENT = True
except ImportError:
    pass


VM_RSS_REGEXP = re.compile('VmRSS:\s+(\d+)\s+kB')
VM_SIZE_REGEXP = re.compile('VmSize:\s+(\d+)\s+kB')


def min_version(major, minor=0):
    return (sys.version_info.major == major and sys.version_info.minor >= minor)


def read_cpu_time():
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    return int((rusage.ru_utime + rusage.ru_stime) * 1e9) # nanoseconds


def read_max_rss():
    rusage = resource.getrusage(resource.RUSAGE_SELF)

    if runtime_info.OS_DARWIN:
        return int(rusage.ru_maxrss / 1000) # KB
    else:
        return rusage.ru_maxrss # KB


def read_current_rss():
    pid = os.getpid()

    output = None
    try:
        f = open('/proc/{0}/status'.format(os.getpid()))
        output = f.read()
        f.close()
    except Exception:
        return None

    match = VM_RSS_REGEXP.search(output)
    if match:
        return int(float(match.group(1)))

    return None


def read_vm_size():
    pid = os.getpid()

    output = None
    try:
        f = open('/proc/{0}/status'.format(os.getpid()))
        output = f.read()
        f.close()
    except Exception:
        return None

    match = VM_SIZE_REGEXP.search(output)
    if match:
        return int(float(match.group(1)))

    return None


def patch(obj, func_name, before_func, after_func):
    if not hasattr(obj, func_name):
        return False
    
    target_func = getattr(obj, func_name)

    # already patched
    if hasattr(target_func, '__stackimpact_orig__'):
        return True

    @wraps(target_func)
    def wrapper(*args, **kwargs):
        data = None

        if before_func:
            args, kwargs, data = before_func(args, kwargs)

        ret = target_func(*args, **kwargs)

        if after_func:
            after_func(args, kwargs, ret, data)

        return ret

    wrapper.__orig__ = target_func
    setattr(obj, func_name, wrapper)

    return True


def unpatch(obj, func_name):
    if not hasattr(obj, func_name):
        return

    wrapper = getattr(obj, func_name)
    if not hasattr(wrapper, '__stackimpact_orig__'):
        return

    setattr(obj, func_name, getattr(wrapper, '__stackimpact_orig__'))


def register_signal(signal_number, handler_func, once=False):
    prev_handler = None

    def _handler(signum, frame):
        skip_prev = handler_func(signum, frame)

        if not skip_prev:
            if callable(prev_handler):
                if once:
                    signal.signal(signum, prev_handler)
                prev_handler(signum, frame)
            elif prev_handler == signal.SIG_DFL and once:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)

    prev_handler = signal.signal(signal_number, _handler)
    
