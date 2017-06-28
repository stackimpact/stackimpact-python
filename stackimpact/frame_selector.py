
import threading
import os
import re
import importlib

from .runtime import runtime_info

if runtime_info.GEVENT:
    import gevent

class FrameSelector:
    MAX_CACHE_SIZE = 2500

    def __init__(self, agent):
        self.agent = agent
        self.agent_frame_cache = None
        self.system_frame_cache = None
        self.http_frame_cache = None

        self.include_agent_frames = None
        self.include_system_frames = None

        self.http_frame_regexp = None

        self.agent_dir = os.path.dirname(os.path.realpath(__file__))
        self.system_dir = os.path.dirname(os.path.realpath(threading.__file__))
        if runtime_info.GEVENT:
            self.gevent_dir = os.path.dirname(os.path.realpath(gevent.__file__))


    def add_http_package(self, name):
        try:
            m = importlib.import_module(name)
            if m and m.__file__:
                self.add_http_frame_regexp(os.path.dirname(os.path.realpath(m.__file__)))
        except Exception:
            pass


    def add_http_frame_regexp(self, regexp_str):
        self.http_frame_regexp.append(re.compile(regexp_str, re.IGNORECASE))


    def start(self):
        self.agent_frame_cache = dict()
        self.system_frame_cache = dict()
        self.http_frame_cache = dict()

        self.include_agent_frames = self.agent.get_option('include_agent_frames')
        self.include_system_frames = self.agent.get_option('include_system_frames')

        self.http_frame_regexp = []
        self.add_http_package('gunicorn')
        self.add_http_package('waitress')
        self.add_http_package('werkzeug')
        self.add_http_package('flask')
        self.add_http_package('django')
        self.add_http_package('pyramid')
        self.add_http_package('cherrypy')
        self.add_http_package('tornado')
        self.add_http_package('web2py')
        self.add_http_package('bottle')


    def destroy(self):
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


    def is_http_frame(self, filename):
        if filename in self.http_frame_cache:
            return self.http_frame_cache[filename]

        http_frame = False

        for r in self.http_frame_regexp:
            if r.search(filename):
                http_frame = True
                break

        if len(self.http_frame_cache) < self.MAX_CACHE_SIZE:
            self.http_frame_cache[filename] = http_frame

        return http_frame

