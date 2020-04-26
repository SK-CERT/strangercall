#!/usr/bin/env python3

from setuptools import setup, find_packages
from os import path


def readme():
    with open('README.md') as f:
        return f.read()


def requirements():
    root = path.dirname(path.realpath(__file__))
    requirementPath = root + '/requires.txt'

    if path.isfile(requirementPath):
        with open(requirementPath) as f:
            return f.read().splitlines()


if __name__ == '__main__':
    setup(
        name='callstranger_honeypot',
        long_description=readme(),
        classifiers=[
            'Programming Language :: Python :: 3'
        ],
        packages=find_packages(),
        install_requires=requirements(),
        entry_points={
            'console_scripts': [
                'hon_upnp = honeypot.hon_upnp:main',
                'hon_ssdp = honeypot.hon_ssdp:main',
                'upnp_sniff = honeypot.upnp_sniff:main'
            ],
        }
    )
