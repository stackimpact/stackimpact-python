from __future__ import print_function
import random
import time     
import sys
import threading
sys.path.append(".")
import stackimpact

agent = stackimpact.start(
    agent_key = 'agent key here',
    app_name = 'MyPythonApp',
    auto_profiling = False)


agent.start_cpu_profiler()

for j in range(0, 1000000):
    random.randint(1, 1000000)

agent.stop_cpu_profiler()


'''
agent.start_allocation_profiler()

mem1 = []
for i in range(0, 1000):
    obj1 = {'v': random.randint(0, 1000000)}
    mem1.append(obj1)

agent.stop_allocation_profiler()
'''


'''
agent.start_block_profiler()

def blocking_call():
    time.sleep(0.1)

for i in range(5):
    blocking_call()

agent.stop_block_profiler()
'''