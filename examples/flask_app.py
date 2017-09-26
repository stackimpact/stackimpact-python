#env AGENT_KEY=agnetkeyhere FLASK_APP=examples/flask_app.py flask run -p 5010

from __future__ import print_function

import os
import time
import sys
import threading
import subprocess
import collections
import random
import traceback
from flask import Flask


try:
    # python 2
    from urllib2 import urlopen
except ImportError:
    # python 3
    from urllib.request import urlopen

sys.path.append(".")
import stackimpact



# StackImpact agent initialization
agent = stackimpact.start(
    agent_key = os.environ['AGENT_KEY'],
    dashboard_address = os.environ['DASHBOARD_ADDRESS'],
    app_name = 'ExamplePythonFlaskApp',
    app_version = '1.0.0',
    debug = True)



# Simulate CPU intensive work
def simulate_cpu():
    duration = 10 * 60 * 60
    usage = 20

    while True:
        for j in range(0, duration):
            for i in range(0, usage * 20000):
                text = "text1" + str(i)
                text = text + "text2"

            time.sleep(1 - usage/100)

t = threading.Thread(target=simulate_cpu)
t.start()


# Simulate memory leak
def simulate_mem_leak():
    while True:
        mem1 = []

        for j in range(0, 1800):
            mem2 = []
            for i in range(0, 1000):
                obj1 = {'v': random.randint(0, 1000000)}
                mem1.append(obj1)

                obj2 = {'v': random.randint(0, 1000000)}
                mem2.append(obj2)

            time.sleep(1)

t = threading.Thread(target=simulate_mem_leak)
t.start()


# Simulate lock
def simulate_lock():
    lock = threading.Lock()

    def lock_wait():
        lock.acquire()
        lock.release()

    while True:
            lock.acquire()
        
            t = threading.Thread(target=lock_wait)
            t.start()

            time.sleep(1)

            lock.release()

            time.sleep(1)

t = threading.Thread(target=simulate_lock)
t.start()


# Simulate exceptions
def simulate_exceptions():
    while True:
        try:
            raise ValueError('some error')
        except:
            traceback.print_exc()
            pass

        time.sleep(2)


t = threading.Thread(target=simulate_exceptions)
t.start()


# Simulate http server
def simulate_http_traffic():
    while True:
        try:
            urlopen('http://localhost:5010', timeout=10)
            time.sleep(2)
        except:
            traceback.print_exc()
            pass


t = threading.Thread(target=simulate_http_traffic)
t.start()


def cpu_work():
    for i in range(0, 1000000):
        text = "text1" + str(i)
        text = text + "text2"


app = Flask(__name__)

@app.route('/')
def hello_world():
    time.sleep(0.5)

    cpu_work()

    return 'Hello'


