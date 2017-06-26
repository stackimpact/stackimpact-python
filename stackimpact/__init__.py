from __future__ import division, print_function, absolute_import

from .agent import Agent

_agent = None

def start(**kwargs):
    global _agent
    
    if not _agent:
        _agent = Agent()

    _agent.start(**kwargs)
    return _agent
