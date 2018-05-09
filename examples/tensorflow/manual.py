from __future__ import print_function
import sys
import tensorflow as tf
sys.path.append(".")
import stackimpact


agent = stackimpact.start(
    agent_key = 'agent key here',
    app_name = 'MyTensorFlowScript',
    auto_profiling = False)

agent.start_tf_profiler()

x = tf.random_normal([1000, 1000])
y = tf.random_normal([1000, 1000])
res = tf.matmul(x, y)

with tf.Session() as sess:
    sess.run(res)


agent.stop_tf_profiler()
