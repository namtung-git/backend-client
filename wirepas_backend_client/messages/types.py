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

    GenericMessage = 0
    AdvertiserMessage = 1
    BootDiagnosticsMessage = 2
    NeighborDiagnosticsMessage = 3
    NeighborScanMessage = 4
    NodeDiagnosticsMessage = 5
    TestNWMessage = 6
    TrafficDiagnosticsMessage = 7
    Ruuvi = 100
