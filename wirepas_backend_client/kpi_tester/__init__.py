"""
    TEST
    ====

    The test module contains a simple interface to control the execution
    of multiple tasks.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .kpi_mesh import start_kpi_tester
from .manager import TestManager

__all__ = ["TestManager", "start_kpi_tester"]
