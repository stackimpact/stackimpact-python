from __future__ import print_function
import stackimpact
import random
import threading
import time     
import signal

agent = stackimpact.start(
    agent_key = 'agent key here',
    app_name = 'LambdaDemoPython',
    app_environment = 'prod',
    block_profiler_disabled = True)


def simulate_cpu_work():
    for j in range(0, 100000):
        random.randint(1, 1000000)

mem = []
def simulate_mem_leak():
   for i in range(0, 1000):
        obj = {'v': random.randint(0, 1000000)}
        mem.append(obj)

def handler(event, context):
    span = agent.profile()

    simulate_cpu_work()
    simulate_mem_leak()

    span.stop()
    
    response = {
        "statusCode": 200,
        "body": 'Done'
    }

    return response


