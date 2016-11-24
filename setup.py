#!/usr/bin/env python

from setuptools import setup

setup(
    name='aioproxy',
    version='0.0.2',
    description='reverse proxy with aiohttp',
    author='Pete Wildsmith',
    author_email='pete@weargoggles.co.uk',
    url='https://github.com/weargoggles/aioproxy',
    py_modules=['aioproxy'],
    install_requires=['aiohttp<0.23'],
    test_suite='nose.collector',
    tests_require=['nose'],
)
