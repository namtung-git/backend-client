"""

    MySQL
    =====

    This module contains classes to interface with a MySQL database
    which follows deprecated APIs from previous iteration of Wirepas
    services.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# flake8: noqa

from .connectors import MySQL
from .handlers import MySQLObserver
from .settings import MySQLSettings

__all__ = ["MySQLSettings", "MySQLObserver", "MySQL"]
