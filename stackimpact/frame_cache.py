
import threading
import os
import re
import importlib

from .runtime import runtime_info

if runtime_info.GEVENT:
    import gevent

class FrameCache(object):
    MAX_CACHE_SIZE = 2500

    def __init__(self, agent):
        self.agent = agent
        self.agent_frame_cache = None
        self.system_frame_cache = None

        self.include_agent_frames = None
        self.include_system_frames = None

        self.agent_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_dir = os.path.dirname(os.path.realpath(threading.__file__))
        if runtime_info.GEVENT:
            self.gevent_dir = os.path.dirname(os.path.realpath(gevent.__file__))


    def start(self):
        self.agent_frame_cache = dict()
        self.system_frame_cache = dict()

        self.include_agent_frames = self.agent.get_option('include_agent_frames')
        self.include_system_frames = self.agent.get_option('include_system_frames')

    def stop(self):
        pass


    def is_agent_frame(self, filename):
        if filename in self.agent_frame_cache:
            return self.agent_frame_cache[filename]

        agent_frame = False

        if not self.include_agent_frames:
            if filename.startswith(self.agent_dir):
                agent_frame = True

        if len(self.agent_frame_cache) < self.MAX_CACHE_SIZE:
            self.agent_frame_cache[filename] = agent_frame

        return agent_frame


    def is_system_frame(self, filename):
        if filename in self.system_frame_cache:
            return self.system_frame_cache[filename]

        system_frame = False

        if not self.include_system_frames:
            if (filename.startswith(self.system_dir) or
                    (runtime_info.GEVENT and filename.startswith(self.gevent_dir))):
                system_frame = True

        if len(self.system_frame_cache) < self.MAX_CACHE_SIZE:
            self.system_frame_cache[filename] = system_frame

        return system_frame
