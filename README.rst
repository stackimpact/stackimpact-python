StackImpact Python Agent
========================

Overview
--------

StackImpact is a performance profiler for production applications. It
gives developers continuous and historical view of application
performance with line-of-code precision, which includes CPU, memory
allocation and blocking call hot spots as well as execution bottlenecks,
errors and runtime metrics. Learn more at
`stackimpact.com <https://stackimpact.com/>`__.

.. figure:: https://stackimpact.com/wp-content/uploads/2017/06/hotspots-cpu-1.4-python.png
   :alt: dashboard

   dashboard

Features
^^^^^^^^

-  Automatic hot spot profiling for CPU, memory allocations, blocking
   calls
-  Automatic bottleneck tracing for HTTP handlers and other libraries
-  Exception monitoring
-  Health monitoring including CPU, memory, garbage collection and other
   runtime metrics
-  Anomaly alerts on most important metrics
-  Multiple account users for team collaboration

Learn more on the `features <https://stackimpact.com/features/>`__ page
(with screenshots).

Documentation
^^^^^^^^^^^^^

See full `documentation <https://stackimpact.com/docs/>`__ for
reference.

Supported environment
---------------------

-  Linux, OS X or Windows. Python version 2.7, 3.4 or higher.
-  Memory allocation profiler and some GC metrics are only available for
   Python 3.
-  Profilers only support Linux and OS X.
-  Time (blocking call) profiler supports threads and gevent.
-  On unix systems the profilers use the following signals: SIGPROF,
   SIGALRM, SIGUSR2. Only SIGUSR2 is handled transparently, i.e. it
   should not conflict with previousely registered handlers.

Getting started
---------------

Create StackImpact account
^^^^^^^^^^^^^^^^^^^^^^^^^^

`Sign up <https://dashboard.stackimpact.com/#/signup>`__ for a free
account (also with GitHub login).

Installing the agent
^^^^^^^^^^^^^^^^^^^^

Install the Python agent by running

::

    pip install stackimpact

And import the package in your application

.. code:: python

    import stackimpact

Configuring the agent
^^^^^^^^^^^^^^^^^^^^^

Start the agent in the main thread by specifying the agent key and
application name. The agent key can be found in your account's
Configuration section.

.. code:: python

    agent = stackimpact.start(
        agent_key = 'agent key here',
        app_name = 'MyPythonApp')

Add the agent initialization to the worker code, e.g. wsgi.py, if
applicable.

All initialization options:

-  ``agent_key`` (Required) The access key for communication with the
   StackImpact servers.
-  ``app_name`` (Required) A name to identify and group application
   data. Typically, a single codebase, deployable unit or executable
   module corresponds to one application.
-  ``app_version`` (Optional) Sets application version, which can be
   used to associate profiling information with the source code release.
-  ``app_environment`` (Optional) Used to differentiate applications in
   different environments.
-  ``host_name`` (Optional) By default, host name will be the OS
   hostname.
-  ``debug`` (Optional) Enables debug logging.
-  ``cpu_profiler_disabled``, ``allocation_profiler_disabled``,
   ``block_profiler_disabled``, ``error_profiler_disabled`` (Optional)
   Disables respective profiler when ``True``.
-  ``include_agent_frames``, ``include_system_frames`` (Optional) Set to
   ``True`` to not exclude agent and/or system stack frames from
   profiles.
-  ``auto_destroy`` (Optional) Set to ``False`` to disable agent's exit
   handlers. If necessary, call ``destroy()`` to gracefully shutdown the
   agent.

Analyzing performance data in the Dashboard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once your application is restarted, you can start observing continuous
CPU, memory, I/O, and other hot spot profiles, execution bottlenecks as
well as process metrics in the
`Dashboard <https://dashboard.stackimpact.com/>`__.

Troubleshooting
^^^^^^^^^^^^^^^

To enable debug logging, add ``debug = True`` to startup options. If the
debug log doesn't give you any hints on how to fix a problem, please
report it to our support team in your account's Support section.

Overhead
--------

The agent overhead is measured to be less than 1% for applications under
high load.
