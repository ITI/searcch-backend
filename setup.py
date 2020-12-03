#!/usr/bin/env python

import setuptools
import os.path
import sys

version = "0.1.0"

if __name__ == "__main__":
    here = os.path.abspath(os.path.dirname(__file__))

    setuptools.setup(
        name="searcch-backend",
        version=version,
        author="Hardik Mahipal Surana",
        author_email="hardiksurana01@gmail.com",
        url="https://github.com/ITI/searcch-backend",
        description="A Python flask SEARCCH API service.",
        long_description="",
        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Environment :: Other Environment",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Topic :: Utilities",
        ],
        keywords="searcch",
        packages=setuptools.find_packages()
    )
