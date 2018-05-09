import threading

class Config(object):
    def __init__(self, agent):
        self.agent = agent
        self.agent_enabled = False
        self.profiling_disabled = False
        self.config_lock = threading.Lock()


    def set_agent_enabled(self, val):
        with self.config_lock:
            self.agent_enabled = val
    
    def is_agent_enabled(self):
        with self.config_lock:
            val = self.agent_enabled
            return val

    def set_profiling_disabled(self, val):
        with self.config_lock:
            self.profiling_disabled = val
    
    def is_profiling_disabled(self):
        with self.config_lock:
            val = self.profiling_disabled
            return val

