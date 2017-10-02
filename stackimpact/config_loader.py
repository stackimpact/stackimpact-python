from .api_request import APIRequest


class ConfigLoader:
    def __init__(self, agent):
        self.agent = agent
        self.load_timer = None


    def start(self):
        self.load_timer = self.agent.schedule(2, 120, self.load)


    def stop(self):
        if self.load_timer:
            self.load_timer.cancel()
            self.load_timer = None


    def load(self):
        try:
            api_request = APIRequest(self.agent)
            config = api_request.post('config', {})

            # agent_enabled yes|no
            if 'agent_enabled' in config:
                self.agent.config.set_agent_enabled(config['agent_enabled'] == 'yes')
            else:
                self.agent.config.set_agent_enabled(False)

            # profiling_disabled yes|no
            if 'profiling_disabled' in config:
                self.agent.config.set_profiling_disabled(config['profiling_disabled'] == 'yes')
            else:
                self.agent.config.set_profiling_disabled(False)


            if self.agent.config.is_agent_enabled() and not self.agent.config.is_profiling_disabled():        
                self.agent.cpu_reporter.start()
                self.agent.allocation_reporter.start()
                self.agent.block_reporter.start()
            else:
                self.agent.cpu_reporter.stop()
                self.agent.allocation_reporter.stop()
                self.agent.block_reporter.stop()

            if self.agent.config.is_agent_enabled():        
                self.agent.error_reporter.start()
                self.agent.process_reporter.start()
                self.agent.log('Agent activated')
            else:
                self.agent.error_reporter.stop()
                self.agent.process_reporter.stop()
                self.agent.log('Agent deactivated')


        except Exception:
            self.agent.log('Error loading config')
            self.agent.exception()
