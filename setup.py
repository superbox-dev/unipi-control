import os
import sys

from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

setup(install_requires=requirements)
