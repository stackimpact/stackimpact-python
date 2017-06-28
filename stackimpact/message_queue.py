import sys
import threading
import copy

from .api_request import APIRequest
from .utils import timestamp, base64_encode


class MessageQueue:
    MESSAGE_TTL = 10 * 60

    def __init__(self, agent):
        self.agent = agent
        self.queue = []
        self.queue_lock = threading.Lock()
        self.flush_timer = None
        self.expire_timer = None
        self.backoff_seconds = 0
        self.last_flush_ts = 0


    def start(self):
        self.expire_timer = self.agent.schedule(60, 60, self.expire)
        self.flush_timer = self.agent.schedule(5, 5, self.flush)


    def destroy(self):
        if self.flush_timer:
            self.flush_timer.cancel()
            self.flush_timer = None

        if self.expire_timer:
            self.expire_timer.cancel()
            self.expire_timer = None


    def add(self, topic, message):
        m = {
            'topic': topic,
            'content': message,
            'added_at': timestamp()
        }

        with self.queue_lock:
            self.queue.append(m)

        self.agent.log('Added message to the queue for topic: ' + topic)
        self.agent.log(message)


    def expire(self):
        if len(self.queue) == 0:
            return

        now = timestamp()

        # expire and copy messages
        with self.queue_lock:
            self.queue = [m for m in self.queue if m['added_at'] >= now - self.MESSAGE_TTL]
    

    def flush(self):
        if len(self.queue) == 0:
            return

        now = timestamp()

        # flush only if backoff time is elapsed
        if self.last_flush_ts + self.backoff_seconds > now:
            return

        # read queue
        outgoing = None
        with self.queue_lock:
            outgoing = self.queue
            self.queue = []

        # remove added_at
        outgoing_copy = copy.deepcopy(outgoing)
        for m in outgoing_copy:
            del m['added_at']

        payload = {
            'messages': outgoing_copy
        }

        self.last_flush_ts = timestamp()

        try:
            api_request = APIRequest(self.agent)
            api_request.post('upload', payload)

            # reset backoff
            self.backoff_seconds = 0
        except Exception:
            self.agent.log('Error uploading messages to dashboard, backing off next upload')
            self.agent.exception()

            self.queue_lock.acquire()
            self.queue[:0] = outgoing
            self.queue_lock.release()

            # increase backoff up to 1 minute
            if self.backoff_seconds == 0:
                self.backoff_seconds = 10
            elif self.backoff_seconds * 2 < 60:
                self.backoff_seconds *= 2

