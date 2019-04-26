"""
    NeighborDiagnostics
    ===================

    Contains helpers to translate network data into NeighborDiagnostics objects used
    within the library and test framework.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import datetime
import logging
import struct
import binascii
import json

from .types import ApplicationTypes
from .generic import GenericMessage

from .. import tools


class NeighborDiagnosticsMessage(GenericMessage):
    """
    NeighborDiagnosticsMessage

    Represents neighbor diagnostics report message sent by nodes.

    Message content:
        neighbor[0..]
            address          uint24
            cluster_channel  uint8
            radio_power      uint8
            node_info        uint8
            rssi             uint8
    """

    def __init__(self, *args, **kwargs) -> "NeighborDiagnosticsMessage":
        super(NeighborDiagnosticsMessage, self).__init__(*args, **kwargs)

        self.type = ApplicationTypes.NeighborDiagnosticsMessage

        if isinstance(self.data_payload, str):
            self.data_payload = bytes(self.data_payload, "utf8")

        self.neighbor = dict()
        s_address = struct.Struct("<I")
        i = 0
        j = 0
        while j < len(self.data_payload):
            address = s_address.unpack(self.data_payload[j : j + 3] + b"\x00")[
                0
            ]
            if address != 0:
                self.neighbor[i] = dict()
                self.neighbor[i]["address"] = address
                self.neighbor[i]["cluster_channel"] = self.data_payload[j + 3]
                self.neighbor[i]["radio_power"] = self.data_payload[j + 4]
                self.neighbor[i]["node_info"] = self.data_payload[j + 5]
                self.neighbor[i]["rssi"] = self.data_payload[j + 6]
                i += 1
                j += 7
            else:
                break
