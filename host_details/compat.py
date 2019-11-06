"""Copyright Placeholder"""
# pylint: skip-file

import sys

if sys.version < 3.7:
    import importlib_resources as pkg_resources
else:
    import importlib.resources as pkg_resources

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
