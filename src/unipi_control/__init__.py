import os
import sys
from .version import __version__  # noqa

# https://stackoverflow.com/questions/16981921/relative-imports-in-python-3
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
