
import threading
import collections
import signal



class Sampler(object):
   def __init__(self, interval=0.001):
        self.stack_counts = collections.defaultdict(int)
        self.interval = 0.001

    def _sample(self, signum, frame):
        stack = []
        while frame is not None:
            formatted_frame = '{}({})'.format(frame.f_code.co_name,
                                              frame.f_globals.get('__name__'))
            stack.append(formatted_frame)
            frame = frame.f_back

        formatted_stack = ';'.join(reversed(stack))
        self.stack_counts[formatted_stack] += 1
        signal.setitimer(signal.ITIMER_PROF, self.interval, 0)

    def start(self):
        signal.signal(signal.SIGPROF, self._sample)


    