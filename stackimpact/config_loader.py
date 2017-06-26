from .api_request import APIRequest


class ConfigLoader:
    def __init__(self, agent):
        self.agent = agent
        self.load_timer = None


    def start(self):
        self.load_timer = self.agent.schedule(2, 120, self.load)


    def destroy(self):
        if self.load_timer:
            self.load_timer.cancel()
            self.load_timer = None


    def load(self):
        try:
            api_request = APIRequest(self.agent)
            config = api_request.post('config', {})

            # profiling_enabled yes|no
            if 'profiling_disabled' in config:
                self.agent.config.set_profiling_disabled(config['profiling_disabled'] == 'yes')
            else:
                self.agent.config.set_profiling_disabled(False)

        except Exception:
            self.agent.log('Error loading config')
            self.agent.exception()
