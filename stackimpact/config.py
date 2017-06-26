import threading

class Config:
    def __init__(self, agent):
        self.agent = agent
        self.profiling_disabled = False
        self.config_lock = threading.Lock()

    def set_profiling_disabled(self, val):
        with self.config_lock:
            self.profiling_disabled = val
    
    def is_profiling_disabled(self):
        with self.config_lock:
            val = self.profiling_disabled
            return val

