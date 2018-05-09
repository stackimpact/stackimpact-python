from __future__ import print_function
import random
import time     
import sys
import threading
import tensorflow as tf
sys.path.append(".")
import stackimpact


agent = stackimpact.start(
    agent_key = 'agent key here',
    app_name = 'MyTensorFlowScript')


def handle_some_event():
	with agent.profile():
		tf.reset_default_graph()
		x = tf.random_normal([1000, 1000])
		y = tf.random_normal([1000, 1000])
		res = tf.matmul(x, y)

		with tf.Session() as sess:
		    sess.run(res)


# Simulate events
while True:
    handle_some_event()
    time.sleep(2)


