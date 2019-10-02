"""
    Types
    =====

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import enum


class ApplicationTypes(enum.Enum):
    """ ApplicationTypes defines the library's message types mapping """

    GenericMessage = enum.auto()
    AdvertiserMessage = enum.auto()
    BootDiagnosticsMessage = enum.auto()
    NeighborDiagnosticsMessage = enum.auto()
    NeighborScanMessage = enum.auto()
    NodeDiagnosticsMessage = enum.auto()
    TestNWMessage = enum.auto()
    TrafficDiagnosticsMessage = enum.auto()
    DiagnosticsMessage = enum.auto()
    PositioningMessage = enum.auto()
    Ruuvi = enum.auto()
