"""
    CLI
    ===

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .shell import GatewayShell
from .__main__ import main as cli_main

__all__ = ["GatewayShell", "cli_main"]
