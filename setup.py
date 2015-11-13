#!/usr/bin/env python

from setuptools import setup

setup(
    name='aioproxy',
    version='0.0.1',
    description='reverse proxy with aiohttp',
    author='Pete Wildsmith',
    author_email='pete@weargoggles.co.uk',
    url='https://github.com/weargoggles/aioproxy',
    py_modules=['aioproxy'],
    requires=['aiohttp'],
    test_suite='nose.collector',
    tests_require=['nose'],
)
