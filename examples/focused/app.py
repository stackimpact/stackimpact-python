from __future__ import print_function
import random
import time     
import sys
import threading
sys.path.append(".")
import stackimpact

agent = stackimpact.start(
    agent_key = 'agent key here',
    app_name = 'MyPythonApp')


def simulate_cpu_work():
    for j in range(0, 100000):
        random.randint(1, 1000000)


def handle_some_event():
    span = agent.profile('some event')

    simulate_cpu_work()

    span.stop()
    
    response = {
        "statusCode": 200,
        "body": 'Done'
    }

    return response


# Simulate events
while True:
    handle_some_event()
    time.sleep(2)

