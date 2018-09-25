import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'stackimpact',
    version = '1.2.4',
    description = 'StackImpact Python Profiler',
    long_description = read('README.rst'),
    author = 'StackImpact',
    author_email = 'devops@stackimpact.com',
    url = 'https://stackimpact.com',
    license = 'BSD',
    keywords = [
        "cpu profiler",
        "memory profiler",
        "blocking call profiler"
        "error monitoring"
        "health metrics"
        "garbage collection metrics"
    ],
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
        'Topic :: System :: Monitoring',
    ],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    packages = find_packages(exclude=[
        'examples.*', 'examples',
        'test.*', 'test'])
)
