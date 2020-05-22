"""
    CLI
    ===

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .shell import GatewayShell
from .cli_starter import start_cli

__all__ = ["GatewayShell", "start_cli"]
