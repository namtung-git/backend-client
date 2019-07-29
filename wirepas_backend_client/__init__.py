"""
    WIREPAS_BACKEND_CLIENT
    ======================

    A package to interface with Wirepas Backend Services, meant for
    testing, cloud to cloud integration and R&D.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
from . import api
from . import management
from . import messages
from . import test

__all__ = ["api", "management", "messages", "test"]
